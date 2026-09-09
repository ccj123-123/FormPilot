from pathlib import Path
import json

import pytest

import trimesh

from src.formpilot.design_spec import DesignSpec
import src.formpilot.pipeline as pipeline
from src.formpilot.pipeline import GenerationRejected, run_generation


def test_pipeline_writes_traceable_artifacts(tmp_path: Path):
    spec = DesignSpec(
        layout="front_back", phone_width=76, phone_thickness=10,
        earbuds_width=65, earbuds_thickness=28, max_base_width=120,
    )

    def fake_generator(spec, run_dir, openscad_bin=None):
        run_dir.mkdir(parents=True, exist_ok=False)
        path = run_dir / "organizer.stl"
        trimesh.creation.box(extents=[82, 113, 20]).export(path)
        return path

    result = run_generation(spec, tmp_path, generator=fake_generator)
    assert result.spec_path.exists()
    assert result.report_path.exists()
    assert result.stl_path.exists()
    assert json.loads(result.spec_path.read_text(encoding="utf-8"))["layout"] == "front_back"
    assert json.loads(result.report_path.read_text(encoding="utf-8"))["passed"] is True


def test_pipeline_does_not_write_json_for_a_rejected_mesh(tmp_path: Path):
    spec = DesignSpec(
        layout="front_back", phone_width=76, phone_thickness=10,
        earbuds_width=65, earbuds_thickness=28, max_base_width=120,
    )

    def bad_generator(spec, run_dir, openscad_bin=None):
        run_dir.mkdir(parents=True, exist_ok=False)
        path = run_dir / "organizer.stl"
        trimesh.creation.box(extents=[80, 113, 20]).export(path)
        return path

    with pytest.raises(GenerationRejected, match="width_mismatch"):
        run_generation(spec, tmp_path, generator=bad_generator)
    assert not list(tmp_path.glob("*/design.json"))
    assert not list(tmp_path.glob("*/report.json"))


def test_pipeline_rejects_an_invalid_spec_before_generation(tmp_path: Path):
    spec = DesignSpec(
        layout="side_by_side", phone_width=76, phone_thickness=10,
        earbuds_width=65, earbuds_thickness=28, max_base_width=150,
    )

    def unexpected_generator(spec, run_dir, openscad_bin=None):
        raise AssertionError("The generator must not run for an invalid spec.")

    with pytest.raises(GenerationRejected):
        run_generation(spec, tmp_path, generator=unexpected_generator)
    assert not list(tmp_path.iterdir())


def test_pipeline_cleans_json_and_wraps_artifact_write_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    spec = DesignSpec(
        layout="front_back", phone_width=76, phone_thickness=10,
        earbuds_width=65, earbuds_thickness=28, max_base_width=120,
    )

    def fake_generator(spec, run_dir, openscad_bin=None):
        run_dir.mkdir(parents=True, exist_ok=False)
        path = run_dir / "organizer.stl"
        trimesh.creation.box(extents=[82, 113, 20]).export(path)
        return path

    original_write_text = Path.write_text

    def fail_report_write(self: Path, data: str, **kwargs):
        if "report" in self.name:
            raise OSError("simulated report write failure")
        return original_write_text(self, data, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_report_write)

    with pytest.raises(GenerationRejected, match="report write failure"):
        run_generation(spec, tmp_path, generator=fake_generator)
    assert not list(tmp_path.iterdir())


def test_pipeline_cleans_json_and_wraps_artifact_publish_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    spec = DesignSpec(
        layout="front_back", phone_width=76, phone_thickness=10,
        earbuds_width=65, earbuds_thickness=28, max_base_width=120,
    )

    def fake_generator(spec, run_dir, openscad_bin=None):
        run_dir.mkdir(parents=True, exist_ok=False)
        path = run_dir / "organizer.stl"
        trimesh.creation.box(extents=[82, 113, 20]).export(path)
        return path

    original_replace = Path.replace

    def fail_run_publish(self: Path, target: Path):
        if Path(target).parent == tmp_path:
            raise OSError("simulated report publish failure")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_run_publish)

    with pytest.raises(GenerationRejected, match="report publish failure"):
        run_generation(spec, tmp_path, generator=fake_generator)
    assert not list(tmp_path.iterdir())


def test_pipeline_reports_staging_cleanup_failure_without_a_final_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    spec = DesignSpec(
        layout="front_back", phone_width=76, phone_thickness=10,
        earbuds_width=65, earbuds_thickness=28, max_base_width=120,
    )

    def fake_generator(spec, run_dir, openscad_bin=None):
        run_dir.mkdir(parents=True, exist_ok=False)
        path = run_dir / "organizer.stl"
        trimesh.creation.box(extents=[82, 113, 20]).export(path)
        return path

    published_paths: list[Path] = []
    original_replace = Path.replace

    def fail_run_publish(self: Path, target: Path):
        if Path(target).parent == tmp_path:
            published_paths.append(Path(target))
            raise OSError("simulated publish failure")
        return original_replace(self, target)

    class FailedCleanup:
        @staticmethod
        def rmtree(path: Path) -> None:
            raise OSError("simulated cleanup failure")

    monkeypatch.setattr(Path, "replace", fail_run_publish)
    monkeypatch.setattr(pipeline, "shutil", FailedCleanup, raising=False)

    with pytest.raises(GenerationRejected, match="publish failure.*cleanup failure"):
        run_generation(spec, tmp_path, generator=fake_generator)
    assert published_paths
    assert not published_paths[0].exists()


def test_pipeline_rejects_mesh_with_correct_width_but_wrong_depth_and_height(
    tmp_path: Path,
):
    spec = DesignSpec(
        layout="side_by_side", phone_width=76, phone_thickness=10,
        earbuds_width=65, earbuds_thickness=50, clearance=2.5,
        max_base_width=180,
    )

    def bad_generator(spec, run_dir, openscad_bin=None):
        run_dir.mkdir(parents=True, exist_ok=False)
        path = run_dir / "organizer.stl"
        trimesh.creation.box(extents=[156, 55, 5]).export(path)
        return path

    with pytest.raises(GenerationRejected, match="depth_mismatch.*height_mismatch"):
        run_generation(spec, tmp_path, generator=bad_generator)
