import httpx2
import pytest

from app.ai.client import AIUnavailableError, GeminiClient, build_ai_client, text_of
from app.ai.schemas import PLAN_SCHEMA, strict_schema
from app.config import Settings
from app.models.api import PlanContent
from tests.api.conftest import FakeAPIError, FakeModels, text_response, tool_response

SCHEMA = {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]}


def _client(*responses: object) -> tuple[GeminiClient, FakeModels]:
    models = FakeModels(*responses)
    return GeminiClient(models, "gemini-test"), models


async def test_generate_json_sends_schema_and_parses() -> None:
    client, models = _client(text_response('{"a": "hi"}'))
    data = await client.generate_json(system="S", prompt="P", schema=SCHEMA, max_tokens=100)
    assert data == {"a": "hi"}
    request = models.requests[0]
    assert request["model"] == "gemini-test"
    assert request["contents"] == "P"
    config = request["config"]
    assert config.system_instruction == "S"
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema == SCHEMA
    assert config.max_output_tokens == 100
    assert config.automatic_function_calling.disable is True


@pytest.mark.parametrize("text", ["not json", "[1, 2]"])
async def test_generate_json_rejects_non_objects(text: str) -> None:
    client, _ = _client(text_response(text))
    with pytest.raises(AIUnavailableError):
        await client.generate_json(system="S", prompt="P", schema=SCHEMA, max_tokens=10)


@pytest.mark.parametrize("finish", ["SAFETY", "PROHIBITED_CONTENT", "MAX_TOKENS", "RECITATION"])
async def test_unusable_finish_reasons_raise(finish: str) -> None:
    client, _ = _client(text_response('{"a": "x"}', finish=finish))
    with pytest.raises(AIUnavailableError):
        await client.generate_json(system="S", prompt="P", schema=SCHEMA, max_tokens=10)


@pytest.mark.parametrize(
    "error", [FakeAPIError(), httpx2.ConnectError("offline"), TimeoutError("slow")]
)
async def test_request_errors_are_mapped(error: Exception) -> None:
    client, _ = _client(error)
    with pytest.raises(AIUnavailableError):
        await client.generate_json(system="S", prompt="P", schema=SCHEMA, max_tokens=10)


async def test_no_candidates_means_blocked() -> None:
    from types import SimpleNamespace

    client, _ = _client(SimpleNamespace(candidates=[], function_calls=None))
    with pytest.raises(AIUnavailableError, match="blocked"):
        await client.generate_json(system="S", prompt="P", schema=SCHEMA, max_tokens=10)


async def test_chat_runs_tools_and_maps_roles() -> None:
    client, models = _client(
        tool_response(("c1", "lookup", {"q": 1})),
        text_response("Done."),
    )
    seen: list[tuple[str, dict]] = []

    def run_tool(name: str, args: dict) -> dict:
        seen.append((name, args))
        return {"value": 42}

    reply, used = await client.chat(
        system="S",
        messages=[("user", "hi"), ("assistant", "hello"), ("user", "look it up")],
        tools=[{"name": "lookup", "description": "d", "parameters": {"type": "object"}}],
        run_tool=run_tool,
        max_rounds=3,
        max_tokens=100,
    )
    assert (reply, used) == ("Done.", ["lookup"])
    assert seen == [("lookup", {"q": 1})]
    first = models.requests[0]["contents"]
    assert [c.role for c in first] == ["user", "model", "user"]
    second = models.requests[1]["contents"]
    assert second[-1].parts[0].function_response.response == {"value": 42}


def test_text_of_skips_thoughts_and_handles_empty() -> None:
    response = text_response("answer")
    from types import SimpleNamespace

    response.candidates[0].content.parts.insert(
        0, SimpleNamespace(text="thinking...", thought=True, function_call=None)
    )
    assert text_of(response) == "answer"
    assert text_of(SimpleNamespace(candidates=[])) == ""


def test_build_client_requires_real_key() -> None:
    assert build_ai_client(Settings(gemini_api_key=None)) is None
    assert build_ai_client(Settings(gemini_api_key="your-gemini-api-key-here")) is None
    client = build_ai_client(Settings(gemini_api_key="k", gemini_model="gemini-x"))
    assert client is not None and client.model == "gemini-x"


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


class _BusyError(FakeAPIError):
    def __init__(self, code: int) -> None:
        super().__init__()
        self.code = code


async def test_busy_model_falls_through_to_backup_and_cools_down() -> None:
    now = [0.0]
    models = FakeModels(
        _BusyError(503), text_response('{"a": "from backup"}'), text_response('{"a": "again"}')
    )
    client = GeminiClient(models, "main", ["backup"], clock=lambda: now[0])
    first = await client.generate_json(system="S", prompt="P", schema=SCHEMA, max_tokens=10)
    assert first == {"a": "from backup"}
    assert [r["model"] for r in models.requests] == ["main", "backup"]
    # While cooling down, the busy model is skipped entirely
    await client.generate_json(system="S", prompt="P", schema=SCHEMA, max_tokens=10)
    assert models.requests[-1]["model"] == "backup"


async def test_busy_model_is_retried_after_cooldown() -> None:
    now = [0.0]
    models = FakeModels(_BusyError(429), text_response('{"a": "1"}'), text_response('{"a": "2"}'))
    client = GeminiClient(models, "main", ["backup"], clock=lambda: now[0])
    await client.generate_json(system="S", prompt="P", schema=SCHEMA, max_tokens=10)
    now[0] = 1000.0
    await client.generate_json(system="S", prompt="P", schema=SCHEMA, max_tokens=10)
    assert models.requests[-1]["model"] == "main"


async def test_all_models_busy_raises() -> None:
    models = FakeModels(_BusyError(503), _BusyError(404))
    client = GeminiClient(models, "main", ["backup"])
    with pytest.raises(AIUnavailableError, match="busy"):
        await client.generate_json(system="S", prompt="P", schema=SCHEMA, max_tokens=10)


async def test_other_client_errors_do_not_switch_models() -> None:
    models = FakeModels(_BusyError(400))
    client = GeminiClient(models, "main", ["backup"])
    with pytest.raises(AIUnavailableError, match="request failed"):
        await client.generate_json(system="S", prompt="P", schema=SCHEMA, max_tokens=10)
    assert len(models.requests) == 1


def test_fallback_models_setting_is_parsed() -> None:
    settings = Settings(gemini_api_key="k", gemini_fallback_models=" a, b ,,")
    assert settings.fallback_models == ["a", "b"]
    client = build_ai_client(settings)
    assert client is not None and client.models[1:] == ["a", "b"]
