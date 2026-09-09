from pathlib import Path

import trimesh

from src.formpilot.mesh_checker import _component_count, check_mesh


def test_accepts_single_watertight_mesh(tmp_path: Path):
    path = tmp_path / "box.stl"
    trimesh.creation.box(extents=[100, 50, 10]).export(path)
    report = check_mesh(path, expected_width=100)
    assert report.passed
    assert report.component_count == 1


def test_rejects_width_mismatch(tmp_path: Path):
    path = tmp_path / "box.stl"
    trimesh.creation.box(extents=[80, 50, 10]).export(path)
    report = check_mesh(path, expected_width=100)
    assert not report.passed
    assert "width_mismatch" in report.issue_codes


def test_rejects_empty_mesh(tmp_path: Path):
    path = tmp_path / "empty.stl"
    trimesh.Trimesh().export(path)
    report = check_mesh(path, expected_width=100)
    assert not report.passed
    assert "empty_mesh" in report.issue_codes
    assert report.component_count == 0


def test_rejects_disconnected_components(tmp_path: Path):
    path = tmp_path / "two_boxes.stl"
    first = trimesh.creation.box(extents=[50, 50, 10])
    second = trimesh.creation.box(extents=[50, 50, 10])
    second.apply_translation([51, 0, 0])
    trimesh.util.concatenate([first, second]).export(path)
    report = check_mesh(path, expected_width=101)
    assert not report.passed
    assert report.component_count == 2
    assert "unexpected_components" in report.issue_codes


def test_rejects_closed_shells_that_touch_at_only_one_vertex(tmp_path: Path):
    path = tmp_path / "vertex_touching_boxes.stl"
    first = trimesh.creation.box(extents=[50, 50, 50])
    second = trimesh.creation.box(extents=[50, 50, 50])
    second.apply_translation([50, 50, 50])
    trimesh.util.concatenate([first, second]).export(path)

    report = check_mesh(path, expected_width=100)

    assert not report.passed
    assert report.component_count == 2
    assert "unexpected_components" in report.issue_codes


def test_rejects_non_watertight_mesh(tmp_path: Path):
    path = tmp_path / "open_box.stl"
    mesh = trimesh.creation.box(extents=[100, 50, 10])
    mesh.update_faces(range(len(mesh.faces) - 1))
    mesh.export(path)

    report = check_mesh(path, expected_width=100)

    assert not report.passed
    assert not report.watertight
    assert "not_watertight" in report.issue_codes


def test_component_counter_handles_a_long_face_chain_without_recursion():
    mesh = type(
        "Mesh",
        (),
        {"faces": [(index, index + 1, index + 2) for index in range(1_200)]},
    )()

    assert _component_count(mesh) == 1


def test_accepts_width_at_tolerance_boundary(tmp_path: Path):
    path = tmp_path / "box.stl"
    trimesh.creation.box(extents=[100.5, 50, 10]).export(path)
    report = check_mesh(path, expected_width=100)
    assert report.passed


def test_rejects_optional_depth_and_height_mismatches(tmp_path: Path):
    path = tmp_path / "box.stl"
    trimesh.creation.box(extents=[100, 50, 10]).export(path)

    report = check_mesh(
        path, expected_width=100, expected_depth=55, expected_height=20
    )

    assert not report.passed
    assert {"depth_mismatch", "height_mismatch"} <= set(report.issue_codes)
