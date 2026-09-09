# FormPilot

FormPilot turns a phone-and-earbuds brief into a validated, printable desk-organizer design.

## 60-second demo flow

1. Run `scripts\setup.bat`, then `scripts\run.bat`.
2. Enter a natural-language brief, or provide the device measurements manually.
3. Review the proposed `DesignSpec`, validation result, and generated preview/download.
4. For a reproducible offline check, copy the values from `examples\normal-front-back.json` into the manual form, or run the test suite.

## Architecture

```mermaid
flowchart LR
    A[Natural language / manual input] --> B[Structured parser / manual fallback]
    B --> C[DesignSpec]
    C --> D[Validation]
    D --> E[OpenSCAD]
    E --> F[Trimesh]
    F --> G[Preview / download]
    G --> H[Physical feedback]
    H --> I[Deterministic V2 revision]
```

## Windows prerequisites

Use the portable tool layout on the D drive: place `uv.exe` at `<repo-root>\.tools\uv\uv.exe` and keep the portable Python installation under `<repo-root>\.tools\python`. Install or point `OPENSCAD_BIN` at a local OpenSCAD executable before generating models.

`scripts\setup.bat` creates its virtual environment and temporary files inside the project, installs managed Python 3.11 through uv when no override is supplied, and keeps uv's cache in `<repo-root>\.cache\uv`.

## Installation

```bat
scripts\setup.bat
```

## Environment variables

Use Windows `set` commands with a placeholder key only. `FORMPILOT_UV` may point to a portable uv executable and `FORMPILOT_PYTHON` may point to a specific Python executable; otherwise setup requires `<repo-root>\.tools\uv\uv.exe` and requests Python 3.11 from uv.

```bat
set OPENAI_API_KEY=your-api-key-here
set FORMPILOT_OPENAI_MODEL=gpt-4.1-mini
set OPENSCAD_BIN=openscad.com
set FORMPILOT_UV=D:\portable-tools\uv.exe
set FORMPILOT_PYTHON=D:\portable-tools\python.exe
```

`FORMPILOT_OPENAI_MODEL` is optional. `OPENSCAD_BIN` may instead be a portable path to `openscad.com`.

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
