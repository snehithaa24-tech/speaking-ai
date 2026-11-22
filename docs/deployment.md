# SAHAYAK AI Deployment Guide

## Overview

This guide covers deploying SAHAYAK AI to production environments.

## Prerequisites

- Domain name with DNS access
- Google Cloud project with Gemini API enabled
- Google OAuth credentials (optional)
- PostgreSQL database (managed service recommended)
- Container registry access (Docker Hub, GHCR, etc.)

## Environment Variables

### Required

```bash
# Gemini AI (Required)
GEMINI_API_KEY=your_gemini_api_key_from_aistudio

# Database (Required)
DATABASE_URL=postgresql://user:pass@host:5432/sahayak

# Frontend URL for CORS (Required)
FRONTEND_URL=https://sahayak.ai

# Security (Required)
SECRET_KEY=generate_with_openssl_rand_hex_32
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
```

### Optional

```bash
# Google OAuth (Optional)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Feature Flags
ENABLE_OAUTH=false
ENABLE_ADMIN_PANEL=false
ENABLE_AUDIO_RECORDING=false

# Logging
LOG_LEVEL=INFO

# Backend
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
BACKEND_WORKERS=4
```

### Generate Secret Key

```bash
openssl rand -hex 32
```

## Frontend Deployment (Vercel)

### Automatic Deployment

1. Push repository to GitHub
2. Import project in Vercel
3. Configure:
   - Framework Preset: Vite
   - Build Command: `npm run build`
   - Output Directory: `dist`
   - Install Command: `npm install`

4. Add Environment Variables:
   ```
   VITE_API_URL=https://api.yourdomain.com
   VITE_WS_URL=wss://api.yourdomain.com
   VITE_GOOGLE_CLIENT_ID=your_client_id
   ```

5. Deploy

### Manual Build

```bash
cd frontend
npm install
npm run build
# Output in dist/
```

### Vercel Configuration (`vercel.json`)

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite",
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "X-XSS-Protection", "value": "1; mode=block" }
      ]
    }
  ]
}
```

## Backend Deployment

### Option 1: Render (Recommended)

1. Create new Web Service on Render
2. Connect GitHub repository
3. Configure:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 4`
   - Environment: Python 3.12

4. Add Environment Variables (from above)

5. Add PostgreSQL Database on Render
   - Copy connection string to `DATABASE_URL`

6. Deploy

### Option 2: Railway

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login and link
railway login
railway link

# Set variables
railway variables set GEMINI_API_KEY=xxx
railway variables set DATABASE_URL=xxx
# ... etc

# Deploy
railway up
```

### Option 3: Fly.io

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

```bash
fly launch
fly secrets set GEMINI_API_KEY=xxx DATABASE_URL=xxx SECRET_KEY=xxx
fly deploy
```

### Option 4: Docker Compose (VPS)

```yaml
# docker-compose.yml
version: '3.8'

services:
  backend:
    build: ./backend
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - DATABASE_URL=postgresql://postgres:password@db:5432/sahayak
      - FRONTEND_URL=https://sahayak.ai
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - db
    ports:
      - "8000:8000"
    restart: unless-stopped

  db:
    image: postgres:16
    environment:
      - POSTGRES_DB=sahayak
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
```

```nginx
# nginx.conf
events { worker_connections 1024; }

http {
    upstream backend {
        server backend:8000;
    }

    server {
        listen 80;
        server_name sahayak.ai www.sahayak.ai;
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
        location / {
            return 301 https://$host$request_uri;
        }
    }

    server {
        listen 443 ssl http2;
        server_name sahayak.ai www.sahayak.ai;

        ssl_certificate /etc/letsencrypt/live/sahayak.ai/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/sahayak.ai/privkey.pem;

        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /ws/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_read_timeout 86400;
        }

        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
        }
    }
}
```

## Database Setup

### Migration

```bash
# Run migrations
cd backend
source .venv/bin/activate
alembic upgrade head
```

### Seed Initial Data

```bash
python -c "
from app.database.session import AsyncSessionLocal
from app.services.knowledge import KnowledgeService
import asyncio

async def seed():
    async with AsyncSessionLocal() as db:
        service = KnowledgeService(db)
        await service.seed_initial_data()

asyncio.run(seed())
"
```

### Backup Strategy

```bash
# Daily backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Restore
psql $DATABASE_URL < backup_20240115.sql
```

## SSL/TLS Configuration

### Let's Encrypt (Certbot)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d sahayak.ai -d www.sahayak.ai

# Auto-renewal
sudo systemctl enable certbot.timer
```

### Cloudflare (Alternative)

1. Add domain to Cloudflare
2. Set SSL/TLS to "Full (Strict)"
3. Enable "Always Use HTTPS"
4. Configure Page Rules for caching

## Monitoring & Logging

### Application Logs

```bash
# Structured JSON logging in production
# Configure in app/core/config.py
LOG_LEVEL=INFO
```

### Health Checks

```bash
# Backend
curl https://api.sahayak.ai/health

# Frontend
curl -I https://sahayak.ai
```

### Uptime Monitoring

- UptimeRobot (free)
- Pingdom
- Datadog
- Better Stack

## Security Hardening

### Backend

```python
# Add to FastAPI app
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["api.sahayak.ai", "localhost"]
)

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/v1/sessions")
@limiter.limit("10/minute")
async def create_session(...):
    ...
```

### Frontend Security Headers

```javascript
// vercel.json or nginx.conf
headers: [
  { "key": "Content-Security-Policy", "value": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' fonts.googleapis.com; font-src 'self' fonts.gstatic.com; connect-src 'self' wss://api.sahayak.ai https://api.sahayak.ai; media-src 'self' blob:; img-src 'self' data:;" },
  { "key": "Permissions-Policy", "value": "microphone=(self), camera=(), geolocation=()" },
  { "key": "Referrer-Policy", "value": "strict-origin-when-cross-origin" }
]
```

## Scaling Considerations

### Horizontal Scaling

- Run multiple backend workers (`WORKERS=4`)
- Use Redis for session affinity (WebSocket)
- Load balancer with sticky sessions for WebSocket

### Database

- Connection pooling (PgBouncer)
- Read replicas for knowledge queries
- Index optimization for search

### CDN

- Static assets via Vercel/Cloudflare CDN
- Cache-Control headers for fonts, images

## CI/CD Pipeline

### GitHub Actions (`.github/workflows/deploy.yml`)

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: cd frontend && npm ci && npm run build
      - uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: '--prod'

  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: cd backend && pip install -r requirements.txt
      - run: cd backend && alembic upgrade head
      - name: Deploy to Render
        uses: render-deploy-action@v1
        with:
          api-key: ${{ secrets.RENDER_API_KEY }}
          service-id: ${{ secrets.RENDER_SERVICE_ID }}
```

## Rollback Procedure

```bash
# Frontend (Vercel)
vercel rollback [deployment-url]

# Backend (Render/Railway)
# Use dashboard to rollback to previous deploy

# Database
alembic downgrade -1  # Rollback one migration
```

## Post-Deployment Checklist

- [ ] Health endpoint returns 200
- [ ] Frontend loads without console errors
- [ ] WebSocket connects successfully
- [ ] Microphone permission works
- [ ] Audio playback works
- [ ] All three languages functional
- [ ] Accessibility features work
- [ ] Knowledge search returns results
- [ ] Google OAuth works (if enabled)
- [ ] SSL certificate valid
- [ ] Monitoring alerts configured
- [ ] Backup verified