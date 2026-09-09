# FormPilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a one-page Python application that turns constrained desk-organizer requirements into validated, previewable, downloadable STL files and records a V1-to-V2 physical-print revision.

**Architecture:** A Gradio UI passes all data through one Pydantic `DesignSpec`. AI only parses and explains requirements through OpenAI Structured Outputs; deterministic Python rules validate manufacturing constraints, OpenSCAD generates geometry, and Trimesh verifies the exported mesh. Every generation uses an isolated run directory and the complete manual path remains available when the API is unavailable.

**Tech Stack:** Windows, Python 3.11, Gradio 6.x, Pydantic 2.x, OpenAI Python SDK 2.x with Responses API, OpenSCAD CLI, Trimesh 5.x, pytest 9.x.

**Spec:** `docs/superpowers/specs/2026-09-08-formpilot-design.md`

## Global Constraints

- Complete the software MVP in 7 days and keep total external spending at or below CNY 500.
- Use millimetres for every dimension; do not accept implicit centimetres or inches.
- Support only phone slot, earbuds slot, cable hole, and `side_by_side` / `front_back` layouts.
- AI may parse, ask, revise, and explain; it must never generate geometry code or bypass deterministic validation.
- Do not send local paths, API keys, or unrelated personal information to the model.
- Read `OPENAI_API_KEY` and `FORMPILOT_OPENAI_MODEL` from environment variables; default model is `gpt-5.4-mini`.
- Read `OPENSCAD_BIN` from the environment when set; otherwise resolve `openscad.com` or `openscad` from `PATH`.
- A failed generation must never overwrite or replace the last successful result.
- All generated files stay under the project-local `outputs/` directory.
- Installation of Python packages or OpenSCAD requires the user's explicit approval at execution time.

## Planned File Map

```text
.
├─ .gitignore                         generated files and secrets exclusions
├─ requirements.txt                   pinned dependency ranges
├─ app.py                             Gradio composition and event handlers
├─ scripts/
│  ├─ setup.bat                       virtual environment and dependency setup
│  └─ run.bat                         local application launcher
├─ src/formpilot/
│  ├─ __init__.py
│  ├─ design_spec.py                  canonical input and result types
│  ├─ validator.py                    deterministic manufacturing rules
│  ├─ model_generator.py              safe OpenSCAD process wrapper
│  ├─ mesh_checker.py                 STL integrity checks
│  ├─ pipeline.py                     validation → generation → inspection
│  ├─ requirement_parser.py           OpenAI Structured Outputs adapter
│  └─ revision.py                     physical-feedback adjustment rules
├─ templates/desk_organizer.scad      deterministic parametric geometry
├─ tests/                              unit and integration tests
├─ examples/                           offline demo inputs
├─ outputs/.gitkeep                    local run artifacts
├─ portfolio/                          screenshots, video and physical evidence
└─ README.md                           setup, demo, architecture and limitations
```

---

### Task 1: Project foundation and canonical data model

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `scripts/setup.bat`
- Create: `src/formpilot/__init__.py`
- Create: `src/formpilot/design_spec.py`
- Create: `tests/test_design_spec.py`
- Create: `outputs/.gitkeep`

**Interfaces:**
- Consumes: no project code.
- Produces: `Layout`, `DesignSpec`, `PartialDesignSpec`, `AgentAction`, `RequirementDecision`, `Feedback`, and `GenerationResult` for all later tasks.

- [ ] **Step 1: Initialize version control and exclusions**

Run from the project root:

```bat
git init
```

Create `.gitignore` with:

```gitignore
.venv/
__pycache__/
.pytest_cache/
*.pyc
.env
outputs/*
!outputs/.gitkeep
portfolio/*.mp4
```

- [ ] **Step 2: Declare the dependency ranges and Windows setup script**

Create `requirements.txt`:

```text
gradio>=6.0,<7
openai>=2.0,<3
pydantic>=2.10,<3
trimesh>=5.0,<6
pytest>=9.0,<10
```

Create `scripts/setup.bat`:

```bat
@echo off
setlocal
cd /d "%~dp0.."
py -3.11 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
endlocal
```

Do not run this script until dependency installation has been approved.

- [ ] **Step 3: After explicit approval, prepare the Python environment**

Run:

```bat
scripts\setup.bat
```

Expected: `.venv` is created and `python -m pytest --version` reports pytest 9.x. If installation is not approved, stop here; do not try alternate package locations.

- [ ] **Step 4: Write the failing data-model tests**

Create `tests/test_design_spec.py`:

```python
import pytest
from pydantic import ValidationError

from src.formpilot.design_spec import DesignSpec, Layout


def valid_payload() -> dict:
    return {
        "layout": "side_by_side",
        "phone_width": 76,
        "phone_thickness": 10,
        "earbuds_width": 65,
        "earbuds_thickness": 28,
        "max_base_width": 180,
    }


def test_defaults_are_visible_and_in_millimetres():
    spec = DesignSpec(**valid_payload())
    assert spec.layout is Layout.SIDE_BY_SIDE
    assert spec.clearance == 1.2
    assert spec.base_thickness == 5.0
    assert spec.cable_hole_diameter == 8.0


def test_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        DesignSpec(**valid_payload(), secret_scale=10)


def test_rejects_out_of_range_phone_thickness():
    payload = valid_payload() | {"phone_thickness": 30}
    with pytest.raises(ValidationError):
        DesignSpec(**payload)
```

