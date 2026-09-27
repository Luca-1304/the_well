"""Independent low-order cross-check for the 3D periodic baseline.

This solver intentionally does not share the pseudospectral nonlinear or
viscous operators. It uses second-order periodic finite differences with an
FFT pressure projection and Heun/RK2 time integration. It is a validation
cross-check, not the primary production solver.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import torch
from torch import Tensor

from .solver3d import SpectralSimulationConfig


@dataclass(frozen=True)
class FiniteDifferenceRecord:
    step: int
    time: float
    kinetic_energy: float
    max_vorticity: float
    divergence_residual: float


class PeriodicFiniteDifferenceNavierStokes3D:
    """Second-order finite-difference periodic incompressible cross-check."""

    def __init__(
        self,
        config: SpectralSimulationConfig,
        *,
        device: torch.device | str = "cpu",
        dtype: torch.dtype = torch.float64,
    ) -> None:
        config.validate()
        if config.controller_enabled:
            raise ValueError(
                "finite-difference cross-check currently supports uncontrolled runs only"
            )
        if config.boundary.environmental_strength != 0.0:
            raise ValueError(
                "finite-difference cross-check currently requires zero environment forcing"
            )

        self.config = config
        self.device = torch.device(device)
        self.dtype = dtype
        n = config.grid_size
        self.dx = config.domain_length / n

        axis = torch.arange(n, dtype=dtype, device=self.device) * self.dx
        self.x, self.y, self.z = torch.meshgrid(axis, axis, axis, indexing="ij")

        frequency = torch.fft.fftfreq(n, d=self.dx, device=self.device) * (
            2.0 * math.pi
        )
        frequency = frequency.to(dtype)
        self.kx, self.ky, self.kz = torch.meshgrid(
            frequency, frequency, frequency, indexing="ij"
        )
        self.k_squared = self.kx**2 + self.ky**2 + self.kz**2

        self.qx = torch.sin(self.kx * self.dx) / self.dx
        self.qy = torch.sin(self.ky * self.dx) / self.dx
        self.qz = torch.sin(self.kz * self.dx) / self.dx
        self.q_squared = self.qx**2 + self.qy**2 + self.qz**2
        self.nonzero_q_squared = torch.where(
            self.q_squared == 0,
            torch.ones_like(self.q_squared),
            self.q_squared,
        )

    def taylor_green_initial_velocity(self, amplitude: float = 1.0) -> Tensor:
        if not math.isfinite(amplitude):
            raise ValueError("amplitude must be finite")
        scale = 2.0 * math.pi / self.config.domain_length
        px = scale * self.x
        py = scale * self.y
        pz = scale * self.z
        u = amplitude * torch.sin(px) * torch.cos(py) * torch.cos(pz)
        v = -amplitude * torch.cos(px) * torch.sin(py) * torch.cos(pz)
        w = torch.zeros_like(u)
        return torch.stack((u, v, w), dim=-1)

    def derivative(self, field: Tensor, axis: int) -> Tensor:
        return (
            torch.roll(field, shifts=-1, dims=axis)
            - torch.roll(field, shifts=1, dims=axis)
        ) / (2.0 * self.dx)

    def laplacian(self, field: Tensor) -> Tensor:
        result = torch.zeros_like(field)
        for axis in range(3):
            result = result + (
                torch.roll(field, shifts=-1, dims=axis)
                - 2.0 * field
                + torch.roll(field, shifts=1, dims=axis)
            ) / (self.dx**2)
        return result

    def project(self, velocity: Tensor) -> Tensor:
        velocity_hat = torch.fft.fftn(velocity, dim=(0, 1, 2))
        q_dot_u = (
            self.qx * velocity_hat[..., 0]
            + self.qy * velocity_hat[..., 1]
            + self.qz * velocity_hat[..., 2]
        )
        velocity_hat[..., 0] -= self.qx * q_dot_u / self.nonzero_q_squared
        velocity_hat[..., 1] -= self.qy * q_dot_u / self.nonzero_q_squared
        velocity_hat[..., 2] -= self.qz * q_dot_u / self.nonzero_q_squared
        return torch.fft.ifftn(velocity_hat, dim=(0, 1, 2)).real

    def divergence_linf(self, velocity: Tensor) -> float:
        divergence = (
            self.derivative(velocity[..., 0], 0)
            + self.derivative(velocity[..., 1], 1)
            + self.derivative(velocity[..., 2], 2)
        )
        return float(divergence.abs().amax().detach().cpu())

    def vorticity(self, velocity: Tensor) -> Tensor:
        omega_x = self.derivative(velocity[..., 2], 1) - self.derivative(
            velocity[..., 1], 2
        )
        omega_y = self.derivative(velocity[..., 0], 2) - self.derivative(
            velocity[..., 2], 0
        )
        omega_z = self.derivative(velocity[..., 1], 0) - self.derivative(
            velocity[..., 0], 1
        )
        return torch.stack((omega_x, omega_y, omega_z), dim=-1)

    def rhs(self, velocity: Tensor) -> Tensor:
        gradients = [
            [self.derivative(velocity[..., component], axis) for axis in range(3)]
            for component in range(3)
        ]
        convection = torch.stack(
            tuple(
                sum(
                    velocity[..., axis] * gradients[component][axis]
                    for axis in range(3)
                )
                for component in range(3)
            ),
            dim=-1,
        )
        diffusion = self.config.viscosity * self.laplacian(velocity)
        return self.project(-convection + diffusion)

    def stable_time_step(self, velocity: Tensor, remaining: float) -> float:
        max_speed = float(
            torch.linalg.vector_norm(velocity, dim=-1).amax().detach().cpu()
        )
        advective_limit = (
            float("inf")
            if max_speed == 0.0
            else self.config.cfl_safety * self.dx / max_speed
        )
        diffusive_limit = 0.10 * self.dx**2 / self.config.viscosity
        return min(
            self.config.time_step,
            advective_limit,
            diffusive_limit,
            remaining,
        )

    def step(self, velocity: Tensor, dt: float) -> Tensor:
        k1 = self.rhs(velocity)
        predictor = self.project(velocity + dt * k1)
        k2 = self.rhs(predictor)
        return self.project(velocity + 0.5 * dt * (k1 + k2))

    def kinetic_energy(self, velocity: Tensor) -> float:
        cell_volume = self.dx**3
        return float(
            (
                0.5
                * self.config.density
                * (velocity * velocity).sum(dim=-1).sum()
                * cell_volume
            )
            .detach()
            .cpu()
        )

    def run(
        self,
        *,
        amplitude: float = 1.0,
    ) -> tuple[Tensor, list[FiniteDifferenceRecord]]:
        velocity = self.project(self.taylor_green_initial_velocity(amplitude))
        records: list[FiniteDifferenceRecord] = []
        time = 0.0
        step = 0

        while time < self.config.final_time:
            if step >= self.config.max_steps:
                raise RuntimeError("max_steps reached before final_time")
            dt = self.stable_time_step(velocity, self.config.final_time - time)
            velocity = self.step(velocity, dt)
            time += dt
            step += 1

            omega = self.vorticity(velocity)
            records.append(
                FiniteDifferenceRecord(
                    step=step,
                    time=time,
                    kinetic_energy=self.kinetic_energy(velocity),
                    max_vorticity=float(
                        torch.linalg.vector_norm(omega, dim=-1)
                        .amax()
                        .detach()
                        .cpu()
                    ),
                    divergence_residual=self.divergence_linf(velocity),
                )
            )

        return velocity, records
