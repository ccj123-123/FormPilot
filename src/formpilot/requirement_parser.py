import json
import os
from time import sleep

from openai import OpenAI

from .design_spec import RequirementDecision


RETRY_DELAY_SECONDS = 0.25
INSTRUCTIONS = """You parse desk-organizer requirements.
All length measurements must be in millimetres.
Choose only one of these actions: ask_user, generate, revise, explain.
Before generate, require layout, phone_width, phone_thickness, earbuds_width,
earbuds_thickness, and max_base_width. Use ask_user for any missing field.
Use no guessed dimensions. Return schema-only output."""
PROVIDERS = {
    "openrouter": {
        "api_key_env": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openrouter/free",
    },
    "deepseek": {
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-v4-flash",
    },
    "openai": {
        "api_key_env": "OPENAI_API_KEY",
        "base_url": None,
        "model": "gpt-5.4-mini",
    },
}


class ParserUnavailable(RuntimeError):
    """Raised when the user should continue with manual parameters."""


class OpenAIRequirementParser:
    """Parse requirements through an OpenAI-compatible Chat Completions client."""

    instructions = INSTRUCTIONS

    def __init__(self, client=None, model: str | None = None):
        self.provider_name = os.getenv("FORMPILOT_AI_PROVIDER", "openrouter").lower()
        self.provider = PROVIDERS.get(self.provider_name)
        self.client = None
        self.api_key = None

        if self.provider is None:
            self.model = model if model is not None else os.getenv(
                "FORMPILOT_AI_MODEL", ""
            )
            return

        self.model = self._select_model(model)
        self.api_key = os.getenv(self.provider["api_key_env"])
        if client is not None:
            self.client = client
        elif self.api_key:
            client_options = {"api_key": self.api_key, "max_retries": 0}
            if self.provider["base_url"] is not None:
                client_options["base_url"] = self.provider["base_url"]
            self.client = OpenAI(**client_options)

    def _select_model(self, explicit_model: str | None) -> str:
        if explicit_model is not None:
            return explicit_model
        configured_model = os.getenv("FORMPILOT_AI_MODEL")
        if configured_model:
            return configured_model
        if self.provider_name == "openai":
            legacy_model = os.getenv("FORMPILOT_OPENAI_MODEL")
            if legacy_model:
                return legacy_model
        return self.provider["model"]

    def _unavailable_message(self) -> str:
        if self.provider is None:
            return "AI requirement parsing is unavailable. Unsupported AI provider."
        if not self.api_key:
            return (
                "AI requirement parsing is unavailable. "
                f"Configure {self.provider['api_key_env']} or use manual parameters."
            )
        return "AI requirement parsing is unavailable. Please use manual parameters."

    def parse(self, text: str) -> RequirementDecision:
        if self.provider is None or not self.api_key or self.client is None:
            raise ParserUnavailable(self._unavailable_message())

        system_message = (
            f"{self.instructions}\n\n"
            "Return a JSON object that validates against this RequirementDecision "
            f"JSON schema:\n{json.dumps(RequirementDecision.model_json_schema())}"
        )
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": text},
                    ],
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Chat completion did not contain JSON content")
                return RequirementDecision.model_validate_json(content)
            except Exception as error:
                last_error = error
                if attempt == 0:
                    sleep(RETRY_DELAY_SECONDS)

        raise ParserUnavailable(self._unavailable_message()) from last_error
