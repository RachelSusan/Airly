import pytest

from app.ai.client import AIUnavailableError, ClaudeClient, build_claude_client, text_of
from app.ai.schemas import PLAN_SCHEMA, strict_schema
from app.config import Settings
from app.models.api import PlanContent
from tests.api.conftest import FakeAPIError, FakeMessages, text_response


def _client(*responses: object) -> tuple[ClaudeClient, FakeMessages]:
    messages = FakeMessages(*responses)
    return ClaudeClient(messages, "claude-opus-5-5"), messages


async def test_create_sends_expected_parameters() -> None:
    client, messages = _client(text_response("hi"))
    await client.create(
        system="S", messages=[{"role": "user", "content": "q"}], max_tokens=100, effort="low"
    )
    request = messages.requests[0]
    assert request["model"] == "claude-opus-5-5"
    assert request["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert request["betas"] == ["server-side-fallback-2026-07-01"]
    assert request["fallbacks"] == "default"
    assert "temperature" not in request
    assert "thinking" not in request
    assert "tools" not in request


@pytest.mark.parametrize("stop_reason", ["refusal", "max_tokens"])
async def test_unusable_stop_reasons_raise(stop_reason: str) -> None:
    client, _ = _client(text_response("x", stop_reason=stop_reason))
    with pytest.raises(AIUnavailableError):
        await client.create(system="S", messages=[], max_tokens=10, effort="low")


async def test_api_errors_are_mapped() -> None:
    client, _ = _client(FakeAPIError())
    with pytest.raises(AIUnavailableError):
        await client.create(system="S", messages=[], max_tokens=10, effort="low")


@pytest.mark.parametrize("text", ["not json", "[1, 2]"])
async def test_create_json_rejects_non_objects(text: str) -> None:
    client, _ = _client(text_response(text))
    with pytest.raises(AIUnavailableError):
        await client.create_json(
            system="S", messages=[], max_tokens=10, effort="low", schema={"type": "object"}
        )


def test_text_of_ignores_non_text_blocks() -> None:
    response = text_response("hello")
    response.content.insert(0, type("Block", (), {"type": "thinking"})())
    assert text_of(response) == "hello"


def test_build_client_requires_key() -> None:
    assert build_claude_client(Settings(anthropic_api_key=None)) is None
    assert build_claude_client(Settings(anthropic_api_key="k")) is not None


def test_plan_schema_is_closed_and_fully_required() -> None:
    def walk(node: object) -> None:
        if isinstance(node, dict):
            assert "$ref" not in node
            assert "title" not in node
            if node.get("type") == "object" and "properties" in node:
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(PLAN_SCHEMA)
    assert strict_schema(PlanContent) == PLAN_SCHEMA
