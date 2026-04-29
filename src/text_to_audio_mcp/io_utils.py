"""Filesystem helpers: text input reading and output path resolution."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .config import Config


class InputError(ValueError):
    """Raised for invalid input paths or content."""


def read_text_file(path: str | Path, config: Config) -> tuple[str, Path]:
    p = Path(path).expanduser().resolve()
    if not p.exists():
        raise InputError(f"Input file does not exist: {p}")
    if not p.is_file():
        raise InputError(f"Input path is not a regular file: {p}")
    size = p.stat().st_size
    if size > config.max_input_bytes:
        raise InputError(
            f"Input file is {size} bytes, exceeds max {config.max_input_bytes}."
        )
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise InputError(f"Input file is not valid UTF-8: {p}") from exc
    return text, p


def resolve_output_path(
    requested: str | Path | None,
    source_name: str,
    config: Config,
) -> Path:
    if requested is not None:
        out = Path(requested).expanduser().resolve()
    else:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        stem = Path(source_name).stem or "audio"
        out = (config.output_dir / f"{stem}-{timestamp}.mp3").resolve()

    out.parent.mkdir(parents=True, exist_ok=True)
    return out
