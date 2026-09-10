import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE = PROJECT_ROOT / "portfolio" / "architecture.png"
RENDERER = PROJECT_ROOT / "scripts" / "render_architecture.py"


def assert_architecture_png(path: Path) -> None:
    with Image.open(path) as image:
        assert image.format == "PNG"
        assert image.size == (1600, 900)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_committed_architecture_is_a_1600_by_900_png():
    assert ARCHITECTURE.is_file()
    assert_architecture_png(ARCHITECTURE)


def test_renderer_recreates_architecture_in_project_tmp():
    output = PROJECT_ROOT / ".tmp" / "architecture-test.png"
    output.unlink(missing_ok=True)
    assert not output.exists()

    result = subprocess.run(
        [sys.executable, str(RENDERER), "--output", str(output)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert_architecture_png(output)
    assert sha256(output) == sha256(ARCHITECTURE)


def test_renderer_output_does_not_depend_on_host_font_files():
    output = PROJECT_ROOT / ".tmp" / "architecture-no-host-fonts.png"
    output.unlink(missing_ok=True)
    assert not output.exists()

    spec = importlib.util.spec_from_file_location("architecture_renderer", RENDERER)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    with patch.object(Path, "is_file", return_value=False):
        spec.loader.exec_module(module)
    module.render(output)

    assert_architecture_png(output)
    assert sha256(output) == sha256(ARCHITECTURE)
