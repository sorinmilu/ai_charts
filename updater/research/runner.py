"""Orchestrate prepare → research → validate → write outputs."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .config import AppConfig, load_config
from .csv_io import write_text
from .prompt_prep import PreparedPrompt, default_output_dir, prepare_prompt
from .providers.base import ProviderResult, ResearchProvider
from .providers.openai_provider import OpenAIProviderError, OpenAIResponsesProvider
from .validate import ValidationResult, assess_provider_payload, validate_additions

logger = logging.getLogger(__name__)


@dataclass
class RunOutcome:
    exit_code: int
    output_dir: Path
    prepared: PreparedPrompt
    provider_result: ProviderResult | None
    validation: ValidationResult | None
    messages: list[str]
    dry_run: bool


def get_provider(config: AppConfig, model_override: str | None = None) -> ResearchProvider:
    if config.provider != "openai":
        raise OpenAIProviderError(
            f"Provider {config.provider!r} is not implemented. "
            "Set AI_PROVIDER=openai."
        )
    return OpenAIResponsesProvider(
        api_key=config.openai_api_key,
        model=model_override or config.openai_model,
        timeout_seconds=config.timeout_seconds,
        max_output_tokens=config.max_output_tokens,
    )


def run_update(
    prompt_path: Path,
    *,
    config: AppConfig | None = None,
    dataset: Path | None = None,
    output_dir: Path | None = None,
    model: str | None = None,
    max_new_rows: int | None = None,
    dry_run: bool = False,
    provider: ResearchProvider | None = None,
    research_date: date | None = None,
) -> RunOutcome:
    cfg = config or load_config()
    rows_limit = max_new_rows if max_new_rows is not None else cfg.max_new_rows

    prepared = prepare_prompt(
        prompt_path,
        cfg.root,
        max_new_rows=rows_limit,
        dataset_override=dataset,
        research_date=research_date,
        model=model or cfg.openai_model,
        timeout_seconds=cfg.timeout_seconds,
        max_output_tokens=cfg.max_output_tokens,
    )

    out = output_dir or default_output_dir(
        cfg.root, Path(prepared.dataset_relative_path).stem
    )
    out.mkdir(parents=True, exist_ok=True)

    messages: list[str] = []
    write_text(out / "filled_prompt.md", prepared.filled_instructions)
    write_text(out / "transport_addendum.md", prepared.transport_addendum)
    write_text(out / "attached_dataset.csv", prepared.dataset_csv)

    if dry_run:
        meta = _meta(prepared, None, None, dry_run=True, messages=["dry-run: no API call"])
        write_text(out / "run_meta.json", json.dumps(meta, indent=2, default=str))
        messages.append(f"Dry run complete. Artifacts written under {out}")
        return RunOutcome(
            exit_code=0,
            output_dir=out,
            prepared=prepared,
            provider_result=None,
            validation=None,
            messages=messages,
            dry_run=True,
        )

    active_provider = provider or get_provider(cfg, model_override=model)

    try:
        # OpenAI provider accepts transport_addendum; other providers may not.
        if isinstance(active_provider, OpenAIResponsesProvider):
            result = active_provider.research(
                instructions=prepared.filled_instructions,
                dataset_csv=prepared.dataset_csv,
                settings=prepared.settings,
                transport_addendum=prepared.transport_addendum,
            )
        else:
            result = active_provider.research(
                instructions=(
                    prepared.filled_instructions
                    + "\n\n"
                    + prepared.transport_addendum
                ),
                dataset_csv=prepared.dataset_csv,
                settings=prepared.settings,
            )
    except OpenAIProviderError as exc:
        messages.append(str(exc))
        meta = _meta(prepared, None, None, dry_run=False, messages=messages, error=str(exc))
        write_text(out / "run_meta.json", json.dumps(meta, indent=2, default=str))
        return RunOutcome(
            exit_code=2,
            output_dir=out,
            prepared=prepared,
            provider_result=None,
            validation=None,
            messages=messages,
            dry_run=False,
        )

    # Persist raw provider payload for diagnosis even when incomplete.
    write_text(out / "provider_raw_output.txt", result.raw_output_text or "")
    write_text(out / prepared.dataset_spec.report_basename, result.update_report_markdown or "")
    write_text(
        out / f"raw_{prepared.dataset_spec.additions_basename}",
        result.additions_csv or "",
    )

    payload_errors = assess_provider_payload(
        status=result.status,
        status_reason=result.status_reason,
        additions_csv=result.additions_csv,
        update_report_markdown=result.update_report_markdown,
        api_status=result.api_status,
        used_web_search=result.used_web_search,
        incomplete_reason=result.incomplete_reason,
    )

    validation: ValidationResult | None = None
    exit_code = 0

    if payload_errors:
        messages.extend(payload_errors)
        exit_code = 3
        # Still attempt parse diagnostics without marking import-ready
        if result.additions_csv.strip():
            validation = validate_additions(
                result.additions_csv,
                expected_header=prepared.header,
                existing_rows=prepared.existing_rows,
                spec=prepared.dataset_spec,
                settings=prepared.settings,
            )
            messages.extend(f"HARD: {e}" for e in validation.hard_errors)
            messages.extend(f"REVIEW: {w}" for w in validation.review_warnings)
    else:
        validation = validate_additions(
            result.additions_csv,
            expected_header=prepared.header,
            existing_rows=prepared.existing_rows,
            spec=prepared.dataset_spec,
            settings=prepared.settings,
        )
        messages.extend(f"HARD: {e}" for e in validation.hard_errors)
        messages.extend(f"REVIEW: {w}" for w in validation.review_warnings)

        if validation.ok:
            write_text(
                out / prepared.dataset_spec.additions_basename,
                result.additions_csv,
            )
            if validation.review_warnings:
                messages.append(
                    "Validation passed with review warnings; "
                    "import-ready additions written but human review is required."
                )
                exit_code = 4  # needs review
            else:
                messages.append("Validation passed; import-ready additions written.")
                exit_code = 0
        else:
            messages.append(
                "Hard validation failures; invalid additions retained for diagnosis "
                "and not marked import-ready."
            )
            exit_code = 5

    # Never modify the live dataset here.
    messages.append(
        "Live dataset was not modified. Review outputs before manually appending rows."
    )

    meta = _meta(
        prepared,
        result,
        validation,
        dry_run=False,
        messages=messages,
    )
    write_text(out / "run_meta.json", json.dumps(meta, indent=2, default=str))
    write_text(out / "validation_summary.md", _validation_markdown(messages, validation))

    return RunOutcome(
        exit_code=exit_code,
        output_dir=out,
        prepared=prepared,
        provider_result=result,
        validation=validation,
        messages=messages,
        dry_run=False,
    )


def _meta(
    prepared: PreparedPrompt,
    result: ProviderResult | None,
    validation: ValidationResult | None,
    *,
    dry_run: bool,
    messages: list[str],
    error: str | None = None,
) -> dict[str, Any]:
    settings = prepared.settings
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "dry_run": dry_run,
        "prompt_path": str(prepared.prompt_path),
        "dataset_path": str(prepared.dataset_path),
        "dataset_relative_path": prepared.dataset_relative_path,
        "settings": {
            "research_date": settings.research_date.isoformat(),
            "publication_window_start": settings.publication_window_start.isoformat(),
            "publication_window_end": settings.publication_window_end.isoformat(),
            "older_gap_filling": settings.older_gap_filling,
            "max_new_rows": settings.max_new_rows,
            "append_only": settings.append_only,
            "analysis_window_start": (
                settings.analysis_window_start.isoformat()
                if settings.analysis_window_start
                else None
            ),
            "analysis_window_end": (
                settings.analysis_window_end.isoformat()
                if settings.analysis_window_end
                else None
            ),
            "model": settings.model,
        },
        "response_id": result.response_id if result else None,
        "provider_status": result.status if result else None,
        "api_status": result.api_status if result else None,
        "used_web_search": result.used_web_search if result else None,
        "validation": {
            "hard_errors": validation.hard_errors if validation else [],
            "review_warnings": validation.review_warnings if validation else [],
            "import_ready": validation.import_ready if validation else False,
            "needs_review": validation.needs_review if validation else False,
        },
        "messages": messages,
        "error": error,
        "note": (
            "File validation does not verify the truth of citations or research claims. "
            "Human review is required before importing into the app. "
            "Existing dataset rows are never removed or updated by this tool."
        ),
    }


def _validation_markdown(messages: list[str], validation: ValidationResult | None) -> str:
    lines = ["# Validation summary", ""]
    for msg in messages:
        lines.append(f"- {msg}")
    if validation:
        lines.append("")
        lines.append(f"Import ready: {validation.import_ready}")
        lines.append(f"Needs review: {validation.needs_review}")
    lines.append("")
    lines.append(
        "Limitation: deterministic checks do not verify citation truth or "
        "guarantee semantic deduplication."
    )
    return "\n".join(lines) + "\n"
