from types import SimpleNamespace

import pytest

import src.formpilot.requirement_parser as requirement_parser
from src.formpilot.requirement_parser import OpenAIRequirementParser, ParserUnavailable


DECISION_JSON = (
    '{"action":"ask_user","values":{"layout":null,"phone_width":76,'
    '"phone_thickness":null,"earbuds_width":null,"earbuds_thickness":null,'
    '"max_base_width":null},"missing_fields":["phone_thickness"],'
    '"message":"Please provide the phone thickness in mm."}'
)
AI_ENVIRONMENT_VARIABLES = (
    "FORMPILOT_AI_PROVIDER",
    "FORMPILOT_AI_MODEL",
    "FORMPILOT_OPENAI_MODEL",
    "OPENROUTER_API_KEY",
    "DEEPSEEK_API_KEY",
    "OPENAI_API_KEY",
)


@pytest.fixture(autouse=True)
def clear_ai_environment(monkeypatch):
    for name in AI_ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(name, raising=False)


class FakeCompletions:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.requests: list[dict] = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        value = next(self.outputs)
        if isinstance(value, Exception):
            raise value
        if isinstance(value, SimpleNamespace):
            return value
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=value))]
        )


def make_parser(outputs, **kwargs):
    completions = FakeCompletions(outputs)
    parser = OpenAIRequirementParser(
        client=SimpleNamespace(chat=SimpleNamespace(completions=completions)), **kwargs
    )
    return parser, completions


@pytest.mark.parametrize(
    ("provider", "key_name", "base_url", "default_model"),
    [
        ("openrouter", "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1", "openrouter/free"),
        ("deepseek", "DEEPSEEK_API_KEY", "https://api.deepseek.com", "deepseek-v4-flash"),
        ("openai", "OPENAI_API_KEY", None, "gpt-5.4-mini"),
    ],
)
def test_constructs_provider_client_with_expected_defaults(
    monkeypatch, provider, key_name, base_url, default_model
):
    captured: dict = {}
    fake_client = object()

    def fake_openai(**kwargs):
        captured.update(kwargs)
        return fake_client

    monkeypatch.setenv("FORMPILOT_AI_PROVIDER", provider)
    monkeypatch.setenv(key_name, "test-api-key")
    monkeypatch.setattr(requirement_parser, "OpenAI", fake_openai)

    parser = OpenAIRequirementParser()

    assert parser.client is fake_client
    assert parser.model == default_model
    expected = {"api_key": "test-api-key", "max_retries": 0}
    if base_url is not None:
        expected["base_url"] = base_url
    assert captured == expected


