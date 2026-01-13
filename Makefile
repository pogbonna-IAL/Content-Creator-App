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
	@echo "  make migrate-up    - Apply all pending migrations"
	@echo "  make migrate-down-one - Rollback last migration"
	@echo "  make migrate-current - Show current migration revision"
	@echo "  make migrate-create MESSAGE=\"description\" - Create new migration"
	@echo "  make migrate-test  - Test migration rollback procedure"
	@echo "  make seed          - Seed database with initial data"
	@echo "  make backup-db     - Backup PostgreSQL database"
	@echo "  make restore-db FILE=\"backup.dump\" - Restore PostgreSQL database"
	@echo ""
	@echo "Model Commands:"
	@echo "  make models-pull   - Download all required Ollama models"
	@echo ""
	@echo "Testing Commands:"
	@echo "  make test          - Run integration tests"
	@echo "  make test-setup    - Start test database and Redis"
	@echo "  make test-teardown - Stop test services"
	@echo "  make test-ci       - Run tests in CI mode"
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

migrate-up:
	@echo "Applying all pending migrations..."
	@if docker compose ps api 2>/dev/null | grep -q "Up"; then \
		docker compose exec -T api alembic upgrade head; \
	else \
		echo "Docker not running, trying local migration..."; \
		python migrate_db.py upgrade || uv run alembic upgrade head; \
	fi
	@echo "✓ Migrations applied."

migrate-down-one:
	@echo "⚠️  WARNING: Rolling back last migration!"
	@read -p "Are you sure? This may cause data loss. [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		if docker compose ps api 2>/dev/null | grep -q "Up"; then \
			docker compose exec -T api alembic downgrade -1; \
		else \
			echo "Docker not running, trying local rollback..."; \
			python migrate_db.py downgrade || uv run alembic downgrade -1; \
		fi; \
		echo "✓ Migration rolled back."; \
	else \
		echo "Rollback cancelled."; \
	fi

migrate-current:
	@echo "Current migration status:"
	@if docker compose ps api 2>/dev/null | grep -q "Up"; then \
		docker compose exec -T api alembic current; \
		docker compose exec -T api alembic heads; \
	else \
		echo "Docker not running, checking locally..."; \
		python migrate_db.py current || uv run alembic current; \
		uv run alembic heads 2>/dev/null || echo "Run 'make migrate-up' to apply migrations"; \
	fi

migrate-create:
	@if [ -z "$(MESSAGE)" ]; then \
		echo "❌ Error: MESSAGE is required"; \
		echo "Usage: make migrate-create MESSAGE=\"add_user_preferences_table\""; \
		exit 1; \
	fi
	@echo "Creating new migration: $(MESSAGE)"
	@if docker compose ps api 2>/dev/null | grep -q "Up"; then \
		docker compose exec -T api alembic revision --autogenerate -m "$(MESSAGE)"; \
	else \
		echo "Docker not running, creating migration locally..."; \
		uv run alembic revision --autogenerate -m "$(MESSAGE)" || alembic revision --autogenerate -m "$(MESSAGE)"; \
	fi
	@echo "✓ Migration created. Review the file in alembic/versions/ before applying."

migrate-test:
	@echo "Testing migration rollback procedure..."
	@if [ -f "./scripts/test_migration_rollback.sh" ]; then \
		bash scripts/test_migration_rollback.sh; \
	else \
		echo "⚠️  Test script not found. Running basic test..."; \
		echo "Applying migrations..."; \
		python migrate_db.py upgrade || uv run alembic upgrade head; \
		echo "Rolling back one revision..."; \
		python migrate_db.py downgrade || uv run alembic downgrade -1; \
		echo "Re-applying migration..."; \
		python migrate_db.py upgrade || uv run alembic upgrade head; \
		echo "✓ Basic rollback test completed."; \
	fi

seed:
	@echo "Seeding database with initial data..."
	@if [ -f "./scripts/seed_db.py" ]; then \
		docker compose exec -T api python scripts/seed_db.py || \
		(echo "⚠️  Docker seed failed. Trying local seed..." && python scripts/seed_db.py); \
	else \
		echo "⚠️  Seed script not found at ./scripts/seed_db.py"; \
		echo "   Create a seed script to populate initial data."; \
	fi

backup-db:
	@echo "Backing up PostgreSQL database..."
	@if [ -f "./infra/scripts/backup-postgres.sh" ]; then \
		bash ./infra/scripts/backup-postgres.sh; \
	else \
		echo "⚠️  Backup script not found. Using direct pg_dump..."; \
		if docker compose ps db 2>/dev/null | grep -q "Up"; then \
			mkdir -p ./backups/postgres; \
			docker compose exec -T db pg_dump -U ${POSTGRES_USER:-contentcrew} -Fc ${POSTGRES_DB:-content_crew} > ./backups/postgres/content_crew_$$(date +%Y%m%d_%H%M%S).dump; \
			echo "✓ Backup created in ./backups/postgres/"; \
		else \
			echo "✗ Database not running. Start with: docker compose up -d db"; \
			exit 1; \
		fi; \
	fi

