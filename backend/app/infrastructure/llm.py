"""Concrete LLM model bindings for the agents (composition-root detail)."""

from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider


def create_extraction_model(model_id: str, openai_api_key: str | None) -> str | Model:
    """Resolve the extraction agent's model binding from settings.

    :param model_id: Pydantic AI model identifier (``provider:model`` form).
    :param openai_api_key: OpenAI API key from settings, if configured.
    :return: A concrete model carrying the settings-provided credentials, or
        the identifier string unchanged when no explicit key applies — the
        agent then defers to Pydantic AI's environment-based provider
        inference at first run.
    """
    provider_name, _, model_name = model_id.partition(":")
    if provider_name == "openai" and openai_api_key:
        return OpenAIResponsesModel(
            model_name, provider=OpenAIProvider(api_key=openai_api_key)
        )
    return model_id
