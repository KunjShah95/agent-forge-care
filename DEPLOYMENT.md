# CareerOS — Deployment Guide

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────────┐
│  Vercel (React) │────▶│  Render (API)   │────▶│  PostgreSQL         │
│  Frontend       │     │  Python FastAPI  │     │  Qdrant Vector DB   │
└─────────────────┘     └─────────────────┘     │  Redis Cache         │
                                                 └─────────────────────┘
```

## Prerequisites

Before starting, make sure you have:
- A **GitHub** account (to connect to Render and Vercel)
- A **Vercel** account (connect with GitHub)
- A **Render** account (connect with GitHub)
- A **Firebase** project (for authentication)
- API keys for any AI/search providers you want to use

---

## Step 1: Deploy Backend to Render

### 1.1 Create Render Account
1. Go to https://render.com
2. Sign up with GitHub

### 1.2 Create New Web Service
1. Click **"New +" → "Web Service"**
2. Connect your GitHub repository
3. Select the `agent-forge-care` repository
4. Render will auto-detect the `render.yaml` config

Alternatively, use the **Blueprint** method:
1. Click **"New +" → "Blueprint"**
2. Connect your GitHub repository
3. Select the `agent-forge-care` repository
4. Render will read `render.yaml` and `backend/render.yaml`

### 1.3 Add PostgreSQL Database
1. Click **"New +" → "PostgreSQL"**
2. Copy the **Internal Database URL** (it looks like `postgres://user:pass@host:5432/careeros`)
3. Set as `DATABASE_URL` environment variable in your Web Service

### 1.4 Add Redis
1. Click **"New +" → "Redis"**
2. Copy the **Internal Redis URL**
3. Set as `REDIS_URL` environment variable in your Web Service

### 1.5 Add Qdrant Vector Database
**Option A — Qdrant Cloud (recommended for production):**
1. Sign up at https://cloud.qdrant.io
2. Create a **free cluster** (1 GB storage)
3. Copy your cluster URL
4. Set as `QDRANT_URL` in Render env vars

**Option B — Self-host as Docker on Render:**
Not directly supported — use Qdrant Cloud.

### 1.6 Set Environment Variables

In Render Dashboard → Your Web Service → **Environment** tab:

#### 🔒 Required
```env
JWT_SECRET=<generate-with: openssl rand -hex 32>
JWT_ALGORITHM=HS256
SECRET_KEY=<generate-with: openssl rand -hex 32>
FIREBASE_PROJECT_ID=your-firebase-project-id
DATABASE_URL=<from Render PostgreSQL>
REDIS_URL=<from Render Redis>
QDRANT_URL=<your Qdrant cluster URL>

# Vercel frontend URL (update after deploying frontend)
CORS_ORIGINS=https://your-app.vercel.app,http://localhost:5173

# Set DEBUG=false in production
DEBUG=false
```

#### 🤖 AI Model Providers (at least ONE required)
```env
OPENAI_API_KEY=sk-...
# OR: GROQ_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, etc.
```

### 1.7 Deploy
1. Render will auto-deploy when you push to GitHub
2. Monitor the build logs in the **Events** tab
3. Once deployed, note your backend URL:
   `https://careeros-api.onrender.com`

### 1.8 Verify Backend
```bash
curl https://careeros-api.onrender.com/health
```
Expected response:
```json
{
  "status": "healthy",
  "service": "CareerOS",
  "checks": {
    "database": "ok",
    "qdrant": "ok",
    "redis": "ok"
  }
}
```

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

### 2.2 Set Environment Variables
In Vercel Dashboard → Project → **Settings → Environment Variables**:

```env
VITE_FIREBASE_API_KEY=AIzaSy...
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-firebase-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-project.firebasestorage.app
VITE_FIREBASE_MESSAGING_SENDER_ID=123456789
VITE_FIREBASE_APP_ID=1:123456789:web:...
VITE_FIREBASE_MEASUREMENT_ID=G-...

VITE_API_URL=https://careeros-api.onrender.com/api/v1
```

### 2.3 Deploy
1. Click **"Deploy"**
2. Note your frontend URL: `https://your-app.vercel.app`

### 2.4 Update Backend CORS
```env
CORS_ORIGINS=https://your-app.vercel.app,http://localhost:5173
```

---

## Step 3: Configure Firebase

1. Go to [Firebase Console](https://console.firebase.google.com) → Authentication → Settings
2. Under **Authorized domains**, add:
   - `your-app.vercel.app`
   - `*.vercel.app`

---

## Quick Deploy Checklist

- [ ] Backend deployed on Render
- [ ] PostgreSQL, Redis, Qdrant running
- [ ] JWT_SECRET and SECRET_KEY set
- [ ] At least one AI provider configured
- [ ] CORS_ORIGINS includes Vercel URL
- [ ] Frontend deployed on Vercel
- [ ] VITE_API_URL points to Render backend
- [ ] Firebase domains updated
- [ ] Can call `/health` successfully
- [ ] Can sign in / register on frontend
