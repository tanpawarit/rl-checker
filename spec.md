# Ad Compliance Checker — Build Specification

> A handoff document for Claude Code to build the system from.
> An AI system that checks loan ads (เงินให้ใจ) for the compliance / marketing team.
> Brain = Gemini on Cloud Run · Front-end = Microsoft Teams · Source of truth = Excel

> **Update 2026-07-18:** the Teams front-end has been removed — the current front-end is a web UI in the same project
> ([ADR-0006](docs/adr/0006-web-ui-replaces-teams.md)) · this spec is kept as the original handoff document.
> For decisions that diverge from the spec, see [docs/adr/](docs/adr/)

---

## 0. System summary (read first)

The system takes an ad (image/text) from a user in Teams, checks it against the full set of compliance rules, and returns a **per-rule report (pass/fail/review) with evidence** for a human to decide on. The system **does not approve/block by itself**.

The core of the runtime is a **single LLM call** (multimodal) with the whole rule catalog in context (full-context, not RAG), where the catalog is held in an **explicit context cache** to cut cost, followed by a **code-based post-check** layer to guard against hallucinations, then assembled into a report.

---

## 1. Settled principles — do not change without asking

These principles are the result of a deliberate, weighed design. Claude Code must follow them and should not propose alternatives that contradict them:

1. **Full-context, not RAG** — every rule must be in context on every check. No retrieval/embedding/vector DB. Reason: compliance needs completeness (a retrieval miss = a false negative = letting a non-compliant ad through); the catalog is small enough to fit entirely.
2. **A single LLM call** — read the image and judge in one call (the pixels stay with the judge). Not split into multiple calls, no agent framework, no ADK. Reason: there are many visual rules, so the judge must see the real image; the system has no loop/tool/multi-agent/session that a framework would help with.
3. **Explicit context caching** — the catalog is cached on the Vertex side, paid for in full once, reused on every ad.
4. **Report-only** — the output is a report for a human to read. `severity` is just a label with no routing/auto-decision logic; a human decides every time.
5. **Guard hallucinations with code + humans, not a second LLM** — the post-check is an assertion; human review is the semantic gate.
6. **catalog = a derived artifact, verbatim** — the rule data comes from Excel (the source of truth), taking the text **in full, not summarized, not paraphrased** (the user extracts it by hand and commits it themselves — this system does not build an extractor).
7. **The front-end is swappable** — the brain is not tied to the front-end; the contract between them is a single HTTP endpoint + a single JSON `CheckResult` (Teams today; can switch to Bot Framework/web later without touching the brain).
8. **Gemini lives only in `app/checker.py`** — `google-genai` is imported in one file; other files know only `CheckResult`, not the model.

---

## 2. Repo structure

```
ad-compliance/
├── README.md
├── .gitignore
├── requirements.txt
├── Dockerfile
│
├── catalog/                         # data side — hand-extracted from Excel (verbatim) then committed
│   ├── rules/                       # judgment rules, 1 category = 1 file (from sheet "A. Ads Checklist")
│   │   ├── 01_design.yaml
│   │   ├── 02_product_info.yaml
│   │   ├── 03_channels.yaml
│   │   └── 04_people.yaml
│   ├── dictionary.yaml              # phrase rules (from sheet "B. Advertising Dictionary")
│   └── required_text.yaml           # required text (from "1.ข้อกำหนดคำเตือน" + Checklist 2.1 column D)
│
├── app/                             # the whole runtime (FastAPI on Cloud Run)
│   ├── __init__.py
│   ├── main.py                      # endpoints: /check · /report/{id} · /healthz
│   ├── compile_catalog.py           # collapse catalog/ → a single context payload (byte-for-byte stable)
│   ├── checker.py                   # ★ Gemini + explicit cache + 1 call (saw/findings)
│   ├── schemas.py                   # Pydantic: CheckResult / Finding / Saw — the shared contract
│   ├── postcheck.py                 # the anti-hallucination gate, in code
│   ├── report.py                    # findings → a full report page (HTML)
│   └── teams_card.py                # findings → adaptive card JSON
│
└── teams/                           # front-end — config, not runtime code
    ├── SETUP.md                     # how to set up the Copilot Studio agent (thin shell) + agent flow
    └── card_template.json           # the adaptive-card skeleton (paired with teams_card.py)
```

