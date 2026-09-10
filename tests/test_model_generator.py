from pathlib import Path
from types import SimpleNamespace

import pytest

import src.formpilot.model_generator as model_generator
from src.formpilot.design_spec import DesignSpec
from src.formpilot.model_generator import (
    OpenScadError,
    build_command,
    generate_model,
    resolve_openscad,
)


def make_spec(**overrides) -> DesignSpec:
    values = dict(
        layout="side_by_side", phone_width=76, phone_thickness=10,
        earbuds_width=65, earbuds_thickness=28, max_base_width=180,
    )
    return DesignSpec(**(values | overrides))


def test_build_command_uses_argument_list_not_shell_text(tmp_path: Path):
    spec = make_spec()
    command = build_command(spec, tmp_path / "result.stl", "openscad.com")
    assert command[0] == "openscad.com"
    assert command[1:3] == ["-o", str(tmp_path / "result.stl")]
    assert "phone_width=76.0" in command
    assert all(isinstance(item, str) for item in command)


def test_build_command_encodes_openscad_strings_and_booleans(tmp_path: Path):
    command = build_command(
        make_spec(layout="front_back", cable_hole_enabled=False),
        tmp_path / "result.stl",
        "openscad.com",
    )
    definitions = [command[index + 1] for index, value in enumerate(command) if value == "-D"]
    assert 'layout="front_back"' in definitions
    assert "cable_hole_enabled=false" in definitions


def test_resolve_openscad_prefers_configured_binary(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OPENSCAD_BIN", "D:/tools/openscad.com")
    assert resolve_openscad() == "D:/tools/openscad.com"


def test_generate_model_retries_once_then_returns_nonempty_stl(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    attempts = 0

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        nonlocal attempts
        attempts += 1
        if attempts == 2:
            Path(command[2]).write_text("solid organizer\nendsolid organizer\n")
            return SimpleNamespace(returncode=0, stderr="", stdout="")
        return SimpleNamespace(returncode=1, stderr="first failure", stdout="")

    monkeypatch.setattr("src.formpilot.model_generator.subprocess.run", fake_run)
    result = generate_model(make_spec(), tmp_path / "run", "openscad.com")
    assert result.name == "organizer.stl"
    assert result.read_text() == "solid organizer\nendsolid organizer\n"
    assert attempts == 2


def test_generate_model_raises_last_error_after_two_failed_attempts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    attempts = 0

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        nonlocal attempts
        attempts += 1
        return SimpleNamespace(returncode=1, stderr=f"failure {attempts}", stdout="")

    monkeypatch.setattr("src.formpilot.model_generator.subprocess.run", fake_run)
    with pytest.raises(OpenScadError, match="failure 2"):
        generate_model(make_spec(), tmp_path / "run", "openscad.com")
    assert attempts == 2


def test_generate_model_suppresses_windows_error_dialogs_before_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    recorded_error_modes: list[int] = []
    existing_error_mode = 0x40
    fake_kernel32 = SimpleNamespace(
        GetErrorMode=lambda: existing_error_mode,
        SetErrorMode=lambda mode: recorded_error_modes.append(mode),
    )
    captured_kwargs: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        captured_kwargs.update(kwargs)
        Path(command[2]).write_text("solid organizer\nendsolid organizer\n")
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(
        model_generator,
        "ctypes",
        SimpleNamespace(WinDLL=lambda name, **kwargs: fake_kernel32),
        raising=False,
    )
    monkeypatch.setattr(model_generator, "sys", SimpleNamespace(platform="win32"), raising=False)
    monkeypatch.setattr(model_generator.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
    monkeypatch.setattr(model_generator.subprocess, "run", fake_run)

    generate_model(make_spec(), tmp_path / "run", "openscad.com")

    assert recorded_error_modes == [existing_error_mode | 0x8003]
    assert captured_kwargs["creationflags"] == 0x08000000


def test_generate_model_uses_no_windows_creation_flags_elsewhere(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    captured_kwargs: dict[str, object] = {}

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        captured_kwargs.update(kwargs)
        Path(command[2]).write_text("solid organizer\nendsolid organizer\n")
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(model_generator, "sys", SimpleNamespace(platform="linux"), raising=False)
    monkeypatch.setattr(model_generator.subprocess, "run", fake_run)

    generate_model(make_spec(), tmp_path / "run", "openscad.com")

    assert captured_kwargs["creationflags"] == 0
