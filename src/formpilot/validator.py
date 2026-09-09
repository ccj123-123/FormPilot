from pydantic import BaseModel, Field
from math import cos, radians, sin

from .design_spec import DesignSpec, Layout

WALL = 3.0
MODULE_GAP = 3.0
BASE_DEPTH = 55.0


def _holder_depth(item_thickness: float, clearance: float, slot_depth: float, tilt: float) -> float:
    cavity_depth = item_thickness + 2 * clearance
    cavity_height = slot_depth + 1
    tilt_radians = radians(tilt)
    tilt_shift = cavity_height * sin(tilt_radians)
    return max(
        BASE_DEPTH,
        WALL + tilt_shift + cavity_depth * cos(tilt_radians) + WALL,
    )


class ValidationIssue(BaseModel):
    code: str
    message: str
    suggestion: str


class ValidationReport(BaseModel):
    passed: bool
    base_width: float
    base_depth: float
    issues: list[ValidationIssue] = Field(default_factory=list)


def calculate_base_size(spec: DesignSpec) -> tuple[float, float]:
    phone_module = spec.phone_width + 2 * WALL
    earbuds_module = spec.earbuds_width + 2 * WALL
    phone_holder_depth = _holder_depth(
        spec.phone_thickness,
        spec.clearance,
        spec.slot_depth,
        spec.phone_tilt_degrees,
    )
    earbuds_holder_depth = _holder_depth(
        spec.earbuds_thickness, spec.clearance, spec.slot_depth, 0
    )
    if spec.layout is Layout.SIDE_BY_SIDE:
        return phone_module + MODULE_GAP + earbuds_module, max(
            phone_holder_depth, earbuds_holder_depth
        )
    return max(phone_module, earbuds_module), (
        phone_holder_depth + MODULE_GAP + earbuds_holder_depth
    )


def validate_spec(spec: DesignSpec) -> ValidationReport:
    width, depth = calculate_base_size(spec)
    issues: list[ValidationIssue] = []
    if width > spec.max_base_width:
        issues.append(ValidationIssue(
            code="base_width_exceeded",
            message=f"计算宽度 {width:.1f} mm 超过限制 {spec.max_base_width:.1f} mm。",
            suggestion="增大最大宽度，或把布局切换为 front_back。",
        ))
    return ValidationReport(
        passed=not issues, base_width=width, base_depth=depth, issues=issues
    )
