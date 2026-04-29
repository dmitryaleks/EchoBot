from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_server_registers_three_tools() -> None:
    from text_to_audio_mcp.server import mcp

    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert names == {"text_to_audio", "text_file_to_audio", "list_voices"}
    for tool in tools:
        assert tool.description and len(tool.description.strip()) > 0
