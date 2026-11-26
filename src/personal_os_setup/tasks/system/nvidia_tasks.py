from __future__ import annotations

import platform
import shutil

from personal_os_setup.detect_os import _is_wsl
from personal_os_setup.tasks.commands import run
from personal_os_setup.tasks.task import TaskResult


def _command_exists(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def detect_nvidia() -> TaskResult:
    """Detect NVIDIA driver availability via `nvidia-smi`.

    Works on Linux and Windows (including CUDA on Windows).
    """
    if not _command_exists("nvidia-smi"):
        system = platform.system().lower()
        return TaskResult(ok=False, summary=f"nvidia-smi not found on PATH ({system})")

    # Keep it simple: run a lightweight query.
    res = run(["nvidia-smi", "-L"], check=False)
    details = (res.stdout + "\n" + res.stderr).strip()
    if res.returncode == 0:
        return TaskResult(ok=True, summary="nvidia-smi: ok", details=details)
    return TaskResult(ok=False, summary="nvidia-smi: failed", details=details)


def detect_cuda() -> TaskResult:
    """High-level CUDA detection.

    Simple rule: CUDA is considered present if `nvcc` is available.
    """
    system = platform.system().lower()
    if not _command_exists("nvcc"):
        return TaskResult(ok=False, summary=f"CUDA not detected (nvcc missing) ({system})")

    res = run(["nvcc", "--version"], check=False)
    details = (res.stdout + "\n" + res.stderr).strip()
    if res.returncode == 0:
        return TaskResult(ok=True, summary="CUDA detected (nvcc available)", details=details)
    return TaskResult(ok=False, summary="CUDA not detected (nvcc failed)", details=details)


def setup_cuda() -> TaskResult:
    """Advanced: CUDA setup task (placeholder).

    Keeping it simple for now: report-only stub.
    """
    system = platform.system().lower()
    return TaskResult(
        ok=False,
        summary=f"CUDA setup (advanced) not implemented yet ({system})",
        details="Planned: provide guided installation steps for Windows/Linux, then validate with nvcc and nvidia-smi.",
    )


def setup_nvidia_wsl_instructions() -> TaskResult:
    """WSL: provide instructions for installing NVIDIA drivers on the Windows host."""
    return TaskResult(
        ok=True,
        summary="NVIDIA setup: WSL detected",
        details=(
            "You are running inside WSL.\n"
            "IMPORTANT: Do NOT install any NVIDIA GPU Linux driver inside WSL 2.\n"
            "The Windows host driver is used directly by WSL 2.\n\n"
            "Steps:\n"
            "1) Verify the Windows driver is installed: open PowerShell and run: nvidia-smi\n"
            "   If nvidia-smi is missing, install the latest NVIDIA Windows driver from https://www.nvidia.com/en-us/drivers/\n"
            "   then reboot Windows.\n"
            "2) In PowerShell: wsl --shutdown\n"
            "3) Re-open your Ubuntu/WSL terminal and run: nvidia-smi\n\n"
            "For CUDA inside WSL 2, follow the official guide:\n"
            "https://docs.nvidia.com/cuda/wsl-user-guide/index.html#cuda-support-for-wsl-2"
        ),
    )


def setup_nvidia_arch() -> TaskResult:
    """CachyOS: report driver status and point at the right packages."""
    if _command_exists("nvidia-smi"):
        return TaskResult(
            ok=True,
            summary="NVIDIA setup: drivers already present",
            details=(
                "nvidia-smi is available. CachyOS ships it preinstalled and keeps the kernel module in sync with the\n"
                "running kernel, so no action is needed.\n\n"
            ),
        )

    return TaskResult(
        ok=True,
        summary="NVIDIA setup: drivers not detected",
        details=(
            "nvidia-smi was not found. CachyOS ships it preinstalled, check your installation"
        ),
    )


def setup_nvidia_ubuntu() -> TaskResult:
    """Setup NVIDIA driver on Ubuntu."""
    if _is_wsl():
        return setup_nvidia_wsl_instructions()

    ubuntu_drivers = shutil.which("ubuntu-drivers")
    if ubuntu_drivers is None:
        return TaskResult(
            ok=False,
            summary="ubuntu-drivers not found",
            details=(
                "Recommended (Ubuntu): install it first, then re-run:\n"
                "sudo apt-get update\n"
                "sudo apt-get install -y ubuntu-drivers-common"
            ),
        )

    actions: list[str] = []

    actions.append("Planned steps (native Linux):")
    actions.append("1) sudo ubuntu-drivers devices")
    actions.append("2) sudo ubuntu-drivers autoinstall")
    actions.append("3) reboot")
    actions.append("4) verify: nvidia-smi")

    devices = run([ubuntu_drivers, "devices"], check=False)
    devices_out = (devices.stdout + "\n" + devices.stderr).strip()
    if devices_out:
        actions.append("\nubuntu-drivers devices output:")
        actions.append(devices_out)

    cmd = ["sudo", ubuntu_drivers, "autoinstall"]
    res = run(cmd, check=False)
    details = (res.stdout + "\n" + res.stderr).strip()
    actions.append(f"\nran: {' '.join(cmd)}")
    if details:
        actions.append(details)

    if res.returncode == 0:
        actions.append("\nDriver install complete. Please reboot, then run: nvidia-smi")
        return TaskResult(
            ok=True,
            summary="NVIDIA driver install: completed (reboot required)",
            details="\n".join(actions).strip(),
        )

    if "a password is required" in details.lower() or "sudo:" in details.lower():
        actions.append(
            "\nsudo needs a password. Run manually in a terminal:\nsudo ubuntu-drivers autoinstall"
        )
        return TaskResult(
            ok=False,
            summary="NVIDIA install requires sudo password",
            details="\n".join(actions).strip(),
        )

    return TaskResult(
        ok=False, summary="NVIDIA driver install: failed", details="\n".join(actions).strip()
    )


def setup_nvidia_windows() -> TaskResult:
    """Setup NVIDIA driver on Windows."""
    return TaskResult(ok=False, summary="NVIDIA setup for Windows not implemented yet")