- [ ] **Step 5: Run the test and verify the expected failure**

Run:

```bat
python -m pytest tests\test_design_spec.py -v
```

Expected: collection fails with `ModuleNotFoundError` for `src.formpilot.design_spec`.

- [ ] **Step 6: Implement the canonical models**

Create `src/formpilot/design_spec.py`:

```python
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
```

- [ ] **Step 7: Run the tests and commit**

Run:

```bat
python -m pytest tests\test_design_spec.py -v
git add .gitignore requirements.txt scripts\setup.bat src\formpilot tests\test_design_spec.py outputs\.gitkeep
git commit -m "feat: define FormPilot project model"
```

Expected: 3 tests pass and the first commit is created.

---

### Task 2: Deterministic manufacturing validation

**Files:**
- Create: `src/formpilot/validator.py`
- Create: `tests/test_validator.py`

**Interfaces:**
- Consumes: `DesignSpec`.
- Produces: `ValidationIssue`, `ValidationReport`, `calculate_base_size(spec) -> tuple[float, float]`, and `validate_spec(spec) -> ValidationReport`.

- [ ] **Step 1: Write failing rule tests**

Create `tests/test_validator.py`:

```python
from src.formpilot.design_spec import DesignSpec
from src.formpilot.validator import calculate_base_size, validate_spec


def make_spec(**overrides) -> DesignSpec:
    values = dict(
        layout="side_by_side", phone_width=76, phone_thickness=10,
        earbuds_width=65, earbuds_thickness=28, max_base_width=180,
    )
    return DesignSpec(**(values | overrides))


def test_side_by_side_width_is_deterministic():
    width, depth = calculate_base_size(make_spec())
    assert width == 156.0
    assert depth == 55.0


def test_front_back_uses_narrower_base():
    report = validate_spec(make_spec(layout="front_back", max_base_width=120))
    assert report.passed


def test_rejects_layout_that_exceeds_user_limit():
    report = validate_spec(make_spec(max_base_width=150))
    assert not report.passed
    assert report.issues[0].code == "base_width_exceeded"
    assert "front_back" in report.issues[0].suggestion
```

- [ ] **Step 2: Verify failure**

Run:

```bat
python -m pytest tests\test_validator.py -v
```

Expected: import fails because `validator.py` does not exist.

- [ ] **Step 3: Implement the exact sizing and reporting rules**

Create `src/formpilot/validator.py`:

```python
from pydantic import BaseModel, Field

from .design_spec import DesignSpec, Layout

WALL = 3.0
MODULE_GAP = 3.0
BASE_DEPTH = 55.0


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
    if spec.layout is Layout.SIDE_BY_SIDE:
        return phone_module + MODULE_GAP + earbuds_module, BASE_DEPTH
    return max(phone_module, earbuds_module), BASE_DEPTH * 2 + MODULE_GAP


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
```

- [ ] **Step 4: Run targeted and full tests**

```bat
python -m pytest tests\test_validator.py -v
python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bat
git add src\formpilot\validator.py tests\test_validator.py
git commit -m "feat: validate organizer manufacturing constraints"
```

---

### Task 3: OpenSCAD template and safe model generator

**Files:**
- Create: `templates/desk_organizer.scad`
- Create: `src/formpilot/model_generator.py`
- Create: `tests/test_model_generator.py`

**Interfaces:**
- Consumes: `DesignSpec` and a destination directory.
- Produces: `OpenScadError` and `generate_model(spec, output_dir, openscad_bin=None) -> Path`.

- [ ] **Step 1: Write a failing process-wrapper test**

Create `tests/test_model_generator.py`:

```python
from pathlib import Path

from src.formpilot.design_spec import DesignSpec
from src.formpilot.model_generator import build_command


def test_build_command_uses_argument_list_not_shell_text(tmp_path: Path):
    spec = DesignSpec(
        layout="side_by_side", phone_width=76, phone_thickness=10,
        earbuds_width=65, earbuds_thickness=28, max_base_width=180,
    )
    command = build_command(spec, tmp_path / "result.stl", "openscad.com")
    assert command[0] == "openscad.com"
    assert command[1:3] == ["-o", str(tmp_path / "result.stl")]
    assert "phone_width=76.0" in command
    assert all(isinstance(item, str) for item in command)
```

- [ ] **Step 2: Verify failure**

```bat
python -m pytest tests\test_model_generator.py -v
```

Expected: import fails because `model_generator.py` does not exist.

- [ ] **Step 3: Create the fixed OpenSCAD template**

Create `templates/desk_organizer.scad` with parameters at the top and two deterministic layout branches:

