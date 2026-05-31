# 🎨 FRONTEND.md — AgentForge Career OS
## Frontend Architecture · Design System · Component Library · State Management

> *"The interface is the product. Everything else is infrastructure."*

---

## 🧭 Overview

The AgentForge frontend is a **Next.js 14 application** with real-time capabilities, a rich design system, and a carefully engineered state management layer. It serves as the command center through which users direct their AI career team.

---

## ⚙️ Technology Stack

| Category          | Technology                  | Version   | Reason                                        |
|-------------------|-----------------------------|-----------|-----------------------------------------------|
| Framework         | Next.js                     | 14.x      | App Router, RSC, Edge SSR, API Routes         |
| Language          | TypeScript                  | 5.x       | Type safety across components and API layer   |
| Styling           | Tailwind CSS + CSS Modules  | 3.4.x     | Utility-first + scoped component styles       |
| Animation         | Framer Motion               | 11.x      | Page transitions, agent activity animations   |
| State (global)    | Zustand                     | 4.x       | Lightweight, devtools-friendly store          |
| State (server)    | TanStack Query              | 5.x       | Server state, caching, background refetch     |
| Forms             | React Hook Form + Zod       | latest    | Performant forms with schema validation       |
| Realtime          | WebSocket (native) + SWR    | -         | Live agent status, streaming LLM output       |
| Auth              | Clerk                       | 5.x       | JWT auth, social login, user management       |
| UI Primitives     | Radix UI                    | latest    | Accessible, unstyled component primitives     |
| Icons             | Lucide React                | latest    | Consistent icon system                        |
| Charts            | Recharts                    | 2.x       | Career analytics dashboards                   |
| Tables            | TanStack Table              | 8.x       | Virtual, sortable opportunity tables          |
| Testing           | Playwright + Vitest         | latest    | E2E + unit testing                            |

---

## 📁 Directory Structure

```
apps/web/
├── app/                          # Next.js 14 App Router
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   └── onboarding/page.tsx
│   ├── (dashboard)/
│   │   ├── layout.tsx            # Sidebar + nav shell
│   │   ├── page.tsx              # Career Command Center (home)
│   │   ├── opportunities/
│   │   │   ├── page.tsx          # Opportunity discovery feed
│   │   │   └── [id]/page.tsx     # Opportunity detail
│   │   ├── applications/
│   │   │   ├── page.tsx          # Application tracker (kanban)
│   │   │   └── [id]/page.tsx     # Application detail + timeline
│   │   ├── resume/
│   │   │   ├── page.tsx          # Resume manager
│   │   │   └── editor/page.tsx   # Live resume editor
│   │   ├── interview/page.tsx    # Mock interview studio
│   │   ├── coach/page.tsx        # Career coach chat
│   │   ├── analytics/page.tsx    # Career intelligence dashboard
│   │   └── settings/page.tsx     # Profile + preferences
│   └── api/                      # Next.js API routes (BFF layer)
│       ├── agent/route.ts
│       ├── memory/route.ts
│       └── ws/route.ts
├── components/
│   ├── ui/                       # Design system primitives
│   ├── agents/                   # Agent-specific UI components
│   ├── career/                   # Domain components
│   ├── layout/                   # Shell, sidebar, nav
│   └── shared/                   # Reusable cross-domain
├── hooks/                        # Custom React hooks
├── stores/                       # Zustand stores
├── lib/                          # Utilities, API clients
├── types/                        # TypeScript definitions
└── styles/                       # Global CSS, tokens
```

---

## 🎨 Design System

### Color Palette

```css
:root {
  /* Brand */
  --forge-primary:       #6366F1;   /* Indigo — primary actions */
  --forge-primary-dark:  #4F46E5;   /* Indigo dark — hover */
  --forge-accent:        #10B981;   /* Emerald — success, skills */
  --forge-warning:       #F59E0B;   /* Amber — pending, review */
  --forge-danger:        #EF4444;   /* Red — rejected, errors */

  /* Neutrals */
  --forge-bg:            #0F0F13;   /* Near-black background */
  --forge-surface-1:     #1A1A24;   /* Card background */
  --forge-surface-2:     #252532;   /* Input, hover background */
  --forge-border:        #2E2E3E;   /* Subtle borders */
  --forge-text-1:        #F8F8FC;   /* Primary text */
  --forge-text-2:        #9CA3AF;   /* Secondary text */
  --forge-text-3:        #6B7280;   /* Muted text */

  /* Agent colors (each agent has a distinct color) */
  --agent-internship:    #818CF8;
  --agent-job:           #34D399;
  --agent-resume:        #60A5FA;
  --agent-cover:         #F472B6;
  --agent-research:      #A78BFA;
  --agent-interview:     #FBBF24;
  --agent-network:       #2DD4BF;
  --agent-coach:         #FB923C;
  --agent-monitor:       #94A3B8;
}
```

### Typography