**Scope note:** there is no `eval/` folder, no `extractor/` (xlsx→catalog is done by hand), no `deploy.sh` (use `gcloud run deploy` directly) — don't add these.

---

## 3. Data layer — `catalog/`

The catalog has 3 parts with different jobs. The user hand-extracts them from Excel. Claude Code must **create the schema/skeleton example files + code that can read them**, but need not fill in the real rule content (the user does that). Include 1-2 example rules per file as a template.

### 3.1 `catalog/rules/NN_<category>.yaml` — judgment rules

Rules the LLM must judge in context, from the Checklist columns: A=id, C=check (requirement), D=required/pass/fail (info that must be present)

```yaml
category: product_info            # category name (matches the 4 categories in the Checklist)
rules:
  - id: RL-2.1
    severity: critical            # critical | high | medium | low  (just a label, no routing)
    check: >                      # ★ verbatim from column C — take it in full, don't summarize
      ต้องแสดงคำเตือน "กู้เท่าที่จำเป็นและชำระคืนไหว" ในสื่อโฆษณาทุกประเภท
      ใส่คำเตือนครบทุกจุด ทุกรูป คลิป โพสต์ และถ้ามี Caption ต้องใส่ใน Caption
      ต้องเห็นคำเตือนชัดเจน ตัวอักษรไม่เล็กเกินไป สีตัดกับพื้นหลัง
      แสดงอัตราดอกเบี้ยที่แท้จริงต่อปีเป็นช่วง ตามผลิตภัณฑ์ที่กล่าวถึง
    required_text_ref: [warn.crl_personal, warn.c2c]   # optional: points to required_text.yaml
    pass:                         # from column D, for a passing example
      - มีคำเตือน + ช่วงเรตตรงผลิตภัณฑ์ แสดงชัด อ่านออก
    fail:                         # from column D, for an example/text to avoid
      - ระบุเรตแต่ไม่มีคำเตือน
      - แสดงเรตเป็น "เริ่มต้น X%" แทนช่วงต่ำสุด-สูงสุด
    source:                       # keep provenance (not forced into context)
      document: "A. Ads Checklist"
      citation: "หมวด 2.1"
```

Rules: `id` in the permanent form `RL-<category>.<number>`, never reused · 1 category = 1 file · order files with a `01_ 02_ ...` prefix.

### 3.2 `catalog/dictionary.yaml` — phrase rules

A lexicon of DO/REVIEW/DON'T phrases from the Advertising Dictionary

```yaml
dont:                             # absolutely forbidden — post-check can string-match directly
  - { phrase: "อนุมัติ 100%", reason: "รับประกันผลการอนุมัติ" }
  - { phrase: "กู้ได้ทุกคน",  reason: "รับประกันผล" }
  - { phrase: "ไม่เช็คบูโร",  reason: "สื่อว่าไม่ตรวจเครดิต" }

review:                           # allowed only with a supporting condition — flag for a human/LLM to review
  - { phrase: "วงเงินสูง", condition: "ต้องมี * เงื่อนไขกำกับ" }
  - { phrase: "เงินด่วน",  condition: "ห้ามสื่อว่าอนุมัติไว/ง่ายเกินจริง" }

do:                               # allowed
  - "เครดิตไม่ดี ซ่อมได้"
  - "การอนุมัติเป็นไปตามหลักเกณฑ์บริษัท"
```

### 3.3 `catalog/required_text.yaml` — required text keyed by product

The canonical text that must appear exactly (warning + rate range) from sheet "1.ข้อกำหนดคำเตือน" and Checklist 2.1 column D — **verbatim**