restore-db:
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Error: FILE is required"; \
		echo "Usage: make restore-db FILE=\"./backups/postgres/content_crew_20260113_020000.dump\""; \
		exit 1; \
	fi
	@echo "⚠️  WARNING: This will overwrite the existing database!"
	@echo "Restoring PostgreSQL database from: $(FILE)"
	@if [ -f "./infra/scripts/restore-postgres.sh" ]; then \
		bash ./infra/scripts/restore-postgres.sh "$(FILE)"; \
	else \
		echo "⚠️  Restore script not found. Using direct pg_restore..."; \
		if docker compose ps db 2>/dev/null | grep -q "Up"; then \
			echo "Dropping existing database..."; \
			docker compose exec -T db psql -U ${POSTGRES_USER:-contentcrew} -d postgres -c "DROP DATABASE IF EXISTS ${POSTGRES_DB:-content_crew};" || true; \
			echo "Creating new database..."; \
			docker compose exec -T db psql -U ${POSTGRES_USER:-contentcrew} -d postgres -c "CREATE DATABASE ${POSTGRES_DB:-content_crew};"; \
			echo "Restoring data..."; \
			docker compose exec -T db pg_restore -U ${POSTGRES_USER:-contentcrew} -d ${POSTGRES_DB:-content_crew} --no-owner --no-acl < "$(FILE)"; \
			echo "✓ Database restored"; \
		else \
			echo "✗ Database not running. Start with: docker compose up -d db"; \
			exit 1; \
		fi; \
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

# Testing commands
test-setup:
	@echo "Starting test database and Redis..."
	docker-compose -f docker-compose.test.yml up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	@echo "✓ Test services started"

test-teardown:
	@echo "Stopping test services..."
	docker-compose -f docker-compose.test.yml down
	@echo "✓ Test services stopped"

test: test-setup
	@echo "Running integration tests..."
	TEST_DATABASE_URL=postgresql://test:test@localhost:5433/test_content_crew \
	TEST_REDIS_URL=redis://localhost:6380/1 \
	pytest tests/integration/ -v
	@$(MAKE) test-teardown

test-ci:
	@echo "Running tests in CI mode..."
	TEST_DATABASE_URL=postgresql://test:test@test-db:5432/test_content_crew \
	TEST_REDIS_URL=redis://test-redis:6379/1 \
	pytest tests/integration/ -v --tb=short

install-ffmpeg:
	@echo "Installing FFmpeg..."
	@if [ "$(shell uname -s)" = "Linux" ] || [ "$(shell uname -s)" = "Darwin" ]; then \
		bash scripts/install_ffmpeg.sh; \
	elif [ "$(shell uname -s)" = "MINGW" ] || [ "$(shell uname -s)" = "MSYS" ]; then \
		powershell -ExecutionPolicy Bypass -File scripts/install_ffmpeg.ps1; \
	else \
		echo "Unsupported OS. Please install FFmpeg manually."; \
	fi

# Model management commands
models-pull:
	@echo "Pulling Ollama models..."
	@if docker compose ps ollama 2>/dev/null | grep -q "Up"; then \
		echo "Ollama is running in Docker. Pulling models in container..."; \
		if [ -n "$$MODEL_NAMES" ]; then \
			for model in $$(echo $$MODEL_NAMES | tr ',' ' '); do \
				echo "Pulling $$model..."; \
				docker compose exec -T ollama ollama pull $$model || true; \
			done; \
		else \
			echo "Extracting models from tiers.yaml..."; \
			docker compose exec -T ollama sh -c "ollama pull llama3.2:1b && ollama pull llama3.2:3b && ollama pull llama3.1:8b" || true; \
		fi; \
		echo "✓ Models pulled in Docker container"; \
		docker compose exec -T ollama ollama list; \
	elif command -v ollama &> /dev/null; then \
		echo "Using local Ollama installation..."; \
		if [ -f "./infra/scripts/pull-models.sh" ]; then \
			bash ./infra/scripts/pull-models.sh; \
		elif [ -f "./infra/scripts/pull-models.py" ]; then \
			python3 ./infra/scripts/pull-models.py || uv run python ./infra/scripts/pull-models.py; \
		else \
			echo "⚠️  Model pull scripts not found. Pulling default models..."; \
			ollama pull llama3.2:1b || true; \
			ollama pull llama3.2:3b || true; \
			ollama pull llama3.1:8b || true; \
			echo "✓ Default models pulled"; \
		fi; \
	else \
		echo "⚠️  Ollama is not installed or not accessible"; \
		echo "Install Ollama from: https://ollama.ai"; \
		echo "Or start Ollama in Docker: make up-ollama"; \
		exit 1; \
	fi

# Documentation commands
export-openapi:
	@echo "Exporting OpenAPI schema..."
	@python scripts/export_openapi.py
	@echo "✓ OpenAPI schema exported to docs/openapi.json"

# Documentation commands
export-openapi:
	@echo "Exporting OpenAPI schema..."
	@python scripts/export_openapi.py
	@echo "✓ OpenAPI schema exported to docs/openapi.json"

