# 🧪 AgentForge Career OS — Staging Environment Guide

> *A production-like environment for testing changes before they hit production.*

---

## 📌 Overview

The staging environment bridges **development** and **production**:

| Aspect | Dev (`docker-compose.yml`) | Staging (`docker-compose.staging.yml`) | Prod (`docker-compose.prod.yml`) |
|--------|---------------------------|----------------------------------------|----------------------------------|
| **DEBUG** | `true` | `false` | `false` |
| **Auth enforcement** | Lax (auto-generates keys) | Strict (validates like prod) | Strict |
| **Rate limits** | — | Staging-appropriate (200/10 req/min) | Production (100/5 req/min) |
| **Data isolation** | Dev volumes | Separate staging volumes | Separate prod volumes |
| **Ports** | 8000, 5432, 6333, 6379 | 8000, 5433, 6335, 6380 | 8000, 5432, 6333, 6379 |
| **Frontend** | Dev server (Vite HMR) | Built + nginx-served | Built + nginx-served |
| **Hot reload** | ✅ Backend source mount | ✅ Backend source mount | ❌ Static Docker image |
| **Data retention** | None (accumulates everything) | Short (7-30 day TTL enforced) | Production TTL enforced |

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose installed
- Firebase project for staging (can be same as dev)
- At least one AI model API key

### 1. Set up environment variables

```bash
# Copy the staging env template
cp .env.staging .env.staging.local

# Edit with your values
# At minimum, set:
# - JWT_SECRET (generate with: openssl rand -hex 32)
# - FIREBASE_PROJECT_ID
# - At least one AI provider key (e.g., GROQ_API_KEY)
nano .env.staging.local
```

### 2. Start the staging environment

```bash
# Load env vars and start all services
export $(grep -v '^\s*#' .env.staging.local | xargs)
docker compose -f docker-compose.staging.yml up -d --build
```

### 3. Verify everything is running

```bash
# Check all service health
curl http://localhost:8000/health

# Check the comprehensive status
curl http://localhost:8000/api/v1/status

# Open the frontend
open http://localhost
```

### 4. Run integration tests against staging

```bash
# Run backend tests pointing to staging services
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/agentforge_staging \
REDIS_URL=redis://localhost:6380 \
JWT_SECRET=staging-test-secret \
DEBUG=true \
pytest tests/ -q --timeout=60
```

---

## 🔄 Workflow

### Testing a new feature

```bash
# 1. Start staging (if not already running)
docker compose -f docker-compose.staging.yml up -d

# 2. Make code changes (backend hot-reloads automatically)
#    Frontend changes require rebuild:
docker compose -f docker-compose.staging.yml build frontend
docker compose -f docker-compose.staging.yml up -d frontend

# 3. Run integration tests
pytest tests/test_integration.py -v

# 4. Test manually via frontend at http://localhost

# 5. Check logs
docker compose -f docker-compose.staging.yml logs -f backend
```

### Refreshing data

```bash
# Wipe staging data and start fresh
docker compose -f docker-compose.staging.yml down -v
docker compose -f docker-compose.staging.yml up -d
```

### Tearing down

```bash
# Stop without deleting volumes
docker compose -f docker-compose.staging.yml down

# Stop and delete all staging data
docker compose -f docker-compose.staging.yml down -v
```

---

## 🗄️ Data Retention in Staging

Staging uses **shorter retention periods** than production to prevent data bloat:

| Data Type | Staging TTL | Production Default | Rationale |
|-----------|-------------|-------------------|-----------|
| Opportunities | 30 days | 90 days | Stale test data shouldn't linger |
| Agent tasks | 14 days | 30 days | Quick cleanup of test runs |
| Notifications | 7 days | 30 days | Test notifications are noise |
| Memory entries | 30 days | 90 days | Per-entry `ttl_days` still applies |

Override with env vars:
```bash
DATA_RETENTION_OPPORTUNITY_DAYS=60
DATA_RETENTION_AGENT_TASK_DAYS=7
DATA_RETENTION_NOTIFICATION_DAYS=3
DATA_RETENTION_MEMORY_DAYS=14
```

The retention cleanup runs automatically every hour via the background task in `main.py`.

---

## 🔐 Security Considerations

1. **Use a separate Firebase project** for staging if possible (isolates test users from prod)
2. **Use restricted API keys** — set daily spending limits on AI provider keys
3. **Never use production JWT_SECRET** in staging
4. **Staging data is disposable** — treat it as such (no real user data)
5. **Different ports** prevent accidental cross-contamination with dev databases

---

## 🐛 Troubleshooting

### "JWT_SECRET is required for staging"
Set `JWT_SECRET` in your `.env.staging.local` file before starting staging.

### "FIREBASE_PROJECT_ID is required for staging"
Set `FIREBASE_PROJECT_ID` — can use the same Firebase project as development.

### Port conflicts
Staging uses different ports than dev. If conflicts still occur:
```bash
# Check what's using the ports
netstat -an | findstr "5433 6335 6380"

# Or change ports in docker-compose.staging.yml
```

### Backend won't start
```bash
# Check backend logs
docker compose -f docker-compose.staging.yml logs backend

# Common issues:
# - Missing env vars (JWT_SECRET, FIREBASE_PROJECT_ID)
# - Database not ready (wait for healthcheck)
# - Qdrant connection refused
```

### Frontend shows blank page
```bash
# Check frontend logs
docker compose -f docker-compose.staging.yml logs frontend

# Verify VITE_API_URL points to the backend
# Verify VITE_FIREBASE_* vars are correct
```

---

## 📋 Staging Checklist

Before deploying to production from staging:

- [ ] All integration tests pass against staging
- [ ] Rate limiting works as expected (test 429 responses)
- [ ] Data retention cleanup runs without errors (check logs)
- [ ] Firestore auth works with staging Firebase project
- [ ] AI model providers respond correctly (check /status)
- [ ] Email notifications work (if SendGrid configured)
- [ ] Search adapters return results (check /status)
- [ ] No cross-contamination with dev data (separate volumes verified)
- [ ] Frontend builds without errors
- [ ] CORS configured for all expected origins

---

## 🏗️ CI/CD Integration

### GitHub Actions — deploy to staging on PR

Add to `.github/workflows/ci.yml`:

```yaml
deploy-staging:
  name: Deploy to Staging
  if: github.event_name == 'pull_request'
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Start staging
      env:
        JWT_SECRET: ${{ secrets.STAGING_JWT_SECRET }}
        FIREBASE_PROJECT_ID: ${{ secrets.STAGING_FIREBASE_PROJECT_ID }}
      run: |
        docker compose -f docker-compose.staging.yml up -d --build
    - name: Run integration tests
      run: |
        cd backend && pytest tests/test_integration.py -v
    - name: Cleanup
      run: |
        docker compose -f docker-compose.staging.yml down -v
```

### Deployment promotion workflow

```
           ┌──────────┐     ┌──────────┐     ┌──────────┐
           │   Dev    │────▶│ Staging  │────▶│   Prod   │
           │  :5173   │     │  :8000   │     │   :443   │
           └──────────┘     └──────────┘     └──────────┘
               │                │                │
           hot-reload      automated        manual
           code changes    tests pass       approval
                           + manual QA      to deploy
```

---

> *"Staging is where good code goes before it becomes great code."*
