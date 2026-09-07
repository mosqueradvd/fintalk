"""Behavioural eval harness for the chat agent.

`pytest` proves the plumbing (core queries, MCP loop, error handling). This
proves the thing that actually matters to a user: given a plain-English
question, does the agent call the right tools and report the right number?

Run: ``python -m evals`` (needs a real ANTHROPIC_API_KEY + the sample DB).
"""