```scad
layout = "side_by_side";
phone_width = 76;
phone_thickness = 10;
earbuds_width = 65;
earbuds_thickness = 28;
clearance = 1.2;
base_thickness = 5;
slot_depth = 15;
cable_hole_enabled = true;
cable_hole_diameter = 8;
wall = 3;
gap = 3;
base_depth = 55;

phone_module_width = phone_width + wall * 2;
earbuds_module_width = earbuds_width + wall * 2;
base_width = layout == "side_by_side"
    ? phone_module_width + gap + earbuds_module_width
    : max(phone_module_width, earbuds_module_width);
total_depth = layout == "side_by_side" ? base_depth : base_depth * 2 + gap;

module slot_holder(x, y, item_width, item_thickness, tilt) {
    translate([x, y, base_thickness])
    difference() {
        cube([
            item_width + wall * 2,
            item_thickness + clearance * 2 + wall * 2,
            slot_depth
        ]);
        translate([wall, wall, wall])
        rotate([tilt, 0, 0])
            cube([
                item_width,
                item_thickness + clearance * 2,
                slot_depth + 1
            ]);
    }
}

difference() {
    union() {
        cube([base_width, total_depth, base_thickness]);
        slot_holder(0, 0, phone_width, phone_thickness, phone_tilt_degrees);
        if (layout == "side_by_side")
            slot_holder(phone_module_width + gap, 0, earbuds_width, earbuds_thickness, 0);
        else
            slot_holder(0, base_depth + gap, earbuds_width, earbuds_thickness, 0);
    }
    if (cable_hole_enabled)
        translate([phone_module_width / 2, base_depth / 2, -1])
            cylinder(h=base_thickness + 2, d=cable_hole_diameter, $fn=48);
}
```

- [ ] **Step 4: Implement safe command construction and execution**

Create `src/formpilot/model_generator.py`:

```python
import os
import shutil
import subprocess
from pathlib import Path

from .design_spec import DesignSpec

TEMPLATE = Path(__file__).resolve().parents[2] / "templates" / "desk_organizer.scad"


class OpenScadError(RuntimeError):
    pass


def resolve_openscad() -> str:
    configured = os.getenv("OPENSCAD_BIN")
    if configured:
        return configured
    found = shutil.which("openscad.com") or shutil.which("openscad")
    if not found:
        raise OpenScadError("未找到 OpenSCAD；请设置 OPENSCAD_BIN。")
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
    last_message = "OpenSCAD 导出失败"
    for _ in range(2):
        output.unlink(missing_ok=True)
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=45, shell=False
        )
        if result.returncode == 0 and output.exists() and output.stat().st_size > 0:
            return output
        last_message = result.stderr or result.stdout or last_message
    raise OpenScadError(last_message[-1000:])
```

- [ ] **Step 5: Run unit tests and manually verify one STL**

After OpenSCAD installation has been separately approved and completed:

```bat
python -m pytest tests\test_model_generator.py -v
openscad.com --version
```

Then run a temporary Python call through the implemented function and confirm `organizer.stl` exists and is non-empty. Do not use `shell=True` or construct one command string.

- [ ] **Step 6: Commit**

```bat
git add templates\desk_organizer.scad src\formpilot\model_generator.py tests\test_model_generator.py
git commit -m "feat: generate organizer STL with OpenSCAD"
```

---

### Task 4: Mesh inspection and generation pipeline

**Files:**
- Create: `src/formpilot/mesh_checker.py`
- Create: `src/formpilot/pipeline.py`
- Create: `tests/test_mesh_checker.py`
- Create: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `DesignSpec`, `validate_spec`, and `generate_model`.
- Produces: `MeshReport`, `check_mesh(path, expected_width) -> MeshReport`, and `run_generation(spec, output_root, generator=generate_model) -> GenerationResult`.

- [ ] **Step 1: Write failing mesh tests using generated fixture geometry**

Create `tests/test_mesh_checker.py`:

```python
from pathlib import Path
import trimesh

from src.formpilot.mesh_checker import check_mesh


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
```

- [ ] **Step 2: Verify failure, then implement mesh checks**

Run the failing test, then create `src/formpilot/mesh_checker.py`:

```python
from pathlib import Path
import trimesh
from pydantic import BaseModel, Field


class MeshReport(BaseModel):
    passed: bool
    watertight: bool
    component_count: int
    extents: tuple[float, float, float]
    issue_codes: list[str] = Field(default_factory=list)


def check_mesh(path: Path, expected_width: float) -> MeshReport:
    loaded = trimesh.load_mesh(path, force="mesh")
    issue_codes: list[str] = []
    if len(loaded.vertices) == 0 or len(loaded.faces) == 0:
        issue_codes.append("empty_mesh")
    components = loaded.split(only_watertight=False)
    if len(components) != 1:
        issue_codes.append("unexpected_components")
    if not loaded.is_watertight:
        issue_codes.append("not_watertight")
    extents = tuple(float(value) for value in loaded.extents)
    if abs(extents[0] - expected_width) > 0.5:
        issue_codes.append("width_mismatch")
    return MeshReport(
        passed=not issue_codes,
        watertight=bool(loaded.is_watertight),
        component_count=len(components),
        extents=extents,
        issue_codes=issue_codes,
    )
```

