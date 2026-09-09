from pydantic import BaseModel

from .design_spec import DesignSpec, Feedback


class RevisionResult(BaseModel):
    spec: DesignSpec
    changes: list[str]


def revise_from_feedback(spec: DesignSpec, feedback: Feedback) -> RevisionResult:
    updates: dict[str, float] = {}
    changes: list[str] = []

    fits = (feedback.phone_fit, feedback.earbuds_fit)
    if "too_tight" in fits:
        clearance = min(2.5, round(spec.clearance + 0.3, 2))
        if clearance != spec.clearance:
            updates["clearance"] = clearance
            changes.append(f"间隙调整为 {clearance:.2f} mm")
    elif "too_loose" in fits:
        clearance = max(0.5, round(spec.clearance - 0.2, 2))
        if clearance != spec.clearance:
            updates["clearance"] = clearance
            changes.append(f"间隙调整为 {clearance:.2f} mm")

    if feedback.stability == "unstable":
        thickness = min(10.0, round(spec.base_thickness + 1.0, 2))
        if thickness != spec.base_thickness:
            updates["base_thickness"] = thickness
            changes.append(f"底座厚度调整为 {thickness:.2f} mm")

    return RevisionResult(spec=spec.model_copy(update=updates), changes=changes)
