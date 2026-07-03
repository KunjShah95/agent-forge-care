# 🎨 FRONTEND.md — AgentForge Frontend Architecture
## React · TypeScript · Vite · Tailwind CSS · shadcn/ui

> *"This document is the frontend blueprint. Every component has a place."*

---

## 📌 Overview

The AgentForge frontend is a **single-page application (SPA)** built with **React 18 + TypeScript**, bundled with **Vite 5**, styled with **Tailwind CSS 3**, and powered by a **shadcn/ui** component library. It communicates with the FastAPI backend via REST and Server-Sent Events (SSE) for streaming agent responses.

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Framework** | React 18 + TypeScript | UI rendering, component composition |
| **Build** | Vite 5 | Fast HMR dev server, optimized production builds |
| **Routing** | React Router DOM v6 | Client-side routing with lazy-loaded pages |
| **State / Data** | TanStack React Query v5 | Server state caching, mutations, polling |
| **Styling** | Tailwind CSS 3 + CSS vars | Utility-first CSS, runtime theming |
| **UI Components** | shadcn/ui (Radix primitives) | Accessible, composable UI building blocks |
| **Icons** | Lucide React | Consistent iconography |
| **Charts** | Recharts | Analytics dashboards and data visualization |
| **Animations** | Framer Motion | Page transitions, micro-interactions |
| **Auth** | Firebase Auth SDK | Email/password + Google SSO |
| **Analytics** | Firebase Analytics | Usage tracking (opt-in via GDPR consent) |
| **Maps** | Leaflet + react-leaflet | Opportunity location map |
| **Drag & Drop** | dnd-kit | Kanban application pipeline |
| **Forms** | react-hook-form + zod | Type-safe form validation |
| **Notifications** | sonner | Toast notifications |
| **SEO / Meta** | react-helmet-async | Per-page meta tags |

---

## 🏗️ Project Structure

```
src/
├── main.tsx                     # Entry point — mounts React root
├── App.tsx                      # Root component (providers, routing)
├── index.css                    # Tailwind directives, CSS variables, globals
├── App.css                      # Minimal app-level overrides
│
├── api/
│   ├── client.ts                # HTTP client, all API endpoint definitions
│   └── hooks.ts                 # TanStack Query hooks (useQuery, useMutation)
│
├── lib/
│   ├── auth-context.tsx         # Firebase auth provider + consumer hook
│   ├── firebase.ts              # Firebase init, analytics consent management
│   ├── agent-types.ts           # Agent type definitions, icons, labels
│   └── utils.ts                 # cn() utility for class merging
│
├── components/
│   ├── ui/                      # shadcn/ui primitives (50+ components)
│   │   ├── button.tsx
│   │   ├── dialog.tsx
│   │   ├── card.tsx
│   │   ├── sidebar.tsx          # Custom sidebar layout
│   │   └── ... (50 files)
│   ├── AppLayout.tsx            # App shell — sidebar + header + content
│   ├── AppSidebar.tsx           # Navigation sidebar
│   ├── ProtectedRoute.tsx       # Auth + onboarding guard
│   ├── ErrorBoundary.tsx        # React error boundary
│   ├── ThemeProvider.tsx        # next-themes dark/light mode
│   ├── ThemeToggle.tsx          # Dark/light toggle button
│   ├── CommandPalette.tsx       # ⌘K command palette
│   ├── AgentChat.tsx            # Streaming agent chat interface
│   ├── ConsentBanner.tsx        # GDPR analytics consent banner
│   ├── NotificationCenter.tsx   # Bell icon + dropdown
│   ├── OpportunityMap.tsx       # Leaflet map for opportunity locations
│   ├── ScrollReveal.tsx         # Intersection observer animations
│   └── EmptyState.tsx           # Reusable empty state
│
├── pages/                       # Route-level page components (lazy-loaded)
│   ├── Landing.tsx              # Public landing page
│   ├── Login.tsx                # Email/password + Google sign-in
│   ├── Register.tsx             # Account creation
│   ├── Onboarding.tsx           # Post-signup profile wizard
│   ├── Dashboard.tsx            # Main dashboard — metrics, activity, matches
│   ├── Opportunities.tsx        # Browse + filter opportunities
│   ├── Applications.tsx         # Kanban pipeline tracker
│   ├── ResumeStudio.tsx         # Resume upload, ATS analysis, search
│   ├── InterviewPrep.tsx        # Mock interview sessions
│   ├── ResearchCenter.tsx       # Company research tool
│   ├── NetworkingHub.tsx        # Contact management + outreach
│   ├── OpportunityMonitor.tsx   # Alert configs + scan settings
│   ├── Analytics.tsx            # Conversion funnel, skills demand, activity
│   ├── CareerCoach.tsx          # AI career guidance chat
│   ├── AgentConsole.tsx         # Agent task management + streaming output
│   ├── TaskQueue.tsx            # Background task queue viewer
│   ├── MemoryViewer.tsx         # Long-term memory browser
│   ├── Settings.tsx             # Profile, agents, billing, privacy
│   └── NotFound.tsx             # 404 page
│
├── hooks/
│   └── use-mobile.tsx           # Responsive breakpoint detection
│
└── test/
    └── setup.ts                 # Vitest setup (jsdom, matchers)
```

