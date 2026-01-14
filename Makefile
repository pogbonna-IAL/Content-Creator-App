.PHONY: help backup backup-verify backup-restore-test backup-cleanup test lint format

# Default target
help:
	@echo "Content Creation Crew - Makefile Commands"
	@echo ""
	@echo "Backup & Restore (M2):"
	@echo "  make backup              Create database backup"
	@echo "  make backup-verify       Verify latest backup can be restored"
	@echo "  make backup-restore-test Restore backup to test database"
	@echo "  make backup-cleanup      Remove old backups"
	@echo ""
	@echo "Development:"
	@echo "  make test                Run all tests"
	@echo "  make lint                Run linters"
	@echo "  make format              Format code"
	@echo ""
	@echo "Testing:"
	@echo "  make test-retention      Run retention tests"
	@echo "  make test-notifications  Run notification tests"
	@echo "  make test-security       Run security tests"

# ============================================================================
# Backup & Restore (M2)
# ============================================================================

backup:
	@echo "Creating database backup..."
	@bash infra/scripts/create-backup.sh

backup-verify:
	@echo "Verifying latest backup..."
	@python3 infra/scripts/verify-backup-restore.py --latest --backup-dir ./backups

backup-verify-file:
	@if [ -z "$(FILE)" ]; then \
		echo "Error: FILE not specified. Usage: make backup-verify-file FILE=path/to/backup.sql"; \
		exit 1; \
	fi
	@echo "Verifying backup: $(FILE)"
	@python3 infra/scripts/verify-backup-restore.py "$(FILE)"

backup-restore-test:
	@echo "Starting restore test environment..."
	@docker-compose -f infra/docker-compose.restore-test.yml --profile restore-test up -d
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 5
	@echo "Running restore verification..."
	@python3 infra/scripts/verify-backup-restore.py --latest --backup-dir ./backups --no-cleanup
	@echo ""
	@echo "Test database is running. Connect with:"
	@echo "  psql -h localhost -p 5433 -U postgres -d restore_test"
	@echo ""
	@echo "To stop: make backup-restore-cleanup"

backup-restore-cleanup:
	@echo "Cleaning up restore test environment..."
	@docker-compose -f infra/docker-compose.restore-test.yml --profile restore-test down -v
	@docker rm -f backup-restore-test 2>/dev/null || true
	@echo "✓ Cleanup complete"

backup-cleanup:
	@echo "Cleaning up old backups..."
	@find ./backups -name "backup_*.sql.gz" -mtime +30 -delete
	@echo "✓ Removed backups older than 30 days"

# ============================================================================
# Development
# ============================================================================

test:
	@echo "Running all tests..."
	@pytest tests/ -v

test-retention:
	@echo "Running retention tests..."
	@pytest tests/test_artifact_retention.py tests/test_retention_notifications.py -v

test-notifications:
	@echo "Running notification tests..."
	@python3 scripts/test_retention_notifications.py --verbose

test-security:
	@echo "Running security regression tests..."
	@pytest tests/integration/test_security_regression.py -v

lint:
	@echo "Running linters..."
	@flake8 src/ tests/ --max-line-length=120 --exclude=__pycache__,*.pyc,venv,env
	@mypy src/ --ignore-missing-imports

format:
	@echo "Formatting code..."
	@black src/ tests/ --line-length=120
	@isort src/ tests/

# ============================================================================
# Docker
# ============================================================================

docker-up:
	@docker-compose up -d

docker-down:
	@docker-compose down

docker-logs:
	@docker-compose logs -f

docker-ps:
	@docker-compose ps
