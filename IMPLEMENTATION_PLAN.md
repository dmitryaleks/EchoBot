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
- [x] **1.1** Create `pyproject.toml` with project name `text-to-audio-mcp`, Python `>=3.11`, deps `mcp[cli]>=1.2`, `edge-tts>=6.1`, dev-deps `pytest`, `pytest-asyncio`. Define console script `text-to-audio-mcp = text_to_audio_mcp.server:main`.
- [x] **1.2** Create matching `requirements.txt` (runtime only) and `requirements-dev.txt` (adds pytest).
- [x] **1.3** Add `.gitignore` covering `__pycache__/`, `.venv/`, `.idea/`, `*.egg-info/`, `dist/`, `build/`, `output/`, `.pytest_cache/`.
- [x] **1.4** `git init`; first commit "scaffold". Done as part of associating with `dmitryaleks/EchoBot` (commit `fbb21f3`).
- [x] **1.5** `pip install -e .[dev]` inside `.venv`. Resolved `mcp 1.27.0`, `edge-tts 7.2.8`. Imports verified.

### Phase 2 — TTS core (`src/text_to_audio_mcp/tts.py`)
- [x] **2.1** Implemented `async def synthesize(text, output_path, voice, rate)` via `edge_tts.Communicate(...).save(...)`.
- [x] **2.2** `SynthesisResult` dataclass returns `output_path / voice / bytes / duration_ms` (`duration_ms` left `None` — no extra dep added).
- [x] **2.3** `list_voices(locale)` wraps `edge_tts.list_voices()` and filters by `Locale` prefix.
- [x] **2.4** `edge_tts.exceptions.NoAudioReceived` is mapped to a typed `TTSError` with actionable wording.

### Phase 3 — IO + config (`io_utils.py`, `config.py`)
- [x] **3.1** `config.load_config()` returns a frozen `Config` from env vars.
- [x] **3.2** `read_text_file()` — existence/regular-file/size/UTF-8 checks all enforced; tested.
- [x] **3.3** `resolve_output_path()` — auto-names `<stem>-<YYYYMMDD-HHMMSS>.mp3` under `output_dir`, creates parents.

### Phase 4 — MCP server (`server.py`)
- [x] **4.1** `FastMCP("text-to-audio")` instance built on `mcp.server.fastmcp`.
- [x] **4.2** `text_to_audio(text, output_path?, voice?, rate?)` registered.
- [x] **4.3** `text_file_to_audio(input_path, output_path?, voice?, rate?)` registered, delegates to shared synthesis path.
- [x] **4.4** `list_voices(locale?)` registered.
- [x] **4.5** `main()` calls `mcp.run()`; wired to console script `text-to-audio-mcp`.
- [x] **4.6** In-process smoke test: `mcp.list_tools()` returns the three tools, and `text_file_to_audio('sample.txt')` produced a 58 KB MP3.

### Phase 5 — Tests (`tests/`)
- [x] **5.1** `pyproject.toml` configures `asyncio_mode = "auto"` and `network` marker; per-test temp paths used directly.
- [x] **5.2** `test_synthesize_writes_mp3` — `@pytest.mark.network`, asserts MP3 magic bytes (`ID3` or `0xFF`).
- [x] **5.3** Coverage for missing/directory/oversize/non-UTF-8 input + auto-named/explicit output paths.
- [x] **5.4** `test_server_registers_three_tools` calls `mcp.list_tools()` and asserts all three with non-empty descriptions.
- [x] **5.5** `pytest -m "not network"` → 9 passed, 1 deselected; `pytest -m network` → 1 passed.

### Phase 6 — Documentation
- [x] **6.1** `README.md` covers install, run, tools table, env var reference, voice-listing snippet.
- [x] **6.2** Includes `claude_desktop_config.json` block referencing the installed `text-to-audio-mcp.exe`.
- [x] **6.3** Limitations section documents internet requirement, MP3-only output, and latency on long inputs.