- [ ] **Step 3: Write a failing pipeline test with an injected generator**

Create `tests/test_pipeline.py`:

```python
from pathlib import Path
import trimesh

from src.formpilot.design_spec import DesignSpec
from src.formpilot.pipeline import run_generation


def test_pipeline_writes_traceable_artifacts(tmp_path: Path):
    spec = DesignSpec(
        layout="front_back", phone_width=76, phone_thickness=10,
        earbuds_width=65, earbuds_thickness=28, max_base_width=120,
    )

    def fake_generator(spec, run_dir, openscad_bin=None):
        run_dir.mkdir(parents=True, exist_ok=False)
        path = run_dir / "organizer.stl"
        trimesh.creation.box(extents=[82, 113, 10]).export(path)
        return path

    result = run_generation(spec, tmp_path, generator=fake_generator)
    assert result.spec_path.exists()
    assert result.report_path.exists()
    assert result.stl_path.exists()
```

- [ ] **Step 4: Implement isolated run directories and atomic success results**

Create `src/formpilot/pipeline.py`:

```python
import json
from pathlib import Path
from typing import Callable
from uuid import uuid4

from .design_spec import DesignSpec, GenerationResult
from .mesh_checker import check_mesh
from .model_generator import OpenScadError, generate_model
from .validator import calculate_base_size, validate_spec


class GenerationRejected(RuntimeError):
    pass


def run_generation(
    spec: DesignSpec,
    output_root: Path,
    generator: Callable = generate_model,
) -> GenerationResult:
    validation = validate_spec(spec)
    if not validation.passed:
        raise GenerationRejected(validation.issues[0].message)
    run_id = uuid4().hex[:12]
    run_dir = output_root / run_id
    try:
        stl_path = generator(spec, run_dir)
        expected_width, _ = calculate_base_size(spec)
        mesh_report = check_mesh(stl_path, expected_width)
    except (OpenScadError, OSError, ValueError) as error:
        raise GenerationRejected(f"模型生成或检查失败：{error}") from error
    if not mesh_report.passed:
        raise GenerationRejected("网格检查失败：" + ", ".join(mesh_report.issue_codes))
    spec_path = run_dir / "design.json"
    report_path = run_dir / "report.json"
    spec_path.write_text(spec.model_dump_json(indent=2), encoding="utf-8")
    report_path.write_text(mesh_report.model_dump_json(indent=2), encoding="utf-8")
    return GenerationResult(
        run_id=run_id,
        spec_path=spec_path,
        stl_path=stl_path,
        report_path=report_path,
        summary=f"模型已通过检查，尺寸 {mesh_report.extents} mm。",
    )
```

- [ ] **Step 5: Run and commit**

```bat
python -m pytest tests\test_mesh_checker.py tests\test_pipeline.py -v
python -m pytest -v
git add src\formpilot\mesh_checker.py src\formpilot\pipeline.py tests\test_mesh_checker.py tests\test_pipeline.py
git commit -m "feat: inspect and trace generated meshes"
```

---

### Task 5: OpenAI requirement parser with retry and manual fallback

**Files:**
- Create: `src/formpilot/requirement_parser.py`
- Create: `tests/test_requirement_parser.py`

**Interfaces:**
- Consumes: user text, `RequirementDecision`, `OPENAI_API_KEY`, `FORMPILOT_OPENAI_MODEL`.
- Produces: `OpenAIRequirementParser.parse(text) -> RequirementDecision` and `ParserUnavailable`.

- [ ] **Step 1: Write tests around an injected Responses client**

Create `tests/test_requirement_parser.py`:

```python
from types import SimpleNamespace
import pytest

from src.formpilot.requirement_parser import OpenAIRequirementParser, ParserUnavailable


class FakeResponses:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        value = next(self.outputs)
        if isinstance(value, Exception):
            raise value
        return SimpleNamespace(output_text=value)


def test_parses_structured_decision():
    output = '{"action":"ask_user","values":{"layout":null,"phone_width":76,"phone_thickness":null,"earbuds_width":null,"earbuds_thickness":null,"max_base_width":null},"missing_fields":["phone_thickness"],"message":"请填写手机厚度。"}'
    responses = FakeResponses([output])
    parser = OpenAIRequirementParser(client=SimpleNamespace(responses=responses))
    decision = parser.parse("手机宽 76 mm")
    assert decision.action.value == "ask_user"
    assert decision.values.phone_width == 76
    assert decision.missing_fields == ["phone_thickness"]


def test_retries_once_then_reports_manual_fallback():
    responses = FakeResponses([RuntimeError("offline"), RuntimeError("offline")])
    parser = OpenAIRequirementParser(client=SimpleNamespace(responses=responses))
    with pytest.raises(ParserUnavailable):
        parser.parse("生成收纳座")
    assert responses.calls == 2


def test_missing_api_key_reports_manual_fallback(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    parser = OpenAIRequirementParser()
    with pytest.raises(ParserUnavailable):
        parser.parse("生成收纳座")
```