```yaml
warn:
  crl_personal:                   # จำนำเล่ม บุคคลธรรมดา
    text: "กู้เท่าที่จำเป็นและชำระคืนไหว อัตราดอกเบี้ยที่แท้จริงต่อปี สินเชื่อจำนำเล่มทะเบียนรถ 12.82% - 24.00%"
    applies_to: [CRL, จำนำเล่ม, บุคคลธรรมดา]
  crl_juristic:                   # จำนำเล่ม นิติบุคคล
    text: "กู้เท่าที่จำเป็นและชำระคืนไหว อัตราดอกเบี้ยที่แท้จริงต่อปี สินเชื่อจำนำเล่มทะเบียนรถ นิติบุคคล 9.50% - 15.00%"
    applies_to: [CRL, จำนำเล่ม, นิติบุคคล]
  c2c:                            # โอนเล่ม (ส่วนตัว + พาณิชย์)
    text: >
      กู้เท่าที่จำเป็นและชำระคืนไหว อัตราดอกเบี้ยที่แท้จริงต่อปี สินเชื่อโอนเล่มทะเบียนรถ
      ส่วนตัว 6.08% - 15.00% และพาณิชย์ 6.08% - 26.62%
    applies_to: [C2C, โอนเล่ม]
```

> The rate numbers above are examples from the file; have the user re-confirm them against Excel before real use.

---

## 4. `app/schemas.py` — the shared contract

Every file references this schema (checker enforces it as response_schema · postcheck validates against it · report/teams_card render it)

```python
from pydantic import BaseModel, Field


class WarningFound(BaseModel):
    text: str
    location: str                       # e.g. "ท้ายภาพ", "caption"
    prominence: str                     # "ชัด" | "เล็ก-จาง" | "ไม่พบ"


class RateShown(BaseModel):
    product: str
    rate: str


class Saw(BaseModel):
    """What the AI read from the ad — the evidence, and what localizes a fail during eval"""
    text_verbatim: str                  # all readable text, including fine print/caption
    products_mentioned: list[str]
    warnings_found: list[WarningFound]
    rates_shown: list[RateShown]
    visual_notes: str


class Finding(BaseModel):
    rule_id: str
    title: str
    status: str                         # "fail" | "review" | "pass"
    severity: str                       # "critical" | "high" | "medium" | "low"
    evidence: str                       # quote text from the ad / cite what is seen in the image
    issue: str
    fix_note: str


class CheckResult(BaseModel):
    saw: Saw
    findings: list[Finding]
    manual_checks: list[str]            # things the AI cannot decide (e.g. font size) → for a human to check
```

---

## 5. `app/compile_catalog.py` — collapse the catalog → a context payload

Walks all three parts of `catalog/` and returns **one string** to be cached.
**Important:** the output must be byte-for-byte stable when the catalog is unchanged (always ordered with `sorted()`, no timestamps or any variable content), because that is the condition for caching to work.

```python
import yaml
import pathlib


def compile_catalog(catalog_dir: str = "catalog") -> str:
    base = pathlib.Path(catalog_dir)
    parts: list[str] = ["<compliance_rules>"]

    # 1) judgment rules — ordered by file name (01_, 02_, ...)
    for f in sorted((base / "rules").glob("*.yaml")):
        data = yaml.safe_load(f.read_text(encoding="utf-8"))
        parts.append(f'\n## หมวด: {data["category"]}')
        for r in data["rules"]:
            parts.append(f'<rule id="{r["id"]}" severity="{r["severity"]}">')
            parts.append(f'check: {" ".join(r["check"].split())}')
            for kind in ("pass", "fail"):
                for ex in r.get(kind, []):
                    parts.append(f'  {kind.upper()}: {ex}')
            if r.get("source", {}).get("citation"):
                parts.append(f'  (อ้างอิง: {r["source"]["citation"]})')
            parts.append("</rule>")
    parts.append("</compliance_rules>")

    # 2) dictionary — DON'T / REVIEW / DO
    d = yaml.safe_load((base / "dictionary.yaml").read_text(encoding="utf-8"))
    parts.append("\n<dictionary>")
    parts.append("ห้ามใช้เด็ดขาด (DON'T):")
    for x in d.get("dont", []):
        parts.append(f'  - "{x["phrase"]}" ({x["reason"]})')
    parts.append("ใช้ได้เฉพาะมีเงื่อนไขรองรับ (REVIEW):")
    for x in d.get("review", []):
        parts.append(f'  - "{x["phrase"]}" — {x["condition"]}')
    parts.append("ใช้ได้ (DO): " + " / ".join(d.get("do", [])))
    parts.append("</dictionary>")

    # 3) required_text — required text, verbatim
    rt = yaml.safe_load((base / "required_text.yaml").read_text(encoding="utf-8"))
    parts.append("\n<required_text>")
    for key, v in rt["warn"].items():
        parts.append(f'[{key}] ต้องมีข้อความ (verbatim): "{" ".join(v["text"].split())}"')
        if v.get("applies_to"):
            parts.append(f'  ใช้กับ: {", ".join(v["applies_to"])}')
    parts.append("</required_text>")

    return "\n".join(parts)
```

