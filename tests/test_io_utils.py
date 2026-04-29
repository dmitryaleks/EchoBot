from __future__ import annotations

from pathlib import Path

import pytest

from text_to_audio_mcp.config import Config
from text_to_audio_mcp.io_utils import (
    InputError,
    read_text_file,
    resolve_output_path,
)


def make_config(tmp_path: Path, max_bytes: int = 1_000_000) -> Config:
    return Config(
        default_voice="en-US-AriaNeural",
        default_rate="+0%",
        output_dir=(tmp_path / "output").resolve(),
        max_input_bytes=max_bytes,
    )


def test_read_text_file_happy_path(tmp_path: Path) -> None:
    p = tmp_path / "in.txt"
    p.write_text("hello world", encoding="utf-8")
    cfg = make_config(tmp_path)
    text, resolved = read_text_file(p, cfg)
    assert text == "hello world"
    assert resolved == p.resolve()


def test_read_text_file_rejects_missing(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    with pytest.raises(InputError, match="does not exist"):
        read_text_file(tmp_path / "missing.txt", cfg)


def test_read_text_file_rejects_directory(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    with pytest.raises(InputError, match="not a regular file"):
        read_text_file(tmp_path, cfg)


def test_read_text_file_rejects_oversize(tmp_path: Path) -> None:
    p = tmp_path / "big.txt"
    p.write_text("x" * 1000, encoding="utf-8")
    cfg = make_config(tmp_path, max_bytes=100)
    with pytest.raises(InputError, match="exceeds max"):
        read_text_file(p, cfg)


def test_read_text_file_rejects_non_utf8(tmp_path: Path) -> None:
    p = tmp_path / "bad.txt"
    p.write_bytes(b"\xff\xfe\xfd not utf-8")
    cfg = make_config(tmp_path)
    with pytest.raises(InputError, match="not valid UTF-8"):
        read_text_file(p, cfg)


def test_resolve_output_path_auto_names(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    out = resolve_output_path(None, "story.txt", cfg)
    assert out.parent == cfg.output_dir
    assert out.suffix == ".mp3"
    assert out.name.startswith("story-")
    assert out.parent.exists()


def test_resolve_output_path_explicit(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    target = tmp_path / "custom" / "out.mp3"
    out = resolve_output_path(target, "ignored.txt", cfg)
    assert out == target.resolve()
    assert out.parent.exists()
