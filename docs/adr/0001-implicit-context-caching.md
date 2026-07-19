# Use implicit context caching instead of explicit

The spec (§1.3, §6) calls for **explicit** Vertex context caching of the catalog, but we chose **implicit** caching instead: for a low-volume internal tool (a handful of ads/day), explicit's guaranteed cache hit is not worth the hourly idle-storage cost (24h TTL) or the lifecycle code (get_or_create_cache, sha256 fingerprint, TTL, retry on cache expiry, list() on every call). Gemini 2.5 has implicit caching on by default, giving an automatic cache-hit discount whenever the prefix repeats — no extra code. We send instruction+catalog inline on every call.

**Consequences:** `compile_catalog()` still has to produce byte-for-byte stable output (so the implicit-cache prefix matches) · `checker.py` is down to a single call with no cache-lifecycle layer · `main.py` no longer warms the cache at startup · we can go back to explicit later if volume grows (change only checker.py).
