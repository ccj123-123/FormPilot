from types import SimpleNamespace

import pytest

import src.formpilot.requirement_parser as requirement_parser
from src.formpilot.design_spec import RequirementDecision
from src.formpilot.requirement_parser import OpenAIRequirementParser, ParserUnavailable


DECISION_JSON = (
    '{"action":"ask_user","values":{"layout":null,"phone_width":76,'
    '"phone_thickness":null,"earbuds_width":null,"earbuds_thickness":null,'
    '"max_base_width":null},"missing_fields":["phone_thickness"],'
    '"message":"Please provide the phone thickness in mm."}'
)


class FakeResponses:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.requests: list[dict] = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        value = next(self.outputs)
        if isinstance(value, Exception):
            raise value
        return SimpleNamespace(output_text=value)


def make_parser(outputs, **kwargs):
    responses = FakeResponses(outputs)
    parser = OpenAIRequirementParser(
        client=SimpleNamespace(responses=responses), **kwargs
    )
    return parser, responses


def test_parses_structured_decision_with_strict_responses_request():
    parser, responses = make_parser([DECISION_JSON])

    decision = parser.parse("My phone is 76 mm wide")

    assert decision.action.value == "ask_user"
    assert decision.values.phone_width == 76
    assert decision.missing_fields == ["phone_thickness"]
    request = responses.requests[0]
    assert request["model"] == "gpt-5.4-mini"
    assert request["input"] == "My phone is 76 mm wide"
    assert request["store"] is False
    assert request["text"] == {
        "format": {
            "type": "json_schema",
            "name": "requirement_decision",
            "strict": True,
            "schema": RequirementDecision.model_json_schema(),
        }
    }
    for required_instruction in (
        "millimetres",
        "ask_user",
        "generate",
        "revise",
        "explain",
        "layout",
        "phone_width",
        "phone_thickness",
        "earbuds_width",
        "earbuds_thickness",
        "max_base_width",
        "no guessed dimensions",
        "schema-only output",
    ):
        assert required_instruction in request["instructions"]


def test_model_override_takes_priority_over_environment(monkeypatch):
    monkeypatch.setenv("FORMPILOT_OPENAI_MODEL", "environment-model")
    parser, responses = make_parser([DECISION_JSON], model="explicit-model")

    parser.parse("My phone is 76 mm wide")

    assert responses.requests[0]["model"] == "explicit-model"


def test_environment_model_takes_priority_over_default(monkeypatch):
    monkeypatch.setenv("FORMPILOT_OPENAI_MODEL", "environment-model")
    parser, responses = make_parser([DECISION_JSON])

    parser.parse("My phone is 76 mm wide")

    assert responses.requests[0]["model"] == "environment-model"


def test_constructed_client_disables_sdk_retries(monkeypatch):
    captured: dict = {}
    fake_client = object()

    def fake_openai(**kwargs):
        captured.update(kwargs)
        return fake_client

    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    monkeypatch.setattr(requirement_parser, "OpenAI", fake_openai)

    parser = OpenAIRequirementParser()

    assert parser.client is fake_client
    assert captured == {"api_key": "test-api-key", "max_retries": 0}


def test_retries_once_then_reports_manual_fallback():
    parser, responses = make_parser([RuntimeError("offline"), RuntimeError("offline")])

    with pytest.raises(ParserUnavailable, match="manual"):
        parser.parse("Make an organizer")

    assert len(responses.requests) == 2


def test_missing_api_key_reports_manual_fallback(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    parser = OpenAIRequirementParser()

    with pytest.raises(ParserUnavailable, match="manual"):
        parser.parse("Make an organizer")
