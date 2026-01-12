# Makefile for Content Creation Crew
# Production-parity Docker Compose setup

.PHONY: help dev dev-api dev-web up down logs migrate seed clean build rebuild

# Default target
help:
	@echo "Content Creation Crew - Makefile Commands"
	@echo ""
	@echo "Development Commands:"
	@echo "  make dev          - Start backend and frontend locally (without Docker)"
	@echo "  make dev-api       - Start only backend locally"
	@echo "  make dev-web       - Start only frontend locally"
	@echo ""
	@echo "Docker Commands:"
	@echo "  make up            - Start all services with Docker Compose"
	@echo "  make up-ollama     - Start all services including Ollama"
	@echo "  make down          - Stop all services"
	@echo "  make logs          - Show logs from all services"
	@echo "  make build         - Build Docker images"
	@echo "  make rebuild       - Rebuild Docker images from scratch"
	@echo ""
	@echo "Database Commands:"
	@echo "  make migrate       - Run database migrations"
	@echo "  make seed          - Seed database with initial data"
	@echo ""
	@echo "Utility Commands:"
	@echo "  make clean         - Stop services and remove volumes (⚠️ deletes data)"
	@echo "  make check-deps    - Check if FFmpeg is installed"
	@echo "  make install-ffmpeg - Install FFmpeg (platform-specific)"
	@echo ""

# Development commands (local, no Docker)
# Note: On Windows, use start_backend.ps1 and start_ui.ps1 scripts directly
dev:
	@echo "Starting backend and frontend locally..."
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"
	@echo ""
	@echo "Note: On Windows, use PowerShell scripts:"
	@echo "  .\start_backend.ps1"
	@echo "  .\start_ui.ps1"
	@if [ -f "./start_backend.sh" ]; then \
		chmod +x ./start_backend.sh && ./start_backend.sh & \
	else \
		uv run python api_server.py & \
	fi
	@sleep 3
	@cd web-ui && npm run dev

dev-api:
	@echo "Starting backend API locally..."
	@echo "Backend: http://localhost:8000"
	@echo "Note: On Windows, use: .\start_backend.ps1"
	@if [ -f "./start_backend.sh" ]; then \
		chmod +x ./start_backend.sh && ./start_backend.sh; \
	else \
		uv run python api_server.py; \
	fi

dev-web:
	@echo "Starting frontend locally..."
	@echo "Frontend: http://localhost:3000"
	@echo "Note: On Windows, use: .\start_ui.ps1"
	@cd web-ui && npm run dev

# Docker Compose commands
up:
	@echo "Starting Docker Compose stack..."
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"
	@echo "PostgreSQL: localhost:5432"
	@echo "Redis: localhost:6379"
	@echo ""
	docker compose up -d
	@echo ""
	@echo "✓ Services started. Use 'make logs' to view logs."
	@echo "  To include Ollama, use: make up-ollama"

up-ollama:
	@echo "Starting Docker Compose stack with Ollama..."
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"
	@echo "PostgreSQL: localhost:5432"
	@echo "Redis: localhost:6379"
	@echo "Ollama: http://localhost:11434"
	@echo ""
	docker compose --profile ollama up -d
	@echo ""
	@echo "✓ Services started. Use 'make logs' to view logs."
	@echo "  Note: Pull Ollama models manually:"
	@echo "    docker exec content-crew-ollama ollama pull llama3.2:1b"

down:
	@echo "Stopping Docker Compose stack..."
	docker compose down
	@echo "✓ Services stopped."

logs:
	@echo "Showing logs from all services (Ctrl+C to exit)..."
	@docker compose logs -f

logs-api:
	@echo "Showing API logs (Ctrl+C to exit)..."
	@docker compose logs -f api

logs-web:
	@echo "Showing Web logs (Ctrl+C to exit)..."
	@docker compose logs -f web

logs-db:
	@echo "Showing Database logs (Ctrl+C to exit)..."
	@docker compose logs -f db

logs-redis:
	@echo "Showing Redis logs (Ctrl+C to exit)..."
	@docker compose logs -f redis

# Build commands
build:
	@echo "Building Docker images..."
	docker compose build
	@echo "✓ Images built."

rebuild:
	@echo "Rebuilding Docker images from scratch..."
	docker compose build --no-cache
	@echo "✓ Images rebuilt."

# Database commands
migrate:
	@echo "Running database migrations..."
	@docker compose exec -T api python migrate_db.py || \
		docker compose exec -T api alembic upgrade head || \
		(echo "⚠️  Migration failed. Trying local migration..." && \
		 python migrate_db.py || uv run alembic upgrade head)
	@echo "✓ Migrations completed."

seed:
	@echo "Seeding database with initial data..."
	@if [ -f "./scripts/seed_db.py" ]; then \
		docker compose exec -T api python scripts/seed_db.py || \
		(echo "⚠️  Docker seed failed. Trying local seed..." && python scripts/seed_db.py); \
	else \
		echo "⚠️  Seed script not found at ./scripts/seed_db.py"; \
		echo "   Create a seed script to populate initial data."; \
	fi

# Utility commands
clean:
	@echo "⚠️  WARNING: This will stop services and remove all volumes (deletes database data)!"
	@echo "Stopping services and removing volumes..."
	docker compose down -v
	@echo "✓ Services stopped and volumes removed."

# Health check
health:
	@echo "Checking service health..."
	@echo ""
	@echo "API Health:"
	@curl -s http://localhost:8000/health | python -m json.tool || echo "❌ API not responding"
	@echo ""
	@echo "Web Health:"
	@curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" http://localhost:3000 || echo "❌ Web not responding"
	@echo ""
	@echo "Database:"
	@docker compose exec -T db pg_isready -U contentcrew || echo "❌ Database not ready"
	@echo ""
	@echo "Redis:"
	@docker compose exec -T redis redis-cli ping || echo "❌ Redis not responding"

check-deps:
	@echo "Checking dependencies..."
	@python scripts/check_ffmpeg.py

install-ffmpeg:
	@echo "Installing FFmpeg..."
	@if [ "$(shell uname -s)" = "Linux" ] || [ "$(shell uname -s)" = "Darwin" ]; then \
		bash scripts/install_ffmpeg.sh; \
	elif [ "$(shell uname -s)" = "MINGW" ] || [ "$(shell uname -s)" = "MSYS" ]; then \
		powershell -ExecutionPolicy Bypass -File scripts/install_ffmpeg.ps1; \
	else \
		echo "Unsupported OS. Please install FFmpeg manually."; \
	fi