```css
/* Display — Hero headings, page titles */
font-family: 'Clash Display', 'Syne', sans-serif;

/* Body — Readable content */
font-family: 'DM Sans', 'Plus Jakarta Sans', sans-serif;

/* Mono — Code, IDs, technical data */
font-family: 'JetBrains Mono', 'Fira Code', monospace;

/* Scale */
--text-xs:   0.75rem;   /* 12px */
--text-sm:   0.875rem;  /* 14px */
--text-base: 1rem;      /* 16px */
--text-lg:   1.125rem;  /* 18px */
--text-xl:   1.25rem;   /* 20px */
--text-2xl:  1.5rem;    /* 24px */
--text-3xl:  1.875rem;  /* 30px */
--text-4xl:  2.25rem;   /* 36px */
--text-5xl:  3rem;      /* 48px */
```

---

## 📐 Page Designs

### 1. Career Command Center (Home Dashboard)

**Concept**: Mission control — a terminal-style overview of all active agents and recent activity.

```
┌─────────────────────────────────────────────────────────────────┐
│  AGENTFORGE                              [⚡ 3 agents active]   │
├──────────────────────┬──────────────────────────────────────────┤
│                      │  🎯 Today's Priority                      │
│  SIDEBAR             │  ┌────────────────────────────────────┐  │
│                      │  │ 4 new internships match your profile│  │
│  📍 Dashboard        │  │ Resume ready for TechCorp apply     │  │
│  🔍 Opportunities    │  └────────────────────────────────────┘  │
│  📋 Applications     │                                           │
│  📄 Resume           │  🤖 Active Agents                         │
│  🎤 Interview        │  ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  💬 Coach            │  │Internship│ │Research  │ │Monitor   │  │
│  📊 Analytics        │  │⟳ Running │ │✓ Done    │ │⟳ Running │  │
│  ⚙️  Settings        │  └──────────┘ └──────────┘ └──────────┘  │
│                      │                                           │
│  ──────────────      │  📈 This Week                             │
│  Profile: KUNJ       │  Applications: 12  Interviews: 2          │
│  Goal: SWE Intern    │  Response Rate: 34%  Top Match: Google     │
│  Level: Junior       │                                           │
└──────────────────────┴──────────────────────────────────────────┘
```

### 2. Opportunities Feed

**Concept**: Tinder for jobs — swipeable, ranked, with AI match scores.

```
┌─────────────────────────────────────────────────────────────────┐
│  🔍 OPPORTUNITIES               Filter ▼  Sort: Match Score ▼   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ [Google Logo] Software Engineering Intern              │     │
│  │ Google · Mountain View (Remote OK) · Summer 2025       │     │
│  │                                                        │     │
│  │ ██████████ 94% Match                                   │     │
│  │                                                        │     │
│  │ Skills: Python ✓  React ✓  System Design ✓             │     │
│  │ Missing: Kubernetes (minor gap)                        │     │
│  │                                                        │     │
│  │ Deadline: March 15 · Applied by 2,341 candidates       │     │
│  │                                                        │     │
│  │ [🔖 Save]  [📋 View Resume Draft]  [⚡ Quick Apply]     │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ [Stripe Logo] Backend Engineering Intern               │     │
│  │ Stripe · San Francisco · Remote                        │     │
│  │ ████████░░ 81% Match        [view]                     │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ [Notion Logo] Product Engineering Intern               │     │
│  │ Notion · NYC · Hybrid                                  │     │
│  │ ███████░░░ 76% Match        [view]                     │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

### 3. Application Tracker (Kanban)

```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│  APPLIED     │  INTERVIEW   │  OFFER       │  CLOSED      │
│  (8)         │  (3)         │  (1)         │  (12)        │
├──────────────┼──────────────┼──────────────┼──────────────┤
│ ┌──────────┐ │ ┌──────────┐ │ ┌──────────┐ │ ┌──────────┐ │
│ │ Google   │ │ │ Stripe   │ │ │ Notion   │ │ │ Amazon   │ │
│ │ SWE Int. │ │ │ Backend  │ │ │ Product  │ │ │ SDE Int. │ │
│ │ Mar 10   │ │ │ Mar 18   │ │ │ OFFER!   │ │ │ Rejected │ │
│ └──────────┘ │ └──────────┘ │ └──────────┘ │ └──────────┘ │
│ ┌──────────┐ │ ┌──────────┐ │              │ ┌──────────┐ │
│ │ Airbnb   │ │ │ Linear   │ │              │ │ Meta     │ │
│ │ Data Int.│ │ │ Frontend │ │              │ │ Ghosted  │ │
│ │ Mar 12   │ │ │ Mar 20   │ │              │ │          │ │
│ └──────────┘ │ └──────────┘ │              │ └──────────┘ │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

### 4. Interview Studio

