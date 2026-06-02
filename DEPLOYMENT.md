# AgentForge Career OS — Deployment Guide

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Vercel (React) │────▶│  Railway (API)  │────▶│  PostgreSQL DB  │
│  Frontend       │     │  Python FastAPI │     │  Qdrant Vector  │
└─────────────────┘     └─────────────────┘     │  Redis Cache    │
                                                 └─────────────────┘
```

## Step 1: Deploy Backend to Railway

### 1.1 Create Railway Account
1. Go to https://railway.app
2. Sign up with GitHub

### 1.2 Create New Project
1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Select `agent-forge-care` repository
4. Select `backend` as the root directory

### 1.3 Add PostgreSQL Database
1. In your Railway project, click "New" → "Database" → "PostgreSQL"
2. Note the connection string (auto-generated)

### 1.4 Add Redis (optional but recommended)
1. Click "New" → "Database" → "Redis"
2. Note the connection string

### 1.5 Add Qdrant (vector database)
Option A: Use Qdrant Cloud (free tier)
1. Sign up at https://cloud.qdrant.io
2. Create a free cluster
3. Note the URL and API key

Option B: Self-host on Railway
1. Click "New" → "Docker Image"
2. Use image: `qdrant/qdrant`
3. Set port: 6333

### 1.6 Set Environment Variables
In Railway project → Variables, add:

```env
# Database (Railway provides this automatically as DATABASE_URL)
# If not auto-set, copy from PostgreSQL service

# Firebase (match your Vercel frontend settings)
FIREBASE_PROJECT_ID=developer-portfolio-aggregator

# JWT (generate a random secret for production)
JWT_SECRET=your-random-secret-here-make-it-long
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Qdrant
QDRANT_URL=https://your-qdrant-url.qdrant.io

# Redis
REDIS_URL=redis://default:password@redis.railway.internal:6379

# OpenAI (for agent intelligence)
OPENAI_API_KEY=sk-...

# Search APIs (optional)
GOOGLE_API_KEY=
GOOGLE_CSE_ID=
SERPAPI_KEY=
TAVILY_API_KEY=

# Cohere (for reranking)
COHERE_API_KEY=

# CORS (your Vercel URL)
CORS_ORIGINS=https://your-app.vercel.app,http://localhost:5173

# App
DEBUG=false
```

### 1.7 Deploy
Railway will auto-deploy when you push to GitHub.

Note your backend URL: `https://your-project.up.railway.app`

---

## Step 2: Configure Vercel Frontend

### 2.1 Set Environment Variables
In Vercel Dashboard → Project → Settings → Environment Variables, add:

```env
# Firebase Configuration
VITE_FIREBASE_API_KEY=AIzaSyA0JAMp3_IcY1sxUvMJbVZcU4UFaIep-Nk
VITE_FIREBASE_AUTH_DOMAIN=developer-portfolio-aggregator.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=developer-portfolio-aggregator
VITE_FIREBASE_STORAGE_BUCKET=developer-portfolio-aggregator.firebasestorage.app
VITE_FIREBASE_MESSAGING_SENDER_ID=695992467963
VITE_FIREBASE_APP_ID=1:695992467963:web:47fcfbfdc05519e33f0b5e
VITE_FIREBASE_MEASUREMENT_ID=G-XE5S00S9HP

# Backend API URL (from Railway)
VITE_API_URL=https://your-project.up.railway.app/api/v1
```

**Important:** Select all environments (Production, Preview, Development) for each variable.

### 2.2 Redeploy
After adding variables, trigger a new deployment:
1. Go to Deployments tab
2. Click "..." on latest deployment
3. Click "Redeploy"

---

## Step 3: Configure Firebase for Production

### 3.1 Add Authorized Domains
1. Go to Firebase Console → Authentication → Settings
2. Under "Authorized domains", add:
   - `your-app.vercel.app`
   - `*.vercel.app` (for preview deployments)

### 3.2 Update CORS on Backend
The backend automatically handles Vercel preview deployments via `VERCEL_URL` env var.

---

## Step 4: Verify Deployment

### 4.1 Test Backend
```bash
curl https://your-project.up.railway.app/health
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

### 4.2 Test Frontend
1. Open your Vercel URL
2. Try to sign in with Google
3. Check browser console for errors

---

## Troubleshooting

### "Missing VITE_API_URL" error
- Make sure `VITE_API_URL` is set in Vercel environment variables
- Redeploy after adding the variable

### CORS errors
- Make sure `CORS_ORIGINS` on Railway includes your Vercel URL
- Check that the backend is deployed and running

### Firebase auth fails on Vercel
- Verify all `VITE_FIREBASE_*` variables are set correctly
- Check Firebase Console → Authentication → Settings → Authorized domains
- Make sure your Vercel domain is listed

### Backend won't start on Railway
- Check Railway logs for errors
- Make sure all required environment variables are set
- Verify PostgreSQL and Redis are connected

---

## Cost Estimate

### Free Tier
- **Vercel**: Free for hobby projects
- **Railway**: $5 free credit/month
- **Qdrant Cloud**: Free tier (1GB storage)
- **Firebase**: Free tier (50K sign-ins/month)

### Production
- **Vercel Pro**: $20/month
- **Railway**: ~$5-20/month depending on usage
- **Qdrant Cloud**: $25/month for more storage