- [ ] **Step 2: Verify failure**

```bat
python -m pytest tests\test_requirement_parser.py -v
```

Expected: import fails because `requirement_parser.py` does not exist.

- [ ] **Step 3: Implement Responses API Structured Outputs**

Create `src/formpilot/requirement_parser.py`:

```python
import os
from time import sleep

from openai import OpenAI

from .design_spec import RequirementDecision


class ParserUnavailable(RuntimeError):
    pass


INSTRUCTIONS = """你是桌面收纳设计需求解析器。所有长度单位必须是毫米。
只能选择 ask_user、generate、revise、explain 之一。
生成前必须获得 layout、phone_width、phone_thickness、earbuds_width、
earbuds_thickness、max_base_width。缺少字段时使用 ask_user，禁止猜测尺寸。
不要输出本 schema 以外的内容。"""


class OpenAIRequirementParser:
    def __init__(self, client=None, model: str | None = None):
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = client or (OpenAI(api_key=api_key) if api_key else None)
        self.model = model or os.getenv("FORMPILOT_OPENAI_MODEL", "gpt-5.4-mini")

    def parse(self, text: str) -> RequirementDecision:
        if self.client is None:
            raise ParserUnavailable("未配置 API 密钥，请使用手动参数模式。")
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                response = self.client.responses.create(
                    model=self.model,
                    instructions=INSTRUCTIONS,
                    input=text,
                    store=False,
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": "requirement_decision",
                            "strict": True,
                            "schema": RequirementDecision.model_json_schema(),
                        }
                    },
                )
                return RequirementDecision.model_validate_json(response.output_text)
            except Exception as error:
                last_error = error
                if attempt == 0:
                    sleep(0.25)
        raise ParserUnavailable("AI 解析暂不可用，请使用手动参数模式。") from last_error
```

The official OpenAI documentation specifies `json_schema` Structured Outputs for schema-conforming JSON and recommends it over the older JSON mode. Keep `store=False` because this application does not need server-side conversation storage.

- [ ] **Step 4: Run tests and commit**

```bat
python -m pytest tests\test_requirement_parser.py -v
python -m pytest -v
git add src\formpilot\requirement_parser.py tests\test_requirement_parser.py
git commit -m "feat: parse requirements with structured AI output"
```

---

### Task 6: Physical-feedback revision rules

**Files:**
- Create: `src/formpilot/revision.py`
- Create: `tests/test_revision.py`

**Interfaces:**
- Consumes: `DesignSpec` and `Feedback`.
- Produces: `RevisionResult` and `revise_from_feedback(spec, feedback) -> RevisionResult`.

- [ ] **Step 1: Write exact adjustment tests**

Create `tests/test_revision.py`:

```python
from src.formpilot.design_spec import DesignSpec, Feedback
from src.formpilot.revision import revise_from_feedback


def base_spec(clearance=1.2, base_thickness=5.0):
    return DesignSpec(
        layout="front_back", phone_width=76, phone_thickness=10,
        earbuds_width=65, earbuds_thickness=28, max_base_width=120,
        clearance=clearance, base_thickness=base_thickness,
    )


def test_tight_fit_adds_clearance_and_unstable_base_adds_thickness():
    feedback = Feedback(
        phone_fit="too_tight", earbuds_fit="good", stability="unstable"
    )
    result = revise_from_feedback(base_spec(), feedback)
    assert result.spec.clearance == 1.5
    assert result.spec.base_thickness == 6.0
    assert len(result.changes) == 2


def test_loose_fit_never_drops_below_minimum():
    feedback = Feedback(
        phone_fit="too_loose", earbuds_fit="too_loose", stability="stable"
    )
    result = revise_from_feedback(base_spec(clearance=0.5), feedback)
    assert result.spec.clearance == 0.5
```

- [ ] **Step 2: Implement immutable revision output**

Create `src/formpilot/revision.py`:

```python
from pydantic import BaseModel

from .design_spec import DesignSpec, Feedback


class RevisionResult(BaseModel):
    spec: DesignSpec
    changes: list[str]


def revise_from_feedback(spec: DesignSpec, feedback: Feedback) -> RevisionResult:
    clearance = spec.clearance
    changes: list[str] = []
    fits = {feedback.phone_fit, feedback.earbuds_fit}
    if "too_tight" in fits:
        clearance = min(2.5, round(clearance + 0.3, 2))
        changes.append(f"配合间隙增加到 {clearance:.1f} mm")
    elif "too_loose" in fits:
        clearance = max(0.5, round(clearance - 0.2, 2))
        if clearance != spec.clearance:
            changes.append(f"配合间隙减少到 {clearance:.1f} mm")
    thickness = spec.base_thickness
    if feedback.stability == "unstable" and thickness < 10:
        thickness = min(10.0, thickness + 1.0)
        changes.append(f"底板厚度增加到 {thickness:.1f} mm")
    revised = spec.model_copy(update={
        "clearance": clearance,
        "base_thickness": thickness,
    })
    return RevisionResult(spec=revised, changes=changes)
```