---

## 🧬 Routing Tree

```
/                     → Landing (public)
/login                → Login (public)
/register             → Register (public)
/onboarding           → Onboarding (auth required)
/app                  → ProtectedRoute → AppLayout
  /app                → Dashboard
  /app/opportunities  → Opportunities
  /app/applications   → Applications
  /app/resume         → ResumeStudio
  /app/interview      → InterviewPrep
  /app/research       → ResearchCenter
  /app/networking     → NetworkingHub
  /app/monitor        → OpportunityMonitor
  /app/coach          → CareerCoach
  /app/analytics      → Analytics
  /app/agents         → AgentConsole
  /app/tasks          → TaskQueue
  /app/memory         → MemoryViewer
  /app/settings       → Settings
/*                    → NotFound (404)
```

All pages under `/app` are lazy-loaded with `React.lazy()` + `Suspense` for code splitting. Routes are guarded by `<ProtectedRoute>` which checks auth state and onboarding completion.

---

## 🔐 Authentication Flow

```
┌──────────┐     ┌──────────────┐     ┌───────────┐     ┌──────────┐
│  User    │────▶│  Firebase    │────▶│  Backend  │────▶│  DB auto │
│  Action  │     │  Auth SDK    │     │  /auth/me │     │-provision│
└──────────┘     └──────────────┘     └───────────┘     └──────────┘
```

1. **`auth-context.tsx`** provides `AuthProvider` wrapping the entire app
2. `onAuthStateChanged` listener syncs Firebase user ↔ React state
3. On login/register, Firebase returns an **ID token** (RS256 JWT)
4. Token is stored in `localStorage` and attached as `Authorization: Bearer <token>` to all API requests
5. Backend verifies the token dynamically against Google's x509 certs
6. If no backend user exists, back-end **auto-provisions** a `User` + `Profile` record
7. `ProtectedRoute` redirects unauthenticated users to `/login`

**Auth methods supported:**
- Email/password (via `signInWithEmailAndPassword`)
- Google SSO (via `signInWithPopup` + `GoogleAuthProvider`)
- Password reset (via `sendPasswordResetEmail`)
- Email verification (via `sendEmailVerification`)

**Error handling:** `getFirebaseErrorMessage()` normalizes Firebase error codes into user-friendly messages.

---

## 📡 API Layer

### client.ts (HTTP Client)

A thin fetch wrapper that handles:
- Base URL resolution (`VITE_API_URL` or proxy `/api/v1`)
- Auth token injection (`Authorization` header)
- JSON serialization/deserialization
- Error normalization (`ApiError` class with status + detail)
- FormData uploads (resume, avatar)

**Organized into namespaced modules:**
```typescript
auth        — /auth/me
profile     — /profile (get, update, uploadAvatar)
opportunities — /opportunities (list, get, matches, refresh, hackathons, filters, locations)
applications — /applications (list, create, update, delete)
contacts    — /contacts (list, create, update, delete)
agents      — /agents (runPlanner, getTasks, monitor, interviewPrep, research, coverLetter, resumeTailor, etc.)
memory      — /memory (list, create, update, delete, getContext)
analytics   — /analytics (summary, funnel, skillsDemand, activity)
monitor     — /monitor (alerts CRUD, settings)
resume      — /resume (upload, list, search, delete, atsAnalysis)
interview   — /interview (sessions, feedback)
notifications — /notifications (list, markRead, markAllRead)
hiringAgent — /hiring-agent (pipeline, extract, evaluate, ats, matchJd, coverLetter, enrich, report, history)
```

### hooks.ts (TanStack Query)

Every API endpoint has a corresponding React Query hook:
- **`useQuery`** for reads (auto-caching, stale-while-revalidate, polling)
- **`useMutation`** for writes (auto-invalidation on success)
- Polling intervals: agent tasks (10s), active task (5s), notifications (15s)
- All queries check `api.getAuthToken()` before enabling

