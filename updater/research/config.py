"""Load research-update settings from environment and optional .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

UPDATER_DIR = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class AppConfig:
    provider: str
    openai_api_key: str
    openai_model: str
    openai_reasoning_effort: str | None
    max_new_rows: int
    timeout_seconds: float | None
    max_output_tokens: int | None
    root: Path


def _optional_float(name: str) -> float | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    return float(raw)


def _optional_int(name: str) -> int | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    return int(raw)


def load_config(env_file: Path | None = None, *, root: Path | None = None) -> AppConfig:
    """Load .env then read settings. Process environment variables take precedence."""
    project_root = root or ROOT
    path = env_file if env_file is not None else UPDATER_DIR / ".env"
    if path.is_file():
        load_dotenv(path, override=False)

    max_rows_raw = os.environ.get("RESEARCH_MAX_NEW_ROWS", "40").strip() or "40"
    reasoning_raw = (os.environ.get("OPENAI_REASONING_EFFORT") or "").strip().lower()
    return AppConfig(
        provider=(os.environ.get("AI_PROVIDER") or "openai").strip().lower(),
        openai_api_key=(os.environ.get("OPENAI_API_KEY") or "").strip(),
        openai_model=(os.environ.get("OPENAI_MODEL") or "gpt-4o").strip(),
        openai_reasoning_effort=reasoning_raw or None,
        max_new_rows=int(max_rows_raw),
        timeout_seconds=_optional_float("RESEARCH_TIMEOUT_SECONDS"),
        max_output_tokens=_optional_int("RESEARCH_MAX_OUTPUT_TOKENS"),
        root=project_root,
    )
