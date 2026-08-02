"""Run repeated clean-package reliability cycles for NASA Data Hub."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
PROBE = APP_DIR / "scripts" / "reliability_probe.py"


def run(*args: str, cwd: Path = APP_DIR, capture: bool = False) -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=capture,
    )
    return result.stdout if capture else ""


def executable_paths(venv_dir: Path) -> tuple[Path, Path]:
    if os.name == "nt":
        return (
            venv_dir / "Scripts" / "python.exe",
            venv_dir / "Scripts" / "nasa-data-hub.exe",
        )
    return (
        venv_dir / "bin" / "python",
        venv_dir / "bin" / "nasa-data-hub",
    )


def validate_launcher() -> None:
    if os.name == "nt":
        script = APP_DIR / "start.ps1"
        command = (
            "[void][scriptblock]::Create((Get-Content "
            f"'{script}' -Raw))"
        )
        run("pwsh", "-NoProfile", "-Command", command)
    else:
        run("bash", "-n", str(APP_DIR / "start.sh"))


def one_pass(phase: int, pass_number: int) -> None:
    dist_dir = APP_DIR / "dist"
    shutil.rmtree(dist_dir, ignore_errors=True)

    run(sys.executable, "-m", "compileall", "-q", "nasa_data_hub")
    run(sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v")
    validate_launcher()
    run(
        sys.executable,
        "-m",
        "pip",
        "wheel",
        ".",
        "--no-deps",
        "--no-build-isolation",
        "-w",
        "dist",
    )
    wheels = list(dist_dir.glob("*.whl"))
    if len(wheels) != 1:
        raise AssertionError(f"Expected exactly one wheel, found {len(wheels)}")

    with tempfile.TemporaryDirectory(prefix=f"nasa-p{phase}-{pass_number}-") as folder:
        venv_dir = Path(folder) / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(venv_dir)
        python, command = executable_paths(venv_dir)
        run(
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-deps",
            str(wheels[0]),
        )
        health_text = run(
            str(command),
            "--env-file",
            str(Path(folder) / "missing.env"),
            "health",
            capture=True,
        )
        health = json.loads(health_text)
        if health.get("ok") is not True:
            raise AssertionError(f"Health failed: {health}")
        key_mode = health.get("key_mode")
        if key_mode not in {"demo", "personal"}:
            raise AssertionError(f"Unexpected key mode: {key_mode}")
        if health.get("using_demo_key") is not (key_mode == "demo"):
            raise AssertionError(f"Inconsistent key mode: {health}")
        run(str(python), str(PROBE))

    shutil.rmtree(dist_dir, ignore_errors=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", type=int, choices=(1, 2), required=True)
    parser.add_argument("--passes", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.passes < 1:
        raise ValueError("passes must be positive")
    for pass_number in range(1, args.passes + 1):
        print(
            f"========== PHASE {args.phase} PASS "
            f"{pass_number}/{args.passes} ==========",
            flush=True,
        )
        one_pass(args.phase, pass_number)
    print(
        f"PHASE {args.phase} RESULT: {args.passes}/{args.passes} PASSED",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
