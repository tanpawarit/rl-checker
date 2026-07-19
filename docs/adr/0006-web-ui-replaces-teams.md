# Remove the Teams front-end — switch to a web UI in the same project

Remove Microsoft Teams (Bot Framework) entirely: `app/bot.py` · `app/teams_card.py` · `teams/` ·
the `/api/messages` endpoint · deps `botbuilder-core` + `aiohttp`.
The new front-end = **a web page served from the existing FastAPI service** (hand-written HTML/CSS — designed first
in `docs/design/ui-mockup.html`, then implemented in `app/web/`: Jinja2 + HTMX, talking to the brain only via `run_check()`).

Rationale: (1) the bot path was never verified against a real Azure Bot (the deferred spike in ADR-0004) and dragged in
infra beyond the job — Azure Bot registration, JWT, Cloud Run "CPU always allocated" for proactive messages;
(2) a web UI gives full control over the report's appearance — ADR-0002 already noted the ~28KB adaptive-card limit;
(3) deploy is still the same single service, with no dependency outside GCP.

**What does not change:** the §1.7 seam is fully intact — `run_check()` (pipeline) + `POST /check` returns
a neutral `{result: CheckResult, flags}`; the brain is not touched by a single line · still stateless,
no persistence (the core of ADR-0002 still applies).

**Supersedes:** [ADR-0004](0004-teams-bot-framework-on-cloud-run.md) in full ·
[ADR-0002](0002-card-only-report-no-persistence.md) only the adaptive-card part
(the "report complete in a single response, no /report + persistence" principle still holds).
