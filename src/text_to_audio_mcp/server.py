"""FastMCP server exposing text-to-audio tools over stdio."""
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import load_config
from .io_utils import read_text_file, resolve_output_path
from .tts import list_voices as tts_list_voices
from .tts import synthesize

mcp = FastMCP("text-to-audio")
_config = load_config()


@mcp.tool()
async def text_to_audio(
    text: str,
    output_path: str | None = None,
    voice: str | None = None,
    rate: str | None = None,
) -> dict[str, Any]:
    """Synthesize the supplied text into an MP3 file and return its path.

    Args:
        text: UTF-8 text to speak.
        output_path: Optional destination MP3 path. If omitted, an auto-named
            file is written under TTS_OUTPUT_DIR (default ./output).
        voice: edge-tts ShortName (e.g. "en-US-AriaNeural"). Defaults to
            TTS_DEFAULT_VOICE.
        rate: Speaking rate adjustment, e.g. "+10%" or "-20%". Defaults to
            TTS_DEFAULT_RATE.
    """
    out = resolve_output_path(output_path, "snippet", _config)
    result = await synthesize(
        text=text,
        output_path=out,
        voice=voice or _config.default_voice,
        rate=rate or _config.default_rate,
    )
    return {
        "output_path": str(result.output_path),
        "voice": result.voice,
        "bytes": result.bytes,
        "duration_ms": result.duration_ms,
    }


@mcp.tool()
async def text_file_to_audio(
    input_path: str,
    output_path: str | None = None,
    voice: str | None = None,
    rate: str | None = None,
) -> dict[str, Any]:
    """Read a UTF-8 text file from disk and synthesize it into an MP3.

    Args:
        input_path: Path to a UTF-8 text file (size <= TTS_MAX_INPUT_BYTES).
        output_path: Optional destination MP3 path. If omitted, an auto-named
            file is written under TTS_OUTPUT_DIR.
        voice: edge-tts ShortName. Defaults to TTS_DEFAULT_VOICE.
        rate: Speaking rate adjustment. Defaults to TTS_DEFAULT_RATE.
    """
    text, source = read_text_file(input_path, _config)
    out = resolve_output_path(output_path, source.name, _config)
    result = await synthesize(
        text=text,
        output_path=out,
        voice=voice or _config.default_voice,
        rate=rate or _config.default_rate,
    )
    return {
        "input_path": str(source),
        "output_path": str(result.output_path),
        "voice": result.voice,
        "bytes": result.bytes,
        "duration_ms": result.duration_ms,
    }


@mcp.tool()
async def list_voices(locale: str | None = None) -> list[dict[str, str]]:
    """List available edge-tts voices.

    Args:
        locale: Optional locale prefix filter, e.g. "en-" or "en-US".
    """
    voices = await tts_list_voices(locale)
    return [
        {
            "short_name": v.short_name,
            "locale": v.locale,
            "gender": v.gender,
            "friendly_name": v.friendly_name,
        }
        for v in voices
    ]


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
