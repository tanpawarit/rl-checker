# The report lives in the adaptive card only — no /report + persistence

> **Partially superseded by [ADR-0006](0006-web-ui-replaces-teams.md)** — the adaptive card was removed along with Teams.
> But the core of this decision still holds: the report is complete in a single response · stateless · no /report + persistence

The spec (§8-9) returns a summary adaptive card + a button linking to a `/report/{id}` page (full HTML) that requires persistence to store the result keyed by id. We chose to **pack the full report into a single adaptive card** for v1 and **drop** report.py (HTML), the `/report/{id}` endpoint, and the entire persistence layer.

Rationale: (1) it removes a whole subsystem — v1 is stateless on every check; (2) it resolves a spec contradiction — Cloud Run is locked private (`--no-allow-unauthenticated`), but a browser clicking the report link from Teams has no token and couldn't reach `/report/{id}` anyway.

**Trade-off / consequences:** an adaptive card has a ~28KB limit — if there are so many findings that the card grows too long, we may need to add an HTML fallback later · there is no check history (no audit trail) in v1, which matches §13 (audit/versioning out of scope).
