import json
from collections.abc import Callable

from fastapi.testclient import TestClient

from tests.api.conftest import (
    FAMILY,
    HOUSEHOLD,
    LOCATION,
    FakeAPIError,
    FakeMessages,
    text_response,
)

MakeClient = Callable[..., TestClient]
BODY = {"location": LOCATION, "members": FAMILY, "household": HOUSEHOLD}


def _ai_plan(member_ids: list[str]) -> str:
    return json.dumps(
        {
            "summary": "Very Poor air this morning.",
            "routine": [
                {
                    "activity": "Walk",
                    "start": "10:00",
                    "end": "11:00",
                    "advice": "avoid",
                    "why": "AQI 333",
                    "impact": "Less smoke inhaled.",
                }
            ],
            "commute": None,
            "school": [],
            "indoor_tips": [],
            "sustainable_choices": [],
            "members": [
                {"member_id": i, "risk_level": "high", "alerts": [], "checklist": []}
                for i in member_ids
            ],
        }
    )


def test_plan_rules_mode_without_ai(make_client: MakeClient) -> None:
    response = make_client().post("/api/plan", json=BODY)
    assert response.status_code == 200
    data = response.json()
    assert data["source"] == "rules"
    assert data["current"]["aqi"] == 351
    assert [m["member_id"] for m in data["members"]] == ["m_1", "m_2"]
    child = data["members"][0]
    assert child["risk_level"] == "very_high"
    assert any(item["id"] == "carry_inhaler" for item in child["checklist"])
    assert data["commute"]["alternative_mode"]
    assert data["sustainable_choices"]
    assert data["indoor_tips"][0]["tip"] == "Keep windows closed"


def test_plan_uses_ai_when_valid(make_client: MakeClient) -> None:
    messages = FakeMessages(text_response(_ai_plan(["m_1", "m_2"])))
    response = make_client(messages=messages).post("/api/plan", json=BODY)
    data = response.json()
    assert data["source"] == "ai"
    assert data["summary"] == "Very Poor air this morning."
    request = messages.requests[0]
    assert request["output_config"]["effort"] == "medium"
    assert request["output_config"]["format"]["type"] == "json_schema"
    assert "FACTS" in request["messages"][0]["content"]


def test_plan_falls_back_when_ai_invents_members(make_client: MakeClient) -> None:
    messages = FakeMessages(text_response(_ai_plan(["m_1", "stranger"])))
    assert make_client(messages=messages).post("/api/plan", json=BODY).json()["source"] == "rules"


def test_plan_falls_back_on_api_error(make_client: MakeClient) -> None:
    messages = FakeMessages(FakeAPIError())
    assert make_client(messages=messages).post("/api/plan", json=BODY).json()["source"] == "rules"


def test_plan_falls_back_on_refusal(make_client: MakeClient) -> None:
    messages = FakeMessages(text_response("", stop_reason="refusal"))
    assert make_client(messages=messages).post("/api/plan", json=BODY).json()["source"] == "rules"


def test_plan_rejects_duplicate_members(make_client: MakeClient) -> None:
    body = {**BODY, "members": [FAMILY[0], FAMILY[0]]}
    assert make_client().post("/api/plan", json=body).status_code == 422


def test_plan_rejects_unknown_fields(make_client: MakeClient) -> None:
    body = {**BODY, "admin": True}
    assert make_client().post("/api/plan", json=body).status_code == 422


def test_plan_rejects_too_many_members(make_client: MakeClient) -> None:
    members = [{"id": f"m{i}", "age_group": "adult"} for i in range(11)]
    assert make_client().post("/api/plan", json={**BODY, "members": members}).status_code == 422
