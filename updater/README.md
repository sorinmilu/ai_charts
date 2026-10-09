# Research CSV updater

Runs a Markdown research prompt against the talking-points CSV it names. Uses the OpenAI Responses API with web search, validates new rows, and **appends them to the live CSV** when there is something valid to add. Otherwise it leaves the CSV alone and logs why.

## Setup

From the project root:

```bash
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
| `OPENAI_REASONING_EFFORT` | Responses API `reasoning.effort` (e.g. `medium`); empty = model default |
| `RESEARCH_MAX_NEW_ROWS` | Ceiling on new rows (default `40`) |
| `RESEARCH_TIMEOUT_SECONDS` | Optional HTTP timeout |
| `RESEARCH_MAX_OUTPUT_TOKENS` | Optional generation budget |

Process environment variables override values from `.env`.

## Layout

| Path | Role |
|------|------|
| `updater/prompts/*.md` | Research prompts (each names its `web-app/data/*.csv`) |
| `web-app/data/*_talking_points.csv` | Live datasets (updated in place when new rows pass) |
| `updater/research/` | Prep, provider, validation |
| `updater/output/runs.log` | One-line log per run |
| `updater/update_data_csv.py` | CLI |

## Commands

```bash
# Research + append validated rows to the live CSV (costs money)
python updater/update_data_csv.py updater/prompts/practical_utility_prompt.md

python updater/update_data_csv.py updater/prompts/future_trajectory_prompt.md
python updater/update_data_csv.py updater/prompts/current_capability_prompt.md --dry-run

python updater/update_data_csv.py updater/prompts/intellectual_jobs_Prompt.md \
  --model gpt-4o \
  --max-new-rows 20
```

`--dry-run` only checks that the prompt and dataset wire up; no API call, no CSV change.

## What a real run does

1. Load the prompt and its CSV.
2. Call OpenAI with web search.
3. Validate new rows (schema, IDs, duplicates, windows, etc.).
4. If there are valid new rows → append them to that CSV.
5. If not → leave the CSV unchanged.
6. Append one summary line to `updater/output/runs.log`.

Existing rows are never removed or rewritten except as part of rewriting the file with old rows + new appends. Validation is mechanical; it does not prove that citations are true.

## Tests

```bash
pytest updater/tests/ -q
```
