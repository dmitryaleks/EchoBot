"""Tkinter GUI that drives the local MCP server as an MCP client.

Paste text → Synthesize → see the resulting MP3's path. The GUI spawns
`python -m text_to_audio_mcp.server` as a stdio subprocess and keeps a single
ClientSession open for its lifetime.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext, ttk
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


CURATED_VOICES: list[str] = [
    "en-US-AriaNeural",
    "en-US-JennyNeural",
    "en-US-GuyNeural",
    "en-GB-SoniaNeural",
    "en-AU-NatashaNeural",
]


class MCPClient:
    """Owns an asyncio loop on a worker thread, holding a long-lived MCP session."""

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._session: ClientSession | None = None
        self._ready = threading.Event()
        self._stop_event: asyncio.Event | None = None
        self._error: BaseException | None = None

    def start(self, timeout: float = 30.0) -> None:
        if self._thread is not None:
            raise RuntimeError("MCPClient already started")
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout):
            raise TimeoutError("MCP server did not become ready in time")
        if self._error is not None:
            raise self._error

    def _run(self) -> None:
        try:
            asyncio.run(self._main())
        except BaseException as exc:
            self._error = exc
            self._ready.set()

    async def _main(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._stop_event = asyncio.Event()
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "text_to_audio_mcp.server"],
            env=os.environ.copy(),
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self._session = session
                self._ready.set()
                await self._stop_event.wait()

    def synthesize(
        self,
        text: str,
        voice: str | None = None,
        rate: str | None = None,
        timeout: float = 120.0,
    ) -> dict[str, Any]:
        if self._session is None or self._loop is None:
            raise RuntimeError("MCP client not ready")
        args: dict[str, Any] = {"text": text}
        if voice:
            args["voice"] = voice
        if rate:
            args["rate"] = rate
        fut = asyncio.run_coroutine_threadsafe(
            self._session.call_tool("text_to_audio", args), self._loop
        )
        result = fut.result(timeout)
        payload = _extract_text(result)
        if getattr(result, "isError", False):
            raise RuntimeError(payload or "tool returned error")
        if not payload:
            raise RuntimeError("tool returned no text content")
        return json.loads(payload)

    def stop(self, timeout: float = 5.0) -> None:
        if self._loop is not None and self._stop_event is not None:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        if self._thread is not None:
            self._thread.join(timeout)


def _extract_text(result: Any) -> str | None:
    for block in getattr(result, "content", None) or []:
        text = getattr(block, "text", None)
        if text:
            return text
    return None


class App:
    """Tkinter front-end. Talks to MCPClient on a background thread."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Text-to-Audio")
        self.root.geometry("720x540")
        self.root.minsize(560, 380)

        self.client = MCPClient()
        self._last_output: Path | None = None

        self._build_widgets()
        self._set_status("Starting MCP server…")
        self.synth_btn.configure(state="disabled")
        self.open_btn.configure(state="disabled")

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        threading.Thread(target=self._start_client, daemon=True).start()

    def _build_widgets(self) -> None:
        frm = ttk.Frame(self.root, padding=12)
        frm.pack(fill="both", expand=True)

        controls = ttk.Frame(frm)
        controls.pack(fill="x")
        ttk.Label(controls, text="Voice:").pack(side="left")
        self.voice_var = tk.StringVar(value=CURATED_VOICES[0])
        ttk.Combobox(
            controls,
            textvariable=self.voice_var,
            values=CURATED_VOICES,
            width=28,
        ).pack(side="left", padx=(4, 16))
        ttk.Label(controls, text="Rate:").pack(side="left")
        self.rate_var = tk.StringVar(value="+0%")
        ttk.Entry(controls, textvariable=self.rate_var, width=8).pack(side="left", padx=(4, 0))

        ttk.Label(frm, text="Text to synthesize:").pack(anchor="w", pady=(12, 4))
        self.text = scrolledtext.ScrolledText(frm, wrap="word", height=12)
        self.text.pack(fill="both", expand=True)

        action_row = ttk.Frame(frm)
        action_row.pack(fill="x", pady=(8, 0))
        self.synth_btn = ttk.Button(action_row, text="Synthesize", command=self._on_synthesize)
        self.synth_btn.pack(side="right")

        self.status_var = tk.StringVar(value="Status: idle")
        ttk.Label(frm, textvariable=self.status_var).pack(anchor="w", pady=(10, 2))

        self.output_var = tk.StringVar(value="Output: (none yet)")
        ttk.Label(frm, textvariable=self.output_var, foreground="#0a64a0").pack(anchor="w")

        self.open_btn = ttk.Button(frm, text="Open output folder", command=self._open_folder)
        self.open_btn.pack(anchor="e", pady=(8, 0))

    def _start_client(self) -> None:
        try:
            self.client.start()
        except Exception as exc:
            self.root.after(0, self._set_status, f"Failed to start MCP server: {exc}")
            return
        self.root.after(0, self._on_ready)

    def _on_ready(self) -> None:
        self._set_status("Ready")
        self.synth_btn.configure(state="normal")

    def _set_status(self, msg: str) -> None:
        self.status_var.set(f"Status: {msg}")

    def _on_synthesize(self) -> None:
        text = self.text.get("1.0", "end").strip()
        if not text:
            self._set_status("Paste some text first.")
            return
        voice = self.voice_var.get().strip() or None
        rate = self.rate_var.get().strip() or None
        self.synth_btn.configure(state="disabled")
        self.open_btn.configure(state="disabled")
        self._set_status("Synthesizing…")
        threading.Thread(
            target=self._do_synthesize,
            args=(text, voice, rate),
            daemon=True,
        ).start()

    def _do_synthesize(
        self, text: str, voice: str | None, rate: str | None
    ) -> None:
        try:
            result = self.client.synthesize(text, voice, rate)
        except Exception as exc:
            self.root.after(0, self._on_synth_error, exc)
            return
        self.root.after(0, self._on_synth_result, result)

    def _on_synth_error(self, exc: BaseException) -> None:
        self._set_status(f"Error: {exc}")
        self.synth_btn.configure(state="normal")

    def _on_synth_result(self, result: dict[str, Any]) -> None:
        path = str(result.get("output_path", "(unknown)"))
        self._last_output = Path(path)
        self.output_var.set(f"Output: {path}")
        size = result.get("bytes", 0)
        voice = result.get("voice", "")
        self._set_status(f"Done • {size:,} bytes • voice {voice}")
        self.synth_btn.configure(state="normal")
        self.open_btn.configure(state="normal")

    def _open_folder(self) -> None:
        if self._last_output is None:
            return
        startfile = getattr(os, "startfile", None)
        if startfile is None:
            return
        try:
            startfile(str(self._last_output.parent))
        except OSError:
            pass

    def _on_close(self) -> None:
        try:
            self.client.stop()
        except Exception:
            pass
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
