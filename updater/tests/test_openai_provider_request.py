"""OpenAI Responses request shaping (no network)."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from updater.research.providers.base import RunSettings
from updater.research.providers.openai_provider import OpenAIResponsesProvider


class _FakeResponses:
    def __init__(self) -> None:
        self.kwargs: dict | None = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            id="resp_test",
            status="completed",
            incomplete_details=None,
            output_text=(
                '{"additions_csv":"id\\n","update_report_markdown":"ok",'
                '"status":"completed","status_reason":""}'
            ),
            output=[SimpleNamespace(type="web_search_call")],
            tools=[{"type": "web_search"}],
            model="gpt-6.1-sol",
        )


class _FakeClient:
    def __init__(self) -> None:
        self.responses = _FakeResponses()


def test_research_enables_web_search_and_reasoning_effort():
    client = _FakeClient()
    provider = OpenAIResponsesProvider(
        api_key="unused",
        model="gpt-6.1-sol",
        reasoning_effort="medium",
        max_output_tokens=16000,
        client=client,
    )
    settings = RunSettings(
        research_date=date(2026, 10, 9),
        publication_window_start=date(2026, 7, 11),
        publication_window_end=date(2026, 10, 9),
        older_gap_filling=True,
        max_new_rows=40,
        append_only=True,
        model="gpt-6.1-sol",
        max_output_tokens=16000,
    )

    result = provider.research(
        instructions="Do research.",
        dataset_csv="id\n",
        settings=settings,
        transport_addendum="Return JSON.",
    )

    assert client.responses.kwargs is not None
    kwargs = client.responses.kwargs
    assert kwargs["tools"] == [{"type": "web_search"}]
    assert kwargs["tool_choice"] == "required"
    assert kwargs["reasoning"] == {"effort": "medium"}
    assert kwargs["max_output_tokens"] == 16000
    assert result.used_web_search is True
    assert result.status == "completed"


def test_research_omits_reasoning_when_unset():
    client = _FakeClient()
    provider = OpenAIResponsesProvider(
        api_key="unused",
        model="gpt-4o",
        client=client,
    )
    settings = RunSettings(
        research_date=date(2026, 10, 9),
        publication_window_start=date(2026, 7, 11),
        publication_window_end=date(2026, 10, 9),
        older_gap_filling=True,
        max_new_rows=40,
        append_only=True,
    )

    provider.research(
        instructions="Do research.",
        dataset_csv="id\n",
        settings=settings,
    )

    assert client.responses.kwargs is not None
    assert "reasoning" not in client.responses.kwargs
    assert client.responses.kwargs["tools"] == [{"type": "web_search"}]
    assert client.responses.kwargs["tool_choice"] == "required"
