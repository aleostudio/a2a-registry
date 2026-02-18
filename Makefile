.PHONY: help setup dev test clean

help: ## Show help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Create virtual env and install deps
	uv venv
	uv sync
	@echo ""
	@echo "Dependencies installed!"

dev: ## Start A2A registry
	uvicorn app.main:app --host 0.0.0.0 --port 8000

test: ## Run tests
	uv run pytest tests/ -v

clean: ## Clean caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true