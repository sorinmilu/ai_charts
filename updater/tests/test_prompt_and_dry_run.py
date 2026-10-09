"""Prompt preparation and dry-run tests (no API credits)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from updater.research.config import AppConfig
from updater.research.prompt_prep import (
    PromptPrepError,
    prepare_prompt,
    resolve_dataset_from_prompt,
    trajectory_analysis_window,
)
from updater.research.providers.base import ProviderResult
from updater.research.runner import run_update

ROOT = Path(__file__).resolve().parents[2]


def _config() -> AppConfig:
    return AppConfig(
        provider="openai",
        openai_api_key="test-key",
        openai_model="gpt-4o",
        max_new_rows=40,
        timeout_seconds=60,
        max_output_tokens=1000,
        root=ROOT,
    )


def test_resolve_dataset_from_prompt_file():
    text = (ROOT / "updater/prompts/practical_utility_prompt.md").read_text(encoding="utf-8")
    relative, path, spec = resolve_dataset_from_prompt(text, ROOT)
    assert relative == "web-app/data/ai_practical_utility_talking_points.csv"
    assert path.is_file()
    assert spec.id_prefix == "UTL"


def test_missing_dataset_path_errors():
    with pytest.raises(PromptPrepError, match="Could not find a dataset path"):
        resolve_dataset_from_prompt("No csv here", ROOT)


def test_prepare_prompt_fills_settings_and_attaches_full_csv():
    prepared = prepare_prompt(
        ROOT / "updater/prompts/practical_utility_prompt.md",
        ROOT,
        max_new_rows=12,
        research_date=date.fromisoformat("2026-10-09"),
    )
    assert "Research cutoff: 2026-10-09" in prepared.filled_instructions
    assert "Maximum new rows: 12" in prepared.filled_instructions
    assert "Older gap-filling sources: YES" in prepared.filled_instructions
    assert "BEGIN EXISTING DATASET CSV" in prepared.filled_instructions
    # Full CSV attached (no truncation to a few examples)
    assert '"UTL001"' in prepared.filled_instructions
    assert '"UTL064"' in prepared.filled_instructions or "UTL064" in prepared.dataset_csv
    assert prepared.dataset_csv in prepared.filled_instructions
    assert prepared.settings.max_new_rows == 12


def test_trajectory_window_locked_from_dataset():
    prepared = prepare_prompt(
        ROOT / "updater/prompts/future_trajectory_prompt.md",
        ROOT,
        max_new_rows=5,
        research_date=date.fromisoformat("2026-10-09"),
    )
    assert prepared.settings.analysis_window_start == date.fromisoformat("2026-10-06")
    assert prepared.settings.analysis_window_end == date.fromisoformat("2036-10-06")
    assert "Analysis window: 2026-10-06 to 2036-10-06" in prepared.filled_instructions


def test_conflicting_trajectory_windows_error():
    rows = [
        {
            "analysis_window_start": "2026-10-06",
            "analysis_window_end": "2036-10-06",
        },
        {
            "analysis_window_start": "2027-01-01",
            "analysis_window_end": "2037-01-01",
        },
    ]
    with pytest.raises(PromptPrepError, match="Conflicting analysis-window"):
        trajectory_analysis_window(rows)


class _CountingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def research(self, *, instructions: str, dataset_csv: str, settings):  # noqa: ANN001
        self.calls += 1
        return ProviderResult(
            additions_csv="",
            update_report_markdown="",
            status="failed",
            status_reason="should not be called",
            used_web_search=False,
        )


def test_dry_run_makes_no_api_call(tmp_path: Path):
    provider = _CountingProvider()
    outcome = run_update(
        ROOT / "updater/prompts/practical_utility_prompt.md",
        config=_config(),
        output_dir=tmp_path / "out",
        dry_run=True,
        provider=provider,
        research_date=date.fromisoformat("2026-10-09"),
    )
    assert outcome.exit_code == 0
    assert outcome.dry_run is True
    assert provider.calls == 0
    assert (tmp_path / "out" / "filled_prompt.md").is_file()
    assert (tmp_path / "out" / "attached_dataset.csv").is_file()
    assert (tmp_path / "out" / "run_meta.json").is_file()


def test_mocked_provider_incomplete_does_not_mark_import_ready(tmp_path: Path):
    class IncompleteProvider:
        def research(self, *, instructions: str, dataset_csv: str, settings):  # noqa: ANN001
            return ProviderResult(
                additions_csv='id\n"UTL999"\n',
                update_report_markdown="partial report",
                status="incomplete",
                status_reason="truncated",
                response_id="resp_test",
                used_web_search=True,
                api_status="incomplete",
                incomplete_reason="max_output_tokens",
                raw_output_text='{"status":"incomplete"}',
            )

    outcome = run_update(
        ROOT / "updater/prompts/practical_utility_prompt.md",
        config=_config(),
        output_dir=tmp_path / "out2",
        dry_run=False,
        provider=IncompleteProvider(),
        research_date=date.fromisoformat("2026-10-09"),
    )
    assert outcome.exit_code != 0
    assert not (tmp_path / "out2" / "practical_utility_additions.csv").exists()
    assert (tmp_path / "out2" / "raw_practical_utility_additions.csv").is_file()
