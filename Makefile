.PHONY: install run clean lint typecheck test

# Install all dependencies
install:
	pip install -e ".[dev]"
	playwright install chromium

# Run the agent
run:
	python -m src.app.cli

# Run with debug output
run-debug:
	DEBUG=1 python -m src.app.cli

# Run with OpenAI instead of Anthropic
run-openai:
	LLM_PROVIDER=openai python -m src.app.cli

# Run in headless mode
run-headless:
	HEADLESS=true python -m src.app.cli

# Clean up runs and caches
clean:
	rm -rf runs/*
	rm -rf __pycache__ src/__pycache__ src/**/__pycache__
	rm -rf .pytest_cache .mypy_cache .ruff_cache

# Clean browser profile (will log out of all sites!)
clean-profile:
	rm -rf profiles/default

# Lint code
lint:
	ruff check src/

# Type check
typecheck:
	mypy src/

# Run tests
test:
	pytest tests/ -v

# Format code
format:
	ruff check --fix src/
	ruff format src/

# Show recent logs
logs:
	@ls -t runs/*/logs.jsonl 2>/dev/null | head -1 | xargs cat 2>/dev/null || echo "No logs found"

# Show screenshots from latest run
screenshots:
	@ls -t runs/*/screenshots/*.png 2>/dev/null | head -10 || echo "No screenshots found"

# Help
help:
	@echo "Available targets:"
	@echo "  install       - Install dependencies and Playwright"
	@echo "  run           - Start the agent"
	@echo "  run-debug     - Start with debug output"
	@echo "  run-openai    - Start with OpenAI provider"
	@echo "  run-headless  - Start in headless mode"
	@echo "  clean         - Remove runs and caches"
	@echo "  clean-profile - Remove browser profile (logs out!)"
	@echo "  lint          - Run linter"
	@echo "  typecheck     - Run type checker"
	@echo "  format        - Format code"
	@echo "  logs          - Show latest run logs"
	@echo "  screenshots   - List recent screenshots"