- [ ] **Step 3: Run and commit**

```bat
python -m pytest tests\test_revision.py -v
python -m pytest -v
git add src\formpilot\revision.py tests\test_revision.py
git commit -m "feat: revise designs from print feedback"
```

---

### Task 7: One-page Gradio application

**Files:**
- Create: `app.py`
- Create: `scripts/run.bat`
- Create: `tests/test_app.py`

**Interfaces:**
- Consumes: parser, `DesignSpec`, pipeline, revision functions.
- Produces: `build_app() -> gr.Blocks`, `handle_parse(text)`, `handle_generate(...)`, and a browser-accessible local demo.

- [ ] **Step 1: Write a smoke test before UI code**

Create `tests/test_app.py`:

```python
import gradio as gr

from app import build_app


def test_build_app_returns_blocks_without_launching_server():
    demo = build_app()
    assert isinstance(demo, gr.Blocks)
```

- [ ] **Step 2: Verify failure**

```bat
python -m pytest tests\test_app.py -v
```

Expected: import fails because `app.py` does not exist.

- [ ] **Step 3: Build the page without mixing domain logic into callbacks**

Create `app.py` with these exact callback responsibilities:

```python
from pathlib import Path
import gradio as gr
from pydantic import ValidationError

from src.formpilot.design_spec import DesignSpec, Feedback
from src.formpilot.pipeline import GenerationRejected, run_generation
from src.formpilot.requirement_parser import OpenAIRequirementParser, ParserUnavailable
from src.formpilot.revision import revise_from_feedback

OUTPUTS = Path(__file__).parent / "outputs"


def handle_parse(text: str):
    if not text.strip():
        return {}, "请先描述你的收纳需求。"
    try:
        decision = OpenAIRequirementParser().parse(text)
        return decision.values.model_dump(exclude_none=True), decision.message
    except ParserUnavailable as error:
        return {}, str(error)


def handle_generate(layout, phone_width, phone_thickness, earbuds_width,
                    earbuds_thickness, max_base_width, clearance,
                    base_thickness, slot_depth, phone_tilt_degrees,
                    cable_hole_enabled, cable_hole_diameter):
    try:
        spec = DesignSpec(
            layout=layout,
            phone_width=phone_width,
            phone_thickness=phone_thickness,
            earbuds_width=earbuds_width,
            earbuds_thickness=earbuds_thickness,
            max_base_width=max_base_width,
            clearance=clearance,
            base_thickness=base_thickness,
            slot_depth=slot_depth,
            phone_tilt_degrees=phone_tilt_degrees,
            cable_hole_enabled=cable_hole_enabled,
            cable_hole_diameter=cable_hole_diameter,
        )
        result = run_generation(spec, OUTPUTS)
        return (
            result.stl_path, result.stl_path, result.spec_path,
            result.summary, spec.model_dump(mode="json"),
        )
    except (ValidationError, GenerationRejected, OSError) as error:
        return gr.skip(), gr.skip(), gr.skip(), f"生成失败：{error}", gr.skip()


def handle_revision(spec_data, phone_fit, earbuds_fit, stability, notes):
    if not spec_data:
        return gr.skip(), gr.skip(), gr.skip(), "请先成功生成 V1。", gr.skip()
    try:
        spec = DesignSpec.model_validate(spec_data)
        feedback = Feedback(
            phone_fit=phone_fit,
            earbuds_fit=earbuds_fit,
            stability=stability,
            notes=notes,
        )
        revision = revise_from_feedback(spec, feedback)
        result = run_generation(revision.spec, OUTPUTS)
        feedback_path = result.stl_path.parent / "feedback.json"
        feedback_path.write_text(feedback.model_dump_json(indent=2), encoding="utf-8")
        summary = "V2 已生成：" + "；".join(revision.changes or ["参数无需调整"])
        return (
            result.stl_path, result.stl_path, result.spec_path,
            summary, revision.spec.model_dump(mode="json"),
        )
    except (ValidationError, GenerationRejected, OSError) as error:
        return gr.skip(), gr.skip(), gr.skip(), f"修订失败：{error}", gr.skip()


def build_app() -> gr.Blocks:
    with gr.Blocks(title="FormPilot") as demo:
        gr.Markdown("# FormPilot\nAI 参数化桌面收纳设计师")
        with gr.Row():
            with gr.Column():
                requirement = gr.Textbox(label="需求描述", lines=3)
                parse_button = gr.Button("AI 解析需求")
                layout = gr.Radio(
                    ["side_by_side", "front_back"], value="front_back", label="布局"
                )
                phone_width = gr.Number(value=76, label="手机宽度 / mm")
                phone_thickness = gr.Number(value=10, label="手机厚度 / mm")
                earbuds_width = gr.Number(value=65, label="耳机盒宽度 / mm")
                earbuds_thickness = gr.Number(value=28, label="耳机盒厚度 / mm")
                max_base_width = gr.Number(value=180, label="最大底座宽度 / mm")
                clearance = gr.Slider(0.5, 2.5, value=1.2, step=0.1, label="配合间隙 / mm")
                base_thickness = gr.Slider(4, 10, value=5, step=0.5, label="底板厚度 / mm")
                slot_depth = gr.Slider(10, 25, value=15, step=1, label="插槽深度 / mm")
                phone_tilt = gr.Slider(0, 25, value=15, step=1, label="手机倾角 / °")
                cable_hole = gr.Checkbox(value=True, label="理线孔")
                cable_hole_diameter = gr.Slider(5, 15, value=8, step=1, label="理线孔直径 / mm")
                generate_button = gr.Button("生成可打印模型", variant="primary")
            with gr.Column():
                model = gr.Model3D(label="3D 预览")
                status = gr.Markdown()
                stl_download = gr.File(label="下载 STL")
                json_download = gr.File(label="下载参数 JSON")
                with gr.Accordion("打印反馈与 V2", open=False):
                    phone_fit = gr.Radio(
                        ["too_tight", "good", "too_loose"], value="good", label="手机槽"
                    )
                    earbuds_fit = gr.Radio(
                        ["too_tight", "good", "too_loose"], value="good", label="耳机槽"
                    )
                    stability = gr.Radio(
                        ["stable", "unstable"], value="stable", label="稳定性"
                    )
                    notes = gr.Textbox(label="实物备注", lines=2)
                    revise_button = gr.Button("根据反馈生成 V2")
        current_spec = gr.State()
        parsed_values = gr.JSON(label="AI 解析出的结构化参数")
        parse_button.click(handle_parse, requirement, [parsed_values, status])
        inputs = [layout, phone_width, phone_thickness, earbuds_width,
                  earbuds_thickness, max_base_width, clearance,
                  base_thickness, slot_depth, phone_tilt,
                  cable_hole, cable_hole_diameter]
        outputs = [model, stl_download, json_download, status, current_spec]
        generate_button.click(
            handle_generate, inputs, outputs
        )
        revise_button.click(
            handle_revision,
            [current_spec, phone_fit, earbuds_fit, stability, notes],
            outputs,
        )
    return demo


if __name__ == "__main__":
    build_app().launch(inbrowser=True)
```

