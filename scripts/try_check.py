"""scripts/try_check.py — local harness that runs judge_ad against a real image (for the user to verify by hand)

Requires:
  - venv + deps:  python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
  - env:          set GEMINI_API_KEY in .env (copy from .env.example — loaded automatically)
                  or export GEMINI_API_KEY=<key from aistudio.google.com>
                  GEMINI_MODEL can be left unset (default gemini-3.1-pro-preview)

Run:
  python scripts/try_check.py path/to/ad.jpg "ad copy/caption (if any)"

Prints the CheckResult (JSON) + post_check flags + logs cached_content_token_count (to see cache hits)
"""

import json
import logging
import mimetypes
import sys

from app.pipeline import run_check

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python scripts/try_check.py <image_path> [ad_text]", file=sys.stderr)
        raise SystemExit(2)

    image_path = sys.argv[1]
    text = sys.argv[2] if len(sys.argv) > 2 else None
    mime = mimetypes.guess_type(image_path)[0] or "image/jpeg"

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    result, flags = run_check(image_bytes, mime=mime, text=text)

    print("\n===== CheckResult =====")
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
    print("\n===== post_check flags =====")
    print("\n".join(flags) if flags else "(ไม่มี flag)")


if __name__ == "__main__":
    main()
