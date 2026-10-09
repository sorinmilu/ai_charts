#!/usr/bin/env python3
"""Local HTTP server for the AI talking-points chart app.

Reads CSV / markdown / bucket JSON on every API request (no startup cache).
"""

from __future__ import annotations

import csv
import json
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
STATIC = ROOT / "static"
PORT = 8765

CONCERNS = [
    {
        "id": "capability",
        "file": "ai_capability_talking_points.csv",
        "label_en": "Current capability",
        "label_ro": "Capacitățile actuale",
    },
    {
        "id": "utility",
        "file": "ai_practical_utility_talking_points.csv",
        "label_en": "Practical utility",
        "label_ro": "Utilitatea practică",
    },
    {
        "id": "economic",
        "file": "ai_economic_impact_talking_points.csv",
        "label_en": "Middle-class economics",
        "label_ro": "Economia clasei de mijloc",
    },
    {
        "id": "jobs",
        "file": "ai_intellectual_jobs_talking_points.csv",
        "label_en": "Intellectual jobs",
        "label_ro": "Locuri de muncă intelectuale",
    },
    {
        "id": "trajectory",
        "file": "ai_future_trajectory_talking_points.csv",
        "label_en": "Future trajectory",
        "label_ro": "Evoluția pe zece ani",
    },
]


def load_bucket_config() -> dict:
    path = DATA / "source_type_buckets.json"
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def resolve_bucket(source_type: str, config: dict) -> str:
    mapping = config.get("mapping") or {}
    if source_type in mapping:
        return mapping[source_type]
    return config.get("default_bucket") or "Blog / essay"


def parse_level(raw: str | None) -> int | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def year_from_date(raw: str | None) -> str | None:
    if not raw:
        return None
    text = str(raw).strip()
    m = re.match(r"(\d{4})", text)
    return m.group(1) if m else None


def load_points() -> dict:
    buckets_cfg = load_bucket_config()
    points = []
    for concern in CONCERNS:
        path = DATA / concern["file"]
        with path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                level = parse_level(row.get("level"))
                if level is None:
                    continue
                if level < -3 or level > 3:
                    continue
                source_type = (row.get("source_type") or "").strip()
                points.append(
                    {
                        "id": (row.get("id") or "").strip(),
                        "concern": concern["id"],
                        "author": (row.get("author") or "").strip(),
                        "talking_point": (row.get("talking_point") or "").strip(),
                        "level": level,
                        "year": year_from_date(row.get("date")),
                        "source_type": source_type,
                        "source_bucket": resolve_bucket(source_type, buckets_cfg),
                        "source_title": (row.get("source_title") or "").strip(),
                        "source_url": (row.get("source_url") or "").strip(),
                    }
                )
    return {
        "concerns": [
            {
                "id": c["id"],
                "label_en": c["label_en"],
                "label_ro": c["label_ro"],
            }
            for c in CONCERNS
        ],
        "buckets": buckets_cfg.get("buckets") or [],
        "points": points,
    }


def _strip_md(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    return text


def _split_lang_sections(md: str) -> dict[str, str]:
    en_m = re.search(r"^## English\s*$", md, re.M)
    ro_m = re.search(r"^## Română\s*$", md, re.M)
    src_m = re.search(r"^## Source datasets", md, re.M)
    if not en_m or not ro_m:
        raise ValueError("Could not find English / Română sections in markdown")
    en_end = ro_m.start()
    ro_end = src_m.start() if src_m else len(md)
    return {
        "en": md[en_m.end() : en_end].strip(),
        "ro": md[ro_m.end() : ro_end].strip(),
    }


def _parse_level_table(block: str) -> list[dict]:
    levels = []
    for line in block.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        if cells[0].lower() in {"level", "nivel"} or set(cells[0]) <= {"-", "—"}:
            continue
        raw_level = cells[0].replace("−", "-").replace("+", "")
        try:
            level = int(raw_level)
        except ValueError:
            continue
        levels.append(
            {
                "level": level,
                "category": _strip_md(cells[1]),
                "meaning": _strip_md(cells[2]),
            }
        )
    levels.sort(key=lambda x: x["level"])
    return levels


def _parse_lang_block(block: str) -> dict:
    common_m = re.search(
        r"### (?:Common scope and interpretation|Domeniu comun și interpretare)\s*\n(.*?)(?=\n### \d+\.)",
        block,
        re.S,
    )
    common = _strip_md(common_m.group(1)) if common_m else ""

    issues = []
    issue_pattern = re.compile(
        r"### (\d+)\.\s*(.+?)\s*\n(.*?)(?=\n### \d+\.|\Z)",
        re.S,
    )
    for m in issue_pattern.finditer(block):
        body = m.group(3).strip()
        q_m = re.search(r"\*\*(?:Question|Întrebare):\s*(.+?)\*\*", body)
        question = _strip_md(q_m.group(1)) if q_m else ""
        interp_m = re.search(
            r"\*\*(?:Interpretation|Interpretare):\*\*\s*(.+?)(?=\n###|\Z)",
            body,
            re.S,
        )
        interpretation = _strip_md(interp_m.group(1)) if interp_m else ""
        levels = _parse_level_table(body)
        concern_id = CONCERNS[int(m.group(1)) - 1]["id"]
        issues.append(
            {
                "id": concern_id,
                "number": int(m.group(1)),
                "title": _strip_md(m.group(2)),
                "question": question,
                "levels": levels,
                "interpretation": interpretation,
            }
        )
    return {"common_scope": common, "issues": issues}


def load_definitions() -> dict:
    md = (DATA / "ai_five_issues_en_ro.md").read_text(encoding="utf-8")
    sections = _split_lang_sections(md)
    return {
        "en": _parse_lang_block(sections["en"]),
        "ro": _parse_lang_block(sections["ro"]),
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        if urlparse(self.path).path.startswith("/api/"):
            self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def do_GET(self):
        if self._handle_api(write_body=True):
            return
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            return self._send_file(STATIC / "index.html", "text/html; charset=utf-8")
        return super().do_GET()

    def do_HEAD(self):
        if self._handle_api(write_body=False):
            return
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            data = (STATIC / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            return
        return super().do_HEAD()

    def _handle_api(self, write_body: bool) -> bool:
        path = urlparse(self.path).path
        if path == "/api/points":
            payload = load_points()
        elif path == "/api/definitions":
            payload = load_definitions()
        elif path == "/api/buckets":
            payload = load_bucket_config()
        else:
            return False
        self._send_json(payload, write_body=write_body)
        return True

    def _send_json(self, payload: dict, write_body: bool = True):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if write_body:
            self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str):
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"AI talking points → http://127.0.0.1:{PORT}/", flush=True)
    print("Serving with runtime CSV/MD reads (no cache). Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.", flush=True)
        server.server_close()


if __name__ == "__main__":
    main()
