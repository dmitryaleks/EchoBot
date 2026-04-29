"""Runtime configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    default_voice: str
    default_rate: str
    output_dir: Path
    max_input_bytes: int


def load_config() -> Config:
    return Config(
        default_voice=os.environ.get("TTS_DEFAULT_VOICE", "en-US-AriaNeural"),
        default_rate=os.environ.get("TTS_DEFAULT_RATE", "+0%"),
        output_dir=Path(os.environ.get("TTS_OUTPUT_DIR", "output")).expanduser().resolve(),
        max_input_bytes=int(os.environ.get("TTS_MAX_INPUT_BYTES", 1_000_000)),
    )
