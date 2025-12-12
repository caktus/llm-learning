import json
import os
from typing import Any

from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai.providers.openai import OpenAIProvider
from rich import print_json

from .http import get_http_client
from .utils import strip_fields

os.environ.setdefault("OLLAMA_BASE_URL", "http://localhost:11434/v1")


def get_model(model_name: str, debug_http: bool = False) -> OpenAIChatModel | str:
    """Get a model, optionally with HTTP logging."""
    if not debug_http:
        return model_name

    # Parse model name like "ollama:qwen2.5-coder:7b" or "openai:gpt-4o-mini"
    provider, name = model_name.split(":", 1)
    http_client = get_http_client(debug_http=debug_http)

    if provider == "ollama":
        ollama_provider = OllamaProvider(http_client=http_client)
        return OpenAIChatModel(model_name=name, provider=ollama_provider)
    else:
        openai_provider = OpenAIProvider(http_client=http_client)
        return OpenAIChatModel(model_name=name, provider=openai_provider)


def print_all_messages(messages: Any | list) -> None:
    """Print AgentRunResult.all_messages while stripping specific fields for a cleaner look."""

    print_json(
        json.dumps(
            strip_fields(
                messages,
                omit={
                    "id",
                    "message_id",
                    "parent_message_id",
                    "timestamp",
                    "part_kind",
                    "kind",
                    "usage",
                    "provider_response_id",
                    "provider_details",
                    "finish_reason",
                    "tool_call_id",
                    "metadata",
                    "model_name",
                    "provider_name",
                },
            )
        )
    )
