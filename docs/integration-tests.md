# Integration Tests Guide

## Overview

Integration tests for Content Creation Crew cover critical flows using Docker Compose with Postgres and Redis. Tests run against real database (no SQLite) and verify end-to-end functionality.

## Table of Contents

1. [Test Setup](#test-setup)
2. [Running Tests](#running-tests)
3. [Test Coverage](#test-coverage)
4. [CI/CD Integration](#cicd-integration)

---

## Test Setup

### Prerequisites

- Docker and Docker Compose installed
- Python 3.10+ with pytest
- Test database and Redis (started via docker-compose)

### Test Database

Tests use a separate test database to avoid affecting development data:

- **Database:** `test_content_crew`
- **User:** `test`
- **Password:** `test`
- **Port:** `5433` (to avoid conflicts with dev database)

### Test Redis

Tests use a separate Redis instance:

- **Port:** `6380` (to avoid conflicts with dev Redis)
- **Database:** `1` (test database)

### Environment Variables

Tests set these environment variables automatically:

```bash
ENV=test
SECRET_KEY=test-secret-key-for-integration-tests-only-min-32-chars
DATABASE_URL=postgresql://test:test@localhost:5433/test_content_crew
REDIS_URL=redis://localhost:6380/1
ENABLE_VIDEO_RENDERING=false
LOG_LEVEL=WARNING
```

---

## Running Tests

### Quick Start

```bash
# Start test services and run tests
make test

# Or manually:
make test-setup    # Start test database and Redis
pytest tests/integration/ -v
make test-teardown # Stop test services
```

### Manual Setup

```bash
# 1. Start test services
docker-compose -f docker-compose.test.yml up -d

# 2. Wait for services to be ready
sleep 5

# 3. Run tests
TEST_DATABASE_URL=postgresql://test:test@localhost:5433/test_content_crew \
TEST_REDIS_URL=redis://localhost:6380/1 \
pytest tests/integration/ -v

# 4. Stop test services
docker-compose -f docker-compose.test.yml down
```

### Run Specific Tests

```bash
# Run specific test class
pytest tests/integration/test_critical_flows.py::TestAuthFlow -v

# Run specific test
pytest tests/integration/test_critical_flows.py::TestAuthFlow::test_signup_and_login -v

# Run with markers
pytest -m integration -v
```

---

## Test Coverage

### Test 1: Auth Flow ✅

**File:** `tests/integration/test_critical_flows.py::TestAuthFlow`

**Tests:**
- `test_signup_and_login` - Sign up/login -> /me returns user
- `test_login_returns_user` - Login returns user info

**Coverage:**
- User signup endpoint
- User login endpoint
- `/api/auth/me` endpoint
- JWT token generation and validation

### Test 2: Plan Flow ✅

**File:** `tests/integration/test_critical_flows.py::TestPlanFlow`

**Tests:**
- `test_default_tier_assigned` - Default tier assigned
- `test_plan_endpoint_returns_tier` - /billing/plan returns tier

**Coverage:**
- Default tier assignment (free)
- Plan endpoint returns tier information
- Tier configuration loading

### Test 3: Blog Generation Flow ✅

**File:** `tests/integration/test_critical_flows.py::TestBlogGenerationFlow`

**Tests:**
- `test_generate_blog_creates_job` - Generate blog creates job
- `test_job_has_artifacts` - Job has artifacts

**Coverage:**
- Content generation endpoint
- Job creation
- Artifact creation

### Test 4: SSE Flow ✅

**File:** `tests/integration/test_critical_flows.py::TestSSEFlow`

**Tests:**
- `test_sse_stream_emits_events` - SSE stream emits events

**Coverage:**
- Server-Sent Events (SSE) streaming
- Event format and structure
- Job progress streaming

### Test 5: Usage Counters Flow ✅

**File:** `tests/integration/test_critical_flows.py::TestUsageCountersFlow`

**Tests:**
- `test_usage_counters_increment` - Usage counters increment
- `test_usage_counter_persists` - Usage counter persists

**Coverage:**
- Usage counter increment
- Database persistence
- Counter retrieval

### Test 6: Limit Exceeded Flow ✅

**File:** `tests/integration/test_critical_flows.py::TestLimitExceededFlow`

**Tests:**
- `test_limit_exceeded_returns_error` - Limit exceeded returns error

**Coverage:**
- Plan limit enforcement
- Error response format
- PLAN_LIMIT_EXCEEDED error code

### Test 7: Cache Flow ✅

**File:** `tests/integration/test_critical_flows.py::TestCacheFlow`

**Tests:**
- `test_cache_hit_fast_response` - Cache hit returns fast

**Coverage:**
- Cache hit/miss behavior
- Cache performance
- Cache marking in responses

### Test 8: Health Check Flow ✅

**File:** `tests/integration/test_critical_flows.py::TestHealthCheckFlow`

**Tests:**
- `test_health_endpoint_responds_quickly` - Health endpoint responds quickly
- `test_health_endpoint_with_bad_db` - Health endpoint handles bad DB

**Coverage:**
- Health endpoint response time (< 3 seconds)
- Database connectivity check
- Graceful degradation

### Test 9: Metrics Flow ✅

**File:** `tests/integration/test_critical_flows.py::TestMetricsFlow`

**Tests:**
- `test_metrics_endpoint_increments` - Metrics endpoint increments
- `test_metrics_increment_on_requests` - Metrics increment on requests

**Coverage:**
- Metrics endpoint (`/metrics`)
- Counter incrementation
- Prometheus format

### Test 10: Migration Flow ✅

**File:** `tests/integration/test_critical_flows.py::TestMigrationFlow`

**Tests:**
- `test_schema_tables_exist` - Schema tables exist
- `test_key_indexes_exist` - Key indexes exist
- `test_migrations_applied` - Migrations applied

**Coverage:**
- Database schema presence
- Index existence
- Migration application

### Additional Tests

**Request ID Flow:**
- `test_request_id_in_response` - Request ID in response headers
- `test_request_id_in_error_response` - Request ID in error responses

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_content_crew
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install pytest pytest-asyncio
          pip install -e .
      
      - name: Run migrations
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test_content_crew
        run: |
          alembic upgrade head
      
      - name: Run tests
        env:
          TEST_DATABASE_URL: postgresql://test:test@localhost:5432/test_content_crew
          TEST_REDIS_URL: redis://localhost:6379/1
        run: |
          pytest tests/integration/ -v --tb=short
```

### Local CI Simulation

```bash
# Run tests in CI mode (assumes services are available)
make test-ci
```

---

## Test Fixtures

### Available Fixtures

- `test_database_url` - Test database URL
- `test_engine` - SQLAlchemy engine for test database
- `db_session` - Database session (auto-rollback after each test)
- `client` - FastAPI test client
- `test_user` - Test user fixture
- `auth_headers` - Authentication headers
- `authenticated_client` - Authenticated test client
- `mock_ollama` - Mock Ollama calls (avoids external dependencies)

### Usage Example

```python
def test_example(authenticated_client: TestClient, db_session: Session):
    """Example test using fixtures"""
    response = authenticated_client.get("/api/auth/me")
    assert response.status_code == 200
```

---

## Best Practices

### ✅ DO

- ✅ Use fixtures for database sessions (auto-rollback)
- ✅ Mock external dependencies (Ollama, payment providers)
- ✅ Use descriptive test names
- ✅ Test one thing per test function
- ✅ Clean up test data (handled by fixtures)

### ❌ DON'T

- ❌ Don't rely on external internet
- ❌ Don't use SQLite (use Postgres)
- ❌ Don't leave test data in database
- ❌ Don't test implementation details
- ❌ Don't skip cleanup

---

## Troubleshooting

### Tests Fail to Connect to Database

**Error:** `Connection refused` or `database does not exist`

**Solution:**
```bash
# Ensure test services are running
docker-compose -f docker-compose.test.yml up -d

# Check service status
docker-compose -f docker-compose.test.yml ps

# Check logs
docker-compose -f docker-compose.test.yml logs test-db
```

### Migration Errors

**Error:** `Migration failed` or `Table already exists`

**Solution:**
```bash
# Reset test database
docker-compose -f docker-compose.test.yml down -v
docker-compose -f docker-compose.test.yml up -d

# Re-run migrations
alembic upgrade head
```

### Port Conflicts

**Error:** `Port already in use`

**Solution:**
```bash
# Check what's using the port
lsof -i :5433  # PostgreSQL
lsof -i :6380  # Redis

# Stop conflicting services or change ports in docker-compose.test.yml
```

---

## Related Documentation

- [Pre-Deploy Readiness](./pre-deploy-readiness.md) - Deployment checklist
- [Database Migrations](./db-migrations.md) - Migration strategy
- [Health Checks](./health-checks-implementation.md) - Health endpoint

---

**Last Updated:** January 13, 2026  
**Status:** ✅ Production Ready