The MVP displays parsed JSON beside the editable form instead of automatically mutating every field. This keeps the AI result inspectable and preserves a complete manual fallback.

- [ ] **Step 4: Add the Windows launcher**

Create `scripts/run.bat`:

```bat
@echo off
setlocal
cd /d "%~dp0.."
call .venv\Scripts\activate.bat
python app.py
endlocal
```

- [ ] **Step 5: Run tests and manual UI smoke test**

```bat
python -m pytest tests\test_app.py -v
python -m pytest -v
scripts\run.bat
```

Manually verify that the page opens, manual inputs generate a preview, and API failure produces the manual-mode message without breaking generation.

- [ ] **Step 6: Commit**

```bat
git add app.py scripts\run.bat tests\test_app.py
git commit -m "feat: add FormPilot one-page demo"
```

---

### Task 8: Offline examples, end-to-end acceptance, and documentation

**Files:**
- Create: `examples/normal-front-back.json`
- Create: `examples/normal-side-by-side.json`
- Create: `examples/invalid-too-narrow.json`
- Create: `tests/test_acceptance.py`
- Create: `README.md`

**Interfaces:**
- Consumes: all completed modules.
- Produces: reproducible offline demo inputs, acceptance evidence, and setup documentation.

- [ ] **Step 1: Add three explicit example payloads**

Use the canonical keys from `DesignSpec`. The front-back example uses `max_base_width=120`; the side-by-side example uses `max_base_width=180`; the invalid example uses the side-by-side layout and `max_base_width=150` so validation must reject it.

- [ ] **Step 2: Add acceptance tests for five device-size combinations**

Create `tests/test_acceptance.py` with a parametrized test that injects a Trimesh-box generator into `run_generation`:

```python
from pathlib import Path
import pytest
import trimesh

from src.formpilot.design_spec import DesignSpec
from src.formpilot.pipeline import run_generation
from src.formpilot.validator import calculate_base_size


CASES = [
    (60, 8, 45, 20),
    (68, 9, 52, 24),
    (76, 10, 65, 28),
    (82, 12, 72, 35),
    (90, 15, 85, 45),
]


@pytest.mark.parametrize("pw,pt,ew,et", CASES)
def test_five_supported_device_sizes(tmp_path: Path, pw, pt, ew, et):
    spec = DesignSpec(
        layout="front_back", phone_width=pw, phone_thickness=pt,
        earbuds_width=ew, earbuds_thickness=et, max_base_width=120,
    )

    def box_generator(spec, run_dir, openscad_bin=None):
        run_dir.mkdir(parents=True, exist_ok=False)
        width, depth = calculate_base_size(spec)
        path = run_dir / "organizer.stl"
        trimesh.creation.box(extents=[width, depth, 10]).export(path)
        return path

    result = run_generation(spec, tmp_path, generator=box_generator)
    assert result.stl_path.stat().st_size > 0
```

- [ ] **Step 3: Run the complete automated verification**

