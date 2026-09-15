.PHONY: help install dev-install test lint format clean docker-up docker-down docker-dev migrate init-db serve serve-dev run cli

help:
	@echo "Available commands:"
	@echo "  make install       Install dependencies"
	@echo "  make dev-install   Install development dependencies"
	@echo "  make test          Run tests"
	@echo "  make lint          Run linters"
	@echo "  make format        Format code"
	@echo "  make clean         Clean temporary files"
	@echo "  make docker-up     Start Docker containers"
	@echo "  make docker-down   Stop Docker containers"
	@echo "  make docker-dev    Start dev API with reload"
	@echo "  make migrate       Run database migrations"
	@echo "  make init-db       Initialize database"
	@echo "  make serve         Start API server"
	@echo "  make serve-dev     Start API server with reload"

install:
	pip install -r requirements.txt

dev-install:
	pip install -r requirements.txt
	pip install -e .[dev,scraping]

test:
	pytest tests/ -v --cov=src

lint:
	flake8 src/ tests/
	mypy src/ tests/
	isort --check-only src/ tests/

format:
	black src/ tests/
	isort src/ tests/

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	find . -type d -name ".coverage" -delete
	find . -type d -name "htmlcov" -delete
	find . -type d -name "*.egg-info" -delete
	rm -rf dist/ build/

docker-up:
	docker-compose up -d postgres redis api

docker-down:
	docker-compose down

docker-dev:
	docker-compose --profile dev up api-dev

migrate:
	alembic upgrade head

init-db:
	python -m src.main --init-db

serve:
	python -m src.main --serve

serve-dev:
	python -m src.main --serve --reload

run:
	python -m src.main --serve --host 0.0.0.0 --port 8000

parse:
	python -m src.main --parse-inn $(INN)