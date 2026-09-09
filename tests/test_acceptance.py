import json
from pathlib import Path

import pytest
import trimesh

from src.formpilot.design_spec import DesignSpec
from src.formpilot.pipeline import run_generation
from src.formpilot.validator import calculate_base_size, validate_spec


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = PROJECT_ROOT / "examples"


@pytest.mark.parametrize(
    ("phone_width", "phone_thickness", "earbuds_width", "earbuds_thickness"),
    [
        (60, 8, 45, 20),
        (68, 9, 52, 24),
        (76, 10, 65, 28),
        (82, 12, 72, 35),
        (90, 15, 85, 45),
    ],
)
def test_front_back_designs_generate_traceable_accepted_stls(
    tmp_path: Path,
    phone_width: int,
    phone_thickness: int,
    earbuds_width: int,
    earbuds_thickness: int,
):
    spec = DesignSpec(
        layout="front_back",
        phone_width=phone_width,
        phone_thickness=phone_thickness,
        earbuds_width=earbuds_width,
        earbuds_thickness=earbuds_thickness,
        max_base_width=120,
    )
    expected_width, expected_depth = calculate_base_size(spec)

    def trimesh_box_generator(design: DesignSpec, staging_dir: Path) -> Path:
        staging_dir.mkdir(parents=True, exist_ok=False)
        stl_path = staging_dir / "organizer.stl"
        trimesh.creation.box(
            extents=[
                expected_width,
                expected_depth,
                design.base_thickness + design.slot_depth,
            ]
        ).export(stl_path)
        return stl_path

    result = run_generation(spec, tmp_path, generator=trimesh_box_generator)

    assert result.stl_path.is_file()
    assert result.stl_path.stat().st_size > 0
    assert json.loads(result.spec_path.read_text(encoding="utf-8")) == spec.model_dump(
        mode="json"
    )
    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert report["passed"] is True
    assert report["extents"] == [
        expected_width,
        expected_depth,
        spec.base_thickness + spec.slot_depth,
    ]


@pytest.mark.parametrize(
    ("filename", "expected_payload", "expected_passed"),
    [
        (
            "normal-front-back.json",
            {
                "layout": "front_back",
                "phone_width": 76.0,
                "phone_thickness": 10.0,
                "earbuds_width": 65.0,
                "earbuds_thickness": 28.0,
                "max_base_width": 120.0,
                "clearance": 1.2,
                "base_thickness": 5.0,
                "slot_depth": 15.0,
                "phone_tilt_degrees": 15.0,
                "cable_hole_enabled": True,
                "cable_hole_diameter": 8.0,
            },
            True,
        ),
        (
            "normal-side-by-side.json",
            {
                "layout": "side_by_side",
                "phone_width": 76.0,
                "phone_thickness": 10.0,
                "earbuds_width": 65.0,
                "earbuds_thickness": 28.0,
                "max_base_width": 180.0,
                "clearance": 1.2,
                "base_thickness": 5.0,
                "slot_depth": 15.0,
                "phone_tilt_degrees": 15.0,
                "cable_hole_enabled": True,
                "cable_hole_diameter": 8.0,
            },
            True,
        ),
        (
            "invalid-too-narrow.json",
            {
                "layout": "side_by_side",
                "phone_width": 76.0,
                "phone_thickness": 10.0,
                "earbuds_width": 65.0,
                "earbuds_thickness": 28.0,
                "max_base_width": 150.0,
                "clearance": 1.2,
                "base_thickness": 5.0,
                "slot_depth": 15.0,
                "phone_tilt_degrees": 15.0,
                "cable_hole_enabled": True,
                "cable_hole_diameter": 8.0,
            },
            False,
        ),
    ],
)
def test_examples_are_complete_design_specs_with_expected_manufacturing_result(
    filename: str, expected_payload: dict[str, object], expected_passed: bool
):
    example_path = EXAMPLES_DIR / filename
    assert example_path.is_file(), f"Missing required example: {example_path}"

    payload = json.loads(example_path.read_text(encoding="utf-8"))
    assert set(payload) == set(DesignSpec.model_fields)
    assert payload == expected_payload
    report = validate_spec(DesignSpec.model_validate(payload))

    assert report.passed is expected_passed
    if not expected_passed:
        assert report.issues[0].code == "base_width_exceeded"
        assert "front_back" in report.issues[0].suggestion
