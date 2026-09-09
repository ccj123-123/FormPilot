from pathlib import Path
import os
import shutil
import subprocess


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SETUP = PROJECT_ROOT / "scripts" / "setup.bat"
RUN = PROJECT_ROOT / "scripts" / "run.bat"


def make_controlled_project(tmp_path: Path) -> Path:
    project = tmp_path / "portable-repo" / ".worktrees" / "project"
    scripts = project / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(SETUP, scripts / "setup.bat")
    shutil.copy2(RUN, scripts / "run.bat")
    (project / "requirements.txt").write_text("", encoding="utf-8")
    return project


def run_setup(project: Path, extra_environment: dict[str, str] | None = None):
    environment = os.environ | (extra_environment or {})
    return subprocess.run(
        ["cmd.exe", "/d", "/c", str(project / "scripts" / "setup.bat")],
        cwd=project,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def write_fake_uv(path: Path, venv_exit: int = 0, pip_exit: int = 0) -> None:
    path.write_text(
        "@echo off\n"
        "if \"%1\"==\"venv\" (\n"
        "  > %FORMPILOT_TMP%\\uv-venv.txt echo %*\n"
        f"  if not \"{venv_exit}\"==\"0\" exit /b {venv_exit}\n"
        "  mkdir .venv\\Scripts\n"
        "  > .venv\\Scripts\\activate.bat echo @echo off\n"
        "  > %FORMPILOT_TMP%\\uv-python-dir.txt echo %UV_PYTHON_INSTALL_DIR%\n"
        "  exit /b 0\n"
        ")\n"
        "if \"%1\"==\"pip\" (\n"
        "  > %FORMPILOT_TMP%\\pip-called.txt echo %*\n"
        f"  exit /b {pip_exit}\n"
        ")\n"
        "exit /b 99\n",
        encoding="utf-8",
    )


def test_setup_fails_before_creating_a_venv_when_portable_uv_is_missing(
    tmp_path: Path,
):
    project = make_controlled_project(tmp_path)

    result = run_setup(project)

    assert result.returncode != 0
    assert "Portable uv was not found" in result.stdout
    assert not (project / ".venv").exists()


def test_setup_uses_overridden_uv_with_project_local_state(tmp_path: Path):
    project = make_controlled_project(tmp_path)
    fake_uv = tmp_path / "fake-uv.bat"
    write_fake_uv(fake_uv)

    result = run_setup(project, {"FORMPILOT_UV": str(fake_uv)})

    assert result.returncode == 0, result.stdout + result.stderr
    assert (project / ".tmp" / "uv-venv.txt").read_text(encoding="utf-8").strip() == "venv --managed-python --python 3.11 .venv"
    assert (project / ".tmp" / "pip-called.txt").read_text(encoding="utf-8").strip() == "pip install -r requirements.txt"
    assert (project / ".tmp" / "uv-python-dir.txt").read_text(encoding="utf-8").strip() == str(
        project.parents[1] / ".tools" / "python"
    )


def test_setup_passes_explicit_python_override_to_uv(tmp_path: Path):
    project = make_controlled_project(tmp_path)
    fake_uv = tmp_path / "fake-uv.bat"
    write_fake_uv(fake_uv)
    override = "D:\\portable-python\\python.exe"

    result = run_setup(
        project,
        {"FORMPILOT_UV": str(fake_uv), "FORMPILOT_PYTHON": override},
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert override in (project / ".tmp" / "uv-venv.txt").read_text(encoding="utf-8")


def test_setup_stops_before_pip_when_venv_fails(tmp_path: Path):
    project = make_controlled_project(tmp_path)
    fake_uv = tmp_path / "fake-uv.bat"
    write_fake_uv(fake_uv, venv_exit=17)

    result = run_setup(project, {"FORMPILOT_UV": str(fake_uv)})

    assert result.returncode != 0
    assert not (project / ".tmp" / "pip-called.txt").exists()


def test_setup_returns_nonzero_when_pip_fails(tmp_path: Path):
    project = make_controlled_project(tmp_path)
    fake_uv = tmp_path / "fake-uv.bat"
    write_fake_uv(fake_uv, pip_exit=18)

    result = run_setup(project, {"FORMPILOT_UV": str(fake_uv)})

    assert result.returncode != 0
    assert (project / ".tmp" / "pip-called.txt").exists()


def test_run_fails_fast_when_no_configured_or_portable_openscad_exists(tmp_path: Path):
    project = make_controlled_project(tmp_path)
    environment = os.environ | {"OPENSCAD_BIN": ""}

    result = subprocess.run(
        ["cmd.exe", "/d", "/c", str(project / "scripts" / "run.bat")],
        cwd=project,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Portable OpenSCAD was not found" in result.stdout


def test_run_preserves_a_configured_openscad_binary_for_the_application(tmp_path: Path):
    project = make_controlled_project(tmp_path)
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    (fake_bin / "python.bat").write_text(
        "@echo off\n"
        "> %FORMPILOT_TMP%\\launch-openscad.txt echo %OPENSCAD_BIN%\n"
        "exit /b 0\n",
        encoding="utf-8",
    )
    activation = project / ".venv" / "Scripts" / "activate.bat"
    activation.parent.mkdir(parents=True)
    activation.write_text(
        f'@echo off\nset "PATH={fake_bin};%PATH%"\n', encoding="utf-8"
    )
    configured_binary = "D:\\approved-portable\\openscad.com"

    result = subprocess.run(
        ["cmd.exe", "/d", "/c", str(project / "scripts" / "run.bat")],
        cwd=project,
        env=os.environ | {"OPENSCAD_BIN": configured_binary},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert (project / ".tmp" / "launch-openscad.txt").read_text(
        encoding="utf-8"
    ).strip() == configured_binary


def install_fake_application(project: Path, tmp_path: Path) -> Path:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    (fake_bin / "python.bat").write_text(
        "@echo off\n"
        "> %FORMPILOT_TMP%\\app-started.txt echo started\n"
        "> %FORMPILOT_TMP%\\launch-openscad.txt echo %OPENSCAD_BIN%\n"
        "exit /b 0\n",
        encoding="utf-8",
    )
    activation = project / ".venv" / "Scripts" / "activate.bat"
    activation.parent.mkdir(parents=True)
    activation.write_text(
        f'@echo off\nset "PATH={fake_bin};%PATH%"\n', encoding="utf-8"
    )
    return fake_bin


def test_run_rejects_a_tools_directory_without_an_openscad_file(tmp_path: Path):
    project = make_controlled_project(tmp_path)
    (project.parents[1] / ".tools").mkdir()
    install_fake_application(project, tmp_path)

    result = subprocess.run(
        ["cmd.exe", "/d", "/c", str(project / "scripts" / "run.bat")],
        cwd=project,
        env=os.environ | {"OPENSCAD_BIN": ""},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Portable OpenSCAD was not found" in result.stdout
    assert not (project / ".tmp" / "app-started.txt").exists()


def test_run_selects_an_existing_nested_portable_openscad_binary(tmp_path: Path):
    project = make_controlled_project(tmp_path)
    portable_binary = (
        project.parents[1]
        / ".tools"
        / "openscad-2021.01"
        / "openscad-2021.01"
        / "openscad.com"
    )
    portable_binary.parent.mkdir(parents=True)
    portable_binary.write_text("portable placeholder", encoding="utf-8")
    install_fake_application(project, tmp_path)

    result = subprocess.run(
        ["cmd.exe", "/d", "/c", str(project / "scripts" / "run.bat")],
        cwd=project,
        env=os.environ | {"OPENSCAD_BIN": ""},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert (project / ".tmp" / "launch-openscad.txt").read_text(
        encoding="utf-8"
    ).strip() == str(portable_binary)
