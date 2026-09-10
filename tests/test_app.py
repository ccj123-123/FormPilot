from pathlib import Path
from types import SimpleNamespace

import gradio as gr
import trimesh

import app
from src.formpilot.design_spec import DesignSpec, Feedback
from src.formpilot.requirement_parser import ParserUnavailable


def sample_spec() -> DesignSpec:
    return DesignSpec(
        layout="front_back",
        phone_width=76,
        phone_thickness=10,
        earbuds_width=65,
        earbuds_thickness=28,
        max_base_width=120,
    )


def generation_result(tmp_path: Path, name: str = "v1") -> SimpleNamespace:
    run_dir = tmp_path / name
    run_dir.mkdir()
    stl_path = run_dir / "organizer.stl"
    spec_path = run_dir / "design.json"
    trimesh.creation.box(extents=(10, 12, 8)).export(stl_path)
    spec_path.write_text("{}", encoding="utf-8")
    return SimpleNamespace(stl_path=stl_path, spec_path=spec_path, summary="已通过检查")


def generate_args() -> tuple:
    return (
        "front_back",
        76,
        10,
        65,
        28,
        120,
        1.2,
        5,
        15,
        15,
        True,
        8,
    )


def assert_glb_preview(preview: str, stl_path: Path) -> None:
    preview_path = Path(preview)
    assert preview_path.suffix == ".glb"
    assert preview_path.parent == stl_path.parent
    assert preview_path != stl_path
    mesh = trimesh.load_mesh(preview_path, force="mesh", process=False)
    assert len(mesh.faces) > 0


def test_build_app_returns_blocks_without_launching_server():
    demo = app.build_app()

    assert isinstance(demo, gr.Blocks)


def test_handle_parse_blank_input_returns_chinese_prompt():
    values, message = app.handle_parse("   ")

    assert values == {}
    assert message == "请先描述你的收纳需求。"


def test_handle_parse_parser_unavailable_keeps_manual_mode(monkeypatch):
    class OfflineParser:
        def parse(self, text):
            raise ParserUnavailable("AI 解析不可用，请使用手动参数。")

    monkeypatch.setattr(app, "OpenAIRequirementParser", OfflineParser)

    values, message = app.handle_parse("做一个收纳架")

    assert values == {}
    assert "手动" in message


def test_handle_parse_returns_inspectable_parser_values(monkeypatch):
    expected = {
        "layout": "front_back",
        "phone_width": 76.0,
        "phone_thickness": 10.0,
        "earbuds_width": 65.0,
        "earbuds_thickness": 28.0,
        "max_base_width": 120.0,
    }

    class SuccessfulParser:
        def parse(self, text):
            return SimpleNamespace(
                values=SimpleNamespace(model_dump=lambda **kwargs: expected),
                message="已提取参数，请在手动表单中确认。",
            )

    monkeypatch.setattr(app, "OpenAIRequirementParser", SuccessfulParser)

    values, message = app.handle_parse("手机 76 mm，耳机盒 65 mm")

    assert values == expected
    assert message == "已提取参数，请在手动表单中确认。"


def test_handle_generate_returns_preview_downloads_and_json_state(monkeypatch, tmp_path):
    result = generation_result(tmp_path)
    monkeypatch.setattr(app, "OUTPUTS", tmp_path)
    monkeypatch.setattr(app, "run_generation", lambda spec, output_root: result)

    preview, stl, design_json, status, state = app.handle_generate(*generate_args())

    assert_glb_preview(preview, result.stl_path)
    assert (stl, design_json) == (str(result.stl_path), str(result.spec_path))
    assert all(isinstance(path, str) for path in (preview, stl, design_json))
    assert gr.File().postprocess(stl).path == str(result.stl_path)
    assert status == "已通过检查"
    assert state == sample_spec().model_dump(mode="json")


def test_handle_generate_failure_keeps_previous_outputs(monkeypatch):
    def reject(spec, output_root):
        raise app.GenerationRejected("OpenSCAD 不可用")

    monkeypatch.setattr(app, "run_generation", reject)

    preview, stl, design_json, status, state = app.handle_generate(*generate_args())

    assert preview == gr.skip()
    assert stl == gr.skip()
    assert design_json == gr.skip()
    assert "生成失败" in status
    assert state == gr.skip()


def test_handle_generate_keeps_downloads_when_glb_preview_fails(
    monkeypatch, tmp_path
):
    result = generation_result(tmp_path)
    monkeypatch.setattr(app, "run_generation", lambda spec, output_root: result)
    monkeypatch.setattr(
        app,
        "build_browser_preview",
        lambda stl_path: (_ for _ in ()).throw(ValueError("GLB export failed")),
    )

    preview, stl, design_json, status, state = app.handle_generate(*generate_args())

    assert preview is None
    assert (stl, design_json) == (str(result.stl_path), str(result.spec_path))
    assert "网页预览失败" in status
    assert "STL 和 JSON 仍可下载" in status
    assert state == sample_spec().model_dump(mode="json")


