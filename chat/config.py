"""Chat orchestrator configuration."""

import os

from dotenv import load_dotenv

load_dotenv()  # read .env at repo root (ANTHROPIC_API_KEY, DATABASE_URL, ...)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Haiku by default — cheapest model that handles this tool-use loop well.
CHAT_MODEL = os.environ.get("CHAT_MODEL", "claude-haiku-4-5-20251001")
MAX_TOKENS = 1024

# Safety valve: stop the tool-use loop after this many round-trips.
MAX_TOOL_ITERATIONS = 6

SYSTEM_PROMPT = """\
You are FinTalk, an assistant for time-poor public-market investors.

You answer questions about quarterly KPI estimates (historical) and
quarter-to-date (QTD) estimates for public companies, using ONLY the tools
provided. Never invent numbers.

Workflow:
- Use find_company to resolve a company name to a ticker before other calls.
- Use list_company_kpis to get exact KPI names; the other tools need them verbatim.
- If a tool returns an "error" with "suggestions", retry with a suggested value
  or ask the user to pick — do not give up silently.

Answers are short and quantitative: lead with the number, add the quarter/date
and the trend (e.g. "up 12% QoQ"). Mention the unit. No filler.
"""
