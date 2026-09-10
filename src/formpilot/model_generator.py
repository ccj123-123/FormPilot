import ctypes
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .design_spec import DesignSpec

TEMPLATE = Path(__file__).resolve().parents[2] / "templates" / "desk_organizer.scad"
WINDOWS_ERROR_MODE_FLAGS = 0x8003


class OpenScadError(RuntimeError):
    """Raised when OpenSCAD cannot produce a valid STL file."""


def resolve_openscad() -> str:
    configured = os.getenv("OPENSCAD_BIN")
    if configured:
        return configured
    found = shutil.which("openscad.com") or shutil.which("openscad")
    if not found:
        raise OpenScadError("OpenSCAD was not found; set OPENSCAD_BIN.")
    return found


def build_command(spec: DesignSpec, output: Path, executable: str) -> list[str]:
    parameters = spec.model_dump()
    parameters["layout"] = spec.layout.value
    command = [executable, "-o", str(output)]
    for name, value in parameters.items():
        if isinstance(value, bool):
            encoded = "true" if value else "false"
        elif isinstance(value, str):
            encoded = f'"{value}"'
        else:
            encoded = str(value)
        command.extend(["-D", f"{name}={encoded}"])
    command.append(str(TEMPLATE))
    return command


def _subprocess_creationflags() -> int:
    if sys.platform != "win32":
        return 0
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.SetErrorMode(kernel32.GetErrorMode() | WINDOWS_ERROR_MODE_FLAGS)
    return subprocess.CREATE_NO_WINDOW


def generate_model(
    spec: DesignSpec, output_dir: Path, openscad_bin: str | None = None
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=False)
    output = output_dir / "organizer.stl"
    command = build_command(spec, output, openscad_bin or resolve_openscad())
    creationflags = _subprocess_creationflags()
    last_message = "OpenSCAD export failed."
    for _ in range(2):
        output.unlink(missing_ok=True)
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=45,
                shell=False,
                creationflags=creationflags,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            last_message = str(error) or last_message
            continue
        if result.returncode == 0 and output.exists() and output.stat().st_size > 0:
            return output
        last_message = result.stderr or result.stdout or last_message
    raise OpenScadError(last_message[-1000:])
