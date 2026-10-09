"""Small provider interface for research backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol


@dataclass(frozen=True)
class RunSettings:
    research_date: date
    publication_window_start: date
    publication_window_end: date
    older_gap_filling: bool
    max_new_rows: int
    append_only: bool
    analysis_window_start: date | None = None
    analysis_window_end: date | None = None
    model: str | None = None
    timeout_seconds: float | None = None
    max_output_tokens: int | None = None


@dataclass
class ProviderResult:
    additions_csv: str
    update_report_markdown: str
    status: str
    status_reason: str
    response_id: str | None = None
    used_web_search: bool = False
    api_status: str | None = None
    incomplete_reason: str | None = None
    raw_output_text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ResearchProvider(Protocol):
    def research(
        self,
        *,
        instructions: str,
        dataset_csv: str,
        settings: RunSettings,
    ) -> ProviderResult:
        """Run research and return a structured result plus metadata."""
        ...
