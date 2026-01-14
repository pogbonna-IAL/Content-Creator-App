# First-Time Deployment Guide

**Content Creation Crew - Production Deployment**

This guide walks you through deploying the Content Creation Crew application to production for the first time.

---

## Prerequisites

### System Requirements
- **Server:** Ubuntu 22.04 LTS or later (recommended)
- **RAM:** Minimum 8GB, recommended 16GB+
- **CPU:** Minimum 4 cores, recommended 8+ cores
- **Disk:** Minimum 100GB SSD
- **Docker:** 24.0+ with Docker Compose v2
- **Network:** Public IP with ports 80, 443 open

### Required Accounts & Keys
- [ ] Stripe account (for payments)
- [ ] Paystack account (optional, for Nigeria)
- [ ] AWS account (if using S3 for storage)
- [ ] Domain name with DNS access
- [ ] SSL certificate (Let's Encrypt recommended)

---

## Step 1: Server Setup

### 1.1 Update System
```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y \
    curl \
    wget \
    git \
    build-essential \
    postgresql-client \
    redis-tools
```

### 1.2 Install Docker
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker compose version
```

### 1.3 Configure Firewall
```bash
# Allow SSH, HTTP, HTTPS
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

---

## Step 2: Clone Repository

```bash
# Clone the repository
git clone https://github.com/your-org/content-creation-crew.git
cd content-creation-crew

# Checkout the release tag
git checkout v1.0.0  # Use your release version
```

---

## Step 3: Environment Configuration

### 3.1 Create Production Environment File
```bash
cp .env.example .env
```

### 3.2 Edit .env with Production Values
```bash
nano .env
```

**Required Configuration:**

```bash
# ===================================
# CORE CONFIGURATION
# ===================================
NODE_ENV=production
SECRET_KEY=<generate-with-openssl-rand-hex-32>

# ===================================
# DATABASE
# ===================================
DATABASE_URL=postgresql://produser:STRONG_PASSWORD@postgres:5432/content_crew_prod
DATABASE_USER=produser
DATABASE_PASSWORD=<generate-strong-password>
DATABASE_NAME=content_crew_prod
DATABASE_PORT=5432

# ===================================
# REDIS
# ===================================
REDIS_URL=redis://:REDIS_PASSWORD@redis:6379/0
REDIS_PASSWORD=<generate-strong-password>
REDIS_PORT=6379

# ===================================
# API CONFIGURATION
# ===================================
API_PORT=8000
API_BASE_URL=https://api.yourdomain.com
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# ===================================
# WEB CONFIGURATION
# ===================================
WEB_PORT=3000
NEXT_PUBLIC_API_URL=https://api.yourdomain.com

# ===================================
# PAYMENT PROVIDERS
# ===================================
STRIPE_SECRET_KEY=sk_live_xxxxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx

PAYSTACK_SECRET_KEY=sk_live_xxxxx
PAYSTACK_PUBLIC_KEY=pk_live_xxxxx

# ===================================
# OLLAMA (LLM)
# ===================================
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=mistral:latest

# ===================================
# FEATURES
# ===================================
ENABLE_VIDEO_RENDERING=true
ENABLE_TTS=true
ENABLE_OLLAMA=true

# ===================================
# STORAGE
# ===================================
STORAGE_PROVIDER=s3  # or 'local'
STORAGE_PATH=./storage

# S3 Configuration (if using S3)
S3_BUCKET=content-crew-prod
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# ===================================
# EMAIL
# ===================================
EMAIL_PROVIDER=smtp
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your_sendgrid_api_key
EMAIL_FROM=noreply@yourdomain.com

# ===================================
# SECURITY
# ===================================
BCRYPT_ROUNDS=12
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120
GDPR_DELETION_GRACE_DAYS=30

# ===================================
# MONITORING
# ===================================
SENTRY_DSN=https://xxxxx@sentry.io/xxxxx  # Optional
LOG_LEVEL=INFO

# ===================================
# BILLING & COMPLIANCE
# ===================================
PRORATION_ENABLED=true
CREDIT_NOTES_ENABLED=true
MULTI_CURRENCY_ENABLED=true
USAGE_BILLING_ENABLED=true
PAYMENT_PLANS_ENABLED=true
CHARGEBACK_HANDLING_ENABLED=true

EXCHANGE_RATE_API_KEY=your_api_key
EXCHANGE_RATE_PROVIDER=exchangerate-api

# ===================================
# RETENTION & CLEANUP
# ===================================
RETENTION_DAYS_FREE=30
RETENTION_DAYS_BASIC=90
RETENTION_DAYS_PRO=365
RETENTION_DAYS_ENTERPRISE=-1
RETENTION_DRY_RUN=false
RETENTION_NOTIFY_ENABLED=true

# ===================================
# RATE LIMITING
# ===================================
RATE_LIMIT_ENABLED=true
MAX_REQUEST_BYTES=2097152  # 2MB
MAX_UPLOAD_BYTES=52428800  # 50MB
```

**Generate Secure Keys:**
```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate database password
openssl rand -base64 32

# Generate Redis password
openssl rand -base64 32
```

---

## Step 4: SSL Certificate Setup

### Option A: Let's Encrypt (Recommended)
```bash
# Install certbot
sudo apt-get install -y certbot

# Generate certificate
sudo certbot certonly --standalone \
    -d yourdomain.com \
    -d www.yourdomain.com \
    -d api.yourdomain.com

# Copy certificates
sudo mkdir -p infra/nginx/ssl
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem infra/nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem infra/nginx/ssl/
sudo chmod 644 infra/nginx/ssl/*.pem
```

### Option B: Custom Certificate
```bash
mkdir -p infra/nginx/ssl
cp your-certificate.crt infra/nginx/ssl/fullchain.pem
cp your-private-key.key infra/nginx/ssl/privkey.pem
chmod 644 infra/nginx/ssl/*.pem
```

---

## Step 5: Nginx Configuration

Create `infra/nginx/nginx.conf`:

```nginx
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    keepalive_timeout 65;
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;

    # API Server
    upstream api_backend {
        server api:8000;
    }

    # Web Server
    upstream web_backend {
        server web:3000;
    }

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com api.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    # Main Website
    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        client_max_body_size 50M;

        location / {
            proxy_pass http://web_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
        }
    }

    # API Server
    server {
        listen 443 ssl http2;
        server_name api.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        client_max_body_size 50M;

        location / {
            limit_req zone=api_limit burst=20 nodelay;
            
            proxy_pass http://api_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
            
            # Timeouts for long-running requests (SSE)
            proxy_read_timeout 300s;
            proxy_connect_timeout 75s;
        }

        location /api/auth/login {
            limit_req zone=login_limit burst=5 nodelay;
            proxy_pass http://api_backend;
        }

        location /health {
            access_log off;
            proxy_pass http://api_backend;
        }
    }
}
```

---

## Step 6: Build Docker Images

```bash
# Build API image
docker build -f Dockerfile.api -t content-crew-api:v1.0.0 .

# Build Web image
docker build -f Dockerfile.web -t content-crew-web:v1.0.0 .

# Verify images
docker images | grep content-crew
```

---

## Step 7: Database Setup

### 7.1 Start Database Services
```bash
docker compose -f docker-compose.prod.yml up -d postgres redis
```

### 7.2 Wait for Services
```bash
# Wait for Postgres
docker compose -f docker-compose.prod.yml exec postgres pg_isready

# Wait for Redis
docker compose -f docker-compose.prod.yml exec redis redis-cli ping
```

### 7.3 Run Migrations
```bash
# Run Alembic migrations
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
```

### 7.4 Create Admin User (Optional)
```bash
docker compose -f docker-compose.prod.yml run --rm api python -c "
from src.content_creation_crew.database import get_db, User, Organization
from src.content_creation_crew.auth import get_password_hash
db = next(get_db())
admin = User(
    email='admin@yourdomain.com',
    hashed_password=get_password_hash('CHANGE_THIS_PASSWORD'),
    email_verified=True
)
db.add(admin)
db.commit()
print('Admin user created')
"
```

---

## Step 8: Start All Services

```bash
# Start all services
docker compose -f docker-compose.prod.yml up -d

# Verify all services are running
docker compose -f docker-compose.prod.yml ps

# Check logs
docker compose -f docker-compose.prod.yml logs -f
```

---

## Step 9: Health Checks

```bash
# Check API health
curl https://api.yourdomain.com/health

# Expected response:
# {
#   "status": "ok",
#   "components": {
#     "database": "ok",
#     "redis": "ok",
#     "storage": "ok"
#   }
# }

# Check website
curl -I https://yourdomain.com

# Expected: HTTP/2 200
```

---

## Step 10: Configure Webhooks

### Stripe Webhooks
1. Go to https://dashboard.stripe.com/webhooks
2. Add endpoint: `https://api.yourdomain.com/api/webhooks/stripe`
3. Select events:
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `charge.dispute.created`
   - `charge.dispute.updated`
   - `charge.dispute.closed`
4. Copy webhook secret to `.env` as `STRIPE_WEBHOOK_SECRET`
5. Restart API: `docker compose -f docker-compose.prod.yml restart api`

### Paystack Webhooks
1. Go to https://dashboard.paystack.com/settings/developer
2. Add webhook URL: `https://api.yourdomain.com/api/webhooks/paystack`
3. No secret needed (verified by IP)

---

## Step 11: Configure Scheduled Jobs

Scheduled jobs run automatically in the API container via APScheduler:
- Exchange rate updates (daily, midnight UTC)
- GDPR hard delete cleanup (daily, 2 AM UTC)
- Session cleanup (daily, 3 AM UTC)
- Artifact retention cleanup (daily, 4 AM UTC)
- Retention notifications (daily, 10 AM UTC)
- Dunning processing (hourly)
- Payment plan installments (hourly)

Verify jobs are running:
```bash
docker compose -f docker-compose.prod.yml logs api | grep "Scheduled job"
```

---

## Step 12: Monitoring Setup

### Prometheus & Grafana (Optional)
```bash
# Add to docker-compose.prod.yml
# See docs/monitoring.md for full setup
```

### Log Aggregation
```bash
# Logs are stored in ./logs directory
# Set up log rotation
sudo nano /etc/logrotate.d/content-crew
```

Add:
```
/path/to/content-creation-crew/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 appuser appuser
    sharedscripts
}
```

---

## Step 13: Backup Configuration

```bash
# Create backup script
chmod +x infra/scripts/create-backup.sh

# Add to crontab
crontab -e

# Add daily backup at 1 AM
0 1 * * * /path/to/content-creation-crew/infra/scripts/create-backup.sh
```

---

## Step 14: DNS Configuration

Add the following DNS records:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | @ | YOUR_SERVER_IP | 300 |
| A | www | YOUR_SERVER_IP | 300 |
| A | api | YOUR_SERVER_IP | 300 |
| CNAME | www | yourdomain.com | 300 |

---

## Step 15: Final Verification

### Checklist
- [ ] All containers running (`docker compose ps`)
- [ ] Health checks passing
- [ ] Website accessible via HTTPS
- [ ] API accessible via HTTPS
- [ ] SSL certificate valid
- [ ] Webhooks configured
- [ ] Scheduled jobs running
- [ ] Backups configured
- [ ] Monitoring setup
- [ ] Admin user created
- [ ] Test payment flow
- [ ] Test content generation

### Test Commands
```bash
# Test signup
curl -X POST https://api.yourdomain.com/api/auth/signup \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"Test123!"}'

# Test login
curl -X POST https://api.yourdomain.com/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"Test123!"}'

# Test metrics
curl https://api.yourdomain.com/metrics
```

---

## Troubleshooting

### Containers Won't Start
```bash
# Check logs
docker compose -f docker-compose.prod.yml logs

# Check specific service
docker compose -f docker-compose.prod.yml logs api

# Restart service
docker compose -f docker-compose.prod.yml restart api
```

### Database Connection Issues
```bash
# Check Postgres
docker compose -f docker-compose.prod.yml exec postgres psql -U produser -d content_crew_prod -c "\dt"

# Check Redis
docker compose -f docker-compose.prod.yml exec redis redis-cli -a $REDIS_PASSWORD ping
```

### SSL Certificate Issues
```bash
# Renew Let's Encrypt
sudo certbot renew

# Copy new certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/*.pem infra/nginx/ssl/

# Restart nginx
docker compose -f docker-compose.prod.yml restart nginx
```

---

## Next Steps

1. **Read Operations Guide:** `docs/operations.md`
2. **Set up Monitoring:** `docs/monitoring.md`
3. **Configure Backups:** `docs/backup-strategy.md`
4. **Review Security:** `docs/security.md`

---

## Support

- **Documentation:** `/docs` directory
- **Issues:** https://github.com/your-org/content-creation-crew/issues
- **Email:** support@yourdomain.com

---

**Deployment Complete! 🚀**

Your Content Creation Crew application is now running in production!

