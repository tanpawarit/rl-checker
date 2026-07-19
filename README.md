# Ad Compliance Checker (เงินให้ใจ)

An AI system that checks loan ads against the full set of compliance rules and returns a **per-rule report (pass/fail/review) with evidence**
for a human to decide on — the system **does not approve/block by itself**.

- Brain: Gemini on Cloud Run (FastAPI) — 1 multimodal call, implicit caching
- Front-end: a web UI in `app/web/` (Jinja2 + HTMX, เงินให้ใจ brand theme — ADR-0006; the neutral contract is `POST /check`)
- Source of truth: Excel → hand-extracted verbatim into `catalog/`

Full design in [spec.md](spec.md) · domain terms in [CONTEXT.md](CONTEXT.md) · decisions that diverge from the spec in [docs/adr/](docs/adr/)

## Structure

```
catalog/   rule data (hand-extracted from Excel, verbatim) — 35 rules · dictionary · required text per product
app/       the brain: schemas · compile_catalog · checker · postcheck · pipeline · config · main
app/web/   the front-end: routes + templates (Jinja2) + static (htmx, logo) — talks to the brain only via pipeline
scripts/   try_check.py — harness that hits the real Gemini (verify by hand)
tests/     unit tests for the deterministic layer (no Gemini calls)
docs/adr/  decision records (6 of them) · docs/design/ the approved ui mockup
```

## Key decisions (diverging from the original spec — from grilling)

| # | Changed to | ADR |
|---|---|---|
| 1 | implicit caching (drop the explicit cache lifecycle) | [0001](docs/adr/0001-implicit-context-caching.md) |
| 2 | a single card, done — drop `/report` + persistence + report.py | [0002](docs/adr/0002-card-only-report-no-persistence.md) |
| 3 | postcheck required_text two-tier (always the warning + a rate per product); product inferred entirely | [0003](docs/adr/0003-postcheck-required-text-two-tier.md) |
| 4 | ~~front-end = a Bot Framework bot on the same Cloud Run~~ (superseded by #6) | [0004](docs/adr/0004-teams-bot-framework-on-cloud-run.md) |
| 5 | model = Gemini 3.1 Pro on the global endpoint · keep the family-3 temperature/thinking/media defaults | [0005](docs/adr/0005-gemini-3-1-pro-default-config.md) |
| 6 | remove Teams — front-end = a web UI in the same project (brain/`/check` contract unchanged) | [0006](docs/adr/0006-web-ui-replaces-teams.md) |

## Setup (dev)

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

> VS Code: set the interpreter to `.venv/bin/python` (otherwise Pyright complains about unresolved imports — that's config, not a bug)

## Run the tests (deterministic — no Gemini calls)

```bash
. .venv/bin/activate && python -m pytest tests -q
```

## Run the web UI (dev)

```bash
cp .env.example .env   # then fill in GEMINI_API_KEY
uvicorn app.main:app --reload
```
Open http://localhost:8000 → attach an ad image (+ caption) → ตรวจโฆษณา → the dossier report renders in the same page

## Verify the brain against the real Gemini (run it yourself)

```bash
cp .env.example .env   # then fill in GEMINI_API_KEY (key from aistudio.google.com)
python scripts/try_check.py path/to/ad.jpg "ad copy (if any)"
```
Prints the CheckResult (JSON) + post_check flags + logs `cached_content_token_count` (to see cache hits)

## Deploy (Cloud Run)

```bash
gcloud run deploy ad-compliance \
  --source . \
  --region us-central1 \
  --timeout 120 \
  --set-env-vars GEMINI_MODEL=gemini-3.1-pro-preview \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest
```

> `--set-secrets` requires creating the secret first: `echo -n "<key>" | gcloud secrets create gemini-api-key --data-file=-` (don't put the key directly in `--set-env-vars` — it can surface in the console/logs)

> The auth mode (public/IAM/IAP) is still undecided — decide it before exposing the web UI beyond the team

## What the user needs to do next
1. Confirm the rate numbers in `catalog/required_text.yaml` against the latest Excel before production use
2. Run `scripts/try_check.py` (or the web UI) to verify end-to-end against real images
