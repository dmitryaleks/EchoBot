# Text-to-Audio MCP Server — Implementation Plan

## Context

`PROJECT_SKETCH.md` specifies one feature: an MCP server that accepts a text file
and returns an audio file produced by text-to-speech.

The repository is greenfield: a Python 3.14 `.venv`, a stub `main.py`, an empty
`IMPLEMENTATION_PLAN.md`, no dependency manifest, no git, no tests. Everything
below builds from scratch on top of that environment.

User-confirmed choices (decided in planning):
- **TTS engine:** `edge-tts` — free, no API key, neural-quality MP3 over Microsoft Edge's online voices.
- **Return mode:** the tool writes the audio file to disk and returns its path. No inline base64.

## Architecture

```
MCP client (Claude Code, Claude Desktop, etc.)
        │  stdio (JSON-RPC over MCP)
        ▼
text_to_audio_mcp.server          ← FastMCP server, registers tools
        │
        ├── text_to_audio_mcp.tts ← thin wrapper around edge-tts
        │       └─ async synthesize(text, voice, rate, output_path) → Path
        │
        └── text_to_audio_mcp.io_utils ← read input file, resolve/validate output path
```

Two MCP tools are exposed:
1. `text_file_to_audio(input_path, output_path?, voice?, rate?)` — reads a UTF-8 text file from disk and synthesizes it.
2. `text_to_audio(text, output_path?, voice?, rate?)` — synthesizes a raw string passed in the call. Useful for short snippets where writing a file first is friction.

Both return a structured result: `{ "output_path": str, "duration_ms": int, "voice": str, "bytes": int }`.

A small `list_voices()` tool is included so callers can discover available `edge-tts` voices without leaving the MCP session.

## File-level changes

| Path | Action | Purpose |
|---|---|---|
| `pyproject.toml` | create | Project metadata, deps (`mcp[cli]`, `edge-tts`), entry point `text-to-audio-mcp`. |
| `requirements.txt` | create | Pinned deps for plain `pip install -r` users. |
| `.gitignore` | create | Standard Python ignores + `.venv/`, `.idea/`, `output/`, `*.mp3`. |
| `README.md` | create | Quickstart: install, run, sample MCP client config snippet. |
| `src/text_to_audio_mcp/__init__.py` | create | Package marker, version. |
| `src/text_to_audio_mcp/server.py` | create | FastMCP server, tool definitions, CLI entry point. |
| `src/text_to_audio_mcp/tts.py` | create | `synthesize()` async wrapper around `edge_tts.Communicate`; `list_voices()` helper. |
| `src/text_to_audio_mcp/io_utils.py` | create | Validate input path is a readable file ≤ size cap; resolve output path (auto-name in `output/` if omitted); ensure parent dir exists. |
| `src/text_to_audio_mcp/config.py` | create | Read env vars: `TTS_DEFAULT_VOICE` (default `en-US-AriaNeural`), `TTS_DEFAULT_RATE` (default `+0%`), `TTS_OUTPUT_DIR` (default `./output`), `TTS_MAX_INPUT_BYTES` (default `1_000_000`). |
| `tests/test_tts.py` | create | Unit test on `synthesize()` against a tiny string, asserts non-empty MP3 written, header bytes look like MP3. |
| `tests/test_io_utils.py` | create | Path validation: missing file, oversize file, output auto-naming, traversal rejection. |
| `tests/test_server.py` | create | Boot FastMCP in-process, call each tool through the MCP client harness, assert result shape. |
| `main.py` | delete | PyCharm stub, unused. |

## Implementation steps (status tracked)

Each step is independently executable and has a clear "done" check. Status legend:
`[ ]` not started · `[~]` in progress · `[x]` done · `[!]` blocked.

### Phase 1 — Project scaffolding
- [ ] **1.1** Create `pyproject.toml` with project name `text-to-audio-mcp`, Python `>=3.11`, deps `mcp[cli]>=1.2`, `edge-tts>=6.1`, dev-deps `pytest`, `pytest-asyncio`. Define console script `text-to-audio-mcp = text_to_audio_mcp.server:main`.
- [ ] **1.2** Create matching `requirements.txt` (runtime only) and `requirements-dev.txt` (adds pytest).
- [ ] **1.3** Add `.gitignore` covering `__pycache__/`, `.venv/`, `.idea/`, `*.egg-info/`, `dist/`, `build/`, `output/`, `.pytest_cache/`.
- [ ] **1.4** `git init`; first commit "scaffold". (Note: repo is currently not a git repo — confirm with user before initializing.)
- [ ] **1.5** `pip install -e .[dev]` inside `.venv`. Verify `python -c "import mcp, edge_tts"` succeeds.

### Phase 2 — TTS core (`src/text_to_audio_mcp/tts.py`)
- [ ] **2.1** Implement `async def synthesize(text: str, output_path: Path, voice: str, rate: str) -> SynthesisResult` using `edge_tts.Communicate(text, voice, rate=rate).save(str(output_path))`.
- [ ] **2.2** Return a `SynthesisResult` dataclass: `output_path: Path`, `voice: str`, `bytes: int`, `duration_ms: int | None` (best-effort via `mutagen` only if already pulled in — otherwise leave `None`; do not add a dep just for this).
- [ ] **2.3** Implement `async def list_voices(locale: str | None = None) -> list[VoiceInfo]` that wraps `edge_tts.list_voices()`, optionally filters by `Locale` prefix (e.g. `"en-"`).
- [ ] **2.4** Catch `edge_tts.exceptions.NoAudioReceived` and raise a typed `TTSError` with a helpful message ("upstream returned no audio — check voice name and connectivity").