---

## 6. `app/checker.py` — Gemini + Explicit Cache ★

The heart of the system. Gemini lives here and only here. It has 3 parts: instruction (prompt), get_or_create cache (explicit), check_ad (1 call)

```python
import hashlib
from google import genai
from google.genai import types
from app.schemas import CheckResult
from app.compile_catalog import compile_catalog

MODEL = "gemini-2.5-pro"          # multimodal + supports explicit caching
CACHE_TTL = "86400s"             # 24 h

client = genai.Client(vertexai=True, project="YOUR_PROJECT", location="us-central1")


# ---- INSTRUCTION (stable, no variables/timestamps — goes into the cache) --------------------
INSTRUCTION = """บทบาท: ตรวจโฆษณาสินเชื่อของบริษัทตามกฎที่ให้ด้านล่าง ออกผลเป็น finding ต่อกฎ
ไม่ต้องตัดสินว่าผ่าน/ไม่ผ่านโดยรวม — รายงานให้คนอ่านตัดสินเอง

ทำ 2 ขั้นตามลำดับ:

ขั้น 1 — อ่าน ad ให้ครบก่อนตัดสินอะไร ใส่ผลลง "saw":
  - ถอดข้อความทั้งหมดที่อ่านได้ รวม fine print และ caption (verbatim)
  - ระบุผลิตภัณฑ์ที่ ad พูดถึงทั้งหมด (จำนำเล่ม/โอนเล่ม × บุคคล/นิติ × ส่วนตัว/พาณิชย์)
  - หาคำเตือน "กู้เท่าที่จำเป็นและชำระคืนไหว" — เจอไหม อยู่ตรงไหน เด่นพอไหม
  - เรตที่ ad โชว์ (คู่กับผลิตภัณฑ์ไหน)
  - ข้อสังเกตภาพ (เงินปลิว, ภาพสื่อว่ากู้ง่าย, ภาพไม่สอดคล้องข้อความ ฯลฯ)

ขั้น 2 — เทียบ saw + สิ่งที่เห็นในรูป กับกฎทุกข้อ ใส่ผลลง "findings" ทีละ rule:
  - required_text: ad พูดถึงผลิตภัณฑ์ใดบ้าง (จาก saw) → คำเตือน+ช่วงเรตครบและตรงทุกผลิตภัณฑ์นั้นไหม
  - dictionary DON'T: เจอวลีต้องห้าม = fail
  - dictionary REVIEW: เจอ = review เว้นแต่มีเงื่อนไข/หมายเหตุรองรับชัด
  - ตัดสินไม่ได้/ก้ำกึ่ง = review (ห้ามเดาเป็น pass หรือ fail)
  - สิ่งที่วัดจากรูปไม่ได้ (เช่น ขนาด font ใหญ่พอไหม) = ใส่ "manual_checks" ไม่ใช่ fail

ทุก finding ต้องมี evidence — ยกข้อความจาก ad หรืออ้างสิ่งที่เห็นในรูป ห้ามบอกลอยๆ
คืนผลเป็น JSON ตาม schema เป๊ะ"""


# ---- Explicit cache: find-or-create (handles TTL expiry + catalog changes) ----------
def get_or_create_cache() -> str:
    payload = compile_catalog()
    # the fingerprint binds instruction + catalog + model → change any one and you get a new cache
    fp = hashlib.sha256((MODEL + INSTRUCTION + payload).encode()).hexdigest()[:12]
    name = f"ads-catalog-{fp}"

    for c in client.caches.list():
        if c.display_name == name:
            return c.name                      # found this version, reuse it

    cache = client.caches.create(              # not found (expired/new catalog/new model) → create
        model=MODEL,
        config=types.CreateCachedContentConfig(
            display_name=name,
            system_instruction=INSTRUCTION,
            contents=[payload],
            ttl=CACHE_TTL,
        ),
    )
    return cache.name


# ---- Check one ad -------------------------------------------------------------
def check_ad(image_bytes: bytes, mime: str = "image/jpeg",
             text: str | None = None) -> CheckResult:
    cache_name = get_or_create_cache()

    contents: list = [types.Part.from_bytes(data=image_bytes, mime_type=mime)]
    if text:
        contents.append(text)

    def _call() -> str:
        resp = client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                cached_content=cache_name,
                response_mime_type="application/json",
                response_schema=CheckResult,
                temperature=0.1,               # low, for consistency
            ),
        )
        return resp.text

    try:
        raw = _call()
    except Exception:
        # cache expired mid-flight → recreate and retry once
        cache_name = get_or_create_cache()
        raw = _call()

    return CheckResult.model_validate_json(raw)
```

