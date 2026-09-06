"""Connects to our own MCP server as a real client (stdio subprocess).

The chat backend deliberately goes through MCP rather than importing core/
directly: the exact tool path our frontend exercises is the one external
clients (Claude Desktop, Cursor) use, so we dogfood it.
"""

from __future__ import annotations

import json
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

_REPO_ROOT = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def mcp_session():
    """Spawn `python -m mcp_server.server` and yield an initialized session."""
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
        cwd=str(_REPO_ROOT),
        env=os.environ.copy(),  # carries DATABASE_URL through
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


def to_anthropic_tools(mcp_tools: list) -> list[dict]:
    """MCP tool definitions -> Anthropic `tools` param."""
    return [
        {
            "name": t.name,
            "description": (t.description or "").strip(),
            "input_schema": t.inputSchema,
        }
        for t in mcp_tools
    ]


def extract_tool_payload(result: Any) -> Any:
    """CallToolResult -> plain Python.

    FastMCP renders a tool that returns a list as one text block *per item*
    (plus structuredContent); a dict comes back as a single text block. Handle
    both so the LLM sees the whole result, not just the first element.
    """
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        # FastMCP wraps non-dict return values as {"result": <value>}.
        return structured["result"] if set(structured) == {"result"} else structured

    texts = [
        b.text for b in (getattr(result, "content", []) or [])
        if getattr(b, "type", None) == "text"
    ]
    if not texts:
        return {"error": "empty_tool_result", "message": "tool returned no content"}

    parsed = []
    for t in texts:
        try:
            parsed.append(json.loads(t))
        except json.JSONDecodeError:
            parsed.append(t)
    return parsed[0] if len(parsed) == 1 else parsed