### Phase 3 — IO + config (`io_utils.py`, `config.py`)
- [ ] **3.1** `config.load_config()` reads env vars once, returns a frozen dataclass with `default_voice`, `default_rate`, `output_dir`, `max_input_bytes`.
- [ ] **3.2** `io_utils.read_text_file(path)` — resolve to absolute, reject if not a file, reject if size > `max_input_bytes`, decode UTF-8 with `errors="strict"`, raise typed errors.
- [ ] **3.3** `io_utils.resolve_output_path(requested, source_name)` — if `requested` is `None`, generate `<output_dir>/<source_stem>-<timestamp>.mp3`; ensure parent dir exists; reject paths outside `output_dir` unless an absolute path was explicitly supplied by the caller.

### Phase 4 — MCP server (`server.py`)
- [ ] **4.1** Build a `FastMCP("text-to-audio")` instance. Use `mcp.server.fastmcp` (Python SDK ≥ 1.2 ships this).
- [ ] **4.2** Register `@mcp.tool() async def text_to_audio(text, output_path=None, voice=None, rate=None) -> dict`. Apply config defaults for `voice`/`rate`. Call `synthesize`. Return result dict.
- [ ] **4.3** Register `@mcp.tool() async def text_file_to_audio(input_path, output_path=None, voice=None, rate=None) -> dict`. Read file via `io_utils.read_text_file`, then delegate to the same synthesis path.
- [ ] **4.4** Register `@mcp.tool() async def list_voices(locale: str | None = None) -> list[dict]`.
- [ ] **4.5** Add `def main()` that calls `mcp.run()` over stdio. Wire it to the `pyproject.toml` console script.
- [ ] **4.6** Smoke test from CLI: `python -m text_to_audio_mcp.server` should start without crashing and respond to a manual `tools/list` JSON-RPC request piped in via stdin.

### Phase 5 — Tests (`tests/`)
- [ ] **5.1** `pytest-asyncio` fixture creating a temp dir as `output_dir`. Override config via env vars per test.
- [ ] **5.2** `test_synthesize_writes_mp3` — short string, assert file exists, size > 1 KB, first 3 bytes are `ID3` or `0xFF 0xFB`. Mark as `@pytest.mark.network` because edge-tts hits the internet.
- [ ] **5.3** `test_read_text_file_rejects_oversize`, `test_read_text_file_rejects_directory`, `test_resolve_output_path_auto_names`.
- [ ] **5.4** `test_server_tools_list` — start FastMCP in-process via `mcp.client.session.ClientSession` against the server's stdio transport (or call the registered tool functions directly if that's simpler with FastMCP); assert all three tools are present and have non-empty descriptions.
- [ ] **5.5** Run `pytest -m "not network"` clean by default; `pytest` (with network) clean when online.

### Phase 6 — Documentation
- [ ] **6.1** Write `README.md`: install, run (`text-to-audio-mcp`), example tool calls, env var reference, voice list snippet.
- [ ] **6.2** Add a sample `claude_desktop_config.json` block showing how to register the server (command, args, env).
- [ ] **6.3** Note known limitations: requires internet for edge-tts; large texts (>~10k chars) may be slow; output is always MP3.

### Phase 7 — Verification
- [ ] **7.1** Manual end-to-end: write a `sample.txt`, call `text_file_to_audio` from a real MCP client (Claude Desktop or `mcp` CLI's `inspector`), play the resulting MP3.
- [ ] **7.2** Run `pytest` — all tests green (network suite included if connected).
- [ ] **7.3** Confirm tool re-registers cleanly after a server restart and that `list_voices()` returns > 100 entries.

## Verification (end-to-end recipe)

```bash
# 1. install
cd C:/Projects/TextToAudio
.venv/Scripts/pip install -e .[dev]

# 2. start the server (stdio); leave it running in another shell
.venv/Scripts/text-to-audio-mcp

# 3. inspect with the MCP CLI
.venv/Scripts/python -m mcp inspector text-to-audio-mcp

# 4. or wire into Claude Desktop via claude_desktop_config.json:
#    { "mcpServers": { "text-to-audio": { "command": "C:/Projects/TextToAudio/.venv/Scripts/text-to-audio-mcp.exe" } } }

# 5. call text_file_to_audio with input_path = "C:/Projects/TextToAudio/sample.txt"
#    expect a path to an MP3 in ./output/, ~few seconds for a paragraph.

# 6. tests
.venv/Scripts/pytest
```

## Out of scope (intentionally deferred)

- SSML input, batching, streaming audio chunks back to the client.
- Alternate engines (pyttsx3 / OpenAI TTS / Piper) — leave engine pluggable but only ship edge-tts.
- Caching identical text→audio pairs.
- Web/HTTP transport for MCP (stdio is sufficient for the local-CLI use case the sketch implies).
