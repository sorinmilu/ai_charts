"""Focused tests for CSV parsing, validation, and dedupe (no API credits)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from updater.research.csv_io import parse_csv, rows_to_csv
from updater.research.datasets import CAPABILITY, JOBS, TRAJECTORY, UTILITY
from updater.research.dedupe import (
    extract_arxiv_id,
    extract_doi,
    normalise_url,
    share_publication,
)
from updater.research.providers.base import RunSettings
from updater.research.validate import (
    assess_provider_payload,
    validate_additions,
)

ROOT = Path(__file__).resolve().parents[2]


def _settings(day: str = "2026-10-09") -> RunSettings:
    d = date.fromisoformat(day)
    return RunSettings(
        research_date=d,
        publication_window_start=date.fromisoformat("2026-07-08"),
        publication_window_end=d,
        older_gap_filling=True,
        max_new_rows=40,
        append_only=True,
    )


def test_parse_quoted_csv_fields():
    text = (
        'id,talking_point,source_title\n'
        '"UTL999","He said, ""hello"", then left.","Title, with comma"\n'
    )
    header, rows = parse_csv(text)
    assert header == ["id", "talking_point", "source_title"]
    assert rows[0]["talking_point"] == 'He said, "hello", then left.'
    assert rows[0]["source_title"] == "Title, with comma"


def test_utility_level_label_rules():
    header = [
        "id",
        "dimension",
        "author",
        "author_expertise",
        "date",
        "source_type",
        "evidence_method",
        "domain",
        "system_scope",
        "talking_point",
        "level",
        "level_label",
        "classification_basis",
        "net_cost_coverage",
        "source_title",
        "source_url",
        "caveat",
        "related_source_family",
        "claim_time",
        "classification_is",
        "scale_rubric",
        "selection_method",
        "researched_on",
    ]
    row = {col: "" for col in header}
    row.update(
        {
            "id": "UTL999",
            "talking_point": "A unique claim about practical utility for tests.",
            "level": "3",
            "level_label": "Wrong label",
            "source_title": "Test Paper",
            "source_url": "https://example.com/paper",
            "researched_on": "2026-10-09",
        }
    )
    csv_text = rows_to_csv(header, [row])
    result = validate_additions(
        csv_text,
        expected_header=header,
        existing_rows=[],
        spec=UTILITY,
        settings=_settings(),
    )
    assert any("level_label" in e for e in result.hard_errors)


def test_id_collision_with_existing():
    header = ["id", "talking_point", "level", "level_label", "source_title", "source_url", "researched_on"]
    # Minimal header mismatch will also error; use matching custom header for unit focus
    # Prefer real utility header subset via full expected from a tiny synthetic dataset
    full_header = list(
        parse_csv((ROOT / "web-app/data/ai_practical_utility_talking_points.csv").read_text(encoding="utf-8-sig"))[0]
    )
    existing = [{"id": "UTL001", "talking_point": "old", "source_url": "https://a.example/1", "source_title": "Old"}]
    row = {col: "x" for col in full_header}
    row.update(
        {
            "id": "UTL001",
            "talking_point": "Brand new distinct talking point for collision test.",
            "level": "1",
            "level_label": "Slightly useful",
            "source_title": "Collision Paper",
            "source_url": "https://example.com/collision",
            "researched_on": "2026-10-09",
        }
    )
    result = validate_additions(
        rows_to_csv(full_header, [row]),
        expected_header=full_header,
        existing_rows=existing,
        spec=UTILITY,
        settings=_settings(),
    )
    assert any("collides" in e for e in result.hard_errors)


def test_arxiv_version_and_tracking_url_dedupe():
    assert extract_arxiv_id("https://arxiv.org/abs/2302.06590v3") == "2302.06590"
    assert extract_arxiv_id("https://arxiv.org/pdf/2302.06590.pdf") == "2302.06590"
    assert extract_doi("https://doi.org/10.1126/science.adh2586") == "10.1126/science.adh2586"

    a = {
        "source_url": "https://arxiv.org/abs/2302.06590v2",
        "source_title": "The Impact of AI on Developer Productivity",
    }
    b = {
        "source_url": "https://arxiv.org/abs/2302.06590?utm_source=twitter&utm_campaign=x",
        "source_title": "The Impact of AI on Developer Productivity",
    }
    assert share_publication(a, b)
    assert normalise_url(b["source_url"]) == normalise_url(
        "https://arxiv.org/abs/2302.06590"
    )


def test_claim_dataset_allows_shared_publication_with_warning():
    header = list(
        parse_csv((ROOT / "web-app/data/ai_intellectual_jobs_talking_points.csv").read_text(encoding="utf-8-sig"))[0]
    )
    existing = [
        {
            "id": "JOB001",
            "talking_point": "Existing employment claim A about young workers.",
            "source_url": "https://example.com/study",
            "source_title": "Shared Study Title",
        }
    ]
    row = {col: "" for col in header}
    row.update(
        {
            "id": "JOB099",
            "talking_point": "A different employment claim B about experienced workers.",
            "level": "0",
            "level_label": "Broadly stable employment",
            "source_title": "Shared Study Title",
            "source_url": "https://example.com/study",
            "researched_on": "2026-10-09",
        }
    )
    result = validate_additions(
        rows_to_csv(header, [row]),
        expected_header=header,
        existing_rows=existing,
        spec=JOBS,
        settings=_settings(),
    )
    assert result.ok
    assert any("shares publication identity" in w for w in result.review_warnings)


def test_publication_unit_rejects_shared_publication():
    header = list(
        parse_csv((ROOT / "web-app/data/ai_practical_utility_talking_points.csv").read_text(encoding="utf-8-sig"))[0]
    )
    existing = [
        {
            "id": "UTL001",
            "talking_point": "Existing utility claim.",
            "source_url": "https://arxiv.org/abs/2302.06590",
            "source_title": "The Impact of AI on Developer Productivity",
        }
    ]
    row = {col: "" for col in header}
    row.update(
        {
            "id": "UTL099",
            "talking_point": "A different wording of a utility finding.",
            "level": "2",
            "level_label": "Moderately useful",
            "source_title": "The Impact of AI on Developer Productivity",
            "source_url": "https://arxiv.org/abs/2302.06590v5",
            "researched_on": "2026-10-09",
        }
    )
    result = validate_additions(
        rows_to_csv(header, [row]),
        expected_header=header,
        existing_rows=existing,
        spec=UTILITY,
        settings=_settings(),
    )
    assert not result.ok
    assert any("publication appears to duplicate" in e for e in result.hard_errors)


def test_future_window_consistency_and_chart_eligibility():
    header = list(
        parse_csv((ROOT / "web-app/data/ai_future_trajectory_talking_points.csv").read_text(encoding="utf-8-sig"))[0]
    )
    settings = _settings()
    settings = RunSettings(
        research_date=settings.research_date,
        publication_window_start=settings.publication_window_start,
        publication_window_end=settings.publication_window_end,
        older_gap_filling=True,
        max_new_rows=40,
        append_only=True,
        analysis_window_start=date.fromisoformat("2026-10-06"),
        analysis_window_end=date.fromisoformat("2036-10-06"),
    )
    row = {col: "" for col in header}
    row.update(
        {
            "id": "T099",
            "talking_point": "Unique trajectory claim for window tests.",
            "level": "",
            "level_label": "Unclassified",
            "source_title": "Window Paper",
            "source_url": "https://example.com/window",
            "researched_on": "2026-10-09",
            "include_in_10_year_chart": "Yes",
            "analysis_window_start": "2026-10-06",
            "analysis_window_end": "2036-10-06",
        }
    )
    result = validate_additions(
        rows_to_csv(header, [row]),
        expected_header=header,
        existing_rows=[],
        spec=TRAJECTORY,
        settings=settings,
    )
    assert any("include_in_10_year_chart=Yes" in e for e in result.hard_errors)

    row["include_in_10_year_chart"] = "No"
    row["analysis_window_start"] = "2027-01-01"
    result2 = validate_additions(
        rows_to_csv(header, [row]),
        expected_header=header,
        existing_rows=[],
        spec=TRAJECTORY,
        settings=settings,
    )
    assert any("analysis window" in e for e in result2.hard_errors)


def test_capability_source_type_matches_type():
    header = list(
        parse_csv((ROOT / "web-app/data/ai_capability_talking_points.csv").read_text(encoding="utf-8-sig"))[0]
    )
    row = {col: "" for col in header}
    row.update(
        {
            "id": "CAP099",
            "talking_point": "Unique capability claim for type agreement test.",
            "level": "1",
            "level_label": "Slightly positive",
            "source_title": "Cap Paper",
            "source_url": "https://example.com/cap",
            "source_type": "Blog",
            "type": "Podcast",
            "researched_on": "2026-10-09",
        }
    )
    result = validate_additions(
        rows_to_csv(header, [row]),
        expected_header=header,
        existing_rows=[],
        spec=CAPABILITY,
        settings=_settings(),
    )
    assert any("source_type and type disagree" in e for e in result.hard_errors)


def test_malformed_and_incomplete_api_output():
    # Truncated API response is still a hard fail.
    errors = assess_provider_payload(
        status="incomplete",
        status_reason="max_output_tokens",
        additions_csv="id\nCAP999\n",
        update_report_markdown="partial",
        api_status="incomplete",
        used_web_search=True,
        incomplete_reason="max_output_tokens",
    )
    assert any("API response status" in e for e in errors)

    # Legacy model status "incomplete" with a CSV still counts as usable.
    errors_partial = assess_provider_payload(
        status="incomplete",
        status_reason="legacy incomplete with rows",
        additions_csv="id\nCAP999\n",
        update_report_markdown="partial",
        api_status="completed",
        used_web_search=True,
        incomplete_reason=None,
    )
    assert errors_partial == []

    # Legacy incomplete with no CSV → hard fail.
    errors_empty = assess_provider_payload(
        status="incomplete",
        status_reason="could not finish",
        additions_csv="",
        update_report_markdown="partial",
        api_status="completed",
        used_web_search=True,
        incomplete_reason=None,
    )
    assert any("additions_csv is empty" in e or "Invalid result status" in e for e in errors_empty)

    errors2 = assess_provider_payload(
        status="completed",
        status_reason="",
        additions_csv="",
        update_report_markdown="report",
        api_status="completed",
        used_web_search=True,
        incomplete_reason=None,
    )
    assert any("additions_csv is empty" in e for e in errors2)

    errors3 = assess_provider_payload(
        status="completed",
        status_reason="",
        additions_csv="id\n",
        update_report_markdown="ok",
        api_status="completed",
        used_web_search=False,
        incomplete_reason=None,
    )
    assert any("web_search" in e for e in errors3)
