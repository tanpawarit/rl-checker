# Ad Compliance Checker (เงินให้ใจ)

Checks loan ads against our compliance rules and gives you a per-rule report (pass / fail / review) with evidence. It doesn't approve or block anything — a person still makes the call.

**How it works:** you attach an ad image (+ caption), Gemini reads it in one pass, and the report renders on the same page.

- **Brain** — Gemini on Cloud Run (FastAPI). The contract is just `POST /check`.
- **Front-end** — a small web UI in `app/web/` (Jinja2 + HTMX).
- **Rules** — hand-extracted from the source Excel into `catalog/` (35 rules).

Deeper docs: [spec.md](spec.md) for the full design, [CONTEXT.md](CONTEXT.md) for domain terms, [docs/adr/](docs/adr/) for decisions that diverge from the spec.

## Project layout

```
catalog/   the rules — 35 of them, plus the dictionary and required text per product
app/       the brain — schemas, checker, pipeline, config, main
app/web/   the web UI — routes, templates, static (talks to the brain via the pipeline only)
scripts/   try_check.py — run a real Gemini check by hand
tests/     unit tests for the deterministic layer (no Gemini calls)
docs/adr/  decision records · docs/design/ the approved UI mockup
```

## Get set up

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

> In VS Code, point the interpreter at `.venv/bin/python`, or Pyright will complain about imports.

## Run it

**Tests** (no Gemini, no key needed):

```bash
python -m pytest tests -q
```

**Web UI** (needs a Gemini key):

```bash
cp .env.example .env   # add your GEMINI_API_KEY (from aistudio.google.com)
uvicorn app.main:app --reload
```

Then open http://localhost:8000, attach an ad, and hit ตรวจโฆษณา.

**One-off check from the terminal:**

```bash
python scripts/try_check.py path/to/ad.jpg "ad copy (if any)"
```

## Deploy (Cloud Run)

First store the key as a secret (don't pass it in `--set-env-vars` — it can leak into logs):

```bash
echo -n "<key>" | gcloud secrets create gemini-api-key --data-file=-
```

Then deploy:

```bash
gcloud run deploy ad-compliance \
  --source . \
  --region us-central1 \
  --timeout 120 \
  --set-env-vars GEMINI_MODEL=gemini-3.1-pro-preview \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest
```

> Auth mode (public / IAM / IAP) isn't decided yet — sort that out before exposing the UI beyond the team.

## Before production

- Double-check the rate numbers in `catalog/required_text.yaml` against the latest Excel.
- Run `scripts/try_check.py` (or the UI) against real ad images to confirm it works end to end.

## Key decisions

These diverge from the original spec — see the ADRs for the why.

| # | What changed | ADR |
|---|---|---|
| 1 | Implicit caching (dropped the explicit cache lifecycle) | [0001](docs/adr/0001-implicit-context-caching.md) |
| 2 | One report card — dropped `/report`, persistence, and report.py | [0002](docs/adr/0002-card-only-report-no-persistence.md) |
| 3 | Two-tier required text (always the warning + a per-product rate); product inferred | [0003](docs/adr/0003-postcheck-required-text-two-tier.md) |
| 5 | Model = Gemini 3.1 Pro, global endpoint, family-3 defaults | [0005](docs/adr/0005-gemini-3-1-pro-default-config.md) |
| 6 | Web UI instead of Teams (brain contract unchanged) | [0006](docs/adr/0006-web-ui-replaces-teams.md) |
