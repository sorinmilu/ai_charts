"""Prompt preparation and runner tests (no API credits)."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import pytest

from updater.research.config import AppConfig
from updater.research.csv_io import parse_csv, read_csv_text, rows_to_csv
from updater.research.prompt_prep import (
    PromptPrepError,
    prepare_prompt,
    resolve_dataset_from_prompt,
    trajectory_analysis_window,
)
from updater.research.providers.base import ProviderResult
from updater.research.runner import run_update

ROOT = Path(__file__).resolve().parents[2]
UTILITY_CSV = ROOT / "web-app/data/ai_practical_utility_talking_points.csv"


def _config(root: Path | None = None) -> AppConfig:
    return AppConfig(
        provider="openai",
        openai_api_key="test-key",
        openai_model="gpt-4o",
        openai_reasoning_effort="medium",
        max_new_rows=40,
        timeout_seconds=60,
        max_output_tokens=1000,
        root=root or ROOT,
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


def test_dry_run_makes_no_api_call():
    provider = _CountingProvider()
    outcome = run_update(
        ROOT / "updater/prompts/practical_utility_prompt.md",
        config=_config(),
        dry_run=True,
        provider=provider,
        research_date=date.fromisoformat("2026-10-09"),
    )
    assert outcome.exit_code == 0
    assert outcome.dry_run is True
    assert provider.calls == 0
    assert outcome.rows_appended == 0
    assert any("Dry run OK" in msg for msg in outcome.messages)


def test_mocked_provider_api_truncated_does_not_change_csv(tmp_path: Path):
    dataset = tmp_path / UTILITY_CSV.name
    shutil.copyfile(UTILITY_CSV, dataset)
    before = dataset.read_text(encoding="utf-8-sig")

    class TruncatedProvider:
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
        dataset=dataset,
        dry_run=False,
        provider=TruncatedProvider(),
        research_date=date.fromisoformat("2026-10-09"),
    )
    assert outcome.exit_code != 0
    assert outcome.rows_appended == 0
    assert dataset.read_text(encoding="utf-8-sig") == before
    assert any("FAILED" in msg for msg in outcome.messages)


def test_mocked_provider_incomplete_research_still_appends(tmp_path: Path):
    dataset = tmp_path / UTILITY_CSV.name
    shutil.copyfile(UTILITY_CSV, dataset)
    header, existing = parse_csv(read_csv_text(dataset))
    before_count = len(existing)

    row = {col: "" for col in header}
    row.update(
        {
            "id": "UTL901",
            "dimension": "Practical utility",
            "author": "Unit Test Author",
            "author_expertise": "Synthetic test fixture",
            "date": "2026-09-01",
            "source_type": "Working paper",
            "evidence_method": "Controlled experiment",
            "domain": "Testing",
            "system_scope": "Synthetic system for unit tests",
            "talking_point": (
                "Second unit-test-only claim: incomplete research status "
                "should still allow validated appends."
            ),
            "level": "1",
            "level_label": "Slightly useful",
            "classification_basis": "Synthetic fixture for incomplete-status append.",
            "net_cost_coverage": "None; test row.",
            "source_title": "Synthetic Unit Test Publication UTL901",
            "source_url": "https://example.com/unique-test-append-utl901",
            "caveat": "Not a real source.",
            "related_source_family": "",
            "claim_time": "At the source date; not a claim about all current systems",
            "classification_is": "Assistant interpretation of published findings or attributed opinion; not an author rating",
            "scale_rubric": existing[0]["scale_rubric"],
            "selection_method": existing[0]["selection_method"],
            "researched_on": "2026-10-09",
        }
    )
    additions = rows_to_csv(header, [row])

    class IncompleteButUsefulProvider:
        def research(self, *, instructions: str, dataset_csv: str, settings):  # noqa: ANN001
            return ProviderResult(
                additions_csv=additions,
                update_report_markdown="one verified row; window incomplete",
                status="incomplete",
                status_reason="Seven verified additions; coverage incomplete",
                response_id="resp_test",
                used_web_search=True,
                api_status="completed",
            )

    outcome = run_update(
        ROOT / "updater/prompts/practical_utility_prompt.md",
        config=_config(),
        dataset=dataset,
        dry_run=False,
        provider=IncompleteButUsefulProvider(),
        research_date=date.fromisoformat("2026-10-09"),
    )
    assert outcome.exit_code == 0, outcome.messages
    assert outcome.rows_appended == 1
    _header, after = parse_csv(read_csv_text(dataset))
    assert len(after) == before_count + 1
    assert after[-1]["id"] == "UTL901"


def test_mocked_provider_no_new_rows_leaves_csv(tmp_path: Path):
    dataset = tmp_path / UTILITY_CSV.name
    shutil.copyfile(UTILITY_CSV, dataset)
    before = dataset.read_text(encoding="utf-8-sig")
    header, _rows = parse_csv(before)
    header_only = ",".join(header) + "\n"

    class EmptyProvider:
        def research(self, *, instructions: str, dataset_csv: str, settings):  # noqa: ANN001
            return ProviderResult(
                additions_csv=header_only,
                update_report_markdown="nothing new",
                status="completed",
                status_reason="",
                used_web_search=True,
                api_status="completed",
            )

    outcome = run_update(
        ROOT / "updater/prompts/practical_utility_prompt.md",
        config=_config(),
        dataset=dataset,
        dry_run=False,
        provider=EmptyProvider(),
        research_date=date.fromisoformat("2026-10-09"),
    )
    assert outcome.exit_code == 0
    assert outcome.rows_appended == 0
    assert dataset.read_text(encoding="utf-8-sig") == before
    assert any("no new rows" in msg for msg in outcome.messages)


def test_mocked_provider_appends_valid_row(tmp_path: Path):
    dataset = tmp_path / UTILITY_CSV.name
    shutil.copyfile(UTILITY_CSV, dataset)
    header, existing = parse_csv(read_csv_text(dataset))
    before_count = len(existing)

    row = {col: "" for col in header}
    row.update(
        {
            "id": "UTL900",
            "dimension": "Practical utility",
            "author": "Unit Test Author",
            "author_expertise": "Synthetic test fixture",
            "date": "2026-09-01",
            "source_type": "Working paper",
            "evidence_method": "Controlled experiment",
            "domain": "Testing",
            "system_scope": "Synthetic system for unit tests",
            "talking_point": (
                "Unit-test-only claim: a unique synthetic finding that must not "
                "match any live dataset row."
            ),
            "level": "1",
            "level_label": "Slightly useful",
            "classification_basis": "Synthetic fixture for append test.",
            "net_cost_coverage": "None; test row.",
            "source_title": "Synthetic Unit Test Publication UTL900",
            "source_url": "https://example.com/unique-test-append-utl900",
            "caveat": "Not a real source.",
            "related_source_family": "",
            "claim_time": "At the source date; not a claim about all current systems",
            "classification_is": "Assistant interpretation of published findings or attributed opinion; not an author rating",
            "scale_rubric": existing[0]["scale_rubric"],
            "selection_method": existing[0]["selection_method"],
            "researched_on": "2026-10-09",
        }
    )
    additions = rows_to_csv(header, [row])

    class GoodProvider:
        def research(self, *, instructions: str, dataset_csv: str, settings):  # noqa: ANN001
            return ProviderResult(
                additions_csv=additions,
                update_report_markdown="one row",
                status="completed",
                status_reason="",
                used_web_search=True,
                api_status="completed",
            )

    outcome = run_update(
        ROOT / "updater/prompts/practical_utility_prompt.md",
        config=_config(),
        dataset=dataset,
        dry_run=False,
        provider=GoodProvider(),
        research_date=date.fromisoformat("2026-10-09"),
    )
    assert outcome.exit_code == 0, outcome.messages
    assert outcome.rows_appended == 1
    _header, after = parse_csv(read_csv_text(dataset))
    assert len(after) == before_count + 1
    assert after[-1]["id"] == "UTL900"
    assert any("UPDATED" in msg for msg in outcome.messages)