```
┌─────────────────────────────────────────────────────────────────┐
│  🎤 INTERVIEW STUDIO · Stripe Backend Engineer Mock              │
├──────────────────────────────┬──────────────────────────────────┤
│                              │  🤖 AgentForge Interviewer        │
│  📊 Session Progress         │  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄   │
│  ████████░░ Q4 of 5          │  "Tell me about a time you        │
│                              │  debugged a complex distributed   │
│  Behavioral    ✓ ✓           │  systems issue under pressure."   │
│  Technical     ✓ ○           │                                   │
│  Situational   ○ ○           │  [Your Answer]                    │
│                              │  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄   │
│  📈 Scores So Far            │  I was working on a payment       │
│  Relevance:   ████░ 4.1      │  processing pipeline at...       │
│  Clarity:     ███░░ 3.2      │                                   │
│  Impact:      ████░ 4.4      │                                   │
│                              │  ┌────────────────────────────┐   │
│  ⏱ Time: 8:34               │  │ 🎯 Feedback on Last Answer  │   │
│                              │  │ Good structure. Missing:    │   │
│  [Pause] [Skip] [End]        │  │ quantified impact + tools  │   │
│                              │  └────────────────────────────┘   │
└──────────────────────────────┴──────────────────────────────────┘
```

---

## 🔄 State Management

### Zustand Stores

```typescript
// stores/agent.store.ts
interface AgentStore {
  activeAgents: Agent[]
  agentLogs: AgentLog[]
  startAgent: (type: AgentType, context: AgentContext) => void
  stopAgent: (id: string) => void
  streamOutput: (id: string, chunk: string) => void
}

// stores/career.store.ts
interface CareerStore {
  opportunities: Opportunity[]
  applications: Application[]
  userProfile: UserProfile
  filters: OpportunityFilters
  setFilters: (filters: Partial<OpportunityFilters>) => void
  applyToOpportunity: (id: string) => Promise<void>
}

// stores/memory.store.ts
interface MemoryStore {
  workingContext: WorkingMemory
  recentEpisodes: Episode[]
  updateContext: (update: Partial<WorkingMemory>) => void
}
```

### TanStack Query Keys

```typescript
export const queryKeys = {
  opportunities: {
    all: ['opportunities'] as const,
    list: (filters: Filters) => ['opportunities', 'list', filters] as const,
    detail: (id: string) => ['opportunities', 'detail', id] as const,
  },
  applications: {
    all: ['applications'] as const,
    byStatus: (status: AppStatus) => ['applications', status] as const,
  },
  agents: {
    active: ['agents', 'active'] as const,
    logs: (id: string) => ['agents', 'logs', id] as const,
  },
  memory: {
    context: ['memory', 'context'] as const,
    episodes: ['memory', 'episodes'] as const,
  }
}
```

---

## 🔌 WebSocket — Real-Time Agent Streaming

```typescript
// hooks/useAgentStream.ts
export function useAgentStream(agentId: string) {
  const [output, setOutput] = useState<string>('')
  const [status, setStatus] = useState<'idle' | 'running' | 'done' | 'error'>('idle')

  useEffect(() => {
    const ws = new WebSocket(`${WS_URL}/agents/${agentId}/stream`)

    ws.onmessage = (event) => {
      const msg: AgentStreamMessage = JSON.parse(event.data)
      
      switch (msg.type) {
        case 'token':    setOutput(prev => prev + msg.content); break
        case 'status':   setStatus(msg.status); break
        case 'tool_use': logToolCall(msg.tool, msg.input); break
        case 'done':     setStatus('done'); ws.close(); break
        case 'error':    setStatus('error'); break
      }
    }

    return () => ws.close()
  }, [agentId])

  return { output, status }
}
```

---

## ♿ Accessibility Standards

| Standard        | Target                                          |
|-----------------|-------------------------------------------------|
| WCAG Level      | AA minimum (AAA for key flows)                  |
| Color Contrast  | 4.5:1 normal text, 3:1 large text               |
| Keyboard Nav    | Full keyboard accessibility, visible focus ring |
| Screen Readers  | ARIA labels on all interactive elements         |
| Motion          | Respects `prefers-reduced-motion`               |
| Font Size       | Base 16px, scales with user system settings     |

---

## 🧪 Testing Strategy

```
Unit Tests (Vitest):
- All Zustand stores
- Custom hooks
- Utility functions
- Form validation schemas

Component Tests (React Testing Library):
- All UI primitives
- Form components
- Agent output components

E2E Tests (Playwright):
- Onboarding flow
- Opportunity discovery → apply flow
- Interview session flow
- Settings update flow
```

---

## 📱 Responsive Breakpoints

```css
/* Mobile-first approach */
sm:   640px   /* Mobile landscape */
md:   768px   /* Tablet portrait */
lg:   1024px  /* Tablet landscape / small laptop */
xl:   1280px  /* Desktop */
2xl:  1536px  /* Wide desktop */
```

---

## 🚀 Performance Targets

| Metric                | Target    | Tool                      |
|-----------------------|-----------|---------------------------|
| First Contentful Paint| < 1.2s    | Lighthouse                |
| Largest Contentful    | < 2.5s    | Core Web Vitals           |
| Total Blocking Time   | < 200ms   | Lighthouse                |
| Cumulative Layout     | < 0.1     | Core Web Vitals           |
| Bundle Size (initial) | < 150KB   | @next/bundle-analyzer     |
| API Response (P95)    | < 800ms   | Grafana                   |

---

> *"The best interface is one the user never thinks about — they just achieve their goals."*

---
*FRONTEND.md v1.0 · AgentForge Frontend Team · Confidential*
