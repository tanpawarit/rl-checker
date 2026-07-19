# postcheck required_text is two-tier + product is inferred entirely

The `/check` input is only **an image + ad copy (caption)** — there is no field carrying the product, since the front-end is a thin shell per §1.7/§11. So the product is **always inferred from the ad content** (the LLM fills in `saw.products_mentioned`); there is no hint from the user.

As a result, postcheck #4 (required_text match) splits into two tiers:
1. **baseline** — the warning read from `required_text.yaml` → the `baseline` field (a single source of truth, not hardcoded) must appear in `saw.text_verbatim` on **every** ad, otherwise flag it (this closes the loophole of a brand ad that mentions no product and thereby dodges the warning).
2. **per-product** — if `saw.products_mentioned` points to a product, that product's canonical rate-range (from required_text.yaml) must appear too.

**Anti-hallucination:** the `product → required_text` mapping is done in deterministic code (matched via `applies_to` tags), not by the LLM's judgment · if the product can't be inferred clearly (e.g. "จำนำเล่ม" without saying person/juristic) → the LLM adds a manual_check for a human to pick the correct required_text.
