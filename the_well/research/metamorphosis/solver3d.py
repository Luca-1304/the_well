"""Safety-integrated 3D periodic Navier–Stokes solver.

This is the first conventional time-stepper in the Metamorphosis research
track. It uses a Fourier pseudospectral discretisation, 2/3 de-aliasing,
Leray projection, explicit RK4 time stepping, and optional passive-scalar
transport.

The safety shell is evaluated inside the evolution loop. Loss of numerical or
model credibility reduces the authority of the experimental controller on the
next step. This is a research simulator, not a proof of Navier–Stokes
regularity and not a validated physical actuator model.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import torch
from torch import Tensor

from .controller import ControllerConfig, vorticity_weighted_damping_force
from .metrics import (
    compute_metrics,
    enstrophy_balance_integrals,
    kinetic_energy,
)
from .safety import (
    BoundaryMode,
    BoundaryState,
    OperationalMode,
    SafetyDecision,
    RunManifest,
    SafetyThresholds,
    ScalarInputRecord,
    ValidityGate,
    VerificationScales,
    VerificationState,
    confidence_from_risk,
    configuration_fingerprint,
    detect_model_mismatch,
    evaluate_safety,
    require_validity,
    risk_from_verification,
    validate_input_records,
)


@dataclass(frozen=True)
class SpectralSimulationConfig:
    grid_size: int = 16
    domain_length: float = 2.0 * math.pi
    viscosity: float = 1.0e-2
    scalar_diffusivity: float = 1.0e-3
    density: float = 1.0
    time_step: float = 2.0e-3
    final_time: float = 2.0e-2
    cfl_safety: float = 0.35
    max_steps: int = 10000
    dealias: bool = True
    stop_on_isolate: bool = True
    controller_enabled: bool = False
    controller: ControllerConfig = field(
        default_factory=lambda: ControllerConfig(
            safe_vorticity=10.0,
            proportional_gain=0.1,
            max_control_force=1.0,
        )
    )
    boundary: BoundaryState = field(
        default_factory=lambda: BoundaryState(
            mode=BoundaryMode.CLOSED_STRONG,
            load=0.0,
            capacity=10.0,
            permeability=0.0,
            coupling=1.0,
            environmental_strength=0.0,
        )
    )
    environment_sign: float = 1.0
    environment_component_weights: tuple[float, float, float] = (1.0, 1.0, 1.0)
    controller_sign: float = 1.0
    sensor_vorticity_scale: float = 1.0
    controller_delay_steps: int = 0
    watchdog_divergence_limit: float = 1.0e-6
    watchdog_energy_residual_limit: float = 1.0
    watchdog_min_scalar_mass_fidelity: float = 0.95
    base_uncertainty: float = 0.0
    observation_mismatch: float = 0.0
    domain_distance: float = 0.0
    control_risk: float = 0.0
    external_risk: float = 0.0
    mismatch_threshold: float = 0.5
    safety_thresholds: SafetyThresholds = field(default_factory=SafetyThresholds)
    verification_scales: VerificationScales = field(
        default_factory=lambda: VerificationScales(
            pde_residual=5.0e-2,
            divergence_residual=1.0e-8,
            energy_residual=5.0e-2,
            solver_discrepancy=5.0e-1,
            convergence_error=1.0e-2,
            observation_mismatch=1.0,
            uncertainty=1.0e-1,
            domain_distance=1.0e-1,
        )
    )

    def validate(self) -> None:
        if self.grid_size < 8 or self.grid_size % 2 != 0:
            raise ValueError("grid_size must be an even integer at least 8")
        if self.domain_length <= 0 or not math.isfinite(self.domain_length):
            raise ValueError("domain_length must be finite and positive")
        if self.viscosity <= 0 or not math.isfinite(self.viscosity):
            raise ValueError("viscosity must be finite and positive")
        if self.scalar_diffusivity < 0 or not math.isfinite(self.scalar_diffusivity):
            raise ValueError("scalar_diffusivity must be finite and non-negative")
        if self.density <= 0 or not math.isfinite(self.density):
            raise ValueError("density must be finite and positive")
        if self.time_step <= 0 or not math.isfinite(self.time_step):
            raise ValueError("time_step must be finite and positive")
        if self.final_time <= 0 or not math.isfinite(self.final_time):
            raise ValueError("final_time must be finite and positive")
        if not 0.0 < self.cfl_safety < 1.0:
            raise ValueError("cfl_safety must lie between 0 and 1")
        if self.max_steps <= 0:
            raise ValueError("max_steps must be positive")
        if self.environment_sign not in (-1.0, 1.0):
            raise ValueError("environment_sign must be either -1 or 1")
        if self.controller_sign not in (-1.0, 1.0):
            raise ValueError("controller_sign must be either -1 or 1")
        if (
            len(self.environment_component_weights) != 3
            or any(
                not math.isfinite(value)
                for value in self.environment_component_weights
            )
        ):
            raise ValueError(
                "environment_component_weights must contain three finite values"
            )
        if self.sensor_vorticity_scale <= 0 or not math.isfinite(
            self.sensor_vorticity_scale
        ):
            raise ValueError("sensor_vorticity_scale must be finite and positive")
        if self.controller_delay_steps < 0:
            raise ValueError("controller_delay_steps cannot be negative")
        if self.watchdog_divergence_limit <= 0 or not math.isfinite(
            self.watchdog_divergence_limit
        ):
            raise ValueError(
                "watchdog_divergence_limit must be finite and positive"
            )
        if self.watchdog_energy_residual_limit <= 0 or not math.isfinite(
            self.watchdog_energy_residual_limit
        ):
            raise ValueError(
                "watchdog_energy_residual_limit must be finite and positive"
            )
        if not 0.0 <= self.watchdog_min_scalar_mass_fidelity <= 1.0:
            raise ValueError(
                "watchdog_min_scalar_mass_fidelity must lie between 0 and 1"
            )
        for name, value in {
            "base_uncertainty": self.base_uncertainty,
            "observation_mismatch": self.observation_mismatch,
            "domain_distance": self.domain_distance,
        }.items():
            if value < 0 or not math.isfinite(value):
                raise ValueError(f"{name} must be finite and non-negative")
        for name, value in {
            "control_risk": self.control_risk,
            "external_risk": self.external_risk,
        }.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must lie between 0 and 1")
        if not 0.0 <= self.mismatch_threshold <= 1.0:
            raise ValueError("mismatch_threshold must lie between 0 and 1")
        self.controller.validate()
        self.safety_thresholds.validate()


@dataclass(frozen=True)
class SimulationRecord:
    step: int
    time: float
    time_step: float
    max_velocity_gradient: float
    max_vorticity: float
    kinetic_energy: float
    enstrophy: float
    stretching_production: float
    viscous_enstrophy_dissipation: float
    vortex_stretching_rate: float
    viscous_redistribution_rate: float
    regulation_ratio: float
    divergence_residual: float
    pde_residual: float
    energy_residual: float
    convergence_error: float
    operator_discrepancy: float
    scalar_mass_fidelity: float
    spectral_tail_fraction: float
    boundary_mode: str
    boundary_load: float
    containment_failed: bool
    environmental_influence: float
    control_effort: float
    environmental_power: float
    control_power: float
    viscous_energy_dissipation: float
    energy_power_dominance_ratio: float
    accumulated_overpowering_energy_fraction: float
    enstrophy_dominance_ratio: float
    watchdog_triggered: bool
    watchdog_reasons: tuple[str, ...]
    safety_mode: str
    authority_scale: float
    confidence: float
    trusted_prediction: bool
    model_mismatch: bool


@dataclass
class SpectralState:
    velocity_hat: Tensor
    scalar_hat: Tensor
    time: float = 0.0
    step: int = 0
    authority_scale: float = 1.0
    accumulated_overpowering_energy: float = 0.0


class PeriodicSpectralNavierStokes3D:
    """3D incompressible periodic pseudospectral solver with live safety checks."""

    def __init__(
        self,
        config: SpectralSimulationConfig,
        *,
        device: torch.device | str = "cpu",
        dtype: torch.dtype = torch.float64,
    ) -> None:
        config.validate()
        self.config = config
        self.device = torch.device(device)
        self.dtype = dtype
        self.complex_dtype = (
            torch.complex128 if dtype == torch.float64 else torch.complex64
        )

        n = config.grid_size
        length = config.domain_length
        self.dx = length / n
        self.spacing = (self.dx, self.dx, self.dx)

        axis = torch.arange(n, dtype=dtype, device=self.device) * self.dx
        self.x, self.y, self.z = torch.meshgrid(axis, axis, axis, indexing="ij")

        frequency = torch.fft.fftfreq(n, d=self.dx, device=self.device) * (2.0 * math.pi)
        frequency = frequency.to(dtype)
        self.kx, self.ky, self.kz = torch.meshgrid(
            frequency, frequency, frequency, indexing="ij"
        )
        self.k_squared = self.kx**2 + self.ky**2 + self.kz**2
        self.nonzero_k_squared = torch.where(
            self.k_squared == 0,
            torch.ones_like(self.k_squared),
            self.k_squared,
        )

        integer_modes = torch.fft.fftfreq(n, d=1.0 / n, device=self.device).abs()
        mx, my, mz = torch.meshgrid(
            integer_modes, integer_modes, integer_modes, indexing="ij"
        )
        cutoff = n / 3.0
        self.dealias_mask = (
            (mx <= cutoff) & (my <= cutoff) & (mz <= cutoff)
        ).to(self.device)

    def input_records(self) -> tuple[ScalarInputRecord, ...]:
        return (
            ScalarInputRecord(
                name="domain_length",
                value=self.config.domain_length,
                unit="nondimensional_length",
                uncertainty=0.0,
                source="SpectralSimulationConfig",
            ),
            ScalarInputRecord(
                name="viscosity",
                value=self.config.viscosity,
                unit="nondimensional_kinematic_viscosity",
                uncertainty=0.0,
                source="SpectralSimulationConfig",
            ),
            ScalarInputRecord(
                name="scalar_diffusivity",
                value=self.config.scalar_diffusivity,
                unit="nondimensional_diffusivity",
                uncertainty=0.0,
                source="SpectralSimulationConfig",
            ),
            ScalarInputRecord(
                name="density",
                value=self.config.density,
                unit="nondimensional_density",
                uncertainty=0.0,
                source="SpectralSimulationConfig",
            ),
            ScalarInputRecord(
                name="time_step",
                value=self.config.time_step,
                unit="nondimensional_time",
                uncertainty=0.0,
                source="SpectralSimulationConfig",
            ),
        )

    def configuration_payload(self) -> dict[str, object]:
        return {
            "grid_size": self.config.grid_size,
            "domain_length": self.config.domain_length,
            "viscosity": self.config.viscosity,
            "scalar_diffusivity": self.config.scalar_diffusivity,
            "density": self.config.density,
            "time_step": self.config.time_step,
            "final_time": self.config.final_time,
            "cfl_safety": self.config.cfl_safety,
            "dealias": self.config.dealias,
            "stop_on_isolate": self.config.stop_on_isolate,
            "controller_enabled": self.config.controller_enabled,
            "controller_sign": self.config.controller_sign,
            "sensor_vorticity_scale": self.config.sensor_vorticity_scale,
            "controller_delay_steps": self.config.controller_delay_steps,
            "boundary_mode": self.config.boundary.mode.value,
            "boundary_capacity": self.config.boundary.capacity,
            "boundary_permeability": self.config.boundary.permeability,
            "boundary_coupling": self.config.boundary.coupling,
            "environmental_strength": self.config.boundary.environmental_strength,
            "environment_sign": self.config.environment_sign,
            "environment_component_weights": list(
                self.config.environment_component_weights
            ),
        }

    def run_manifest(self, *, code_version: str = "unverified-working-tree") -> RunManifest:
        manifest = RunManifest(
            code_version=code_version,
            model_version="metamorphosis-3d-spectral-v1",
            initial_condition_id="taylor-green-3d",
            boundary_condition="periodic",
            solver="fourier-pseudospectral-rk4-step-doubling",
            precision=str(self.dtype).replace("torch.", ""),
            grid_shape=(
                self.config.grid_size,
                self.config.grid_size,
                self.config.grid_size,
            ),
            time_step=self.config.time_step,
            random_seed=0,
            configuration_fingerprint=configuration_fingerprint(
                self.configuration_payload()
            ),
        )
        manifest.validate()
        return manifest

    def validity_gate(self) -> ValidityGate:
        try:
            validate_input_records(self.input_records())
            self.run_manifest()
        except ValueError:
            return ValidityGate(
                units_valid=False,
                domain_valid=True,
                inputs_complete=False,
                initial_conditions_valid=True,
                boundary_conditions_valid=True,
                identifiable=True,
            )
        return ValidityGate(
            units_valid=True,
            domain_valid=True,
            inputs_complete=True,
            initial_conditions_valid=True,
            boundary_conditions_valid=True,
            identifiable=True,
        )

    def taylor_green_initial_velocity(self, amplitude: float = 1.0) -> Tensor:
        if not math.isfinite(amplitude):
            raise ValueError("amplitude must be finite")
        scale = 2.0 * math.pi / self.config.domain_length
        phase_x = scale * self.x
        phase_y = scale * self.y
        phase_z = scale * self.z
        u = amplitude * torch.sin(phase_x) * torch.cos(phase_y) * torch.cos(phase_z)
        v = -amplitude * torch.cos(phase_x) * torch.sin(phase_y) * torch.cos(phase_z)
        w = torch.zeros_like(u)
        return torch.stack((u, v, w), dim=-1)

    def centred_marked_scalar(self, width: float = 0.6) -> Tensor:
        if width <= 0 or not math.isfinite(width):
            raise ValueError("width must be finite and positive")
        length = self.config.domain_length
        centre = length / 2.0
        half_length = length / 2.0
        dx = torch.remainder(self.x - centre + half_length, length) - half_length
        dy = torch.remainder(self.y - centre + half_length, length) - half_length
        dz = torch.remainder(self.z - centre + half_length, length) - half_length
        radius_squared = dx**2 + dy**2 + dz**2
        return torch.exp(-radius_squared / (2.0 * width**2))

    def initialise(
        self,
        *,
        amplitude: float = 1.0,
        scalar_width: float = 0.6,
    ) -> SpectralState:
        require_validity(self.validity_gate())
        velocity = self.taylor_green_initial_velocity(amplitude)
        scalar = self.centred_marked_scalar(scalar_width)
        velocity_hat = self.project_velocity_hat(self._fft_vector(velocity))
        velocity_hat = self._apply_dealias(velocity_hat)
        scalar_hat = self._apply_dealias(torch.fft.fftn(scalar, dim=(0, 1, 2)))
        return SpectralState(
            velocity_hat=velocity_hat,
            scalar_hat=scalar_hat,
            authority_scale=self.initial_authority_scale(),
        )

    def initial_authority_scale(self) -> float:
        preflight = VerificationState(
            pde_residual=0.0,
            divergence_residual=0.0,
            energy_residual=0.0,
            solver_discrepancy=0.0,
            convergence_error=0.0,
            observation_mismatch=self.config.observation_mismatch,
            uncertainty=self.config.base_uncertainty,
            domain_distance=self.config.domain_distance,
        )
        risk = risk_from_verification(
            preflight,
            self.config.verification_scales,
            control_risk=self.config.control_risk,
            external_risk=self.config.external_risk,
        )
        mismatch = detect_model_mismatch(
            preflight,
            self.config.verification_scales,
            threshold=self.config.mismatch_threshold,
        )
        return evaluate_safety(
            risk,
            thresholds=self.config.safety_thresholds,
            model_mismatch=mismatch,
        ).authority_scale

    def physical_velocity(self, state: SpectralState) -> Tensor:
        return self._ifft_vector(state.velocity_hat)

    def physical_scalar(self, state: SpectralState) -> Tensor:
        return torch.fft.ifftn(state.scalar_hat, dim=(0, 1, 2)).real

    def _fft_vector(self, field: Tensor) -> Tensor:
        return torch.fft.fftn(field, dim=(0, 1, 2))

    def _ifft_vector(self, field_hat: Tensor) -> Tensor:
        return torch.fft.ifftn(field_hat, dim=(0, 1, 2)).real

    def _apply_dealias(self, field_hat: Tensor) -> Tensor:
        if not self.config.dealias:
            return field_hat
        mask = self.dealias_mask
        while mask.ndim < field_hat.ndim:
            mask = mask.unsqueeze(-1)
        return field_hat * mask

    def project_velocity_hat(self, velocity_hat: Tensor) -> Tensor:
        if velocity_hat.shape[-1] != 3:
            raise ValueError("velocity_hat must have three components")
        k_dot_u = (
            self.kx * velocity_hat[..., 0]
            + self.ky * velocity_hat[..., 1]
            + self.kz * velocity_hat[..., 2]
        )
        projected = velocity_hat.clone()
        projected[..., 0] -= self.kx * k_dot_u / self.nonzero_k_squared
        projected[..., 1] -= self.ky * k_dot_u / self.nonzero_k_squared
        projected[..., 2] -= self.kz * k_dot_u / self.nonzero_k_squared
        return projected

    def divergence_linf_hat(self, velocity_hat: Tensor) -> float:
        divergence_hat = 1j * (
            self.kx * velocity_hat[..., 0]
            + self.ky * velocity_hat[..., 1]
            + self.kz * velocity_hat[..., 2]
        )
        divergence = torch.fft.ifftn(divergence_hat, dim=(0, 1, 2)).real
        return float(divergence.abs().amax().detach().cpu())

    def spectral_vorticity(self, velocity_hat: Tensor) -> Tensor:
        omega_x_hat = 1j * (
            self.ky * velocity_hat[..., 2] - self.kz * velocity_hat[..., 1]
        )
        omega_y_hat = 1j * (
            self.kz * velocity_hat[..., 0] - self.kx * velocity_hat[..., 2]
        )
        omega_z_hat = 1j * (
            self.kx * velocity_hat[..., 1] - self.ky * velocity_hat[..., 0]
        )
        omega_hat = torch.stack((omega_x_hat, omega_y_hat, omega_z_hat), dim=-1)
        return self._ifft_vector(omega_hat)

    def _velocity_gradients(self, velocity_hat: Tensor) -> list[list[Tensor]]:
        wave_numbers = (self.kx, self.ky, self.kz)
        gradients: list[list[Tensor]] = []
        for component in range(3):
            row = []
            for wave_number in wave_numbers:
                derivative_hat = 1j * wave_number * velocity_hat[..., component]
                row.append(
                    torch.fft.ifftn(derivative_hat, dim=(0, 1, 2)).real
                )
            gradients.append(row)
        return gradients

    def environment_force(self, boundary: BoundaryState) -> Tensor:
        amplitude = (
            self.config.environment_sign * boundary.environmental_influence
        )
        scale = 2.0 * math.pi / self.config.domain_length
        weights = self.config.environment_component_weights
        phase_x = scale * self.x
        phase_y = scale * self.y
        phase_z = scale * self.z
        return amplitude * torch.stack(
            (
                weights[0]
                * torch.sin(phase_x)
                * torch.cos(phase_y)
                * torch.cos(phase_z),
                -weights[1]
                * torch.cos(phase_x)
                * torch.sin(phase_y)
                * torch.cos(phase_z),
                weights[2] * torch.sin(phase_x) * torch.sin(phase_y),
            ),
            dim=-1,
        )

    def _dynamic_boundary(self, velocity: Tensor) -> BoundaryState:
        speed_squared = (velocity * velocity).sum(dim=-1)
        load = 0.5 * self.config.density * float(
            speed_squared.amax().detach().cpu()
        )
        boundary = replace(self.config.boundary, load=load)
        if boundary.containment_failed and boundary.mode is not BoundaryMode.OPEN:
            return BoundaryState(
                mode=BoundaryMode.OPEN,
                load=load,
                capacity=boundary.capacity,
                permeability=1.0,
                coupling=boundary.coupling,
                environmental_strength=boundary.environmental_strength,
            )
        return boundary

    def project_physical_vector(self, field: Tensor) -> Tensor:
        projected_hat = self.project_velocity_hat(
            self._apply_dealias(self._fft_vector(field))
        )
        return self._ifft_vector(projected_hat)

    def _forces(
        self,
        velocity: Tensor,
        velocity_hat: Tensor,
        authority_scale: float,
        control_override: Tensor | None = None,
    ) -> tuple[Tensor, Tensor, Tensor, BoundaryState]:
        boundary = self._dynamic_boundary(velocity)
        environmental = self.environment_force(boundary)

        if control_override is not None:
            if control_override.shape != velocity.shape:
                raise ValueError("control_override must match velocity shape")
            control = control_override
        elif self.config.controller_enabled:
            omega = (
                self.config.sensor_vorticity_scale
                * self.spectral_vorticity(velocity_hat)
            )
            control = self.config.controller_sign * vorticity_weighted_damping_force(
                velocity,
                omega,
                self.config.controller,
                authority_scale=authority_scale,
            )
        else:
            control = torch.zeros_like(velocity)

        return control + environmental, control, environmental, boundary

    def _rhs(
        self,
        velocity_hat: Tensor,
        scalar_hat: Tensor,
        authority_scale: float,
        control_override: Tensor | None = None,
    ) -> tuple[Tensor, Tensor]:
        velocity_hat = self.project_velocity_hat(self._apply_dealias(velocity_hat))
        velocity = self._ifft_vector(velocity_hat)
        gradients = self._velocity_gradients(velocity_hat)

        convection = torch.stack(
            (
                velocity[..., 0] * gradients[0][0]
                + velocity[..., 1] * gradients[0][1]
                + velocity[..., 2] * gradients[0][2],
                velocity[..., 0] * gradients[1][0]
                + velocity[..., 1] * gradients[1][1]
                + velocity[..., 2] * gradients[1][2],
                velocity[..., 0] * gradients[2][0]
                + velocity[..., 1] * gradients[2][1]
                + velocity[..., 2] * gradients[2][2],
            ),
            dim=-1,
        )
        nonlinear_hat = self._apply_dealias(self._fft_vector(convection))
        nonlinear_hat = self.project_velocity_hat(nonlinear_hat)

        total_force, _, _, _ = self._forces(
            velocity,
            velocity_hat,
            authority_scale,
            control_override=control_override,
        )
        force_hat = self.project_velocity_hat(
            self._apply_dealias(self._fft_vector(total_force))
        )

        velocity_rhs = (
            -nonlinear_hat
            - self.config.viscosity * self.k_squared.unsqueeze(-1) * velocity_hat
            + force_hat
        )

        scalar = torch.fft.ifftn(scalar_hat, dim=(0, 1, 2)).real
        scalar_gradients = []
        for wave_number in (self.kx, self.ky, self.kz):
            gradient_hat = 1j * wave_number * scalar_hat
            scalar_gradients.append(
                torch.fft.ifftn(gradient_hat, dim=(0, 1, 2)).real
            )
        scalar_advection = (
            velocity[..., 0] * scalar_gradients[0]
            + velocity[..., 1] * scalar_gradients[1]
            + velocity[..., 2] * scalar_gradients[2]
        )
        scalar_rhs = (
            -self._apply_dealias(
                torch.fft.fftn(scalar_advection, dim=(0, 1, 2))
            )
            - self.config.scalar_diffusivity * self.k_squared * scalar_hat
        )
        return velocity_rhs, scalar_rhs

    def _rk4(
        self,
        velocity_hat: Tensor,
        scalar_hat: Tensor,
        dt: float,
        authority_scale: float,
        control_override: Tensor | None = None,
    ) -> tuple[Tensor, Tensor]:
        k1u, k1c = self._rhs(
            velocity_hat,
            scalar_hat,
            authority_scale,
            control_override=control_override,
        )
        k2u, k2c = self._rhs(
            velocity_hat + 0.5 * dt * k1u,
            scalar_hat + 0.5 * dt * k1c,
            authority_scale,
            control_override=control_override,
        )
        k3u, k3c = self._rhs(
            velocity_hat + 0.5 * dt * k2u,
            scalar_hat + 0.5 * dt * k2c,
            authority_scale,
            control_override=control_override,
        )
        k4u, k4c = self._rhs(
            velocity_hat + dt * k3u,
            scalar_hat + dt * k3c,
            authority_scale,
            control_override=control_override,
        )
        next_velocity = velocity_hat + (dt / 6.0) * (
            k1u + 2.0 * k2u + 2.0 * k3u + k4u
        )
        next_scalar = scalar_hat + (dt / 6.0) * (
            k1c + 2.0 * k2c + 2.0 * k3c + k4c
        )
        next_velocity = self.project_velocity_hat(
            self._apply_dealias(next_velocity)
        )
        next_scalar = self._apply_dealias(next_scalar)
        return next_velocity, next_scalar

    def stable_time_step(self, velocity_hat: Tensor, remaining: float) -> float:
        velocity = self._ifft_vector(velocity_hat)
        max_speed = float(
            torch.linalg.vector_norm(velocity, dim=-1).amax().detach().cpu()
        )
        advective_limit = (
            float("inf")
            if max_speed == 0.0
            else self.config.cfl_safety * self.dx / max_speed
        )
        diffusivity = max(self.config.viscosity, self.config.scalar_diffusivity)
        diffusive_limit = (
            float("inf")
            if diffusivity == 0.0
            else 0.15 * self.dx**2 / diffusivity
        )
        return min(
            self.config.time_step,
            advective_limit,
            diffusive_limit,
            remaining,
        )

    def spectral_tail_fraction(self, velocity_hat: Tensor) -> float:
        energy = (velocity_hat.abs() ** 2).sum(dim=-1)
        mode = torch.fft.fftfreq(
            self.config.grid_size,
            d=1.0 / self.config.grid_size,
            device=self.device,
        ).abs()
        mx, my, mz = torch.meshgrid(mode, mode, mode, indexing="ij")
        shell = (
            (mx >= self.config.grid_size / 4.0)
            | (my >= self.config.grid_size / 4.0)
            | (mz >= self.config.grid_size / 4.0)
        )
        total = energy.sum()
        if total <= 0:
            return 0.0
        return float((energy[shell].sum() / total).detach().cpu())

    def _gradient_dissipation(self, velocity_hat: Tensor) -> float:
        gradients = self._velocity_gradients(velocity_hat)
        squared = torch.zeros_like(gradients[0][0])
        for row in gradients:
            for derivative in row:
                squared = squared + derivative * derivative
        cell_volume = self.dx**3
        return float(
            (
                self.config.density
                * self.config.viscosity
                * squared.sum()
                * cell_volume
            )
            .detach()
            .cpu()
        )

    def _control_effort(self, control: Tensor) -> float:
        cell_volume = self.dx**3
        return float(
            (
                torch.linalg.vector_norm(control, dim=-1).sum() * cell_volume
            )
            .detach()
            .cpu()
        )

    def _scalar_mass(self, scalar_hat: Tensor) -> float:
        scalar = torch.fft.ifftn(scalar_hat, dim=(0, 1, 2)).real
        return float((scalar.sum() * self.dx**3).detach().cpu())

    def _relative_norm(self, difference: Tensor, reference: Tensor) -> float:
        numerator = torch.linalg.vector_norm(difference.reshape(-1))
        denominator = torch.linalg.vector_norm(reference.reshape(-1))
        return float(
            (numerator / (denominator + torch.finfo(self.dtype).eps))
            .detach()
            .cpu()
        )

    def _verification(
        self,
        old_velocity_hat: Tensor,
        old_scalar_hat: Tensor,
        new_velocity_hat: Tensor,
        new_scalar_hat: Tensor,
        full_step_velocity_hat: Tensor,
        dt: float,
        authority_scale: float,
        old_energy: float,
        initial_scalar_mass: float,
        control_override: Tensor | None = None,
    ) -> tuple[
        VerificationState,
        float,
        float,
        float,
        float,
        BoundaryState,
        float,
        float,
        float,
        float,
    ]:
        new_velocity = self._ifft_vector(new_velocity_hat)
        _, control, environmental, boundary = self._forces(
            new_velocity,
            new_velocity_hat,
            authority_scale,
            control_override=control_override,
        )
        applied_control = self.project_physical_vector(control)
        applied_environmental = self.project_physical_vector(environmental)
        total_force = applied_control + applied_environmental

        new_energy = float(
            kinetic_energy(
                new_velocity,
                cell_volume=self.dx**3,
                density=self.config.density,
            )
            .detach()
            .cpu()
        )
        energy_rate = (new_energy - old_energy) / dt
        def power_from_force(force: Tensor) -> float:
            return float(
                (
                    self.config.density
                    * (new_velocity * force).sum(dim=-1).sum()
                    * self.dx**3
                )
                .detach()
                .cpu()
            )

        environmental_power = power_from_force(applied_environmental)
        control_power = power_from_force(applied_control)
        total_power = power_from_force(total_force)
        dissipation = self._gradient_dissipation(new_velocity_hat)
        energy_scale = max(
            abs(energy_rate),
            abs(total_power) + abs(dissipation),
            1.0e-12,
        )
        energy_residual = abs(
            energy_rate - (total_power - dissipation)
        ) / energy_scale

        rhs_old, _ = self._rhs(
            old_velocity_hat,
            old_scalar_hat,
            authority_scale,
            control_override=control_override,
        )
        rhs_new, _ = self._rhs(
            new_velocity_hat,
            new_scalar_hat,
            authority_scale,
            control_override=control_override,
        )
        finite_difference = (new_velocity_hat - old_velocity_hat) / dt
        trapezoid_rhs = 0.5 * (rhs_old + rhs_new)
        pde_residual = self._relative_norm(
            finite_difference - trapezoid_rhs,
            finite_difference,
        )

        convergence_error = self._relative_norm(
            new_velocity_hat - full_step_velocity_hat,
            new_velocity_hat,
        )

        divergence_residual = self.divergence_linf_hat(new_velocity_hat)

        spectral_omega = self.spectral_vorticity(new_velocity_hat)
        spectral_omega_max = float(
            torch.linalg.vector_norm(spectral_omega, dim=-1)
            .amax()
            .detach()
            .cpu()
        )
        finite_difference_metrics = compute_metrics(
            new_velocity,
            self.spacing,
            viscosity=self.config.viscosity,
            density=self.config.density,
        )
        operator_discrepancy = abs(
            spectral_omega_max - finite_difference_metrics.max_vorticity
        ) / max(spectral_omega_max, 1.0e-12)

        tail_fraction = self.spectral_tail_fraction(new_velocity_hat)
        uncertainty = self.config.base_uncertainty + convergence_error + tail_fraction

        verification = VerificationState(
            pde_residual=pde_residual,
            divergence_residual=divergence_residual,
            energy_residual=energy_residual,
            solver_discrepancy=operator_discrepancy,
            convergence_error=convergence_error,
            observation_mismatch=self.config.observation_mismatch,
            uncertainty=uncertainty,
            domain_distance=max(self.config.domain_distance, tail_fraction),
        )

        current_scalar_mass = self._scalar_mass(new_scalar_hat)
        scalar_mass_fidelity = max(
            0.0,
            1.0
            - abs(current_scalar_mass - initial_scalar_mass)
            / max(abs(initial_scalar_mass), 1.0e-12),
        )
        return (
            verification,
            new_energy,
            scalar_mass_fidelity,
            tail_fraction,
            self._control_effort(applied_control),
            boundary,
            operator_discrepancy,
            environmental_power,
            control_power,
            dissipation,
        )

    def step(
        self,
        state: SpectralState,
        *,
        initial_scalar_mass: float,
        initial_energy: float,
        control_override: Tensor | None = None,
    ) -> tuple[SpectralState, SimulationRecord]:
        remaining = self.config.final_time - state.time
        if remaining <= 0:
            raise ValueError("simulation has already reached final_time")
        dt = self.stable_time_step(state.velocity_hat, remaining)
        if dt <= 0 or not math.isfinite(dt):
            raise RuntimeError("no positive stable time step is available")

        old_velocity = self._ifft_vector(state.velocity_hat)
        old_energy = float(
            kinetic_energy(
                old_velocity,
                cell_volume=self.dx**3,
                density=self.config.density,
            )
            .detach()
            .cpu()
        )

        full_velocity_hat, _ = self._rk4(
            state.velocity_hat,
            state.scalar_hat,
            dt,
            state.authority_scale,
            control_override=control_override,
        )
        half_velocity_hat, half_scalar_hat = self._rk4(
            state.velocity_hat,
            state.scalar_hat,
            0.5 * dt,
            state.authority_scale,
            control_override=control_override,
        )
        accepted_velocity_hat, accepted_scalar_hat = self._rk4(
            half_velocity_hat,
            half_scalar_hat,
            0.5 * dt,
            state.authority_scale,
            control_override=control_override,
        )

        (
            verification,
            new_energy,
            scalar_mass_fidelity,
            tail_fraction,
            control_effort,
            boundary,
            operator_discrepancy,
            environmental_power,
            control_power,
            viscous_energy_dissipation,
        ) = self._verification(
            state.velocity_hat,
            state.scalar_hat,
            accepted_velocity_hat,
            accepted_scalar_hat,
            full_velocity_hat,
            dt,
            state.authority_scale,
            old_energy,
            initial_scalar_mass,
            control_override=control_override,
        )

        positive_environmental_power = max(environmental_power, 0.0)
        power_external_risk = positive_environmental_power / (
            positive_environmental_power
            + viscous_energy_dissipation
            + 1.0e-12
        )
        containment_risk = boundary.load / (
            boundary.load + boundary.capacity
        )
        dynamic_external_risk = max(
            self.config.external_risk,
            power_external_risk,
            containment_risk,
        )

        risk = risk_from_verification(
            verification,
            self.config.verification_scales,
            control_risk=self.config.control_risk,
            external_risk=dynamic_external_risk,
        )
        mismatch = detect_model_mismatch(
            verification,
            self.config.verification_scales,
            threshold=self.config.mismatch_threshold,
        )
        decision: SafetyDecision = evaluate_safety(
            risk,
            thresholds=self.config.safety_thresholds,
            model_mismatch=mismatch,
        )
        confidence = confidence_from_risk(risk)

        accepted_velocity = self._ifft_vector(accepted_velocity_hat)
        continuation = compute_metrics(
            accepted_velocity,
            self.spacing,
            viscosity=self.config.viscosity,
            density=self.config.density,
        )
        total_enstrophy, stretching_production, viscous_dissipation = (
            enstrophy_balance_integrals(
                accepted_velocity,
                self.spacing,
                self.config.viscosity,
            )
        )
        stretching_production_value = float(
            stretching_production.detach().cpu()
        )
        viscous_enstrophy_dissipation = float(
            viscous_dissipation.detach().cpu()
        )

        restoring_power = (
            viscous_energy_dissipation + max(-control_power, 0.0)
        )
        if restoring_power == 0.0:
            energy_power_dominance_ratio = (
                0.0
                if positive_environmental_power == 0.0
                else float("inf")
            )
        else:
            energy_power_dominance_ratio = (
                positive_environmental_power / restoring_power
            )
        overpowering_increment = max(
            positive_environmental_power - restoring_power,
            0.0,
        ) * dt
        accumulated_overpowering_energy = (
            state.accumulated_overpowering_energy + overpowering_increment
        )
        accumulated_overpowering_fraction = (
            accumulated_overpowering_energy / max(initial_energy, 1.0e-12)
        )

        positive_stretching = max(stretching_production_value, 0.0)
        if viscous_enstrophy_dissipation == 0.0:
            enstrophy_dominance_ratio = (
                0.0 if positive_stretching == 0.0 else float("inf")
            )
        else:
            enstrophy_dominance_ratio = (
                positive_stretching / viscous_enstrophy_dissipation
            )

        watchdog_reasons: list[str] = []
        critical_values = (
            continuation.max_velocity_gradient,
            continuation.max_vorticity,
            new_energy,
            verification.pde_residual,
            verification.divergence_residual,
            verification.energy_residual,
        )
        if any(not math.isfinite(value) for value in critical_values):
            watchdog_reasons.append("nonfinite_state_or_residual")
        if (
            verification.divergence_residual
            > self.config.watchdog_divergence_limit
        ):
            watchdog_reasons.append("divergence_limit")
        if (
            verification.energy_residual
            > self.config.watchdog_energy_residual_limit
        ):
            watchdog_reasons.append("energy_accounting_limit")
        if (
            scalar_mass_fidelity
            < self.config.watchdog_min_scalar_mass_fidelity
        ):
            watchdog_reasons.append("scalar_mass_fidelity")

        if watchdog_reasons:
            decision = SafetyDecision(
                mode=OperationalMode.ISOLATE,
                authority_scale=0.0,
                trusted_prediction=False,
                model_mismatch=True,
                reasons=decision.reasons + tuple(watchdog_reasons),
            )
            confidence = 0.0

        record = SimulationRecord(
            step=state.step + 1,
            time=state.time + dt,
            time_step=dt,
            max_velocity_gradient=continuation.max_velocity_gradient,
            max_vorticity=continuation.max_vorticity,
            kinetic_energy=new_energy,
            enstrophy=float(total_enstrophy.detach().cpu()),
            stretching_production=stretching_production_value,
            viscous_enstrophy_dissipation=viscous_enstrophy_dissipation,
            vortex_stretching_rate=continuation.vortex_stretching_rate,
            viscous_redistribution_rate=continuation.viscous_redistribution_rate,
            regulation_ratio=continuation.regulation_ratio,
            divergence_residual=verification.divergence_residual,
            pde_residual=verification.pde_residual,
            energy_residual=verification.energy_residual,
            convergence_error=verification.convergence_error,
            operator_discrepancy=operator_discrepancy,
            scalar_mass_fidelity=scalar_mass_fidelity,
            spectral_tail_fraction=tail_fraction,
            boundary_mode=boundary.mode.value,
            boundary_load=boundary.load,
            containment_failed=boundary.containment_failed,
            environmental_influence=boundary.environmental_influence,
            control_effort=control_effort,
            environmental_power=environmental_power,
            control_power=control_power,
            viscous_energy_dissipation=viscous_energy_dissipation,
            energy_power_dominance_ratio=energy_power_dominance_ratio,
            accumulated_overpowering_energy_fraction=(
                accumulated_overpowering_fraction
            ),
            enstrophy_dominance_ratio=enstrophy_dominance_ratio,
            watchdog_triggered=bool(watchdog_reasons),
            watchdog_reasons=tuple(watchdog_reasons),
            safety_mode=decision.mode.value,
            authority_scale=decision.authority_scale,
            confidence=confidence,
            trusted_prediction=decision.trusted_prediction,
            model_mismatch=decision.model_mismatch,
        )

        next_state = SpectralState(
            velocity_hat=accepted_velocity_hat,
            scalar_hat=accepted_scalar_hat,
            time=record.time,
            step=record.step,
            authority_scale=decision.authority_scale,
            accumulated_overpowering_energy=accumulated_overpowering_energy,
        )
        return next_state, record

    def run(
        self,
        *,
        amplitude: float = 1.0,
        scalar_width: float = 0.6,
    ) -> tuple[SpectralState, list[SimulationRecord]]:
        state = self.initialise(amplitude=amplitude, scalar_width=scalar_width)
        initial_scalar_mass = self._scalar_mass(state.scalar_hat)
        initial_velocity = self._ifft_vector(state.velocity_hat)
        initial_energy = float(
            kinetic_energy(
                initial_velocity,
                cell_volume=self.dx**3,
                density=self.config.density,
            )
            .detach()
            .cpu()
        )
        records: list[SimulationRecord] = []
        velocity_history: list[Tensor] = [state.velocity_hat.detach().clone()]

        while state.time < self.config.final_time:
            if state.step >= self.config.max_steps:
                raise RuntimeError("max_steps reached before final_time")
            control_override: Tensor | None = None
            if (
                self.config.controller_enabled
                and self.config.controller_delay_steps > 0
            ):
                if len(velocity_history) <= self.config.controller_delay_steps:
                    delayed_velocity = self._ifft_vector(state.velocity_hat)
                    control_override = torch.zeros_like(delayed_velocity)
                else:
                    delayed_hat = velocity_history[
                        -1 - self.config.controller_delay_steps
                    ]
                    delayed_velocity = self._ifft_vector(delayed_hat)
                    delayed_omega = (
                        self.config.sensor_vorticity_scale
                        * self.spectral_vorticity(delayed_hat)
                    )
                    control_override = (
                        self.config.controller_sign
                        * vorticity_weighted_damping_force(
                            delayed_velocity,
                            delayed_omega,
                            self.config.controller,
                            authority_scale=state.authority_scale,
                        )
                    )

            state, record = self.step(
                state,
                initial_scalar_mass=initial_scalar_mass,
                initial_energy=initial_energy,
                control_override=control_override,
            )
            records.append(record)
            velocity_history.append(state.velocity_hat.detach().clone())

            if (
                self.config.stop_on_isolate
                and record.safety_mode == OperationalMode.ISOLATE.value
            ):
                break

        return state, records
