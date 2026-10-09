#!/usr/bin/env python3
"""Update AI research CSV datasets using Markdown research prompts.

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
from updater.research.prompt_prep import PromptPrepError
from updater.research.providers.openai_provider import OpenAIProviderError
from updater.research.runner import run_update


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run a research prompt against its named CSV dataset via OpenAI "
            "Responses API with web search. Writes review artifacts; does not "
            "modify live web-app/data/*.csv files."
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
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for additions, report, and diagnostics",
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
        help="Prepare filled prompt and attachment only; make no API call",
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
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    try:
        config = load_config()
        outcome = run_update(
            args.prompt,
            config=config,
            dataset=args.dataset,
            output_dir=args.output_dir,
            model=args.model,
            max_new_rows=args.max_new_rows,
            dry_run=args.dry_run,
        )
    except PromptPrepError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except OpenAIProviderError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    for message in outcome.messages:
        print(message)
    print(f"Output directory: {outcome.output_dir}")
    return outcome.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
