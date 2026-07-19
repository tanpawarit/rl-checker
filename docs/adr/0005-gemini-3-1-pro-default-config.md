# Upgrade the model to Gemini 3.1 Pro and keep the family-3 default config

Change the default `GEMINI_MODEL` from `gemini-2.5-pro` → **`gemini-3.1-pro-preview`** (the largest model actually callable as of Jul 2026 — Gemini 3.5 Pro is still limited preview and not generally accessible), and strip out config that was 2.5-era advice:

- **auth**: use the **Gemini Developer API + `GEMINI_API_KEY`** (not Vertex) → no `GOOGLE_CLOUD_PROJECT` / `GOOGLE_CLOUD_LOCATION` in the system
- **temperature**: drop `temperature=0.1` — the Gemini 3 guidance is to **keep the 1.0 default**; going lower risks loops/degraded reasoning quality. The system's consistency comes from response_schema + evidence + postcheck, not temperature
- **thinking**: default is unset (= `thinking_level=high` for 3.1 Pro, which fits this task), but a `GEMINI_THINKING_LEVEL` knob (`minimal|low|medium|high`) is exposed to cut cost/latency without touching code
- **media_resolution**: unset — the 3.1 Pro default uses high `media_resolution` (1120 tokens/image, good for reading fine print), which already matches what ad-checking needs
- **implicit caching (ADR-0001 still applies)**: 3.1 Pro's minimum prefix = **4,096 tokens** (2.5 Pro = 2,048) — the current catalog template is smaller than that, so you won't see cache hits until the real catalog from Excel is large enough. This is not a bug

**Rollback**: set env `GEMINI_MODEL=gemini-2.5-pro` without touching code.
