# FormPilot

FormPilot turns a phone-and-earbuds brief into a validated, printable desk-organizer design.

## 60–90 second demo flow

1. Run `scripts\setup.bat`, then `scripts\run.bat`.
2. Enter a natural-language brief, or provide the device measurements manually.
3. Review the status summary and interactive 3D preview, then download the STL and `design.json` for inspection.
4. For a reproducible offline check, copy the values from `examples\normal-front-back.json` into the manual form, or run the test suite.

Use the [truthful recording script](portfolio/demo-script.md) for a portfolio walkthrough. It keeps physical-fit evidence and V2 explicitly pending until a real print is tested.

## Architecture

![FormPilot architecture](portfolio/architecture.png)

The system map separates AI-assisted intent parsing from deterministic validation, geometry generation, mesh inspection, and revision math. The physical-feedback stage is marked `PENDING` because no printed-fit result is claimed yet.

## Windows prerequisites

Use the portable tool layout on the D drive: place `uv.exe` at `<repo-root>\.tools\uv\uv.exe` and keep the portable Python installation under `<repo-root>\.tools\python`. Install or point `OPENSCAD_BIN` at a local OpenSCAD executable before generating models.

`scripts\setup.bat` creates its virtual environment and temporary files inside the project, installs managed Python 3.11 through uv when no override is supplied, and keeps uv's cache in `<repo-root>\.cache\uv`.

## Installation

```bat
scripts\setup.bat
```

## Environment variables

Use Windows `set` commands with a placeholder key only. OpenRouter is the recommended default provider; its free-tier availability and rate limits may change. Never commit API keys. `FORMPILOT_UV` may point to a portable uv executable and `FORMPILOT_PYTHON` may point to a specific Python executable; otherwise setup requires `<repo-root>\.tools\uv\uv.exe` and requests Python 3.11 from uv.

### OpenRouter (recommended and default)

```bat
set OPENROUTER_API_KEY=your-openrouter-key-here
```

### DeepSeek

```bat
set FORMPILOT_AI_PROVIDER=deepseek
set DEEPSEEK_API_KEY=your-deepseek-key-here
```

### OpenAI

```bat
set FORMPILOT_AI_PROVIDER=openai
set OPENAI_API_KEY=your-openai-key-here
```

### Optional model override

Set this only when you want to override the selected provider's default model.

```bat
set FORMPILOT_AI_MODEL=your-model-name
```

### Other runtime variables

```bat
set OPENSCAD_BIN=openscad.com
set FORMPILOT_UV=D:\portable-tools\uv.exe
set FORMPILOT_PYTHON=D:\portable-tools\python.exe
```

`FORMPILOT_AI_PROVIDER` defaults to `openrouter`; supported values are `openrouter`, `deepseek`, and `openai`. `FORMPILOT_AI_MODEL` is optional. For backwards compatibility, `FORMPILOT_OPENAI_MODEL` remains an OpenAI-only fallback when `FORMPILOT_AI_MODEL` is unset. `OPENSCAD_BIN` may instead be a portable path to `openscad.com`.

## Start

```bat
scripts\run.bat
```

## Tests

Run from the D-drive project directory so all temporary files remain under its `.tmp` folder:

```bat
set TMP=%CD%\.tmp
set TEMP=%CD%\.tmp
.venv\Scripts\python.exe -m pytest -v
```

## Manual fallback

If structured parsing is unavailable or incomplete, enter the required measurements and layout manually; FormPilot validates the resulting `DesignSpec` before generation.

## Manufacturing assumptions and units

FormPilot assumes a flat desk and that the maker verifies dimensions and fit before printing; all dimensions are in millimetres (mm).

## Known limitations

FormPilot does not provide photo measurement, arbitrary/free-form modelling, image-to-3D, automatic Taobao ordering, accounts or a cloud multi-user service, a multi-Agent framework, or professional slicing/printer control. The MVP uses one shared clearance for both holders; when revision feedback conflicts, a too-tight fit takes precedence over a too-loose fit. A failed mesh inspection is rejected and reported; FormPilot does not automatically regenerate a replacement mesh.

## Reference V1 and physical evidence

A generic front-back reference V1 has passed the automated manufacturing checks with an 82 × 113 × 20 mm mesh. Its assumed device sizes are recorded in `portfolio/v1-parameters.json`; they are demonstration values, not measurements of the user's devices. The reference has not been ordered or physically fitted.

V1/V2 physical-fit evidence remains pending until a measured model is printed and inspected. This repository does not claim a completed physical feedback loop.

## References

- Local [design specification](docs/superpowers/specs/2026-09-08-formpilot-design.md) and [implementation plan](docs/superpowers/plans/2026-09-08-formpilot-implementation.md)
- [OpenSCAD documentation](https://openscad.org/documentation.html)
- [Trimesh documentation](https://trimesh.org/)
- [Gradio Model3D documentation](https://www.gradio.app/docs/gradio/model3d)
- [OpenAI structured outputs guide](https://platform.openai.com/docs/guides/structured-outputs)
