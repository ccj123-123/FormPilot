from pathlib import Path
import os
import subprocess

import numpy as np
import pytest
import trimesh

from src.formpilot.design_spec import DesignSpec
from src.formpilot.model_generator import generate_model


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OPENSCAD = (
    PROJECT_ROOT.parents[1]
    / ".tools"
    / "openscad-2021.01"
    / "openscad-2021.01"
    / "openscad.com"
)
TEMPLATE = PROJECT_ROOT / "templates" / "desk_organizer.scad"


def resolve_test_openscad() -> Path:
    return Path(os.environ.get("OPENSCAD_BIN", DEFAULT_OPENSCAD))


def horizontal_cap_z_values(mesh: trimesh.Trimesh, point: tuple[float, float]) -> list[float]:
    """Return horizontal face heights whose XY triangle contains ``point``."""
    point_array = np.asarray(point)
    heights: list[float] = []
    for triangle in mesh.triangles:
        if np.ptp(triangle[:, 2]) > 1e-6:
            continue
        edges = np.roll(triangle[:, :2], -1, axis=0) - triangle[:, :2]
        offsets = point_array - triangle[:, :2]
        cross_products = edges[:, 0] * offsets[:, 1] - edges[:, 1] * offsets[:, 0]
        if np.all(cross_products >= -1e-6) or np.all(cross_products <= 1e-6):
            heights.append(float(triangle[0, 2]))
    return heights


def test_openscad_regression_prefers_configured_binary(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENSCAD_BIN", "D:/portable/openscad.com")

    assert resolve_test_openscad() == Path("D:/portable/openscad.com")


def test_openscad_tilted_cavity_keeps_three_millimetre_front_envelope(
    tmp_path: Path,
):
    output = tmp_path / "tilted-cavity-envelope.stl"
    result = subprocess.run(
        [str(resolve_test_openscad()), "-D", "debug_cavity_envelope=true", "-o", str(output), str(TEMPLATE)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    cavity = trimesh.load_mesh(output, force="mesh")
    assert cavity.bounds[0][1] >= 2.99


@pytest.mark.parametrize(
    ("spec", "expected_depth"),
    [
        (
            DesignSpec(
                layout="front_back", phone_width=76, phone_thickness=10,
                earbuds_width=65, earbuds_thickness=28, max_base_width=120,
            ),
            113.0,
        ),
        (
            DesignSpec(
                layout="side_by_side", phone_width=76, phone_thickness=10,
                earbuds_width=65, earbuds_thickness=50, clearance=2.5,
                max_base_width=180,
            ),
            61.0,
        ),
        (
            DesignSpec(
                layout="front_back", phone_width=76, phone_thickness=10,
                earbuds_width=65, earbuds_thickness=50, clearance=2.5,
                max_base_width=120,
            ),
            119.0,
        ),
    ],
)
def test_openscad_exports_depth_matching_holder_envelopes(
    tmp_path: Path, spec: DesignSpec, expected_depth: float
):
    stl_path = generate_model(spec, tmp_path / "render", str(resolve_test_openscad()))
    mesh = trimesh.load_mesh(stl_path, force="mesh")

    assert mesh.extents[1] == pytest.approx(expected_depth, abs=0.01)
    assert mesh.extents[2] == pytest.approx(spec.base_thickness + spec.slot_depth, abs=0.01)


@pytest.mark.parametrize(
    ("layout", "expected_depth"),
    [("side_by_side", 63.27), ("front_back", 121.27)],
)
def test_openscad_extreme_phone_stress_fixture_expands_holder_depth(
    tmp_path: Path, layout: str, expected_depth: float
):
    output = tmp_path / f"extreme-phone-{layout}.stl"
    result = subprocess.run(
        [
            str(resolve_test_openscad()), "-D", f'layout="{layout}"',
            "-D", "phone_thickness=50", "-D", "clearance=2.5",
            "-o", str(output), str(TEMPLATE),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert trimesh.load_mesh(output, force="mesh").extents[1] == pytest.approx(
        expected_depth, abs=0.01
    )


def test_openscad_default_cable_hole_has_no_horizontal_cap_above_its_centre(
    tmp_path: Path,
):
    output = tmp_path / "default-cable-hole.stl"
    result = subprocess.run(
        [str(resolve_test_openscad()), "-o", str(output), str(TEMPLATE)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    mesh = trimesh.load_mesh(output, force="mesh")
    assert not horizontal_cap_z_values(mesh, (41.0, 27.5))
