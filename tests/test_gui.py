"""GUI module smoke test: import surface only, no Tk render."""
from __future__ import annotations


def test_gui_module_public_surface() -> None:
    from text_to_audio_mcp import gui

    assert callable(gui.main)
    assert hasattr(gui, "App")
    assert hasattr(gui, "MCPClient")
    assert isinstance(gui.CURATED_VOICES, list)
    assert all(isinstance(v, str) and v for v in gui.CURATED_VOICES)


def test_mcpclient_synthesize_requires_started() -> None:
    from text_to_audio_mcp.gui import MCPClient

    client = MCPClient()
    try:
        client.synthesize("hello")
    except RuntimeError as exc:
        assert "not ready" in str(exc).lower()
    else:
        raise AssertionError("expected RuntimeError when synthesize() called before start()")
