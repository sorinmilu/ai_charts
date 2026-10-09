#!/usr/bin/env python3
"""Update a talking-points CSV using a Markdown research prompt.

Example:
  python updater/update_data_csv.py updater/prompts/practical_utility_prompt.md
  python updater/update_data_csv.py updater/prompts/future_trajectory_prompt.md --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from updater.research.config import load_config
from updater.research.progress import Progress
from updater.research.prompt_prep import PromptPrepError
from updater.research.providers.openai_provider import OpenAIProviderError
from updater.research.runner import run_update


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Research new talking points via OpenAI (with web search) and append "
            "validated rows to the live CSV named in the prompt."
        )
    )
    parser.add_argument(
        "prompt",
        type=Path,
        help="Path to the research prompt Markdown file",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="Optional path to the dataset CSV (must match the file named in the prompt)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override OPENAI_MODEL for this run",
    )
    parser.add_argument(
        "--max-new-rows",
        type=int,
        default=None,
        help="Ceiling on new rows (default from RESEARCH_MAX_NEW_ROWS or 40)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check prompt/dataset wiring only; no API call, no CSV changes",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    progress = Progress(enabled=True)

    try:
        progress.step("Loading configuration")
        config = load_config()
        progress.ok(f"provider={config.provider}, model={config.openai_model}")

        outcome = run_update(
            args.prompt,
            config=config,
            dataset=args.dataset,
            model=args.model,
            max_new_rows=args.max_new_rows,
            dry_run=args.dry_run,
            progress=progress,
        )
    except PromptPrepError as exc:
        progress.fail(str(exc))
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except OpenAIProviderError as exc:
        progress.fail(str(exc))
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        progress.fail(str(exc))
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return outcome.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
