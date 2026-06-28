# AgentForge Career OS — Deployment Guide

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────────┐
│  Vercel (React) │────▶│  Railway (API)  │────▶│  PostgreSQL         │
│  Frontend       │     │  Python FastAPI │     │  Qdrant Vector DB   │
└─────────────────┘     └─────────────────┘     │  Redis Cache         │
                                                 └─────────────────────┘
```

## Prerequisites

Before starting, make sure you have:
- A **GitHub** account (to connect to Railway)
- A **Vercel** account (connect with GitHub)
- A **Firebase** project (for authentication)
- API keys for any AI/search providers you want to use

---

## Step 1: Deploy Backend to Railway

### 1.1 Create Railway Account
1. Go to https://railway.app
2. Sign up with GitHub

### 1.2 Create New Project
1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Select `agent-forge-care` repository
4. Set **Root Directory** to `backend`
5. Railway will auto-detect the `railway.json` config and use Docker

### 1.3 Add PostgreSQL Database
1. Click **"New" → "Database" → "PostgreSQL"**
2. Railway auto-generates a connection string and injects it as `DATABASE_URL`

### 1.4 Add Redis Cache
1. Click **"New" → "Database" → "Redis"**
2. Railway auto-generates a connection string and injects it as `REDIS_URL`

### 1.5 Add Qdrant Vector Database
**Option A — Qdrant Cloud (recommended for production):**
1. Sign up at https://cloud.qdrant.io
2. Create a **free cluster** (1 GB storage)
3. Copy your cluster URL (e.g., `https://xxxxx-xxxxx.us-east-1-0.aws.cloud.qdrant.io:6333`)
4. Set it as `QDRANT_URL` in Railway env vars

**Option B — Self-host on Railway (free):**
1. Click **"New" → "Docker Image"**
2. Use image: `qdrant/qdrant`
3. Set port to `6333`
4. Set Railway env var `QDRANT_URL=http://qdrant:6333`

### 1.6 Set Environment Variables

In Railway Dashboard → Your Project → **Variables** tab, add the following. You can add them one by one or paste a `.env` file:

#### 🔒 Required (without these the backend won't start)
```env
# Generate a strong random secret (64+ chars)
JWT_SECRET=<generate-with: openssl rand -hex 32>
JWT_ALGORITHM=HS256
SECRET_KEY=<generate-with: openssl rand -hex 32>
FIREBASE_PROJECT_ID=developer-portfolio-aggregator

# Vercel frontend URL (update after deploying frontend)
CORS_ORIGINS=https://your-app.vercel.app,http://localhost:5173

# Set DEBUG=false in production
DEBUG=false
```

#### 🤖 AI Model Providers (at least ONE required for agents to work)
```env
# OpenAI (paid) — best quality, most reliable
OPENAI_API_KEY=sk-...

# OR Anthropic Claude (paid)
ANTHROPIC_API_KEY=sk-ant-...

# OR Google Gemini (free tier: 60 req/min)
GOOGLE_API_KEY=AIza...

# OR Groq (free tier — fast open-source inference)
GROQ_API_KEY=gsk_...

# OR Mistral AI (free tier available)
MISTRAL_API_KEY=...

# OR DeepSeek (very cheap open-source)
DEEPSEEK_API_KEY=sk-...

# OR Together AI (prepaid $5+, open-source models)
TOGETHER_API_KEY=...

# OR Fireworks AI ($1 free starter credits)
FIREWORKS_API_KEY=...

# OR OpenRouter (gateway to 200+ models, free tier)
OPENROUTER_API_KEY=sk-or-...
```

#### 🔍 Search APIs (optional — enables real web search)
```env
# Tavily (best for AI agents)
TAVILY_API_KEY=tvly-...

# OR Google Custom Search
GOOGLE_API_KEY=AIza...
GOOGLE_CSE_ID=...

# OR Brave Search (2,000 free queries/month)
BRAVE_API_KEY=...

# OR Exa (AI-native search)
EXA_API_KEY=...

# OR SerpAPI (Google Jobs)
SERPAPI_KEY=...

# OR Mojeek (privacy-friendly, free tier)
MOJEEK_API_KEY=...

# OR SearXNG (self-hosted meta search)
SEARXNG_BASE_URL=https://your-searxng-instance.com
```

