"""Async wrapper around edge-tts: synthesize() and list_voices()."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import edge_tts


class TTSError(RuntimeError):
    """Raised when speech synthesis fails."""


@dataclass(frozen=True)
class SynthesisResult:
    output_path: Path
    voice: str
    bytes: int
    duration_ms: int | None = None


@dataclass(frozen=True)
class VoiceInfo:
    short_name: str
    locale: str
    gender: str
    friendly_name: str


async def synthesize(
    text: str,
    output_path: Path,
    voice: str,
    rate: str = "+0%",
) -> SynthesisResult:
    if not text.strip():
        raise TTSError("Cannot synthesize empty text.")

    communicate = edge_tts.Communicate(text, voice, rate=rate)
    try:
        await communicate.save(str(output_path))
    except edge_tts.exceptions.NoAudioReceived as exc:
        raise TTSError(
            f"edge-tts returned no audio for voice {voice!r}. "
            "Verify the voice name (try list_voices) and your internet connection."
        ) from exc

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise TTSError("edge-tts produced no output file or wrote a zero-byte file.")

    return SynthesisResult(
        output_path=output_path,
        voice=voice,
        bytes=output_path.stat().st_size,
        duration_ms=None,
    )


async def list_voices(locale: str | None = None) -> list[VoiceInfo]:
    raw: list[dict[str, Any]] = await edge_tts.list_voices()
    out: list[VoiceInfo] = []
    for v in raw:
        v_locale = v.get("Locale", "")
        if locale and not v_locale.startswith(locale):
            continue
        out.append(
            VoiceInfo(
                short_name=v.get("ShortName", ""),
                locale=v_locale,
                gender=v.get("Gender", ""),
                friendly_name=v.get("FriendlyName", ""),
            )
        )
    return out
