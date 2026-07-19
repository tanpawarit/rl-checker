"""app/config.py — single home for LLM config, read from env (auto-loads .env at root)

Other files must not call os.getenv directly — everything goes through LLMConfig.from_env().
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # real env always wins — load_dotenv does not override already-set variables

DEFAULT_MODEL = "gemini-3.1-pro-preview"  # largest model actually callable as of Jul 2026 (ADR-0005)


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    model: str = DEFAULT_MODEL
    # None = do not send thinking_config, let the model use its default (3.1 Pro = high, ADR-0005)
    # Allowed values: minimal | low | medium | high
    thinking_level: str | None = None

    @classmethod
    def from_env(cls) -> "LLMConfig":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:  # fail-fast with a clear name instead of an obscure SDK error on first request
            raise RuntimeError("GEMINI_API_KEY is not set (ตั้งใน .env หรือ export)")
        return cls(
            api_key=api_key,
            model=os.getenv("GEMINI_MODEL", DEFAULT_MODEL),
            thinking_level=os.getenv("GEMINI_THINKING_LEVEL") or None,  # "" = not set
        )
