# Target Deployment Architecture

**Date**: 2024  
**Branch**: Features  
**Purpose**: First Production Deployment Architecture

This document describes the target architecture for the first production deployment of Content Creation Crew.

---

## Table of Contents

1. [Overview](#overview)
2. [Service Architecture](#service-architecture)
3. [Infrastructure Components](#infrastructure-components)
4. [Network Architecture](#network-architecture)
5. [Data Flow](#data-flow)
6. [Environment Configuration](#environment-configuration)
7. [Deployment Options](#deployment-options)
8. [Scaling Considerations](#scaling-considerations)

---

## Overview

### Deployment Goal

Deploy Content Creation Crew as a production-ready SaaS application with:
- One backend service (FastAPI)
- One frontend service (Next.js)
- Managed PostgreSQL database
- Managed Redis cache (optional for first deploy)
- Ollama runtime (same host for staging, separate for production)
- Webhook endpoints for payment providers (Stripe/Paystack)

### Deployment Principles

1. **Simplicity First**: Start with minimal services, add complexity as needed
2. **Managed Services**: Use managed databases and caches where possible
3. **Containerization**: Docker-based deployment for consistency
4. **Environment-Based Config**: All configuration via environment variables
5. **Health Monitoring**: Health checks for all services
6. **Security**: Secrets management, HTTPS, proper authentication

---

## Service Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Internet / Users                         │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Load Balancer / CDN                      │
│              (Optional: Cloudflare, AWS ALB)                │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┴──────────────────┐
        │                                      │
        ▼                                      ▼
┌──────────────────┐                ┌──────────────────┐
│  Frontend Service │                │  Backend Service │
│   (Next.js)       │                │   (FastAPI)      │
│                   │                │                   │
│  Port: 3000       │                │  Port: 8000       │
│  Health: /        │                │  Health: /health │
└──────────────────┘                └────────┬─────────┘
                                              │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
                    ▼                        ▼                        ▼
        ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
        │   PostgreSQL     │    │      Redis       │    │     Ollama       │
        │   (Managed)      │    │   (Managed)      │    │   (Optional)     │
        │                   │    │                   │    │                   │
        │  - Users          │    │  - Content Cache │    │  - LLM Runtime   │
        │  - Sessions       │    │  - User Cache    │    │  - Models         │
        │  - Subscriptions  │    │  - Rate Limits   │    │                   │
        └──────────────────┘    └──────────────────┘    └──────────────────┘
                    │                        │                        │
                    └────────────────────────┼────────────────────────┘
                                             │
                                             ▼
                                ┌──────────────────┐
                                │  Payment Webhooks │
                                │  (Stripe/Paystack)│
                                └──────────────────┘
```

---

## Infrastructure Components

### 1. Backend Service (FastAPI)

**Service Type**: Containerized Python application

**Specifications:**
- **Runtime**: Python 3.11+ (slim image)
- **Framework**: FastAPI with Uvicorn
- **Port**: 8000 (configurable via `PORT` env var)
- **Health Check**: `GET /health`
- **Resource Requirements**:
  - CPU: 1-2 cores (minimum)
  - Memory: 512MB-1GB (minimum)
  - Storage: Minimal (stateless)

**Key Features:**
- RESTful API endpoints
- Server-Sent Events (SSE) streaming
- JWT authentication
- OAuth integration
- Content generation orchestration

**Environment Variables Required:**
- `SECRET_KEY` - JWT signing key
- `DATABASE_URL` - PostgreSQL connection string
- `OLLAMA_BASE_URL` - Ollama service URL
- `FRONTEND_CALLBACK_URL` - OAuth callback URL
- `API_BASE_URL` - Backend API URL
- `CORS_ORIGINS` - Allowed frontend origins
- OAuth credentials (optional)

**Deployment Options:**
- Docker container
- Railway, Render, Fly.io
- AWS ECS/Fargate, Google Cloud Run
- Kubernetes deployment

### 2. Frontend Service (Next.js)

**Service Type**: Containerized Node.js application

**Specifications:**
- **Runtime**: Node.js 20+ (Alpine image)
- **Framework**: Next.js 14 (App Router)
- **Port**: 3000 (configurable via `PORT` env var)
- **Health Check**: `GET /` (or custom endpoint)
- **Resource Requirements**:
  - CPU: 0.5-1 core (minimum)
  - Memory: 256MB-512MB (minimum)
  - Storage: Minimal (static assets)

**Key Features:**
- React-based UI
- Server-Side Rendering (SSR)
- API route proxying for SSE
- Cookie-based authentication

**Environment Variables Required:**
- `NEXT_PUBLIC_API_URL` - Backend API URL (build-time)
- `PORT` - Server port (runtime)
- `NODE_ENV` - Environment (production)

**Deployment Options:**
- Docker container
- Vercel (optimized for Next.js)
- Railway, Render, Netlify
- AWS Amplify, Google Cloud Run

### 3. PostgreSQL Database (Managed)

**Service Type**: Managed PostgreSQL service

**Specifications:**
- **Version**: PostgreSQL 14+ (16 recommended)
- **Storage**: 10GB+ (scales as needed)
- **Backups**: Automated daily backups
- **High Availability**: Multi-AZ for production

**Schema:**
- `users` - User accounts
- `sessions` - User sessions
- `subscription_tiers` - Tier definitions
- `user_subscriptions` - User subscriptions (future)
- `usage_tracking` - Usage records (future)

**Connection:**
- Connection string provided via `DATABASE_URL`
- Connection pooling configured in application
- SSL/TLS required for production

**Managed Service Options:**
- Railway PostgreSQL
- AWS RDS PostgreSQL
- Google Cloud SQL
- Supabase, Neon, PlanetScale
- Docker Compose (for staging only)

### 4. Redis Cache (Managed) - Optional for First Deploy

**Service Type**: Managed Redis service

**Specifications:**
- **Version**: Redis 6+ (7 recommended)
- **Memory**: 256MB+ (scales as needed)
- **Persistence**: Optional (AOF or RDB)

**Use Cases:**
- Content caching (currently in-memory)
- User tier caching
- Rate limiting counters
- Session storage (future)

**Current State:**
- Application uses in-memory caching
- Can be added post-deployment
- Not required for first deploy

**Managed Service Options:**
- Railway Redis
- AWS ElastiCache
- Google Cloud Memorystore
- Upstash, Redis Cloud
- Docker Compose (for staging only)

### 5. Ollama Runtime

**Service Type**: LLM runtime service

**Specifications:**
- **Runtime**: Ollama server
- **Port**: 11434
- **Models**: llama3.2:1b, llama3.2:3b, llama3.1:8b, llama3.1:70b
- **Resource Requirements**:
  - CPU: 2-4 cores (varies by model)
  - Memory: 2GB-16GB (varies by model)
  - GPU: Optional but recommended for larger models

**Deployment Options:**

**Staging (Same Host):**
- Deploy Ollama in same Docker Compose network
- Accessible via `http://ollama:11434` (internal)
- Shared resources with backend

**Production (Separate Host):**
- Dedicated Ollama service/container
- Accessible via `https://ollama.yourdomain.com:11434` (external)
- Isolated resources for better performance
- Can scale independently

**Alternative: Cloud LLM APIs**
- Use OpenAI, Anthropic, or other providers via LiteLLM
- No Ollama deployment needed
- Configure via `OLLAMA_BASE_URL` or LiteLLM config

### 6. Payment Webhook Endpoints

**Service Type**: HTTP endpoints for payment providers

**Endpoints Required:**
- `POST /api/webhooks/stripe` - Stripe webhook handler
- `POST /api/webhooks/paystack` - Paystack webhook handler

**Current State:**
- **⚠️ NOT IMPLEMENTED**: Webhook endpoints don't exist yet
- Must be added before payment integration

**Requirements:**
- Verify webhook signatures
- Handle subscription events (created, updated, cancelled)
- Update user subscriptions in database
- Idempotent processing (handle duplicate events)

**Security:**
- Webhook signature verification
- Rate limiting on webhook endpoints
- Separate authentication (webhook secrets)

---

## Network Architecture

### Staging Environment

```
Internet
   │
   ▼
[Load Balancer] (Optional)
   │
   ├─── Frontend (Next.js) :3000
   │
   └─── Backend (FastAPI) :8000
           │
           ├─── PostgreSQL (Managed or Docker)
           ├─── Redis (Optional, Docker)
           └─── Ollama (Same Host, Docker) :11434
```

**Characteristics:**
- Single host/container environment
- Docker Compose for local services
- Managed PostgreSQL (or Docker)
- Ollama on same network

### Production Environment

```
Internet
   │
   ▼
[CDN / Load Balancer]
   │
   ├─── Frontend (Next.js) :3000
   │      │
   │      └─── [Multiple Instances] (Auto-scaling)
   │
   └─── Backend (FastAPI) :8000
           │
           ├─── [Multiple Instances] (Auto-scaling)
           │
           ├─── PostgreSQL (Managed, Multi-AZ)
           ├─── Redis (Managed, High Availability)
           └─── Ollama (Dedicated Service) :11434
                   │
                   └─── [Multiple Instances] (Load Balanced)
```

**Characteristics:**
- Distributed services
- Managed databases and caches
- Separate Ollama service
- Auto-scaling capabilities
- High availability

---

## Data Flow

### User Request Flow

```
1. User → Frontend (Next.js)
   │
   ▼
2. Frontend → Backend API (FastAPI)
   │  - Authentication via JWT token
   │
   ▼
3. Backend → PostgreSQL
   │  - User validation
   │  - Tier lookup
   │  - Usage tracking
   │
   ▼
4. Backend → Ollama
   │  - Content generation request
   │
   ▼
5. Ollama → Backend
   │  - Generated content (streaming)
   │
   ▼
6. Backend → Frontend
   │  - SSE stream of content
   │
   ▼
7. Frontend → User
   │  - Real-time content display
```

### Payment Webhook Flow

```
1. Stripe/Paystack → Backend Webhook Endpoint
   │  - Payment event (subscription created/updated/cancelled)
   │
   ▼
2. Backend → Verify Webhook Signature
   │
   ▼
3. Backend → PostgreSQL
   │  - Update user subscription
   │  - Update user tier
   │
   ▼
4. Backend → Redis (if implemented)
   │  - Invalidate user cache
   │
   ▼
5. Backend → Response (200 OK)
```

---

## Environment Configuration

### Backend Environment Variables

```env
# Required
SECRET_KEY=<strong-random-key-min-32-chars>
DATABASE_URL=postgresql://user:password@host:port/database
OLLAMA_BASE_URL=http://ollama:11434  # Staging (internal)
# OR
OLLAMA_BASE_URL=https://ollama.yourdomain.com:11434  # Production (external)

# Frontend URLs
FRONTEND_CALLBACK_URL=https://yourdomain.com/auth/callback
API_BASE_URL=https://api.yourdomain.com
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# OAuth (Optional)
GOOGLE_CLIENT_ID=<google-client-id>
GOOGLE_CLIENT_SECRET=<google-client-secret>
FACEBOOK_CLIENT_ID=<facebook-client-id>
FACEBOOK_CLIENT_SECRET=<facebook-client-secret>
GITHUB_CLIENT_ID=<github-client-id>
GITHUB_CLIENT_SECRET=<github-client-secret>

# Payment Webhooks (Future)
STRIPE_WEBHOOK_SECRET=<stripe-webhook-secret>
PAYSTACK_WEBHOOK_SECRET=<paystack-webhook-secret>

# Optional
PORT=8000
LOG_LEVEL=INFO
```

### Frontend Environment Variables

```env
# Required (Build-time)
NEXT_PUBLIC_API_URL=https://api.yourdomain.com

# Optional (Runtime)
PORT=3000
NODE_ENV=production
```

### Database Environment Variables

**Managed Service (Auto-provided):**
- `DATABASE_URL` - Full connection string with credentials

**Docker Compose (Manual):**
```env
POSTGRES_USER=contentcrew
POSTGRES_PASSWORD=<strong-password>
POSTGRES_DB=content_crew
```

### Redis Environment Variables (Optional)

**Managed Service:**
- `REDIS_URL` - Connection string (if implemented)

**Docker Compose:**
```env
REDIS_PASSWORD=<optional-password>
```

---

## Deployment Options

### Option 1: Railway (Recommended for First Deploy)

**Services:**
- Backend: Railway service (Python)
- Frontend: Railway service (Node.js)
- PostgreSQL: Railway PostgreSQL addon
- Redis: Railway Redis addon (optional)
- Ollama: Separate Railway service or external

**Pros:**
- Simple setup
- Managed databases
- Automatic HTTPS
- Environment variables UI
- Good for MVP

**Cons:**
- Vendor lock-in
- Limited customization
- Cost scales with usage

### Option 2: Docker Compose + Managed DB

**Services:**
- Backend + Frontend + Ollama: Docker Compose on VPS
- PostgreSQL: Managed service (Supabase, Neon, etc.)
- Redis: Managed service (Upstash, etc.)

**Pros:**
- Full control
- Cost-effective
- Flexible configuration

**Cons:**
- More setup required
- Manual scaling
- Infrastructure management

### Option 3: Cloud Platform (AWS/GCP/Azure)

**Services:**
- Backend: ECS/Fargate, Cloud Run, Container Instances
- Frontend: Amplify, Cloud Run, App Service
- PostgreSQL: RDS, Cloud SQL, Azure Database
- Redis: ElastiCache, Memorystore, Azure Cache
- Ollama: EC2/GCE/VM or separate container service

**Pros:**
- Enterprise-grade
- Auto-scaling
- High availability
- Advanced features

**Cons:**
- Complex setup
- Higher cost
- Steeper learning curve

---

## Scaling Considerations

### Horizontal Scaling

**Backend:**
- Stateless design (ready for horizontal scaling)
- Load balancer distributes requests
- Shared database and cache
- Session management via JWT (stateless)

**Frontend:**
- Static assets can be CDN-cached
- API routes are stateless
- Can scale to multiple instances

**Ollama:**
- Can run multiple instances
- Load balance requests
- Model-specific instances (small models vs large)

### Vertical Scaling

**Backend:**
- Increase CPU/memory for faster processing
- Better for CPU-intensive content generation

**Ollama:**
- GPU instances for larger models
- More memory for model loading
- Critical for performance

### Database Scaling

**Read Replicas:**
- Add read replicas for heavy read workloads
- Application can use read replicas for queries

**Connection Pooling:**
- Already configured in application
- Adjust pool size based on load

### Caching Strategy

**Current (In-Memory):**
- Per-instance cache
- Lost on restart
- Not shared across instances

**Future (Redis):**
- Shared cache across instances
- Persistent cache
- Better for multi-instance deployments

---

## Security Considerations

### Network Security

- **HTTPS**: All external traffic must use HTTPS
- **Internal Network**: Backend → Database/Redis on private network
- **Firewall**: Restrict Ollama access to backend only
- **CORS**: Configured for production domains only

### Authentication & Authorization

- **JWT Tokens**: Secure token generation and validation
- **Token Expiration**: 7-day expiration (configurable)
- **OAuth**: Secure OAuth flow with proper redirects
- **Webhook Security**: Signature verification for payment webhooks

### Data Security

- **Database Encryption**: Encrypted at rest (managed services)
- **Connection Encryption**: SSL/TLS for database connections
- **Password Hashing**: Bcrypt with SHA256 pre-hash
- **Secrets Management**: Use platform secrets management (not env files)

### Monitoring & Logging

- **Health Checks**: `/health` endpoint for monitoring
- **Error Tracking**: Integrate Sentry or similar
- **Logging**: Structured logging for production
- **Metrics**: Application metrics for monitoring

---

## Deployment Checklist

### Pre-Deployment

- [ ] Set up managed PostgreSQL database
- [ ] Configure environment variables
- [ ] Set up SSL/TLS certificates
- [ ] Configure CORS for production domains
- [ ] Set up monitoring and logging
- [ ] Test database migrations
- [ ] Verify health check endpoints

### Deployment

- [ ] Deploy backend service
- [ ] Deploy frontend service
- [ ] Configure DNS and load balancer
- [ ] Set up Ollama service (or configure cloud LLM)
- [ ] Test end-to-end functionality
- [ ] Verify authentication flow
- [ ] Test content generation

### Post-Deployment

- [ ] Monitor application logs
- [ ] Set up alerts for errors
- [ ] Configure backups
- [ ] Set up payment webhooks (when ready)
- [ ] Performance testing
- [ ] Security audit

---

## Cost Estimation (Rough)

### Staging Environment

- Backend: $5-10/month (small instance)
- Frontend: $5-10/month (small instance)
- PostgreSQL: $5-10/month (small managed DB)
- Ollama: $10-20/month (VPS or container)
- **Total**: ~$25-50/month

### Production Environment

- Backend: $20-50/month (medium instance, auto-scaling)
- Frontend: $10-30/month (medium instance, CDN)
- PostgreSQL: $20-50/month (managed, backups)
- Redis: $10-20/month (optional)
- Ollama: $50-200/month (dedicated, GPU optional)
- **Total**: ~$110-350/month (scales with usage)

---

**Document Version**: 1.0  
**Last Updated**: 2024  
**Next Review**: After first deployment

