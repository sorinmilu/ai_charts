"""CSV helpers using the standard library csv module."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any


def read_csv_text(path: Path) -> str:
    """Read CSV file text, preserving content (including UTF-8 BOM if present)."""
    return path.read_text(encoding="utf-8-sig")


def parse_csv(text: str) -> tuple[list[str], list[dict[str, str]]]:
    """Parse CSV text into header and row dicts. Handles quoted fields."""
    # utf-8-sig style BOM may remain if present as a character
    if text.startswith("\ufeff"):
        text = text[1:]
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration as exc:
        raise ValueError("CSV is empty") from exc
    header = [h.strip() for h in header]
    if not header or not any(header):
        raise ValueError("CSV header is empty")

    rows: list[dict[str, str]] = []
    for line_no, fields in enumerate(reader, start=2):
        if len(fields) == 0 or all(not f.strip() for f in fields):
            continue
        if len(fields) != len(header):
            raise ValueError(
                f"CSV row {line_no}: expected {len(header)} fields, got {len(fields)}"
            )
        rows.append({header[i]: fields[i] for i in range(len(header))})
    return header, rows


def rows_to_csv(header: list[str], rows: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    for row in rows:
        writer.writerow([row.get(col, "") for col in header])
    return buf.getvalue()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
