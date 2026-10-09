"""Validate research additions against dataset schema and dedupe rules."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from urllib.parse import urlparse

from .csv_io import parse_csv
from .datasets import DatasetSpec, InclusionUnit
from .dedupe import claim_key, claims_similar, publication_keys, share_publication
from .providers.base import RunSettings

ID_RE_TEMPLATE = r"^{prefix}(\d{{3,}})$"


@dataclass
class ValidationResult:
    hard_errors: list[str] = field(default_factory=list)
    review_warnings: list[str] = field(default_factory=list)
    additions_rows: list[dict[str, str]] = field(default_factory=list)
    header: list[str] = field(default_factory=list)
    needs_review: bool = False
    import_ready: bool = False

    @property
    def ok(self) -> bool:
        return not self.hard_errors


def _level_key(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    try:
        value = int(float(text))
    except ValueError:
        return text
    return str(value)


def _valid_http_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _check_id(row_id: str, prefix: str) -> bool:
    pattern = re.compile(ID_RE_TEMPLATE.format(prefix=re.escape(prefix)))
    return bool(pattern.match(row_id))


def validate_additions(
    additions_csv: str,
    *,
    expected_header: list[str],
    existing_rows: list[dict[str, str]],
    spec: DatasetSpec,
    settings: RunSettings,
) -> ValidationResult:
    result = ValidationResult()

    try:
        header, rows = parse_csv(additions_csv)
    except ValueError as exc:
        result.hard_errors.append(f"Failed to parse additions CSV: {exc}")
        return result

    result.header = header
    result.additions_rows = rows

    if header != expected_header:
        result.hard_errors.append(
            "Additions header does not match the input dataset "
            f"(expected {expected_header!r}, got {header!r})."
        )
        # Continue with further checks where possible, but not import-ready.

    existing_ids = {(r.get("id") or "").strip() for r in existing_rows}
    seen_ids: set[str] = set()
    research_date = settings.research_date.isoformat()

    for i, row in enumerate(rows, start=1):
        prefix = f"additions row {i}"
        row_id = (row.get("id") or "").strip()
        if not row_id:
            result.hard_errors.append(f"{prefix}: missing id")
        else:
            if not _check_id(row_id, spec.id_prefix):
                result.hard_errors.append(
                    f"{prefix}: id {row_id!r} does not match prefix "
                    f"{spec.id_prefix}###"
                )
            if row_id in existing_ids:
                result.hard_errors.append(
                    f"{prefix}: id {row_id} collides with an existing dataset row"
                )
            if row_id in seen_ids:
                result.hard_errors.append(
                    f"{prefix}: duplicate id {row_id} within additions"
                )
            seen_ids.add(row_id)

        level_key = _level_key(row.get("level") or "")
        label = (row.get("level_label") or "").strip()
        if level_key not in spec.level_labels and not (
            level_key == "" and spec.allows_unclassified
        ):
            # Empty handled via allows_unclassified
            if level_key == "" and not spec.allows_unclassified:
                result.hard_errors.append(
                    f"{prefix}: blank level not permitted for this dataset"
                )
            elif level_key != "":
                result.hard_errors.append(
                    f"{prefix}: invalid level {row.get('level')!r}"
                )
        else:
            expected_label = spec.level_labels.get(level_key)
            if expected_label is not None and label != expected_label:
                result.hard_errors.append(
                    f"{prefix}: level_label {label!r} does not match level "
                    f"{level_key!r} (expected {expected_label!r})"
                )
            if level_key == "" and spec.unclassified_label and label != spec.unclassified_label:
                result.hard_errors.append(
                    f"{prefix}: blank level requires unclassified label "
                    f"{spec.unclassified_label!r}, got {label!r}"
                )

        title = (row.get("source_title") or "").strip()
        url = (row.get("source_url") or "").strip()
        if not title:
            result.hard_errors.append(f"{prefix}: missing source_title")
        if not url:
            result.hard_errors.append(f"{prefix}: missing source_url")
        elif not _valid_http_url(url):
            result.hard_errors.append(
                f"{prefix}: source_url must use http or https ({url!r})"
            )

        researched = (row.get("researched_on") or "").strip()
        if researched != research_date:
            result.hard_errors.append(
                f"{prefix}: researched_on {researched!r} != run date {research_date!r}"
            )

        if spec.has_type_column:
            source_type = (row.get("source_type") or "").strip()
            type_col = (row.get("type") or "").strip()
            if source_type != type_col:
                result.hard_errors.append(
                    f"{prefix}: source_type and type disagree "
                    f"({source_type!r} vs {type_col!r})"
                )

        if spec.is_trajectory:
            _validate_trajectory_row(row, settings, result, prefix)

    _validate_duplicates(rows, existing_rows, spec, result)

    result.needs_review = bool(result.review_warnings) or bool(result.hard_errors)
    result.import_ready = result.ok and not result.hard_errors
    if result.review_warnings:
        result.needs_review = True
    return result


def _validate_trajectory_row(
    row: dict[str, str],
    settings: RunSettings,
    result: ValidationResult,
    prefix: str,
) -> None:
    if settings.analysis_window_start is None or settings.analysis_window_end is None:
        result.hard_errors.append(f"{prefix}: missing fixed analysis window in settings")
        return

    start = (row.get("analysis_window_start") or "").strip()
    end = (row.get("analysis_window_end") or "").strip()
    expected_start = settings.analysis_window_start.isoformat()
    expected_end = settings.analysis_window_end.isoformat()
    if start != expected_start or end != expected_end:
        result.hard_errors.append(
            f"{prefix}: analysis window {start!r}→{end!r} does not match "
            f"dataset window {expected_start!r}→{expected_end!r}"
        )

    chart = (row.get("include_in_10_year_chart") or "").strip()
    if chart not in {"Yes", "No"}:
        result.hard_errors.append(
            f"{prefix}: include_in_10_year_chart must be Yes or No, got {chart!r}"
        )

    level_blank = not (row.get("level") or "").strip()
    label = (row.get("level_label") or "").strip()
    if chart == "Yes" and (level_blank or label == "Unclassified"):
        result.hard_errors.append(
            f"{prefix}: include_in_10_year_chart=Yes is not allowed for unclassified claims"
        )


def _validate_duplicates(
    additions: list[dict[str, str]],
    existing: list[dict[str, str]],
    spec: DatasetSpec,
    result: ValidationResult,
) -> None:
    existing_claim_keys = {claim_key(r): (r.get("id") or "?") for r in existing if claim_key(r)}
    existing_pub_index: list[tuple[str, dict[str, str]]] = [
        ((r.get("id") or "?"), r) for r in existing
    ]

    addition_claim_keys: dict[str, str] = {}
    for i, row in enumerate(additions, start=1):
        ck = claim_key(row)
        rid = (row.get("id") or f"row{i}")
        if not ck:
            result.hard_errors.append(f"additions row {i}: empty talking_point")
            continue
        if ck in existing_claim_keys:
            result.hard_errors.append(
                f"additions row {i} ({rid}): exact duplicate claim of existing "
                f"id {existing_claim_keys[ck]}"
            )
        if ck in addition_claim_keys:
            result.hard_errors.append(
                f"additions row {i} ({rid}): exact duplicate claim within additions "
                f"(also {addition_claim_keys[ck]})"
            )
        addition_claim_keys[ck] = rid

        # Near-duplicate claims (review warning)
        for other_id, other in existing_pub_index:
            other_claim = other.get("talking_point") or ""
            if claims_similar(row.get("talking_point") or "", other_claim):
                if claim_key(row) != claim_key(other):
                    result.review_warnings.append(
                        f"{rid}: likely similar claim to existing {other_id} "
                        f"(SequenceMatcher >= threshold; not a semantic guarantee)"
                    )

        for j, other in enumerate(additions, start=1):
            if j <= i:
                continue
            if claims_similar(row.get("talking_point") or "", other.get("talking_point") or ""):
                if claim_key(row) != claim_key(other):
                    other_id = other.get("id") or f"row{j}"
                    result.review_warnings.append(
                        f"{rid}: likely similar claim to additions {other_id} "
                        f"(SequenceMatcher >= threshold; not a semantic guarantee)"
                    )

        # Publication identity
        for other_id, other in existing_pub_index:
            if not share_publication(row, other):
                continue
            if spec.inclusion_unit == InclusionUnit.PUBLICATION:
                result.hard_errors.append(
                    f"additions row {i} ({rid}): publication appears to duplicate "
                    f"existing id {other_id} (DOI/arXiv/URL/title identity)"
                )
            else:
                result.review_warnings.append(
                    f"{rid}: shares publication identity with existing {other_id}; "
                    f"review that the claim is distinct (claim-based dataset)"
                )

        for j, other in enumerate(additions, start=1):
            if j <= i:
                continue
            if not share_publication(row, other):
                continue
            other_id = other.get("id") or f"row{j}"
            if spec.inclusion_unit == InclusionUnit.PUBLICATION:
                result.hard_errors.append(
                    f"additions row {i} ({rid}): publication duplicate within "
                    f"additions ({other_id})"
                )
            else:
                result.review_warnings.append(
                    f"{rid}: shares publication identity with additions {other_id}; "
                    f"review that the claim is distinct"
                )


def assess_provider_payload(
    *,
    status: str,
    status_reason: str,
    additions_csv: str,
    update_report_markdown: str,
    api_status: str | None,
    used_web_search: bool,
    incomplete_reason: str | None,
) -> list[str]:
    """Hard errors for incomplete/failed/malformed provider results."""
    errors: list[str] = []
    if api_status and api_status not in {"completed"}:
        errors.append(
            f"API response status is {api_status!r}"
            + (f" ({incomplete_reason})" if incomplete_reason else "")
            + "; not treating output as successful research."
        )
    if status == "failed":
        errors.append(f"Provider reported failed: {status_reason or '(no reason)'}")
    if status == "incomplete":
        errors.append(
            f"Provider reported incomplete: {status_reason or incomplete_reason or '(no reason)'}; "
            "partial rows will not be imported."
        )
    if status not in {"completed", "incomplete", "failed"}:
        errors.append(f"Invalid result status {status!r}")
    if not used_web_search and status == "completed":
        errors.append(
            "Research completed without detectable web_search tool use; "
            "refusing to accept stored-knowledge-only output as verified research."
        )
    if status == "completed":
        if additions_csv is None or not str(additions_csv).strip():
            errors.append("completed status but additions_csv is empty")
        if update_report_markdown is None or not str(update_report_markdown).strip():
            errors.append("completed status but update_report_markdown is empty")
    return errors
