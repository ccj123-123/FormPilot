import shutil
from pathlib import Path
from typing import Callable
from uuid import uuid4

from .design_spec import DesignSpec, GenerationResult
from .mesh_checker import MeshReport, check_mesh
from .model_generator import OpenScadError, generate_model
from .validator import calculate_base_size, validate_spec


class GenerationRejected(RuntimeError):
    """Raised when a design cannot produce a validated generation run."""


def _write_artifacts(
    staging_dir: Path, spec: DesignSpec, mesh_report: MeshReport
) -> tuple[Path, Path]:
    spec_path = staging_dir / "design.json"
    report_path = staging_dir / "report.json"
    spec_path.write_text(spec.model_dump_json(indent=2), encoding="utf-8")
    report_path.write_text(mesh_report.model_dump_json(indent=2), encoding="utf-8")
    return spec_path, report_path


def _raise_after_cleanup(staging_dir: Path, error: Exception) -> None:
    try:
        shutil.rmtree(staging_dir)
    except OSError as cleanup_error:
        raise GenerationRejected(
            f"{error}; staging cleanup failed: {cleanup_error}"
        ) from error
    raise GenerationRejected(str(error)) from error


def run_generation(
    spec: DesignSpec,
    output_root: Path,
    generator: Callable = generate_model,
) -> GenerationResult:
    validation = validate_spec(spec)
    if not validation.passed:
        raise GenerationRejected(validation.issues[0].message)

    run_id = uuid4().hex[:12]
    staging_dir = output_root / f".{run_id}.tmp"
    final_dir = output_root / run_id
    try:
        stl_path = generator(spec, staging_dir)
        expected_width, expected_depth = calculate_base_size(spec)
        mesh_report = check_mesh(
            stl_path,
            expected_width,
            expected_depth=expected_depth,
            expected_height=spec.base_thickness + spec.slot_depth,
        )
        if not mesh_report.passed:
            raise GenerationRejected(
                "Mesh inspection failed: " + ", ".join(mesh_report.issue_codes)
            )
        _write_artifacts(staging_dir, spec, mesh_report)
        staging_dir.replace(final_dir)
    except (OpenScadError, OSError, ValueError, GenerationRejected) as error:
        _raise_after_cleanup(staging_dir, error)

    return GenerationResult(
        run_id=run_id,
        spec_path=final_dir / "design.json",
        stl_path=final_dir / stl_path.name,
        report_path=final_dir / "report.json",
        summary=f"Model passed inspection; extents {mesh_report.extents} mm.",
    )
