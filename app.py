from pathlib import Path

import gradio as gr
from pydantic import ValidationError

from src.formpilot.design_spec import DesignSpec, Feedback
from src.formpilot.pipeline import GenerationRejected, run_generation
from src.formpilot.requirement_parser import OpenAIRequirementParser, ParserUnavailable
from src.formpilot.revision import revise_from_feedback


OUTPUTS = Path(__file__).resolve().parent / "outputs"


def handle_parse(text: str):
    if not text.strip():
        return {}, "请先描述你的收纳需求。"
    try:
        decision = OpenAIRequirementParser().parse(text)
        return decision.values.model_dump(exclude_none=True), decision.message
    except ParserUnavailable:
        return {}, "AI 解析暂不可用，请使用手动参数。"


def handle_generate(
    layout,
    phone_width,
    phone_thickness,
    earbuds_width,
    earbuds_thickness,
    max_base_width,
    clearance,
    base_thickness,
    slot_depth,
    phone_tilt_degrees,
    cable_hole_enabled,
    cable_hole_diameter,
):
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
            str(result.stl_path),
            str(result.stl_path),
            str(result.spec_path),
            result.summary,
            spec.model_dump(mode="json"),
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
            str(result.stl_path),
            str(result.stl_path),
            str(result.spec_path),
            summary,
            revision.spec.model_dump(mode="json"),
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
                    ["side_by_side", "front_back"],
                    value="front_back",
                    label="布局",
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
                        ["too_tight", "good", "too_loose"],
                        value="good",
                        label="手机槽",
                    )
                    earbuds_fit = gr.Radio(
                        ["too_tight", "good", "too_loose"],
                        value="good",
                        label="耳机槽",
                    )
                    stability = gr.Radio(
                        ["stable", "unstable"], value="stable", label="稳定性"
                    )
                    notes = gr.Textbox(label="实物备注", lines=2)
                    revise_button = gr.Button("根据反馈生成 V2")
        current_spec = gr.State()
        parsed_values = gr.JSON(label="AI 解析出的结构化参数")
        parse_button.click(handle_parse, requirement, [parsed_values, status])
        inputs = [
            layout,
            phone_width,
            phone_thickness,
            earbuds_width,
            earbuds_thickness,
            max_base_width,
            clearance,
            base_thickness,
            slot_depth,
            phone_tilt,
            cable_hole,
            cable_hole_diameter,
        ]
        outputs = [model, stl_download, json_download, status, current_spec]
        generate_button.click(handle_generate, inputs, outputs)
        revise_button.click(
            handle_revision,
            [current_spec, phone_fit, earbuds_fit, stability, notes],
            outputs,
        )
    return demo


if __name__ == "__main__":
    build_app().launch(inbrowser=True)
