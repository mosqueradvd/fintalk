.PHONY: test eval

# Plumbing tests: core queries + MCP loop + error handling (mock LLM, no API cost).
test:
	pytest

# Behavioural evals: real model + real tools — question -> right tools -> right number.
# Needs ANTHROPIC_API_KEY + the sample DB. ~$0.05/run.
eval:
	python -m evals
