# Ad Compliance Checker

Domain: an AI system that checks loan ads (เงินให้ใจ) against the full set of compliance rules, then produces a **report for a human to decide on** — the system does not decide by itself.

The terms here are the project's *ubiquitous language*. Use them consistently across code, spec, and discussion.

## Language

**Ad** (โฆษณา):
A loan-ad artifact submitted for checking = one image (+ text if any) per check.
_Avoid_: creative, banner, content, ชิ้นงาน

**Catalog**:
The whole set of rules used for checking, taken verbatim from Excel (the source of truth). Has 3 parts: judgment rules · dictionary · required text.
_Avoid_: knowledge base, ruleset, ฐานกฎ

**Judgment rule** (Rule for short):
A requirement the LLM must judge in context. Has a permanent id in the form `RL-<category>.<number>`.
_Avoid_: policy, check item, เงื่อนไข

**Dictionary** (Phrase rule):
A dictionary of DO / REVIEW / DON'T phrases compared against the text in an ad.
_Avoid_: wordlist, คำต้องห้าม (use "dictionary")

**Required text** (ข้อความบังคับ):
The canonical wording that must appear **exactly** (the risk warning + the effective-annual-interest-rate range), stored keyed by product.
_Avoid_: disclaimer, คำเตือน (use "required text" for the mandatory text itself)

**Product** (ผลิตภัณฑ์):
A loan product an ad may mention. Taxonomy = จำนำเล่ม/โอนเล่ม × บุคคลธรรมดา/นิติบุคคล × ส่วนตัว/พาณิชย์ — **always inferred from the ad content**, never given as user input.
_Avoid_: SKU, loan type, สินค้า

**Risk warning** (คำเตือนความเสี่ยง):
The text "กู้เท่าที่จำเป็นและชำระคืนไหว" that must appear on **every** ad regardless of product — a baseline obligation that postcheck verifies separately from the per-product rate range (it is a kind of required text, but always mandatory).
_Avoid_: disclaimer

**Saw**:
A record of what the AI actually "read/saw" in the ad (verbatim text, products found, warnings found, rates shown, visual notes), used as **evidence**.
_Avoid_: observation, extraction, สิ่งที่เห็น

**Finding**:
The check result for one rule, consisting of status + severity + evidence + issue + fix note.
_Avoid_: violation, result, ผลตรวจ

**Status**:
A value on a finding, one of `pass` | `fail` | `review` — where `review` = the AI cannot decide cleanly / it's borderline.
_Avoid_: verdict, outcome, ผล

**Severity**:
A `critical`|`high`|`medium`|`low` label on a finding — **just a label, no routing/decision logic**.
_Avoid_: priority, risk level, ความสำคัญ

**Manual check**:
Something the AI can't decide from the media (e.g. the real font size in mm), handed to a human — **distinct from `review`**.
_Avoid_: TODO, human task

**Post-check**:
A deterministic code layer that catches hallucinations after the LLM call. **Never edits the result, only flags it.**
_Avoid_: validation, verification, ตรวจสอบ

**Flag**:
A warning flag that post-check emits (does not make the system auto-decide).
_Avoid_: error, alert, ข้อผิดพลาด

**Report-only**:
The core constraint: the system produces a *report* for a human to decide on, never auto-approve/block/route.
_Avoid_: auto-decision

**Check result**:
The single contract between the brain and the front-end = `saw` + `findings` + `manual_checks`.
_Avoid_: response, payload
