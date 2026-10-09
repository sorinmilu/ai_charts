# Research CSV updater

`update_data_csv.py` runs a Markdown research prompt against its named talking-points CSV using the OpenAI Responses API with web search. It writes review artifacts; it does **not** modify live files under `web-app/data/`.

## Setup

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r updater/requirements.txt
cp updater/.env.example updater/.env
# Edit updater/.env and set OPENAI_API_KEY (and optionally OPENAI_MODEL)
```

### Environment (`updater/.env`)

| Variable | Purpose |
|----------|---------|
| `AI_PROVIDER` | Must be `openai` (only implemented provider) |
| `OPENAI_API_KEY` | Secret; never commit |
| `OPENAI_MODEL` | Model supporting Responses API + `web_search` (default `gpt-4o`) |
| `RESEARCH_MAX_NEW_ROWS` | Ceiling on new rows (default `40`) |
| `RESEARCH_TIMEOUT_SECONDS` | Optional HTTP timeout |
| `RESEARCH_MAX_OUTPUT_TOKENS` | Optional generation budget |

Process environment variables override values from `.env`.  
`ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` are reserved in `.env.example` for a future provider and are not required.

## Directory map

| Path | Role |
|------|------|
| `updater/prompts/*.md` | Research prompts (complete instructions; each names its `web-app/data/*.csv`) |
| `web-app/data/*_talking_points.csv` | Live datasets consumed by the chart app |
| `updater/research/` | Python library (prep, provider, validation) |
| `updater/output/<dataset>/<timestamp>/` | Run artifacts (gitignored) |
| `updater/update_data_csv.py` | CLI entrypoint |

Prompt → dataset mapping is taken **from the prompt file**, not guessed by the model. If the path is missing or the file is not on disk, the script exits with an error.

## Example commands

From the project root:

```bash
# Normal research run (calls OpenAI; incurs cost)
python updater/update_data_csv.py updater/prompts/practical_utility_prompt.md

# Future trajectory (preserves existing analysis window from the CSV)
python updater/update_data_csv.py updater/prompts/future_trajectory_prompt.md

# Prepare filled prompt + full CSV attachment only (no API call)
python updater/update_data_csv.py updater/prompts/current_capability_prompt.md --dry-run

# Overrides
python updater/update_data_csv.py updater/prompts/intellectual_jobs_Prompt.md \
  --model gpt-4o \
  --max-new-rows 20 \
  --output-dir /tmp/jobs_run
```

### Outputs (per run directory)

- `*_additions.csv` — written only when validation hard-checks pass (import-ready candidate)
- `*_update_report.md` — model research report
- `raw_*_additions.csv` — model CSV retained even when invalid
- `filled_prompt.md`, `attached_dataset.csv`, `run_meta.json`, `validation_summary.md`

**Live `web-app/data/*.csv` files are never appended or edited by this tool.** After human review, append validated rows manually (or with a separate merge step).

## Costs and review

- Research calls use the model and **web search**; they can incur non-trivial cost.
- Outputs require **human review** before importing into the chart app.
- File validation checks schema, IDs, rubrics, URLs, windows, and deterministic duplicate signals. It does **not** verify that citations are true or that research claims are correct. Deterministic similarity checks do not guarantee semantic deduplication.

## Tests

```bash
pytest updater/tests/ -q
```

Tests mock the provider and do not spend API credits.
