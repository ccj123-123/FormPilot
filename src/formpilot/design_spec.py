from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Layout(str, Enum):
    SIDE_BY_SIDE = "side_by_side"
    FRONT_BACK = "front_back"


class DesignSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layout: Layout
    phone_width: float = Field(ge=55, le=100)
    phone_thickness: float = Field(ge=5, le=20)
    earbuds_width: float = Field(ge=40, le=90)
    earbuds_thickness: float = Field(ge=15, le=50)
    max_base_width: float = Field(ge=120, le=260)
    clearance: float = Field(default=1.2, ge=0.5, le=2.5)
    base_thickness: float = Field(default=5.0, ge=4, le=10)
    slot_depth: float = Field(default=15.0, ge=10, le=25)
    phone_tilt_degrees: float = Field(default=15.0, ge=0, le=25)
    cable_hole_enabled: bool = True
    cable_hole_diameter: float = Field(default=8.0, ge=5, le=15)


class AgentAction(str, Enum):
    ASK_USER = "ask_user"
    GENERATE = "generate"
    REVISE = "revise"
    EXPLAIN = "explain"


class PartialDesignSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    layout: Layout | None
    phone_width: float | None
    phone_thickness: float | None
    earbuds_width: float | None
    earbuds_thickness: float | None
    max_base_width: float | None


class RequirementDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: AgentAction
    values: PartialDesignSpec
    missing_fields: list[str]
    message: str


class Feedback(BaseModel):
    phone_fit: Literal["too_tight", "good", "too_loose"]
    earbuds_fit: Literal["too_tight", "good", "too_loose"]
    stability: Literal["stable", "unstable"]
    notes: str = Field(default="", max_length=500)


class GenerationResult(BaseModel):
    run_id: str
    spec_path: Path
    stl_path: Path
    report_path: Path
    summary: str
