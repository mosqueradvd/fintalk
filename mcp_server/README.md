# mcp_server/ — MCP server

Exposes the FinTalk data as MCP tools for external AI clients. Imports
[`core/`](../core) directly (no HTTP hop through the REST API).

## Tools

| Tool | Args | Returns |
|------|------|---------|
| `find_company` | `query` | up to 10 `{ticker, name, sector}` matches (fuzzy) |
| `list_company_kpis` | `ticker` | `[{name, unit}]` |
| `get_history` | `ticker`, `kpi`, `quarters=8` | quarterly history for one KPI |
| `get_qtd` | `ticker`, `kpi` | latest QTD snapshot + full snapshot series |

Natural flow for an agent: `find_company` → `list_company_kpis` → `get_history` / `get_qtd`.

### Recoverable errors

Unknown ticker/KPI returns a payload, not an exception:

```json
{"error": "kpi_not_found",
 "message": "'IGC' has no KPI named 'Revenu'.",
 "suggestions": ["ASP ($)", "Total Revenue ($MM)", ...]}
```

The LLM can retry with a suggested value.

## Auditing

Every call logs one JSON line (tool, args, outcome, result summary, latency) to
`logs/mcp_audit.log` and stderr. stdout is reserved for the MCP protocol.

## Run

```bash
export DATABASE_URL=postgresql://fintalk:fintalk@localhost:5432/fintalk
python -m mcp_server.server        # stdio transport
```

## Connect from Claude Desktop

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "fintalk": {
      "command": "/ABSOLUTE/PATH/fintalk/.venv/bin/python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/ABSOLUTE/PATH/fintalk",
      "env": { "DATABASE_URL": "postgresql://fintalk:fintalk@localhost:5432/fintalk" }
    }
  }
}
```

Restart Claude Desktop; the 4 tools appear under the 🔌 menu. (Cursor: same
command/args in its MCP settings.)
