# text-to-audio-mcp

An MCP server that converts text — passed inline or as a file path — into MP3
audio using [edge-tts](https://github.com/rany2/edge-tts) (free, neural voices,
no API key required, internet needed).

## Tools

| Tool | Purpose |
|---|---|
| `text_to_audio(text, output_path?, voice?, rate?)` | Synthesize a string. |
| `text_file_to_audio(input_path, output_path?, voice?, rate?)` | Read a UTF-8 text file and synthesize it. |
| `list_voices(locale?)` | List available edge-tts voices, optionally filtered by locale prefix (`"en-"`, `"en-US"`, …). |

All synthesis tools return `{ output_path, voice, bytes, duration_ms }` and
write MP3 to disk. If `output_path` is omitted, the file is auto-named under
the configured output directory.

## Install

```bash
# from the project root, with a Python 3.11+ venv active
pip install -e .[dev]
```

## Run

```bash
text-to-audio-mcp           # stdio transport, ready for an MCP client
```

### Claude Desktop config

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "text-to-audio": {
      "command": "C:/Projects/TextToAudio/.venv/Scripts/text-to-audio-mcp.exe"
    }
  }
}
```

## Configuration

All optional, set via environment variables:

| Var | Default | Meaning |
|---|---|---|
| `TTS_DEFAULT_VOICE` | `en-US-AriaNeural` | edge-tts ShortName. |
| `TTS_DEFAULT_RATE` | `+0%` | Speaking rate adjustment, e.g. `+10%`, `-20%`. |
| `TTS_OUTPUT_DIR` | `./output` | Where auto-named MP3s are written. |
| `TTS_MAX_INPUT_BYTES` | `1000000` | Max accepted size for `text_file_to_audio`. |

Browse voices with the `list_voices` tool, or run:

```bash
python -c "import asyncio, edge_tts; print('\n'.join(v['ShortName'] for v in asyncio.run(edge_tts.list_voices()) if v['Locale'].startswith('en-')))"
```

## Tests

```bash
pytest -m "not network"   # offline tests only
pytest                    # full suite (calls edge-tts upstream)
```

## Limitations

- Requires internet — edge-tts uses Microsoft Edge's online voices.
- Output is always MP3.
- Long inputs (~10k+ characters) take seconds to synthesize and are streamed
  end-to-end before the tool returns.