**Important notes**
- `contents` per request has only the **ad image** (+ text if any) — the catalog is **not sent** because it's already in the cache
- Verify a cache hit via `resp.usage_metadata.cached_content_token_count` (should equal the catalog size)
- `MODEL` is in the fingerprint → upgrading the model version gets a new cache automatically
- If you need CMEK (governance), add `kms_key_name` to `CreateCachedContentConfig`

---

## 7. `app/postcheck.py` — the anti-hallucination gate, in code

Takes a `CheckResult` + catalog, runs 4 deterministic checks, and returns a list of flags (never edits the result, only flags it)

```python
def post_check(result: CheckResult, catalog_dir: str = "catalog") -> list[str]:
    flags: list[str] = []
    valid_ids = load_rule_ids(catalog_dir)          # read all ids from rules/*.yaml
    required = load_required_texts(catalog_dir)     # read all text from required_text.yaml
    saw_text = result.saw.text_verbatim

    for fnd in result.findings:
        # 1) rule_id must actually exist in the catalog
        if fnd.rule_id not in valid_ids:
            flags.append(f"หลอน: rule_id ไม่มีใน catalog — {fnd.rule_id}")
        # 2) evidence quotes must be in saw (catch fake quotes) — compare with whitespace normalized
        # 3) saw ↔ findings consistency (e.g. warnings_found empty but the warning rule = pass → flag)

    # 4) required_text match: the canonical string should be in saw_text if the ad references that product
    #    → close false-passes on the warning/rate deterministically, without relying on the LLM's judgment
    return flags
```

Details of each check:
1. **rule_id ∈ catalog** — every `finding.rule_id` must be in the set of real ids
2. **evidence ⊆ saw** — text in `evidence` quoted from the ad should be a substring of `saw.text_verbatim` (normalize whitespace before comparing)
3. **saw ↔ findings** — if `saw.warnings_found` is empty (no warning found) yet the warning rule (e.g. RL-2.1) is `pass` = contradiction, flag it
4. **required_text match** — for products named in `saw.products_mentioned`, check whether the canonical `text` from required_text.yaml appears in `saw.text_verbatim` (fuzzy/normalize). If not present = confirm a fail in code (this is the most important point — it guards the "the warning is already there" hallucination)

The resulting flags are shown in the report (they do not make the system auto-decide)

---

## 8. `app/report.py` and `app/teams_card.py` — rendering

Both take a `CheckResult` (+ flags from postcheck) and group findings into **4 buckets**:
- ❌ **ต้องแก้** (must fix) — `status == "fail"` (ordered by severity)
- ⚠️ **ควรตรวจ** (should review) — `status == "review"`
- 👤 **ให้คนตรวจเพิ่ม** (needs a human check) — `manual_checks`
- ✅ **ผ่าน** (pass) — `status == "pass"` (collapsed to a list of ids)

The header shows `saw` (what the AI read: products / warning found? / rates shown / text) as evidence. Each finding shows `[rule_id] title · severity` + evidence + fix_note

- `report.py` → full HTML (using the เงินให้ใจ brand style), served at `/report/{id}`
- `teams_card.py` → adaptive card JSON (summarizing the 4 buckets + a "view full report" link button pointing to `/report/{id}`), following the skeleton in `teams/card_template.json`

---

## 9. `app/main.py` — endpoints (FastAPI)

