from collections.abc import Callable

from fastapi.testclient import TestClient

from tests.api.conftest import (
    FAMILY,
    LOCATION,
    FakeAPIError,
    FakeModels,
    text_response,
    tool_response,
    tool_results,
)

MakeClient = Callable[..., TestClient]


def _body(question: str) -> dict:
    return {
        "messages": [{"role": "user", "content": question}],
        "context": {"location": LOCATION, "members": FAMILY},
    }


def test_chat_rules_answers_window_question(make_client: MakeClient) -> None:
    data = make_client().post("/api/chat", json=_body("Should I open my windows?")).json()
    assert data["source"] == "rules"
    assert data["reply"].startswith("Not right now.")
    assert data["tools_used"] == []


def test_chat_rules_answers_children_question(make_client: MakeClient) -> None:
    data = make_client().post("/api/chat", json=_body("Can my children play outside?")).json()
    assert "outdoor play" in data["reply"]


def test_chat_ai_tool_loop(make_client: MakeClient) -> None:
    models = FakeModels(
        tool_response(("t1", "get_current_conditions", {})),
        tool_response(("t2", "get_forecast_windows", {"activity": "jog", "duration_hours": 1})),
        text_response("Not right now. AQI is 351."),
    )
    data = make_client(models=models).post("/api/chat", json=_body("Jog now?")).json()
    assert data == {
        "source": "ai",
        "reply": "Not right now. AQI is 351.",
        "tools_used": ["get_current_conditions", "get_forecast_windows"],
    }
    # Tool results go back as function responses carrying real engine numbers
    first_result = tool_results(models.requests[1])[0]
    assert first_result.name == "get_current_conditions"
    assert first_result.response["now"]["aqi"] == 351
    # The conversation sent to Gemini: user turn, then model call, then tool results
    first = models.requests[0]
    assert first["contents"][0].role == "user"
    declared = {d.name for d in first["config"].tools[0].function_declarations}
    assert "check_ventilation" in declared
    assert first["config"].automatic_function_calling.disable is True


def test_chat_bad_tool_input_is_reported_as_error(make_client: MakeClient) -> None:
    models = FakeModels(
        tool_response(("t1", "get_forecast_windows", {"activity": "fly", "duration_hours": 9})),
        text_response("Sorry, let me try again."),
    )
    data = make_client(models=models).post("/api/chat", json=_body("Walk?")).json()
    assert "error" in tool_results(models.requests[1])[0].response
    assert data["tools_used"] == []


def test_chat_unknown_tool_is_reported_as_error(make_client: MakeClient) -> None:
    models = FakeModels(tool_response(("t1", "delete_everything", {})), text_response("OK."))
    data = make_client(models=models).post("/api/chat", json=_body("Hi")).json()
    assert data["tools_used"] == []
    assert "error" in tool_results(models.requests[1])[0].response


def test_chat_too_many_tool_rounds_falls_back(make_client: MakeClient) -> None:
    loop = [tool_response((f"t{i}", "check_ventilation", {})) for i in range(5)]
    data = make_client(models=FakeModels(*loop)).post("/api/chat", json=_body("Window?"))
    assert data.json()["source"] == "rules"


def test_chat_api_error_falls_back(make_client: MakeClient) -> None:
    data = make_client(models=FakeModels(FakeAPIError())).post("/api/chat", json=_body("Mask?"))
    assert data.json()["source"] == "rules"
    assert "N95" in data.json()["reply"]


def test_chat_empty_reply_falls_back(make_client: MakeClient) -> None:
    data = make_client(models=FakeModels(text_response(""))).post("/api/chat", json=_body("Hi"))
    assert data.json()["source"] == "rules"


def test_chat_commute_switch_tool(make_client: MakeClient) -> None:
    args = {"from_mode": "petrol_car", "to_mode": "metro", "distance_km": 12, "days_per_week": 5}
    models = FakeModels(
        tool_response(("t1", "estimate_commute_switch", args)), text_response("Saves 874 kg.")
    )
    make_client(models=models).post("/api/chat", json=_body("Metro?"))
    assert tool_results(models.requests[1])[0].response["co2_kg"] == -873.6


def test_chat_must_end_with_user(make_client: MakeClient) -> None:
    body = _body("Hi")
    body["messages"].append({"role": "assistant", "content": "Hello"})
    assert make_client().post("/api/chat", json=body).status_code == 422


def test_chat_rejects_long_message(make_client: MakeClient) -> None:
    assert make_client().post("/api/chat", json=_body("x" * 1001)).status_code == 422


def test_chat_rejects_system_role(make_client: MakeClient) -> None:
    body = _body("Hi")
    body["messages"][0]["role"] = "system"
    assert make_client().post("/api/chat", json=body).status_code == 422


def test_chat_rules_answers_which_city(make_client: MakeClient) -> None:
    body = _body("Which city am I in now?")
    body["context"]["location"]["name"] = "Mumbai, Maharashtra, India"
    data = make_client().post("/api/chat", json=body).json()
    assert data["reply"].startswith(
        "You're seeing live air quality for Mumbai, Maharashtra, India."
    )


def test_current_conditions_tool_includes_place_name(make_client: MakeClient) -> None:
    models = FakeModels(
        tool_response(("t1", "get_current_conditions", {})), text_response("Mumbai.")
    )
    body = _body("Where am I?")
    body["context"]["location"]["name"] = "Mumbai, Maharashtra, India"
    make_client(models=models).post("/api/chat", json=body)
    result = tool_results(models.requests[1])[0].response
    assert result["location"]["name"] == "Mumbai, Maharashtra, India"