### Phase 7 — Verification
- [x] **7.1** Manual end-to-end: `sample.txt` → `text_file_to_audio` → `output/sample-20260429-195925.mp3` (58,896 bytes, voice `en-US-AriaNeural`).
- [x] **7.2** `pytest` clean both with and without `network` marker (10 tests total).
- [x] **7.3** Tool re-registers cleanly across reimports; `list_voices()` returns > 100 entries (verified via edge-tts API directly).

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

---

# GUI Tool — Implementation Plan

## Context

Add a desktop GUI on top of the MCP server: paste text, hit Synthesize, the
GUI talks to the local MCP server as a real client and surfaces the resulting
MP3's path. Framework: Tkinter (stdlib, no new deps).

## Architecture

- GUI spawns `python -m text_to_audio_mcp.server` as a stdio subprocess via
  `mcp.client.stdio.stdio_client` and keeps a single `ClientSession` open for
  the window's lifetime.
- A worker thread owns the asyncio loop and the long-lived session. Synthesize
  clicks dispatch coroutines via `asyncio.run_coroutine_threadsafe`; results
  marshal back to Tk via `root.after(0, …)`.
- Tool called: `text_to_audio(text, voice?, rate?)`. The result dict's
  `output_path` is shown in the window.

## File-level changes

| Path | Action | Purpose |
|---|---|---|
| `src/text_to_audio_mcp/gui.py` | create | `MCPClient` worker + Tk `App`. Exports `main()`. |
| `pyproject.toml` | modify | Add console script `text-to-audio-gui`. |
| `README.md` | modify | New "GUI" section. |
| `tests/test_gui.py` | create | Module import + public surface assertions. |

## Implementation steps

### Phase 1 — `MCPClient` + `App` (`gui.py`)
- [x] **G1.1** `MCPClient` with `start()`, `stop()`, `synthesize(text, voice, rate, timeout)` returning the parsed tool result dict.
- [x] **G1.2** Worker thread runs `asyncio.run(_main)`, holding `stdio_client` + `ClientSession` open until a stop-event fires.
- [x] **G1.3** `synthesize()` schedules `session.call_tool("text_to_audio", ...)` via `run_coroutine_threadsafe` and parses the JSON text content.
- [x] **G1.4** Tk `App` with voice combobox, rate entry, scrolled paste box, Synthesize button, status + output labels, "Open output folder" button.
- [x] **G1.5** Synthesize click runs in a worker thread; result is marshalled back via `root.after(0, …)`. Errors land in the status label.
- [x] **G1.6** `WM_DELETE_WINDOW` calls `MCPClient.stop()` so the spawned server is reaped on close.

### Phase 2 — Packaging + docs
- [x] **G2.1** Added `text-to-audio-gui = "text_to_audio_mcp.gui:main"` console script.
- [x] **G2.2** Reinstalled (`pip install -e .`); `text-to-audio-gui.exe` registered.
- [x] **G2.3** README "GUI" section documents launch, behavior, and shared `TTS_*` env vars.

### Phase 3 — Tests
- [x] **G3.1** `tests/test_gui.py` asserts the public surface (`App`, `MCPClient`, `main`, `CURATED_VOICES`).
- [x] **G3.2** Negative test: `MCPClient.synthesize()` before `start()` raises `RuntimeError("not ready")`.

### Phase 4 — Verification
- [x] **G4.1** Headless integration: spun up `MCPClient`, called `synthesize()` twice — server ready in 2.25 s, first call 0.58 s, second call 0.28 s (session-reuse confirmed). Both MP3s written to `output/`.
- [x] **G4.2** `pytest -m "not network"` → 11 passed (9 existing + 2 GUI), 1 deselected.
- [ ] **G4.3** Manual GUI smoke (visual): launch `text-to-audio-gui`, paste text, click Synthesize, confirm path label updates and Open-folder works. *Pending user verification — not runnable headless from this session.*

## Out of scope (intentional)

- No "Load file" button — brief specifies pasting.
- No in-app playback. Surface the path; user opens it themselves.
- No live `list_voices` RPC at startup. Voice combobox is curated + free-text.
- No tray icon, theming, or window-state persistence.