#### 🎯 Optional Services
```env
# Embeddings & Cohere (for reranking search results)
COHERE_API_KEY=...

# SendGrid (for email notifications)
SENDGRID_API_KEY=...
FROM_EMAIL=noreply@agentforge.ai

# LangSmith (for LLM observability)
LANGCHAIN_API_KEY=...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=agentforge-career-os
```

### 1.7 Deploy
1. Railway will auto-deploy when you push to GitHub
2. Monitor the build logs in the **Deployments** tab
3. Once deployed, note your backend URL:
   `https://your-project-name.up.railway.app`

### 1.8 Verify Backend
```bash
curl https://your-project-name.up.railway.app/health
```
Expected response:
```json
{
  "status": "healthy",
  "service": "AgentForge Career OS",
  "checks": {
    "database": "ok",
    "qdrant": "ok",
    "redis": "ok"
  }
}
```

Also check the comprehensive status endpoint:
```bash
curl https://your-project-name.up.railway.app/api/v1/status
```
This shows all available AI providers, search sources, and database connections.

---

## Step 2: Deploy Frontend to Vercel

### 2.1 Import Project
1. Go to https://vercel.com
2. Click **"Add New" → "Project"**
3. Import the `agent-forge-care` GitHub repository
4. Vercel auto-detects Vite and sets:
   - **Framework Preset**: Vite
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

### 2.2 Set Environment Variables (Vercel)
In Vercel Dashboard → Project → **Settings → Environment Variables**, add:

Make sure to select **"All Environments"** (Production, Preview, Development).

```env
# ── Firebase Configuration (from your Firebase Console) ──
VITE_FIREBASE_API_KEY=AIzaSy...
VITE_FIREBASE_AUTH_DOMAIN=developer-portfolio-aggregator.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=developer-portfolio-aggregator
VITE_FIREBASE_STORAGE_BUCKET=developer-portfolio-aggregator.firebasestorage.app
VITE_FIREBASE_MESSAGING_SENDER_ID=695992467963
VITE_FIREBASE_APP_ID=1:695992467963:web:...
VITE_FIREBASE_MEASUREMENT_ID=G-...

# ── Backend API URL (from Railway) ──
VITE_API_URL=https://your-project-name.up.railway.app/api/v1
```

### 2.3 Deploy
1. Click **"Deploy"**
2. Vercel will build and deploy automatically
3. Note your frontend URL: `https://your-app.vercel.app`

### 2.4 Update Backend CORS
After deploying the frontend, go back to Railway and update:
```env
CORS_ORIGINS=https://your-app.vercel.app,http://localhost:5173
```
The backend also automatically handles Vercel preview deployments via `VERCEL_URL`.

---

## Step 3: Configure Firebase for Production