```python
from fastapi import FastAPI, UploadFile, Request
from app.checker import check_ad, get_or_create_cache
from app.postcheck import post_check
from app import report, teams_card

app = FastAPI()

@app.on_event("startup")
def _warm():
    get_or_create_cache()                 # create the cache ahead of time at startup

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/check")                       # called from Teams (Copilot Studio flow / bot)
async def check(file: UploadFile):
    data = await file.read()
    result = check_ad(data, mime=file.content_type or "image/jpeg")
    flags = post_check(result)
    # store result+flags keyed by an id (in memory/BigQuery) so /report/{id} can fetch it
    return teams_card.build(result, flags)   # return the adaptive card to Teams

@app.get("/report/{rid}")                 # the full report page (linked from the card)
def full_report(rid: str, request: Request):
    result, flags = load_result(rid)
    return report.render_html(result, flags)
```

**Note:** a check takes ~10-40s; the Teams flow must reply "กำลังตรวจ…" first and then use an async response · set the Cloud Run request timeout high enough · the endpoint accepts only requests from the flow/bot (service account + token), not public

---

## 10. Operational flow

**When rules change (rare — done by hand):**
Excel (source of truth) → the user hand-extracts the 3 sheets verbatim → commit `catalog/` → review the diff → deploy

**When the service starts:**
`compile_catalog()` → payload → `get_or_create_cache()` creates an explicit cache on Vertex (paying for the catalog in full once)

**When checking 1 ad:**
```
A user in Teams attaches an ad image (1:1 chat or @mention in a channel)
  → the Copilot Studio agent (thin shell) replies "กำลังตรวจ…" then HTTP POST → Cloud Run /check
  → checker.py: Gemini 1 call = [cached catalog] + image → returns CheckResult {saw, findings, manual_checks}
  → postcheck.py: rule_id∈catalog · evidence⊆saw · saw↔findings · required_text match
  → teams_card.py: a 4-bucket adaptive card back into Teams + a full-report link
  → a human reads the findings and decides (the system does not auto-pass/block)
```

---

## 11. Teams front-end — `teams/SETUP.md` (summary to include)

The Copilot Studio agent is a **thin shell with no brain** — do not put ad-checking knowledge/instructions in it. Its only job is to receive the file → call Cloud Run → show the result. Setup:
1. Create an agent in Copilot Studio, enable file/image upload
2. agent flow: (a) receive the message+attachment → (b) an HTTP action POSTs to Cloud Run `/check` → (c) receive the adaptive card back → (d) show it in chat (use an async response because a check takes >30s)
3. Publish to Teams (1:1 chat + add to channel `#ads-review`, responding on @mention)
4. auth: users are already in the M365 tenant; lock Cloud Run to accept only requests from the flow

> Alternative (no Copilot Studio license cost): write a Teams bot with Bot Framework running on the same Cloud Run — change only the caller of `/check`; the brain needs no changes

---

## 12. Deploy — Dockerfile + requirements

`requirements.txt`
```
fastapi
uvicorn[standard]
google-genai
pyyaml
pydantic
python-multipart
```

`Dockerfile` (single Python)
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app
COPY catalog/ ./catalog
ENV PORT=8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

deploy: `gcloud run deploy ad-compliance --source . --region us-central1 --no-allow-unauthenticated` (set a timeout that allows for the check, bind a service account with Vertex permissions)

---

## 13. Out of scope — do not build

- ❌ an automatic xlsx→catalog extractor (the user does it by hand + review)
- ❌ RAG / vector DB / embeddings
- ❌ a second LLM / agent framework / ADK / multi-agent
- ❌ auto-approve / auto-block / routing by severity
- ❌ an eval folder, deploy.sh
- ❌ full audit/versioning (this scope covers only the data side)

---

## 14. Recommended build order

1. `schemas.py` — the shared contract (do it first, everything references it)
2. `compile_catalog.py` + example files in `catalog/` (1-2 rules per file as a template)
3. `checker.py` — Gemini + explicit cache (test cache hits with `cached_content_token_count`)
4. `postcheck.py` — the 4 assertions
5. `report.py` + `teams_card.py`
6. `main.py` + `Dockerfile` → deploy to Cloud Run
7. `teams/SETUP.md` + set up Copilot Studio (last)

After the build is done, the user extracts the real catalog from Excel (verbatim) and tests end-to-end.
