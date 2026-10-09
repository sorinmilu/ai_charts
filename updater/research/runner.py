"""Orchestrate prepare → research → validate → append to the live CSV."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from .config import AppConfig, load_config
from .csv_io import rows_to_csv, write_text
from .progress import NO_PROGRESS, Progress
from .prompt_prep import PreparedPrompt, prepare_prompt
from .providers.base import ProviderResult, ResearchProvider
from .providers.openai_provider import OpenAIProviderError, OpenAIResponsesProvider
from .validate import ValidationResult, assess_provider_payload, validate_additions

logger = logging.getLogger(__name__)


@dataclass
class RunOutcome:
    exit_code: int
    prepared: PreparedPrompt
    provider_result: ProviderResult | None
    validation: ValidationResult | None
    messages: list[str]
    dry_run: bool
    rows_appended: int = 0


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
        reasoning_effort=config.openai_reasoning_effort,
    )


def run_update(
    prompt_path: Path,
    *,
    config: AppConfig | None = None,
    dataset: Path | None = None,
    model: str | None = None,
    max_new_rows: int | None = None,
    dry_run: bool = False,
    provider: ResearchProvider | None = None,
    research_date: date | None = None,
    progress: Progress | None = None,
) -> RunOutcome:
    prog = progress if progress is not None else NO_PROGRESS
    cfg = config or load_config()
    rows_limit = max_new_rows if max_new_rows is not None else cfg.max_new_rows

    prog.blank()
    prog.step("Reading prompt")
    prog.ok(str(prompt_path))

    prog.step("Reading dataset and preparing request")
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
    settings = prepared.settings
    prog.ok(
        f"{prepared.dataset_relative_path} "
        f"({len(prepared.existing_rows)} rows, max_new={settings.max_new_rows})"
    )

    messages: list[str] = []

    if dry_run:
        summary = (
            f"Dry run OK — prompt={prepared.prompt_path.name} "
            f"dataset={prepared.dataset_relative_path} "
            f"existing_rows={len(prepared.existing_rows)} "
            f"max_new_rows={settings.max_new_rows} "
            f"model={settings.model or '(default)'}"
        )
        prog.step("Dry run")
        prog.ok("wiring checks passed (no API call)")
        return _finish(
            cfg.root, prepared, None, None, messages, summary, dry_run=True, progress=prog
        )

    model_name = model or cfg.openai_model
    effort = cfg.openai_reasoning_effort or "default"

    if provider is None:
        prog.step("Connecting to OpenAI")
        try:
            active_provider = get_provider(cfg, model_override=model)
        except OpenAIProviderError as exc:
            prog.fail(str(exc))
            return _finish(
                cfg.root,
                prepared,
                None,
                None,
                messages,
                f"ERROR {prepared.dataset_relative_path}: {exc}",
                dry_run=False,
                exit_code=2,
                progress=prog,
            )
        detail = f"model={model_name}"
        if cfg.openai_reasoning_effort:
            detail += f", reasoning={effort}"
        prog.ok(detail)
    else:
        active_provider = provider
        prog.step("Using test provider")
        prog.ok(type(active_provider).__name__)

    prog.step("Sending prompt")
    prog.note("web search required — this can take a while")
    try:
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
        prog.fail(str(exc))
        return _finish(
            cfg.root,
            prepared,
            None,
            None,
            messages,
            f"ERROR {prepared.dataset_relative_path}: {exc}",
            dry_run=False,
            exit_code=2,
            progress=prog,
        )

    search = "web search used" if result.used_web_search else "no web search detected"
    prog.ok(f"status={result.status}, {search}")

    prog.step("Checking model payload")
    payload_errors = assess_provider_payload(
        status=result.status,
        status_reason=result.status_reason,
        additions_csv=result.additions_csv,
        update_report_markdown=result.update_report_markdown,
        api_status=result.api_status,
        used_web_search=result.used_web_search,
        incomplete_reason=result.incomplete_reason,
    )
    if payload_errors:
        detail = "; ".join(payload_errors)
        prog.fail(detail)
        return _finish(
            cfg.root,
            prepared,
            result,
            None,
            messages,
            f"FAILED {prepared.dataset_relative_path}: {detail}",
            dry_run=False,
            exit_code=3,
            progress=prog,
        )
    prog.ok("payload looks complete")

    prog.step("Validating additions")
    validation = validate_additions(
        result.additions_csv,
        expected_header=prepared.header,
        existing_rows=prepared.existing_rows,
        spec=prepared.dataset_spec,
        settings=prepared.settings,
    )
    if not validation.ok:
        detail = "; ".join(validation.hard_errors[:5])
        if len(validation.hard_errors) > 5:
            detail += f" (+{len(validation.hard_errors) - 5} more)"
        prog.fail(detail)
        return _finish(
            cfg.root,
            prepared,
            result,
            validation,
            messages,
            f"FAILED {prepared.dataset_relative_path}: {detail}",
            dry_run=False,
            exit_code=5,
            progress=prog,
        )

    new_rows = validation.additions_rows
    if not new_rows:
        prog.ok("no new rows to add")
        return _finish(
            cfg.root,
            prepared,
            result,
            validation,
            messages,
            f"OK {prepared.dataset_relative_path}: no new rows",
            dry_run=False,
            exit_code=0,
            progress=prog,
        )
    prog.ok(f"{len(new_rows)} row(s) ready")

    prog.step("Updating CSV")
    merged = prepared.existing_rows + new_rows
    write_text(
        prepared.dataset_path,
        rows_to_csv(prepared.header, merged),
    )
    prog.ok(
        f"appended {len(new_rows)} "
        f"({len(prepared.existing_rows)} → {len(merged)})"
    )
    return _finish(
        cfg.root,
        prepared,
        result,
        validation,
        messages,
        (
            f"UPDATED {prepared.dataset_relative_path}: "
            f"appended {len(new_rows)} row(s) "
            f"({len(prepared.existing_rows)} → {len(merged)})"
        ),
        dry_run=False,
        exit_code=0,
        rows_appended=len(new_rows),
        progress=prog,
    )


def _finish(
    root: Path,
    prepared: PreparedPrompt,
    result: ProviderResult | None,
    validation: ValidationResult | None,
    messages: list[str],
    summary: str,
    *,
    dry_run: bool,
    exit_code: int = 0,
    rows_appended: int = 0,
    progress: Progress = NO_PROGRESS,
) -> RunOutcome:
    messages.append(summary)
    logger.info(summary)
    log_path = _append_run_log(root, summary)
    messages.append(f"Logged to {log_path}")
    progress.blank()
    if exit_code == 0:
        progress.note(summary)
        progress.note(f"log: {log_path}")
    else:
        progress.note(summary)
        progress.note(f"log: {log_path}")
    progress.blank()
    return RunOutcome(
        exit_code=exit_code,
        prepared=prepared,
        provider_result=result,
        validation=validation,
        messages=messages,
        dry_run=dry_run,
        rows_appended=rows_appended,
    )


def _append_run_log(root: Path, line: str) -> Path:
    log_dir = root / "updater" / "output"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "runs.log"
    stamp = datetime.now().isoformat(timespec="seconds")
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{stamp} {line}\n")
    return log_path
