.PHONY: help install install-dev lint lint-fix format test test-cov test-integration clean docker-build docker-run dev run version

PYTHON := python3
PIP := $(PYTHON) -m pip

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install production dependencies
	$(PIP) install -e "."

install-dev: ## Install development dependencies
	$(PIP) install -e ".[dev,lint,test,all]"
	pre-commit install

lint: ## Run all linters (ruff, mypy, bandit)
	@echo "=== Ruff Lint ==="
	ruff check backend/
	@echo "=== MyPy Type Check ==="
	mypy backend/
	@echo "=== Bandit Security ==="
	bandit -r backend/ -ll

lint-fix: ## Auto-fix linting issues with ruff
	ruff check backend/ --fix
	ruff format backend/

format: ## Format code with ruff
	ruff format backend/

test: ## Run unit tests
	pytest tests/unit/ -v -x

test-cov: ## Run tests with coverage report
	pytest tests/ -v --cov=backend --cov-report=term-missing --cov-report=html

test-integration: ## Run integration tests (requires Redis)
	pytest tests/integration/ -v -m integration

test-all: ## Run all tests
	pytest tests/ -v --cov=backend --cov-report=term-missing -n auto

db-migrate: ## Run database migrations
	alembic upgrade head

db-revision: ## Create a new migration revision
	@read -p "Migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"

db-downgrade: ## Downgrade database by one revision
	alembic downgrade -1

docker-build: ## Build Docker images
	docker-compose build

docker-run: ## Run with Docker Compose
	docker-compose up -d

docker-logs: ## Show Docker logs
	docker-compose logs -f

docker-stop: ## Stop Docker containers
	docker-compose down

docker-clean: ## Clean Docker volumes and networks
	docker-compose down -v --remove-orphans

dev: ## Run development server with hot reload
	uvicorn backend.router:app --reload --host 0.0.0.0 --port 8000

dev-worker: ## Run RQ worker for background tasks
	$(PYTHON) -m rq.worker --with-scheduler

dev-redis: ## Start Redis (requires Docker)
	docker run -d --name luqi-redis -p 6379:6379 redis:7-alpine || docker start luqi-redis

run: ## Run production server
	gunicorn backend.router:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

clean: ## Clean generated files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov build/ dist/
	rm -rf .ruff_cache

requirements: ## Export requirements.txt from pyproject.toml
	$(PIP) install pip-tools
	pip-compile pyproject.toml -o requirements.txt

version: ## Show current version
	@$(PYTHON) -c "import backend; print(backend.__version__)"
