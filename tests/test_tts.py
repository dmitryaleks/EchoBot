from __future__ import annotations

from pathlib import Path

import pytest

from text_to_audio_mcp.tts import TTSError, synthesize


@pytest.mark.asyncio
async def test_synthesize_empty_text_raises(tmp_path: Path) -> None:
    with pytest.raises(TTSError, match="empty"):
        await synthesize(
            text="   ",
            output_path=tmp_path / "out.mp3",
            voice="en-US-AriaNeural",
        )


@pytest.mark.network
@pytest.mark.asyncio
async def test_synthesize_writes_mp3(tmp_path: Path) -> None:
    out = tmp_path / "hello.mp3"
    result = await synthesize(
        text="Hello world.",
        output_path=out,
        voice="en-US-AriaNeural",
    )
    assert result.output_path == out
    assert out.exists()
    assert out.stat().st_size > 1024
    head = out.read_bytes()[:3]
    assert head[:3] == b"ID3" or head[0] == 0xFF