def test_defaults_to_openrouter_when_provider_is_unset(monkeypatch):
    captured: dict = {}

    monkeypatch.delenv("FORMPILOT_AI_PROVIDER", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-api-key")
    monkeypatch.setattr(
        requirement_parser, "OpenAI", lambda **kwargs: captured.update(kwargs)
    )

    parser = OpenAIRequirementParser()

    assert parser.model == "openrouter/free"
    assert captured == {
        "api_key": "test-api-key",
        "base_url": "https://openrouter.ai/api/v1",
        "max_retries": 0,
    }


def test_model_precedence_and_openai_legacy_fallback(monkeypatch):
    monkeypatch.setenv("FORMPILOT_AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    monkeypatch.setenv("FORMPILOT_AI_MODEL", "provider-model")
    monkeypatch.setenv("FORMPILOT_OPENAI_MODEL", "legacy-model")

    explicit, _ = make_parser([DECISION_JSON], model="explicit-model")
    configured, _ = make_parser([DECISION_JSON])
    monkeypatch.delenv("FORMPILOT_AI_MODEL")
    legacy, _ = make_parser([DECISION_JSON])

    assert explicit.model == "explicit-model"
    assert configured.model == "provider-model"
    assert legacy.model == "legacy-model"


def test_openai_legacy_model_does_not_override_other_provider(monkeypatch):
    monkeypatch.setenv("FORMPILOT_AI_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-api-key")
    monkeypatch.delenv("FORMPILOT_AI_MODEL", raising=False)
    monkeypatch.setenv("FORMPILOT_OPENAI_MODEL", "legacy-model")

    parser, _ = make_parser([DECISION_JSON])

    assert parser.model == "deepseek-v4-flash"


def test_parses_chat_completion_json_with_schema_in_system_message(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-api-key")
    parser, completions = make_parser([DECISION_JSON])

    decision = parser.parse("My phone is 76 mm wide")

    assert decision.action.value == "ask_user"
    assert decision.values.phone_width == 76
    request = completions.requests[0]
    assert request["model"] == "openrouter/free"
    assert request["response_format"] == {"type": "json_object"}
    assert request["messages"][1] == {
        "role": "user",
        "content": "My phone is 76 mm wide",
    }
    system_message = request["messages"][0]
    assert system_message["role"] == "system"
    for required_instruction in ("millimetres", "ask_user", "no guessed dimensions"):
        assert required_instruction in system_message["content"]
    assert '"action"' in system_message["content"]
    assert '"missing_fields"' in system_message["content"]


def test_retries_after_malformed_chat_content_then_validates_locally(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-api-key")
    parser, completions = make_parser(["not JSON", DECISION_JSON])

    decision = parser.parse("Make an organizer")

    assert decision.values.phone_width == 76
    assert len(completions.requests) == 2


def test_retries_once_then_reports_manual_fallback(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-api-key")
    parser, completions = make_parser([RuntimeError("offline"), None])

    with pytest.raises(ParserUnavailable, match="manual"):
        parser.parse("Make an organizer")

    assert len(completions.requests) == 2


def test_retries_then_falls_back_when_json_fails_requirement_schema(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-api-key")
    invalid_decision = '{"action":"not-a-valid-action"}'
    parser, completions = make_parser([invalid_decision, invalid_decision])

    with pytest.raises(ParserUnavailable, match="manual"):
        parser.parse("Make an organizer")

    assert len(completions.requests) == 2


@pytest.mark.parametrize(
    "response",
    [
        SimpleNamespace(),
        SimpleNamespace(choices=[]),
        SimpleNamespace(choices=[SimpleNamespace()]),
        SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace())]),
    ],
    ids=["missing_choices", "empty_choices", "missing_message", "missing_content"],
)
def test_retries_then_falls_back_when_chat_completion_structure_is_missing(
    monkeypatch, response
):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-api-key")
    parser, completions = make_parser([response, response])

    with pytest.raises(ParserUnavailable, match="manual"):
        parser.parse("Make an organizer")

    assert len(completions.requests) == 2


def test_missing_provider_key_reports_safe_configuration_name(monkeypatch):
    monkeypatch.setenv("FORMPILOT_AI_PROVIDER", "deepseek")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    factory_calls = []
    monkeypatch.setattr(
        requirement_parser, "OpenAI", lambda **kwargs: factory_calls.append(kwargs)
    )

    parser = OpenAIRequirementParser()

    with pytest.raises(ParserUnavailable, match="DEEPSEEK_API_KEY"):
        parser.parse("Make an organizer")
    assert factory_calls == []


def test_missing_key_with_injected_client_does_not_make_a_request(monkeypatch):
    monkeypatch.setenv("FORMPILOT_AI_PROVIDER", "deepseek")
    parser, completions = make_parser([DECISION_JSON])

    with pytest.raises(ParserUnavailable, match="DEEPSEEK_API_KEY"):
        parser.parse("Make an organizer")

    assert completions.requests == []


def test_unsupported_provider_does_not_call_injected_client(monkeypatch):
    monkeypatch.setenv("FORMPILOT_AI_PROVIDER", "unsupported")
    parser, completions = make_parser([DECISION_JSON])

    with pytest.raises(ParserUnavailable, match="Unsupported AI provider"):
        parser.parse("Make an organizer")

    assert completions.requests == []


def test_unsupported_provider_message_does_not_echo_configured_value(monkeypatch):
    unsafe_provider = "<b>secret-like-provider-value</b>"
    monkeypatch.setenv("FORMPILOT_AI_PROVIDER", unsafe_provider)
    parser, completions = make_parser([DECISION_JSON])

    with pytest.raises(ParserUnavailable) as error:
        parser.parse("Make an organizer")

    assert str(error.value) == "AI requirement parsing is unavailable. Unsupported AI provider."
    assert unsafe_provider not in str(error.value)
    assert completions.requests == []