```bat
python -m pytest -v
```

Expected: every test passes with no live API request and no requirement for OpenSCAD in unit tests.

- [ ] **Step 4: Write README with reproducible operator steps**

The README must contain, in this order:

1. One-sentence product pitch.
2. 60-second demo flow.
3. Architecture diagram using the exact pipeline from the spec.
4. Windows prerequisites: Python 3.11 and OpenSCAD.
5. Approved installation command: `scripts\setup.bat`.
6. Environment variables and an example that uses `set`, never a real key.
7. Start command: `scripts\run.bat`.
8. Test command: `python -m pytest -v`.
9. Manual fallback behavior.
10. Manufacturing assumptions and millimetre units.
11. Known limitations copied from the design spec.
12. V1/V2 evidence section that is completed only after physical feedback exists.
13. Links to the design spec, implementation plan, OpenSCAD docs, Trimesh docs, Gradio Model3D docs, and official OpenAI Structured Outputs documentation.

- [ ] **Step 5: Commit**

```bat
git add examples tests\test_acceptance.py README.md
git commit -m "docs: add reproducible demo and acceptance coverage"
```

---

### Task 9: Real STL, print order, revision evidence, and portfolio package

**Files:**
- Create: `outputs/<run-id>/organizer.stl` through the application
- Create: `outputs/<run-id>/design.json` through the application
- Create: `portfolio/v1-parameters.json`
- Create: `portfolio/feedback.json`
- Create: `portfolio/v2-parameters.json`
- Create: `portfolio/architecture.png`
- Create: `portfolio/physical-result.jpg` after delivery
- Create: `portfolio/demo.mp4`
- Modify: `README.md`

**Interfaces:**
- Consumes: complete application, the user's measured device dimensions, and physical feedback.
- Produces: truthful manufacturing evidence and a 60–90 second portfolio demonstration.

- [ ] **Step 1: Generate the real V1 model**

Measure devices including cases, enter the measurements manually, generate V1, and retain the run's STL, JSON, and report. Open the STL in the target slicer and confirm scale is in millimetres, the model is on the build plate, and no mesh error is reported.

- [ ] **Step 2: Place only the approved V1 print order**

Before ordering, confirm the quoted total keeps project spending under CNY 500. Request PLA, ordinary layer height, no painting, and a screenshot of the slicer preview. This external purchase requires the user's explicit approval at execution time.

- [ ] **Step 3: Record feedback without overstating completion**

After delivery, measure the print and save `portfolio/feedback.json` using the exact `Feedback` schema. Until the part arrives, the README wording must remain “已完成可制造性校验并送印”; only change it to “已完成实物闭环” after physical inspection.

- [ ] **Step 4: Generate and document V2**

Run `revise_from_feedback`, save V1, feedback, and V2 JSON files, generate V2 STL, and add a compact comparison table to README. Print V2 only if the change has a clear validation purpose and the remaining approved budget covers it.

- [ ] **Step 5: Create the portfolio assets**

The architecture image must show the deterministic boundary between AI and geometry. The video sequence is:

1. 0–10 s: user problem and natural-language request.
2. 10–25 s: missing-size question and completed parameter form.
3. 25–45 s: generated 3D preview and manufacturing checks.
4. 45–60 s: STL download and slicer preview.
5. 60–80 s: physical result and V1-to-V2 changes.
6. 80–90 s: architecture summary and limitations.

- [ ] **Step 6: Final verification and commit**

Run:

```bat
python -m pytest -v
git status --short
```

Manually launch `scripts\run.bat`, execute the offline/manual demo once, then execute one live AI parse if an approved API key is available. Check that no API key, `.env`, or generated temporary file is staged.

```bat
git add README.md portfolio
git commit -m "docs: add FormPilot manufacturing evidence"
```

Expected final evidence: passing tests, a slicer-valid STL, an order or physical-print record, traceable V1/feedback/V2 files, and a 60–90 second demo.

## Implementation Checkpoints

- End of Day 1: Tasks 1–2 pass without OpenSCAD.
- End of Day 2: Task 3 generates the real V1 STL and the print order is ready for approval.
- End of Day 3: Task 7 manual-mode UI can preview and download a model.
- End of Day 4: Task 5 AI parse and fallback work.
- End of Day 5: Tasks 4, 6, and 8 pass as a complete automated suite.
- End of Day 6: physical feedback is recorded if delivered; otherwise the wording remains “送印”.
- End of Day 7: Task 9 portfolio package and final verification are complete.

## Official Technical References

- OpenAI Responses API Structured Outputs: https://developers.openai.com/api/reference/cli/resources/beta/subresources/responses
- GPT-5.4 Mini model capabilities: https://developers.openai.com/api/docs/models/gpt-5.4-mini
- OpenSCAD command-line export: https://files.openscad.org/documentation/manual/Using_OpenSCAD_in_a_command_line_environment.html
- Trimesh repair and watertight checks: https://trimesh.org/trimesh.repair.html
- Gradio Model3D: https://gradio.app/main/docs/gradio/model3d
