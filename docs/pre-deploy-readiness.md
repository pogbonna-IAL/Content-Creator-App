# Pre-Deploy Readiness Audit

**Date**: 2024  
**Branch**: Features  
**Status**: Pre-Deployment Audit

This document provides a comprehensive audit of the Content Creation Crew application's current state, identifying what must be addressed before the first production deployment.

---

## Table of Contents

1. [Startup Commands](#startup-commands)
2. [Environment Variables](#environment-variables)
3. [Database Dependencies](#database-dependencies)
4. [SSE Route Paths and Proxy Usage](#sse-route-paths-and-proxy-usage)
5. [Tier Configuration Usage](#tier-configuration-usage)
6. [Secrets and Security](#secrets-and-security)
7. [Pre-Deployment Checklist](#pre-deployment-checklist)

---

## Startup Commands

### Backend (FastAPI)

**Development:**
```bash
# Linux/Mac
./start_backend.sh
# OR
uv run python api_server.py

# Windows PowerShell
.\start_backend.ps1
# OR
uv run python api_server.py
```

**Production (Docker):**
```bash
docker-compose up backend
# OR
docker build -t content-crew-backend .
docker run -p 8000:8000 content-crew-backend
```

**Key Details:**
- Entry point: `api_server.py`
- Default port: `8000` (reads from `PORT` env var if set)
- Uses `uv` package manager for dependency management
- Requires Python 3.10-3.13 (3.14 not supported)

### Frontend (Next.js)

**Development:**
```bash
# Linux/Mac
cd web-ui
npm run dev

# Windows PowerShell
cd web-ui
npm run dev
```

**Production (Docker):**
```bash
docker-compose up frontend
# OR
cd web-ui
docker build -t content-crew-frontend .
docker run -p 3000:3000 content-crew-frontend
```

**Key Details:**
- Entry point: `web-ui/package.json` → `npm run dev` (dev) or `npm start` (prod)
- Default port: `3000` (reads from `PORT` env var if set)
- Uses Next.js 14 App Router
- Requires Node.js 18.x or higher

### Combined Startup (Helper Scripts)

**Linux/Mac:**
```bash
./start_ui.sh  # Starts both backend and frontend
```

**Windows PowerShell:**
```powershell
.\start_ui.ps1  # Starts both backend and frontend
```

---

## Environment Variables

### Backend Environment Variables

**Location**: Centralized in `src/content_creation_crew/config.py` with validation

**Configuration Module**: All environment variables are now read through the `config` module (`src/content_creation_crew/config.py`), which:
- Validates required variables at startup
- Fails fast in staging/prod if required vars are missing
- Provides safe defaults for development only
- Loads `.env` file only in development mode

**Required Variables:**

| Variable | Required | Default (Dev) | Production Required | Description | Location Read |
|----------|----------|---------------|---------------------|-------------|---------------|
| `ENV` | ✅ **YES** | `dev` | ✅ **YES** | Environment: `dev`, `staging`, or `prod` | `src/content_creation_crew/config.py` |
| `SECRET_KEY` | ✅ **YES** | None (warns) | ✅ **YES** | JWT secret key (min 32 chars) | `src/content_creation_crew/config.py` |
| `DATABASE_URL` | ✅ **YES** | None (required) | ✅ **YES** (PostgreSQL) | PostgreSQL connection string | `src/content_creation_crew/config.py` |
| `OLLAMA_BASE_URL` | ✅ **YES** | `http://localhost:11434` | ✅ **YES** | Ollama LLM runtime URL | `src/content_creation_crew/config.py` |

**Optional Variables:**

| Variable | Required | Default | Description | Location Read |
|----------|----------|---------|-------------|---------------|
| `REDIS_URL` | No | None | Redis cache URL (optional) | `src/content_creation_crew/config.py` |
| `PORT` | No | `8000` | Backend server port | `src/content_creation_crew/config.py` |
| `LOG_LEVEL` | No | `INFO` | Logging level: DEBUG, INFO, WARNING, ERROR | `src/content_creation_crew/config.py` |
| `FRONTEND_CALLBACK_URL` | No | `http://localhost:3000/auth/callback` | OAuth callback URL | `src/content_creation_crew/config.py` |
| `API_BASE_URL` | No | `http://localhost:8000` | Backend API base URL | `src/content_creation_crew/config.py` |
| `CORS_ORIGINS` | No | `http://localhost:3000,http://127.0.0.1:3000` | CORS allowed origins (comma-separated) | `src/content_creation_crew/config.py` |
| `GOOGLE_CLIENT_ID` | No | None | Google OAuth client ID | `src/content_creation_crew/config.py` |
| `GOOGLE_CLIENT_SECRET` | No | None | Google OAuth client secret | `src/content_creation_crew/config.py` |
| `FACEBOOK_CLIENT_ID` | No | None | Facebook OAuth client ID | `src/content_creation_crew/config.py` |
| `FACEBOOK_CLIENT_SECRET` | No | None | Facebook OAuth client secret | `src/content_creation_crew/config.py` |
| `GITHUB_CLIENT_ID` | No | None | GitHub OAuth client ID | `src/content_creation_crew/config.py` |
| `GITHUB_CLIENT_SECRET` | No | None | GitHub OAuth client secret | `src/content_creation_crew/config.py` |
| `STRIPE_WEBHOOK_SECRET` | No | None | Stripe webhook secret (future) | `src/content_creation_crew/config.py` |
| `PAYSTACK_WEBHOOK_SECRET` | No | None | Paystack webhook secret (future) | `src/content_creation_crew/config.py` |
| `BUILD_VERSION` | No | `dev` | Build version (set in CI/CD) | `src/content_creation_crew/config.py` |
| `BUILD_COMMIT` | No | `unknown` | Git commit hash (set in CI/CD) | `src/content_creation_crew/config.py` |
| `BUILD_TIME` | No | Empty | Build timestamp (set in CI/CD) | `src/content_creation_crew/config.py` |

**Validation Rules:**
- **Development (`ENV=dev`)**: Warns on missing/invalid vars but continues
- **Staging/Production (`ENV=staging` or `ENV=prod`)**: 
  - Fails fast if `SECRET_KEY` is missing or < 32 chars
  - Fails fast if `SECRET_KEY` is default value
  - Fails fast if `DATABASE_URL` is missing or not PostgreSQL
  - Fails fast if URLs don't use HTTPS
  - Fails fast if `CORS_ORIGINS` doesn't include HTTPS origins

**LiteLLM Configuration (Auto-set):**
- `LITELLM_DISABLE_PROXY=1` (set in `api_server.py:20`)
- `LITELLM_REQUEST_TIMEOUT=1800` (30 minutes, set in `api_server.py:23`)
- `LITELLM_TIMEOUT=1800` (set in `api_server.py:24`)
- `LITELLM_CONNECTION_TIMEOUT=1800` (set in `api_server.py:25`)

**Python Path Configuration:**
- `PYTHONPATH` should include `/app/src:/app` in Docker (set in Dockerfile)
- Fallback paths added in `api_server.py:109-116`

### Frontend Environment Variables

**Location**: Validated in `web-ui/lib/env.ts`, used throughout frontend

**Configuration Module**: Environment variables are validated via `web-ui/lib/env.ts`:
- Validates `NEXT_PUBLIC_API_URL` at build time
- Warns in development if missing
- Fails in production if missing
- Validates HTTPS in production

**Required Variables:**

| Variable | Required | Default (Dev) | Production Required | Description | Location Read |
|----------|----------|---------------|---------------------|-------------|---------------|
| `NEXT_PUBLIC_API_URL` | ⚠️ **YES** (for prod) | `http://localhost:8000` | ✅ **YES** | Backend API URL | `web-ui/lib/env.ts`, `web-ui/app/api/generate/route.ts` |

**Optional Variables:**

| Variable | Required | Default | Description | Location Read |
|----------|----------|---------|-------------|---------------|
| `PORT` | No | `3000` | Frontend server port | Next.js default |
| `NODE_ENV` | No | `development` | Node environment | Next.js default |

**Build-Time Configuration:**
- Set via `ARG` in `web-ui/Dockerfile:20,42`
- Must be set before `npm run build` for production builds
- Validated via `web-ui/lib/env.ts` on import

**Validation:**
- Development: Warns if `NEXT_PUBLIC_API_URL` not set, uses default
- Production: Throws error if `NEXT_PUBLIC_API_URL` not set
- Production: Warns if URL doesn't use HTTPS

---

## Database Dependencies

### Current Database: PostgreSQL Only

**Status**: ✅ **PostgreSQL Required**

**Configuration:**
- Connection: PostgreSQL only (via `DATABASE_URL` environment variable)
- Format: `postgresql://user:password@host:port/database`
- ORM: SQLAlchemy 2.0+
- Migration tool: Alembic

**Database Requirements:**
- **✅ REQUIRED**: `DATABASE_URL` must be set and must be a PostgreSQL connection string
- Application fails to start if `DATABASE_URL` is missing or not PostgreSQL
- SQLite is no longer supported

### Migration Status

**Alembic Configuration:**
- Config file: `alembic.ini` (URL set from `DATABASE_URL` env var in `alembic/env.py`)
- Migration directory: `alembic/versions/`
- All migrations use PostgreSQL-specific features (JSONB, etc.)

**Migration Execution:**
- Auto-run on startup: `api_server.py:140` calls `init_db()`
- `init_db()` runs: `alembic upgrade head`
- Migrations are the single source of truth for schema

**PostgreSQL Features Used:**
- ✅ JSONB columns for structured data (`content_json`, `payload_json`)
- ✅ Proper indexes on foreign keys and frequently queried columns
- ✅ Connection pooling optimized for PostgreSQL
- ✅ Health checks and error handling included

### Database Schema

**Current Tables (from migration):**
1. `users` - User accounts (email, password hash, OAuth info)
2. `sessions` - User sessions (for future token blacklisting)

**Defined but Not Migrated:**
1. `subscription_tiers` - Tier definitions (loaded from YAML, not DB)
2. `user_subscriptions` - User subscription records (future implementation)
3. `usage_tracking` - Usage tracking records (future implementation)

**⚠️ ISSUE**: `subscription_tiers` table is referenced in code but:
- Data is loaded from `tiers.yaml` file, not database
- Table creation migration doesn't exist
- `subscription_routes.py` tries to sync YAML → DB but table may not exist

---

## SSE Route Paths and Proxy Usage

### Backend SSE Endpoint

**Route**: `POST /api/generate`

**Location**: `api_server.py:968-1084`

**Response Type**: `StreamingResponse` with `text/event-stream`

**Key Details:**
- Uses Server-Sent Events (SSE) format
- Streams content chunks in real-time
- Sends keep-alive messages every 15 seconds
- Returns JSON events: `status`, `content`, `complete`, `error`

**Authentication:**
- Requires JWT token via `Depends(get_current_user)`
- Token extracted from `Authorization: Bearer <token>` header

**Request Body:**
```json
{
  "topic": "string",
  "content_types": ["blog", "social", "audio", "video"]  // Optional
}
```

### Frontend Proxy (Next.js API Route)

**Route**: `POST /api/generate`

**Location**: `web-ui/app/api/generate/route.ts`

**Purpose**: Proxies SSE stream from FastAPI to frontend client

**Key Details:**
- Next.js API route acts as proxy
- Reads `NEXT_PUBLIC_API_URL` or defaults to `http://localhost:8000`
- Forwards request to `${API_URL}/api/generate`
- Streams SSE response back to client
- Handles authentication via cookies (`auth_token`)
- Timeout: 30 minutes (`maxDuration = 1800`)

**Proxy Flow:**
```
Client → Next.js /api/generate → FastAPI /api/generate → Ollama
         (SSE proxy)              (SSE stream)          (LLM)
```

**Authentication Flow:**
1. Client sends request to Next.js API route
2. Next.js extracts `auth_token` from cookies
3. Next.js forwards request with `Authorization: Bearer <token>` header
4. FastAPI validates token and processes request

**⚠️ ISSUE**: Next.js API route uses `process.env.API_URL` (line 3) but should use `NEXT_PUBLIC_API_URL` for consistency. Currently has fallback to `http://localhost:8000`.

### Client-Side SSE Consumption

**Location**: `web-ui/app/page.tsx:49-325`

**Implementation:**
- Uses `fetch()` with `response.body.getReader()`
- Parses SSE format: `data: {...}\n\n`
- Handles events: `status`, `content`, `complete`, `error`
- Updates UI in real-time as content streams

**Endpoint Called:**
- `fetch('/api/generate', ...)` - Calls Next.js proxy route
- Not directly calling FastAPI (proxied through Next.js)

---

## Tier Configuration Usage

### Configuration File

**Location**: `src/content_creation_crew/config/tiers.yaml`

**Structure:**
- Defines 4 tiers: `free`, `basic`, `pro`, `enterprise`
- Each tier has: `features`, `limits`, `content_types`, `model`, `max_parallel_tasks`

### Loading Mechanism

**Backend Loading:**
1. **CrewAI Crew** (`src/content_creation_crew/crew.py:84-96`):
   - Loads via `_load_tier_config()` method
   - Path: `Path(__file__).parent / "config" / "tiers.yaml"`
   - Used for: Model selection, parallel task configuration

2. **Subscription Service** (`src/content_creation_crew/services/subscription_service.py:22-29`):
   - Loads via `_load_tier_config()` method
   - Path: `Path(__file__).parent.parent / "config" / "tiers.yaml"`
   - Used for: Tier access checks, feature gating, usage limits

3. **Subscription Routes** (`src/content_creation_crew/subscription_routes.py:84-99`):
   - Loads YAML directly for API endpoints
   - Syncs YAML → Database (if `subscription_tiers` table exists)

### Middleware Usage

**Location**: `src/content_creation_crew/middleware/tier_middleware.py`

**Decorators Available:**
1. `@require_tier(*allowed_tiers)` - Requires specific tier(s)
2. `@check_content_type_access(content_type)` - Checks content type access
3. `@check_feature_access(feature)` - Checks feature access

**Current Usage:**
- **⚠️ NOT USED**: Middleware decorators are defined but not applied to any routes
- Tier checks are done manually in `api_server.py:1000-1025` via `SubscriptionService`
- Middleware exists but is not integrated

### Tier Assignment

**Current Implementation:**
- All users default to `'free'` tier (`subscription_service.py:51`)
- No subscription management implemented yet
- Tier is cached in `UserCache` for performance

**Future Implementation:**
- `UserSubscription` table exists in schema but not used
- Subscription management code is commented out
- Payment integration fields exist but not implemented

---

## Secrets and Security

### Hardcoded Secrets

**⚠️ CRITICAL ISSUES:**

1. **Docker Compose Defaults** (`docker-compose.yml:35`):
   ```yaml
   SECRET_KEY: ${SECRET_KEY:-your-secret-key-change-in-production-min-32-chars}
   ```
   - Default value is a placeholder, not secure
   - **MUST CHANGE**: Use strong random key in production

2. **PostgreSQL Default Password** (`docker-compose.yml:10`):
   ```yaml
   POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-contentcrew123}
   ```
   - Default password is weak and predictable
   - **MUST CHANGE**: Use strong password in production

3. **Alembic Config** (`alembic.ini:61`):
   ```ini
   # sqlalchemy.url is set from DATABASE_URL env var in alembic/env.py
   ```
   - Hardcoded SQLite URL (not a secret, but should use env var)

### Missing Secrets

**✅ VALIDATED**: Config module now validates required secrets at startup

**Required but May Be Missing:**

1. **SECRET_KEY**:
   - Required for JWT token signing
   - Must be minimum 32 characters
   - **✅ VALIDATED**: Config module fails fast in staging/prod if missing or invalid
   - **✅ VALIDATED**: Fails if default placeholder value is used in non-dev environments

2. **OAuth Credentials**:
   - `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`
   - `FACEBOOK_CLIENT_ID` / `FACEBOOK_CLIENT_SECRET`
   - `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET`
   - Optional but needed for OAuth features
   - **✅ VALIDATED**: Not required, but validated if provided

3. **Database Credentials** (if using PostgreSQL):
   - `DATABASE_URL` must contain credentials
   - Should be provided by managed database service
   - **✅ VALIDATED**: Config module fails fast if DATABASE_URL is missing or not PostgreSQL

### Security Considerations

**✅ Good Practices:**
- Passwords hashed with bcrypt
- JWT tokens with expiration (7 days)
- CORS configured via `config.CORS_ORIGINS` (validated in staging/prod)
- SQL injection prevented via SQLAlchemy ORM
- **✅ NEW**: Structured logging with request IDs for traceability
- **✅ NEW**: Environment-based validation (strict in staging/prod)
- **✅ NEW**: HTTPS validation for URLs in staging/prod

**⚠️ Issues:**
- Default secrets in Docker Compose (validated but still need to change)
- No rate limiting implemented
- No token blacklisting (Sessions table exists but not used)
- CORS origins need production URLs (validated in staging/prod)

---

## Pre-Deployment Checklist

### Critical (Must Fix Before Deploy)

- [x] **✅ SECRET_KEY**: Config module validates and fails fast if missing/invalid
- [x] **Database**: PostgreSQL-only (SQLite removed, validated - fails if not PostgreSQL)
- [ ] **Database Migrations**: Create missing migrations for `subscription_tiers`, `user_subscriptions`, `usage_tracking`
- [x] **✅ CORS Origins**: Config module validates HTTPS origins in staging/prod
- [x] **✅ Environment Variables**: Centralized config with validation (fails fast in staging/prod)
- [ ] **Ollama**: Deploy Ollama service or configure cloud LLM API
- [ ] **Docker Secrets**: Remove default passwords from `docker-compose.yml` (still need manual change)
- [x] **✅ Frontend API URL**: Validated via `web-ui/lib/env.ts` (fails in prod if missing)

### Important (Should Fix Before Deploy)

- [x] **✅ Alembic Config**: Application uses `DATABASE_URL` from config (Alembic can use env override)
- [x] **✅ Next.js API Route**: Fixed to use `NEXT_PUBLIC_API_URL` via `web-ui/lib/env.ts`
- [ ] **Tier Middleware**: Integrate middleware decorators or remove unused code
- [ ] **Subscription Tables**: Create database migrations for subscription-related tables
- [x] **✅ Health Checks**: Enhanced `/health` endpoint checks DB + cache + Ollama
- [x] **✅ Logging**: Structured logging with request IDs and environment labels implemented
- [x] **✅ Meta Endpoint**: Added `/meta` endpoint for build version and deployment info

### Nice to Have (Can Fix After Deploy)

- [ ] **Rate Limiting**: Implement rate limiting per tier
- [ ] **Token Blacklisting**: Implement token revocation using Sessions table
- [ ] **Monitoring**: Set up application monitoring (Sentry, DataDog, etc.)
- [ ] **Caching**: Consider Redis for distributed caching (currently in-memory)
- [ ] **CDN**: Configure CDN for static assets
- [ ] **SSL/TLS**: Ensure HTTPS is configured
- [ ] **Backup Strategy**: Set up database backups

### Configuration Files to Review

- [ ] `alembic.ini` - Database URL configuration
- [ ] `docker-compose.yml` - Default secrets and passwords
- [ ] `api_server.py` - CORS origins, port configuration
- [ ] `web-ui/app/api/generate/route.ts` - API URL configuration
- [ ] `src/content_creation_crew/config/tiers.yaml` - Tier definitions

---

## Summary

### Current State

**✅ Working:**
- Development environment fully functional
- PostgreSQL database working
- SSE streaming functional
- Tier configuration loading from YAML
- Authentication and OAuth working

**⚠️ Needs Attention:**
- Database migration to PostgreSQL
- Missing database migrations for subscription tables
- Hardcoded secrets in Docker Compose
- CORS origins need production URLs
- Environment variable inconsistencies

**❌ Blockers for Production:**
- SECRET_KEY must be set
- Database must be PostgreSQL (SQLite removed, PostgreSQL required for all environments)
- Production URLs must be configured
- Ollama service must be accessible

### Recommended Actions

1. **✅ COMPLETED**: Centralized config with validation (fails fast in staging/prod)
2. **✅ COMPLETED**: Structured logging with request IDs
3. **✅ COMPLETED**: Enhanced health check endpoint
4. **✅ COMPLETED**: Frontend env validation
5. **Before Deploy**: Migrate to PostgreSQL and create missing migrations
6. **Before Deploy**: Set `ENV=staging` or `ENV=prod` to enable strict validation
7. **Before Deploy**: Configure production environment variables (validation will catch issues)
8. **Before Deploy**: Update CORS origins and API URLs (validation ensures HTTPS in staging/prod)
9. **After Deploy**: Monitor using `/health` and `/meta` endpoints
10. **After Deploy**: Add rate limiting/security enhancements

---

**Document Version**: 1.0  
**Last Updated**: 2024  
**Next Review**: Before first production deployment