### 3.1 Add Authorized Domains
1. Go to [Firebase Console](https://console.firebase.google.com) → Your Project → **Authentication → Settings**
2. Under **Authorized domains**, add:
   - `your-app.vercel.app` (your Vercel production URL)
   - `*.vercel.app` (for preview deployments)

### 3.2 Enable Sign-in Methods
1. In **Authentication → Sign-in method**:
   - **Email/Password**: Enable
   - **Google**: Enable (configure OAuth consent if needed)

---

## Step 4: Verify End-to-End

### 4.1 Check Backend Health
```bash
curl https://your-project-name.up.railway.app/api/v1/status | python -m json.tool
```
Look for:
- `"status": "healthy"`
- AI model providers listed with `"available": true` for the ones you configured
- Database connections showing `"connected"`

### 4.2 Test the Full App
1. Open your Vercel URL
2. Sign up / Sign in with email or Google
3. Try running the planner: "Find AI internships"
4. Check the Agent Console for task execution

---

## Quick Reference: All Env Vars

### Backend (Railway)
| Variable | Required | Purpose |
|----------|----------|---------|
| `DATABASE_URL` | ✅ Auto by Railway | PostgreSQL connection |
| `JWT_SECRET` | ✅ | Token signing (generate strong random) |
| `SECRET_KEY` | ✅ | Encryption key (generate strong random) |
| `FIREBASE_PROJECT_ID` | ✅ | Firebase auth |
| `CORS_ORIGINS` | ✅ | Your Vercel URL + localhost |
| `OPENAI_API_KEY` | 🎯 | Best LLM provider (recommended) |
| `TAVILY_API_KEY` | 🎯 | Best search for AI agents |
| `QDRANT_URL` | ⚠️ | Vector DB (cluster or self-hosted) |
| `REDIS_URL` | ⚠️ | Caching (auto by Railway if added) |
| Any other `*_API_KEY` | Optional | Additional AI/search providers |

### Frontend (Vercel)
| Variable | Required | Purpose |
|----------|----------|---------|
| `VITE_FIREBASE_*` | ✅ | Firebase client SDK config |
| `VITE_API_URL` | ✅ | Backend API URL |

---

## Cost Estimate

### Free Tier
| Service | Cost | Limits |
|---------|------|--------|
| **Vercel** | Free | Unlimited static sites |
| **Railway** | $5 free credit/month | Enough for low-traffic API |
| **Qdrant Cloud** | Free | 1 GB storage |
| **Firebase** | Free | 50K sign-ins/month |
| **Groq** | Free | Fast open-source LLM inference |
| **Gemini** | Free | 60 requests/min |
| **Google CSE** | Free | 100 queries/day |
| **Brave Search** | Free | 2,000 queries/month |

### Production
| Service | Plan | Cost |
|---------|------|------|
| Vercel Pro | $20/month | Production features |
| Railway | Usage-based | ~$5-20/month |
| Qdrant Cloud | Scale plan | $25+/month |
| OpenAI API | Pay-as-you-go | ~$5-50/month depending on usage |

---

## Troubleshooting

### Backend won't start on Railway
- **Check logs**: Railway Dashboard → Deployments → View logs
- **Missing env vars**: Make sure `JWT_SECRET`, `SECRET_KEY`, and `FIREBASE_PROJECT_ID` are set
- **DB connection**: Verify PostgreSQL service is running (Railway auto-injects `DATABASE_URL`)
- If DEBUG=false, `SECRET_KEY` is required (not empty)

### CORS errors in browser
- Verify `CORS_ORIGINS` on Railway includes your exact Vercel URL
- Example: `CORS_ORIGINS=https://agent-forge-care.vercel.app,http://localhost:5173`

### Firebase auth fails on Vercel
1. Check all `VITE_FIREBASE_*` variables are set correctly in Vercel
2. Redeploy after adding/changing variables
3. Add your Vercel domain to Firebase Console → Authentication → Authorized domains

### "Missing VITE_API_URL" error
- Set `VITE_API_URL` in Vercel environment variables
- Must include `/api/v1` suffix, e.g. `https://your-backend.up.railway.app/api/v1`

### AI agents return no results
- Check `/api/v1/status` to see which LLM providers are available
- If no LLM is available, agents will use keyword-based fallbacks
- Set at least `OPENAI_API_KEY` or `GROQ_API_KEY` for best results

### Quick deploy checklist
- [ ] Backend deployed on Railway with Docker
- [ ] PostgreSQL, Redis, Qdrant services running
- [ ] JWT_SECRET and SECRET_KEY set (generated, not defaults)
- [ ] At least one AI model provider configured (OpenAI recommended)
- [ ] CORS_ORIGINS includes Vercel URL
- [ ] Frontend deployed on Vercel
- [ ] VITE_API_URL points to Railway backend
- [ ] Firebase Authorized domains updated with Vercel URL
- [ ] Can call /health endpoint successfully
- [ ] Can sign in / register on the frontend
