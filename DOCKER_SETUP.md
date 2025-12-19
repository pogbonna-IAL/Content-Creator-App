# Docker Setup Guide

This guide explains how to set up and run Content Creation Crew using Docker and Docker Compose.

## Prerequisites

- Docker Desktop (Windows/Mac) or Docker Engine + Docker Compose (Linux)
- At least 4GB RAM available for Docker
- Ollama installed and running on your host machine (or use Ollama in Docker)

## Quick Start

### 1. Clone and Navigate

```bash
cd content_creation_crew
```

### 2. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and update the following:

- **SECRET_KEY**: Generate a strong random key (min 32 characters)
  ```bash
  # Generate a secret key (Linux/Mac)
  openssl rand -hex 32
  
  # Or use Python
  python -c "import secrets; print(secrets.token_hex(32))"
  ```

- **OAuth Credentials** (Optional): Add your OAuth client IDs and secrets if you want OAuth login

- **OLLAMA_BASE_URL**: 
  - **Docker Desktop (Windows/Mac)**: `http://host.docker.internal:11434`
  - **Linux**: `http://host.docker.internal:11434` or `http://ollama:11434` if using Ollama in Docker

### 3. Start Ollama (if not already running)

**Option A: Use Ollama on Host Machine**
- Install Ollama on your host machine
- Start Ollama: `ollama serve`
- Pull required models:
  ```bash
  ollama pull llama3.2:1b
  ollama pull llama3.2:3b
  ollama pull llama3.1:8b
  ```

**Option B: Use Ollama in Docker** (Uncomment ollama service in docker-compose.yml)
- Uncomment the `ollama` service in `docker-compose.yml`
- After starting, pull models:
  ```bash
  docker exec content-crew-ollama ollama pull llama3.2:1b
  ```

### 4. Build and Start Services

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db
```

### 5. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Health Check**: http://localhost:8000/health
- **Database**: localhost:5432 (PostgreSQL)

### 6. Initialize Database

The database will be automatically initialized on first startup. If you need to run migrations manually:

```bash
docker-compose exec backend alembic upgrade head
```

## Service Details

### Backend Service
- **Port**: 8000
- **Health Check**: http://localhost:8000/health
- **Logs**: `docker-compose logs -f backend`

### Frontend Service
- **Port**: 3000
- **Health Check**: http://localhost:3000
- **Logs**: `docker-compose logs -f frontend`

### Database Service
- **Port**: 5432
- **User**: contentcrew (default)
- **Password**: contentcrew123 (default - change in production!)
- **Database**: content_crew
- **Persistent Volume**: `postgres_data`

## Common Commands

### Start Services
```bash
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

### Stop and Remove Volumes (⚠️ Deletes Database)
```bash
docker-compose down -v
```

### Rebuild Services
```bash
docker-compose build --no-cache
docker-compose up -d
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db
```

### Execute Commands in Containers
```bash
# Backend shell
docker-compose exec backend bash

# Run migrations
docker-compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "description"

# Frontend shell
docker-compose exec frontend sh
```

### Check Service Status
```bash
docker-compose ps
```

### Restart a Service
```bash
docker-compose restart backend
docker-compose restart frontend
```

## Troubleshooting

### Backend Won't Start

1. **Check Database Connection**:
   ```bash
   docker-compose logs db
   docker-compose logs backend
   ```

2. **Verify Database is Healthy**:
   ```bash
   docker-compose ps
   # db service should show "healthy"
   ```

3. **Check Environment Variables**:
   ```bash
   docker-compose exec backend env | grep DATABASE_URL
   ```

### Frontend Can't Connect to Backend

1. **Check NEXT_PUBLIC_API_URL**:
   ```bash
   docker-compose exec frontend env | grep NEXT_PUBLIC_API_URL
   ```
   Should be: `http://localhost:8000` (for localhost access) or `http://backend:8000` (for internal Docker network)

2. **Update docker-compose.yml**:
   If accessing from browser, use `http://localhost:8000`
   If frontend needs internal access, use `http://backend:8000`

### Ollama Connection Issues

1. **Check Ollama is Running**:
   ```bash
   curl http://localhost:11434/api/tags
   ```

2. **For Docker Desktop (Windows/Mac)**:
   Use `host.docker.internal:11434` in OLLAMA_BASE_URL

3. **For Linux**:
   Add `network_mode: host` to backend service or use `host.docker.internal` if available

### Database Connection Issues

1. **Check PostgreSQL is Running**:
   ```bash
   docker-compose ps db
   ```

2. **Verify Connection String**:
   ```bash
   docker-compose exec backend python -c "import os; print(os.getenv('DATABASE_URL'))"
   ```

3. **Reset Database** (⚠️ Deletes all data):
   ```bash
   docker-compose down -v
   docker-compose up -d
   ```

### Port Already in Use

If ports 3000, 8000, or 5432 are already in use:

1. **Change ports in docker-compose.yml**:
   ```yaml
   ports:
     - "3001:3000"  # Frontend on 3001
     - "8001:8000"  # Backend on 8001
     - "5433:5432"  # Database on 5433
   ```

2. **Update .env**:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8001
   ```

## Production Considerations

### Security

1. **Change Default Passwords**:
   - Update `POSTGRES_PASSWORD` in `.env`
   - Use strong `SECRET_KEY`

2. **Use Environment Variables**:
   - Never commit `.env` file
   - Use Docker secrets or environment variables in production

3. **HTTPS**:
   - Use reverse proxy (nginx/traefik) with SSL certificates
   - Update CORS settings in `api_server.py`

### Performance

1. **Database Optimization**:
   - Use PostgreSQL connection pooling
   - Consider read replicas for high traffic

2. **Caching**:
   - Add Redis for distributed caching
   - Configure content cache TTL

3. **Resource Limits**:
   Add to docker-compose.yml:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 2G
       reservations:
         cpus: '1'
         memory: 1G
   ```

### Monitoring

1. **Health Checks**: Already configured in docker-compose.yml
2. **Logging**: Configure log aggregation (ELK, Loki, etc.)
3. **Metrics**: Add Prometheus/Grafana for monitoring

## Development vs Production

### Development
- Use volume mounts for live code reloading
- Enable debug logging
- Use SQLite for simplicity

### Production
- Build optimized images
- Use PostgreSQL
- Disable debug logging
- Use reverse proxy
- Enable HTTPS
- Set up monitoring and alerting

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)
- [Next.js Docker Deployment](https://nextjs.org/docs/deployment#docker-image)

