# Front-end = a Bot Framework bot on the same Cloud Run service as the brain

> **Superseded by [ADR-0006](0006-web-ui-replaces-teams.md)** — Teams was removed entirely (the bot was never verified against real Azure).
> The current front-end = a web UI in the same project · this record is kept for history.

Spec §11 sets the default to a Copilot Studio agent (thin shell). We chose the **alternative in §11** instead: a Teams bot using **Bot Framework** running on the same Cloud Run service as the brain — no Copilot Studio license cost + full control over async.

## Architecture

- **Endpoints (a single FastAPI host):**
  - `/api/messages` — Bot Framework (called by Azure Bot Service)
  - `/check` — HTTP contract per §1.7: returns a neutral `{result: CheckResult, flags}`, not tied to any front-end (the card is purely the Teams adapter's concern) · the bot does **not** call this over HTTP but calls `run_check()` (`app/pipeline.py` — the single seam of the brain: check_ad → post_check) in-process
  - `/healthz`
- **Auth (a reversal from spec §9):** Cloud Run must be **public** — Azure Bot Service can't present a GCP service-account token; security comes from the **Bot Framework JWT** (MicrosoftAppId/Password) that the bot verifies itself, not IAM `--no-allow-unauthenticated`
- **Async (background task):** a check takes 10-40s > the Bot Connector timeout of ~15s → `/api/messages` sends typing + "กำลังตรวจ…", stores the **conversation reference**, fires a background task, and returns 200 immediately; the task runs `check_ad → post_check → teams_card` and sends the card back **proactively** to the original conversation → this requires Cloud Run **"CPU always allocated"** (otherwise the task is throttled after the 200 is returned)
- **Attachment:** the bot receives the image as a `contentUrl` + bearer token → downloads it to bytes → `check_ad(image_bytes, mime, text)`
- **Extra deps:** `botbuilder-core`

## Infra the user must set up
Azure Bot registration (yields MicrosoftAppId/Password) + add a Teams channel · env: `MicrosoftAppId`, `MicrosoftAppPassword`

## Trade-off
More code than Copilot Studio + you have to register an Azure Bot · but no license cost, a single deploy, and full control over async/typing · the §1.7 seam still lives at `run_check()` + `/check`
