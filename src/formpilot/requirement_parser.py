import os
from time import sleep

from openai import OpenAI

from .design_spec import RequirementDecision


DEFAULT_MODEL = "gpt-5.4-mini"
RETRY_DELAY_SECONDS = 0.25
INSTRUCTIONS = """You parse desk-organizer requirements.
All length measurements must be in millimetres.
Choose only one of these actions: ask_user, generate, revise, explain.
Before generate, require layout, phone_width, phone_thickness, earbuds_width,
earbuds_thickness, and max_base_width. Use ask_user for any missing field.
Use no guessed dimensions. Return schema-only output."""


class ParserUnavailable(RuntimeError):
    """Raised when the user should continue with manual parameters."""


class OpenAIRequirementParser:
    instructions = INSTRUCTIONS

    def __init__(self, client=None, model: str | None = None):
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = (
            client
            if client is not None
            else OpenAI(api_key=api_key, max_retries=0)
            if api_key
            else None
        )
        self.model = model if model is not None else os.getenv(
            "FORMPILOT_OPENAI_MODEL", DEFAULT_MODEL
        )

    def parse(self, text: str) -> RequirementDecision:
        if self.client is None:
            raise ParserUnavailable(
                "AI requirement parsing is unavailable. Please use manual parameters."
            )

        last_error: Exception | None = None
        for attempt in range(2):
            try:
                response = self.client.responses.create(
                    model=self.model,
                    instructions=self.instructions,
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
                    sleep(RETRY_DELAY_SECONDS)

        raise ParserUnavailable(
            "AI requirement parsing is unavailable. Please use manual parameters."
        ) from last_error
