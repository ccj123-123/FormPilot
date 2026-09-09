import os
import shutil
import subprocess
from pathlib import Path

from .design_spec import DesignSpec

TEMPLATE = Path(__file__).resolve().parents[2] / "templates" / "desk_organizer.scad"


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


def generate_model(
    spec: DesignSpec, output_dir: Path, openscad_bin: str | None = None
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=False)
    output = output_dir / "organizer.stl"
    command = build_command(spec, output, openscad_bin or resolve_openscad())
    last_message = "OpenSCAD export failed."
    for _ in range(2):
        output.unlink(missing_ok=True)
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=45, shell=False
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            last_message = str(error) or last_message
            continue
        if result.returncode == 0 and output.exists() and output.stat().st_size > 0:
            return output
        last_message = result.stderr or result.stdout or last_message
    raise OpenScadError(last_message[-1000:])