---

## 🎨 Styling System

### Tailwind CSS + CSS Variables

The app uses a **dark-first theme** with CSS custom properties for runtime theming:

```
--background, --foreground       # Page chrome
--primary, --primary-foreground  # Accent (gradient-purple)
--card, --card-foreground        # Bento card surfaces
--muted, --muted-foreground       # Subtle text
--border                          # Borders
--glass: rgba(255,255,255,0.05)  # Glass morphism
```

Key patterns:
- **Bento cards**: `bento-card` class with glass/glow effects
- **Gradient accents**: `bg-gradient-1` (purple→blue), `shadow-glow`
- **Glass panels**: `glass` / `glass-strong` classes for translucent surfaces

### shadcn/ui Components

50+ primitives installed via the CLI registry. Each component is a local file (`src/components/ui/*.tsx`) with full control over styling. Uses **Radix UI** primitives for accessibility (keyboard nav, screen readers, ARIA attributes).

---

## 📦 State Management

| Concern | Solution | Why |
|---------|----------|-----|
| **Server state** | TanStack React Query | Cache, dedup, refetch, optimistic updates |
| **Auth state** | React Context (`AuthProvider`) | Simple, globally needed, rarely changes |
| **Theme** | `next-themes` | Persistent dark/light with system preference |
| **Agent toggles** | Backend memory (`useCreateMemory`) | Persisted across sessions |
| **Form state** | react-hook-form | Performant, re-renders only changed fields |
| **Local UI state** | `useState` / `useReducer` | Component-scoped |

---

## 🧩 Key Components Deep Dive

### AppLayout.tsx
The authenticated app shell. Renders:
- `AppSidebar` — left nav with agent links, collapse on mobile
- `Header` — command palette trigger, notification bell, theme toggle, user avatar
- `<Outlet />` — React Router outlet for nested routes

### AgentChat.tsx
Streaming chat interface for agents. Uses Server-Sent Events (SSE) via `@ai-sdk/react` for real-time token streaming. Features:
- Multi-turn conversation
- Quality score visualization (green/gray bars)
- Agent-type indicator icons
- Auto-scroll on new messages

### ProtectedRoute.tsx
Authentication guard that:
1. Waits for `isLoading` to complete
2. Redirects to `/login` if not authenticated
3. Redirects to `/onboarding` if not onboarded
4. Renders children if authenticated + onboarded

### ConsentBanner.tsx
GDPR-compliant analytics consent banner:
- Shows on first visit (1s delay)
- Three options: Accept, Decline, Ask Later
- Expandable "Learn more" section
- Persists choice in localStorage
- Respects `hasAnalyticsConsent()` / `revokeAnalyticsConsent()` from firebase.ts

---

## 🔄 Build & Deploy

### Development
```bash
npm run dev          # Vite dev server on :8080, API proxy → :8000
npm run test         # Vitest (jsdom)
npm run lint         # ESLint
```

### Production
```bash
npm run build        # Vite build → dist/
npm run preview      # Preview production build
```

Build output is configured with manual chunk splitting (`vite.config.ts`):
- `vendor` — react, react-dom, react-router-dom
- `ui` — radix primitives
- `charts` — recharts
- `utils` — date-fns, clsx, tailwind-merge
- `firebase` — firebase/app, firebase/auth, firebase/analytics

### Deployment
- **Vercel** (primary): SPA with `vercel.json` rewrite for client-side routing
- **Docker**: `Dockerfile.frontend` for containerized deployment behind nginx

---

## 📐 Design Principles

1. **Component colocation** — Components live near where they're used
2. **Lazy loading** — All pages are code-split; zero upfront bundle cost for unused routes
3. **Data-driven UI** — TanStack Query drives loading/error/empty states consistently
4. **Graceful degradation** — Falls back to Firebase-derived user if backend is unavailable
5. **Privacy by design** — No analytics without explicit user consent
6. **Offline resilience** — Auth tokens in localStorage survive page refreshes
7. **Accessibility** — Radix UI provides keyboard nav, screen reader support, focus management

---

## 📊 Performance Budget

| Metric | Target | Current |
|--------|--------|---------|
| Initial JS bundle | < 200 KB gzip | ~150 KB (vendor split) |
| Lighthouse Performance | > 90 | Target |
| First Contentful Paint | < 1.5s | ~1.2s (dev) |
| Time to Interactive | < 3.0s | ~2.5s (dev) |

---

> *"A frontend that feels like a native app — fast, responsive, and always available."*

---
*FRONTEND.md v1.0 · AgentForge Frontend Team · July 2026*