def test_handle_revision_requires_successful_v1():
    preview, stl, design_json, status, state = app.handle_revision(
        None, "good", "good", "stable", ""
    )

    assert preview == gr.skip()
    assert stl == gr.skip()
    assert design_json == gr.skip()
    assert status == "请先成功生成 V1。"
    assert state == gr.skip()


def assert_revision_failure(result):
    preview, stl, design_json, status, state = result

    assert preview == gr.skip()
    assert stl == gr.skip()
    assert design_json == gr.skip()
    assert "修订失败" in status
    assert state == gr.skip()


def test_handle_revision_keeps_v1_outputs_when_revision_rule_rejects(monkeypatch):
    def reject(spec, feedback):
        raise app.GenerationRejected("反馈参数不可修订")

    monkeypatch.setattr(app, "revise_from_feedback", reject)

    result = app.handle_revision(
        sample_spec().model_dump(mode="json"),
        "too_tight",
        "good",
        "stable",
        "略紧",
    )

    assert_revision_failure(result)


def test_handle_revision_keeps_v1_outputs_when_v2_generation_rejects(
    monkeypatch,
):
    def reject(spec, output_root):
        raise app.GenerationRejected("V2 网格检查失败")

    monkeypatch.setattr(app, "run_generation", reject)

    result = app.handle_revision(
        sample_spec().model_dump(mode="json"),
        "too_tight",
        "good",
        "stable",
        "略紧",
    )

    assert_revision_failure(result)


def test_handle_revision_keeps_v1_outputs_when_feedback_write_fails(monkeypatch, tmp_path):
    v2 = generation_result(tmp_path, "v2")

    def reject_write(self, text, encoding):
        raise OSError("反馈文件不可写")

    monkeypatch.setattr(app, "run_generation", lambda spec, output_root: v2)
    monkeypatch.setattr(type(v2.stl_path), "write_text", reject_write)

    result = app.handle_revision(
        sample_spec().model_dump(mode="json"),
        "too_tight",
        "good",
        "stable",
        "略紧",
    )

    assert_revision_failure(result)


def test_handle_revision_writes_feedback_and_returns_v2_state(monkeypatch, tmp_path):
    v2 = generation_result(tmp_path, "v2")
    revised = sample_spec().model_copy(update={"clearance": 1.5})
    monkeypatch.setattr(app, "OUTPUTS", tmp_path)
    monkeypatch.setattr(
        app,
        "revise_from_feedback",
        lambda spec, feedback: SimpleNamespace(spec=revised, changes=["间隙已调整"]),
    )
    monkeypatch.setattr(app, "run_generation", lambda spec, output_root: v2)

    preview, stl, design_json, status, state = app.handle_revision(
        sample_spec().model_dump(mode="json"),
        "too_tight",
        "good",
        "stable",
        "略紧",
    )

    assert_glb_preview(preview, v2.stl_path)
    assert (stl, design_json) == (str(v2.stl_path), str(v2.spec_path))
    assert all(isinstance(path, str) for path in (preview, stl, design_json))
    assert status == "V2 已生成：间隙已调整"
    assert state == revised.model_dump(mode="json")
    feedback = Feedback.model_validate_json(
        (v2.stl_path.parent / "feedback.json").read_text(encoding="utf-8")
    )
    assert feedback.notes == "略紧"


def test_handle_revision_keeps_downloads_when_glb_preview_fails(
    monkeypatch, tmp_path
):
    v2 = generation_result(tmp_path, "v2")
    revised = sample_spec().model_copy(update={"clearance": 1.5})
    monkeypatch.setattr(
        app,
        "revise_from_feedback",
        lambda spec, feedback: SimpleNamespace(spec=revised, changes=["间隙已调整"]),
    )
    monkeypatch.setattr(app, "run_generation", lambda spec, output_root: v2)
    monkeypatch.setattr(
        app,
        "build_browser_preview",
        lambda stl_path: (_ for _ in ()).throw(ValueError("GLB export failed")),
    )

    preview, stl, design_json, status, state = app.handle_revision(
        sample_spec().model_dump(mode="json"),
        "too_tight",
        "good",
        "stable",
        "略紧",
    )

    assert preview is None
    assert (stl, design_json) == (str(v2.stl_path), str(v2.spec_path))
    assert "网页预览失败" in status
    assert "STL 和 JSON 仍可下载" in status
    assert state == revised.model_dump(mode="json")
    assert (v2.stl_path.parent / "feedback.json").is_file()
