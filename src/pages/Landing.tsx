import { Link } from "react-router-dom";
import {
  ArrowRight,
  BellRing,
  FileText,
  MessagesSquare,
  Mic,
  Search,
  Users,
} from "lucide-react";

/* CareerOS landing. Dark theme locked. Single accent: emerald. */

const NAV_LINKS = [
  { label: "Product", href: "#agents" },
  { label: "How it works", href: "#process" },
  { label: "Pricing", href: "#pricing" },
  { label: "FAQ", href: "#faq" },
];

const SOURCES = [
  { name: "LinkedIn", slug: "linkedin" },
  { name: "Indeed", slug: "indeed" },
  { name: "Glassdoor", slug: "glassdoor" },
  { name: "Y Combinator", slug: "ycombinator" },
  { name: "Stack Overflow", slug: "stackoverflow" },
  { name: "GitHub", slug: "github" },
];

const AGENTS = [
  {
    icon: BellRing,
    name: "Opportunity Monitor",
    desc: "Scans 50+ sources around the clock. High matches land in your inbox before the window closes.",
    tint: true,
  },
  {
    icon: FileText,
    name: "Resume Studio",
    desc: "ATS analysis plus tailored rewrites. Pass through rates up 40% on average.",
    tint: false,
  },
  {
    icon: Mic,
    name: "Interview Prep",
    desc: "Mock sessions with real feedback. Behavioral, technical, and company specific.",
    tint: false,
  },
  {
    icon: Search,
    name: "Research Agent",
    desc: "Company briefs with culture signals, recent news, and interview patterns.",
    tint: true,
  },
  {
    icon: Users,
    name: "Networking Hub",
    desc: "Find the right people, draft outreach that lands, track every follow up.",
    tint: false,
  },
  {
    icon: MessagesSquare,
    name: "Career Coach",
    desc: "Strategy built on your profile and market data. No motivational templates.",
    tint: false,
  },
];

const STEPS = [
  {
    num: "01",
    title: "Tell us where you want to go",
    desc: "Upload a resume, add skills, set preferences. Five minutes and your agents have what they need.",
  },
  {
    num: "02",
    title: "Agents work while you live",
    desc: "Discovery, tailoring, prep, and follow ups run in the background. You return to results, not tasks.",
  },
  {
    num: "03",
    title: "You make the moves",
    desc: "Every application ships with intelligence attached. The groundwork is done. You choose.",
  },
];

const STATS = [
  { value: "24/7", label: "Monitoring" },
  { value: "8", label: "Specialist agents" },
  { value: "50+", label: "Sources scanned" },
  { value: "78%", label: "Match accuracy" },
];

const QUOTES = [
  {
    body: "Applied to eleven roles in a week. Every one felt hand written. Three callbacks.",
    name: "Priya N.",
    role: "New grad, frontend",
  },
  {
    body: "The interview prep called out the exact system design round I walked into.",
    name: "Marcus T.",
    role: "Career switcher, backend",
  },
  {
    body: "It found a fellowship I had never heard of. Deadline in four days. I made it.",
    name: "Sofia R.",
    role: "Student, ML",
  },
];

const PLANS = [
  {
    name: "Free",
    price: "$0",
    per: "forever",
    points: ["50 scans / month", "3 resume analyses", "2 mock interviews", "3 agents"],
    featured: false,
  },
  {
    name: "Pro",
    price: "$29",
    per: "per month, billed annually",
    points: ["Unlimited everything", "All 8 agents", "24/7 monitoring + alerts", "Offer coaching"],
    featured: true,
  },
  {
    name: "Team",
    price: "$79",
    per: "per user / month",
    points: ["Shared workspace", "API access", "Coach overview", "Priority support"],
    featured: false,
  },
];

const FAQS = [
  {
    q: "How is this different from a job board?",
    a: "Boards list roles. CareerOS runs the search for you: discovery, tailoring, prep, outreach, and tracking across eight agents with shared memory.",
  },
  {
    q: "Do I need to pay to start?",
    a: "No. The free plan covers light usage with no credit card. Pro unlocks unlimited scans and all eight agents.",
  },
  {
    q: "Which industries are covered?",
    a: "Tech and tech enabled roles have the deepest coverage: engineering, data, design, and product across full time, contract, and internships.",
  },
  {
    q: "Is my data used for training?",
    a: "No. Personal data is never used for general model training. Full export and deletion are available on request.",
  },
];

const INK = "#0B1220";
const PAPER = "#F4F2EC";
const MUTED = "rgba(244,242,236,0.62)";
const FAINT = "rgba(244,242,236,0.38)";
const LINE = "rgba(244,242,236,0.12)";
const ACCENT = "#34D399";

export default function Landing() {
  return (
    <div style={{ background: INK, color: PAPER, fontFamily: "var(--font-body)" }}>
      {/* ── Nav ── */}
      <header className="sticky top-0 z-40" style={{ background: "rgba(11,18,32,0.86)", backdropFilter: "blur(12px)", borderBottom: `1px solid ${LINE}` }}>
        <div className="max-w-7xl mx-auto px-5 sm:px-8 h-16 flex items-center justify-between gap-4">
          <Link to="/" className="text-xl tracking-tight shrink-0" style={{ fontFamily: "var(--font-display)" }}>
            CareerOS
          </Link>
          <nav className="hidden md:flex items-center gap-7 min-w-0">
            {NAV_LINKS.map(({ label, href }) => (
              <a key={label} href={href} className="text-sm transition-colors hover:text-white" style={{ color: MUTED }}>
                {label}
              </a>
            ))}
          </nav>
          <div className="flex items-center gap-2 sm:gap-3 shrink-0">
            <Link to="/login" className="text-sm px-3 py-2 transition-colors hover:text-white" style={{ color: MUTED }}>
              Log in
            </Link>
            <Link to="/register" className="rounded-full px-5 py-2.5 text-sm font-medium text-black transition-transform duration-200 hover:scale-[1.03] active:scale-[0.98]" style={{ background: ACCENT }}>
              Get started
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero: split ── */}
      <section className="max-w-7xl mx-auto px-5 sm:px-8 pt-16 pb-20 md:pt-24 md:pb-28 grid md:grid-cols-2 gap-12 md:gap-8 items-center min-h-[calc(100dvh-4rem)]">
        <div>
          <p className="text-[11px] uppercase tracking-[0.22em] font-mono mb-5" style={{ color: ACCENT }}>
            AI career team · 8 agents
          </p>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl max-w-[16ch]" style={{ fontFamily: "var(--font-display)", lineHeight: 1.04 }}>
            Your job search, run by 8 agents.
          </h1>
          <p className="mt-5 text-base sm:text-lg leading-relaxed max-w-[42ch]" style={{ color: MUTED }}>
            Discovery, resumes, prep, and outreach on autopilot. Five minutes to set up.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Link to="/register" className="rounded-full px-8 py-3.5 text-sm font-medium text-black transition-transform duration-200 hover:scale-[1.03] active:scale-[0.98]" style={{ background: ACCENT }}>
              Get started
            </Link>
            <a href="#process" className="text-sm transition-colors hover:text-white" style={{ color: MUTED }}>
              See how it works →
            </a>
          </div>
          <dl className="mt-10 flex gap-8">
            {STATS.slice(1, 4).map((s) => (
              <div key={s.label}>
                <dt className="sr-only">{s.label}</dt>
                <dd className="text-2xl font-mono" style={{ color: PAPER }}>{s.value}</dd>
                <dd className="text-xs mt-1" style={{ color: FAINT }}>{s.label}</dd>
              </div>
            ))}
          </dl>
        </div>

        {/* Live product preview: scored match card */}
        <div className="rounded-2xl p-5 sm:p-6 animate-float-slow" style={{ background: "rgba(244,242,236,0.04)", border: `1px solid ${LINE}` }}>
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs font-mono uppercase tracking-[0.18em]" style={{ color: FAINT }}>Top match · just found</p>
            <span className="text-[11px] font-mono px-2.5 py-1 rounded-full" style={{ background: "rgba(52,211,153,0.14)", color: ACCENT, border: "1px solid rgba(52,211,153,0.35)" }}>
              92% match
            </span>
          </div>
          <p className="text-xl" style={{ fontFamily: "var(--font-display)" }}>Frontend Engineer, New Grad</p>
          <p className="text-sm mt-1" style={{ color: MUTED }}>Linear · New York · $130–180k</p>
          <ul className="mt-4 space-y-2.5">
            {["React + TypeScript daily driver", "Design system experience", "YC pace, small team"].map((r) => (
              <li key={r} className="flex items-start gap-2.5 text-sm" style={{ color: MUTED }}>
                <span className="mt-[7px] h-1.5 w-1.5 rounded-full shrink-0" style={{ background: ACCENT }} />
                {r}
              </li>
            ))}
          </ul>
          <div className="mt-5 flex flex-wrap gap-2">
            {["React", "TypeScript", "Design"].map((s) => (
              <span key={s} className="text-xs font-mono px-2.5 py-1 rounded-full" style={{ border: `1px solid ${LINE}`, color: MUTED }}>
                {s}
              </span>
            ))}
            <span className="text-xs font-mono px-2.5 py-1 rounded-full" style={{ background: "rgba(52,211,153,0.14)", color: ACCENT }}>
              +1 skill gap
            </span>
          </div>
          <div className="mt-5 pt-4 flex items-center justify-between" style={{ borderTop: `1px solid ${LINE}` }}>
            <p className="text-xs" style={{ color: FAINT }}>Resume tailored · deadline in 6 days</p>
            <span className="text-sm font-medium" style={{ color: ACCENT }}>Apply →</span>
          </div>
        </div>
      </section>

      {/* ── Source strip + the one marquee ── */}
      <section className="py-10" style={{ borderTop: `1px solid ${LINE}`, borderBottom: `1px solid ${LINE}` }}>
        <p className="text-center text-xs font-mono uppercase tracking-[0.2em] mb-6" style={{ color: FAINT }}>
          Agents scan 50+ sources daily
        </p>
        <div className="overflow-hidden">
          <div className="flex w-max animate-marquee items-center gap-14 pr-14">
            {[...SOURCES, ...SOURCES].map((s, i) => (
              <span key={`${s.slug}-${i}`} className="flex items-center gap-2.5 shrink-0" aria-label={s.name}>
                <img
                  src={`https://cdn.simpleicons.org/${s.slug}/F4F2EC`}
                  alt=""
                  width={20}
                  height={20}
                  loading="lazy"
                  onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
                />
                <span className="text-sm whitespace-nowrap" style={{ color: MUTED }}>{s.name}</span>
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── Agents bento ── */}
      <section id="agents" className="max-w-7xl mx-auto px-5 sm:px-8 py-20 md:py-28">
        <h2 className="text-3xl sm:text-4xl md:text-5xl max-w-[20ch]" style={{ fontFamily: "var(--font-display)", lineHeight: 1.08 }}>
          Six tools. One shared memory.
        </h2>
        <p className="mt-4 text-base leading-relaxed max-w-[56ch]" style={{ color: MUTED }}>
          Each agent is a specialist. Together they run the whole search without being asked twice.
        </p>
        <div className="mt-12 grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {AGENTS.map(({ icon: Icon, name, desc, tint }) => (
            <article
              key={name}
              className="rounded-2xl p-6 sm:p-7 transition-transform duration-300 hover:-translate-y-1 active:translate-y-0"
              style={{
                background: tint ? "rgba(52,211,153,0.07)" : "rgba(244,242,236,0.03)",
                border: `1px solid ${tint ? "rgba(52,211,153,0.28)" : LINE}`,
              }}
            >
              <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl mb-5" style={{ background: "rgba(52,211,153,0.12)", color: ACCENT }}>
                <Icon size={19} strokeWidth={1.75} />
              </span>
              <h3 className="text-xl mb-2" style={{ fontFamily: "var(--font-display)" }}>{name}</h3>
              <p className="text-sm leading-relaxed" style={{ color: MUTED }}>{desc}</p>
            </article>
          ))}
        </div>
      </section>

      {/* ── Process: vertical timeline ── */}
      <section id="process" className="py-20 md:py-28" style={{ background: "rgba(244,242,236,0.025)", borderTop: `1px solid ${LINE}`, borderBottom: `1px solid ${LINE}` }}>
        <div className="max-w-3xl mx-auto px-5 sm:px-8">
          <h2 className="text-3xl sm:text-4xl md:text-5xl" style={{ fontFamily: "var(--font-display)", lineHeight: 1.08 }}>
            Three steps. Then clarity.
          </h2>
          <ol className="mt-12">
            {STEPS.map((s, i) => (
              <li key={s.num} className="relative pl-16 pb-12 last:pb-0">
                {i < STEPS.length - 1 && (
                  <span aria-hidden className="absolute left-[19px] top-12 bottom-0 w-px" style={{ background: LINE }} />
                )}
                <span className="absolute left-0 top-0 flex h-10 w-10 items-center justify-center rounded-full text-xs font-mono" style={{ background: "rgba(52,211,153,0.12)", color: ACCENT, border: "1px solid rgba(52,211,153,0.35)" }}>
                  {s.num}
                </span>
                <h3 className="text-2xl mb-2" style={{ fontFamily: "var(--font-display)" }}>{s.title}</h3>
                <p className="text-sm sm:text-base leading-relaxed max-w-[58ch]" style={{ color: MUTED }}>{s.desc}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ── Quotes ── */}
      <section className="max-w-7xl mx-auto px-5 sm:px-8 py-20 md:py-28">
        <h2 className="text-3xl sm:text-4xl md:text-5xl" style={{ fontFamily: "var(--font-display)", lineHeight: 1.08 }}>
          People getting hired.
        </h2>
        <div className="mt-12 grid md:grid-cols-3 gap-8 md:gap-10">
          {QUOTES.map((q) => (
            <figure key={q.name} className="pt-6" style={{ borderTop: `2px solid rgba(52,211,153,0.5)` }}>
              <blockquote className="text-lg leading-snug" style={{ fontFamily: "var(--font-display)" }}>
                “{q.body}”
              </blockquote>
              <figcaption className="mt-4 text-sm" style={{ color: MUTED }}>
                {q.name} · {q.role}
              </figcaption>
            </figure>
          ))}
        </div>
      </section>

      {/* ── Pricing ── */}
      <section id="pricing" className="py-20 md:py-28" style={{ background: "rgba(244,242,236,0.025)", borderTop: `1px solid ${LINE}`, borderBottom: `1px solid ${LINE}` }}>
        <div className="max-w-6xl mx-auto px-5 sm:px-8">
          <p className="text-[11px] uppercase tracking-[0.22em] font-mono mb-4" style={{ color: ACCENT }}>
            Pricing
          </p>
          <h2 className="text-3xl sm:text-4xl md:text-5xl" style={{ fontFamily: "var(--font-display)", lineHeight: 1.08 }}>
            Free to start. Pro when serious.
          </h2>
          <div className="mt-12 grid md:grid-cols-3 gap-4 items-stretch">
            {PLANS.map((p) => (
              <article
                key={p.name}
                className="rounded-2xl p-7 flex flex-col"
                style={{
                  background: p.featured ? "rgba(52,211,153,0.08)" : "rgba(244,242,236,0.03)",
                  border: `1px solid ${p.featured ? "rgba(52,211,153,0.45)" : LINE}`,
                }}
              >
                <h3 className="text-lg" style={{ fontFamily: "var(--font-display)" }}>{p.name}</h3>
                <p className="mt-3 flex items-baseline gap-2">
                  <span className="text-4xl font-mono">{p.price}</span>
                </p>
                <p className="text-xs mt-1 mb-6" style={{ color: FAINT }}>{p.per}</p>
                <ul className="space-y-2.5 mb-8">
                  {p.points.map((pt) => (
                    <li key={pt} className="flex items-start gap-2.5 text-sm" style={{ color: MUTED }}>
                      <span className="mt-[7px] h-1.5 w-1.5 rounded-full shrink-0" style={{ background: ACCENT }} />
                      {pt}
                    </li>
                  ))}
                </ul>
                <Link
                  to="/register"
                  className="mt-auto text-center rounded-full px-6 py-3 text-sm font-medium transition-transform duration-200 hover:scale-[1.02] active:scale-[0.98]"
                  style={p.featured ? { background: ACCENT, color: "#000" } : { border: `1px solid ${LINE}`, color: PAPER }}
                >
                  Get started
                </Link>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ── FAQ ── */}
      <section id="faq" className="max-w-3xl mx-auto px-5 sm:px-8 py-20 md:py-28">
        <h2 className="text-3xl sm:text-4xl md:text-5xl mb-10" style={{ fontFamily: "var(--font-display)", lineHeight: 1.08 }}>
          Questions, answered.
        </h2>
        <div>
          {FAQS.map((f) => (
            <details key={f.q} className="py-5 group" style={{ borderBottom: `1px solid ${LINE}` }}>
              <summary className="cursor-pointer list-none flex items-center justify-between gap-4 text-base sm:text-lg" style={{ fontFamily: "var(--font-display)" }}>
                {f.q}
                <span className="shrink-0 text-sm font-mono transition-transform group-open:rotate-45" style={{ color: ACCENT }}>+</span>
              </summary>
              <p className="mt-3 text-sm sm:text-base leading-relaxed max-w-[62ch]" style={{ color: MUTED }}>{f.a}</p>
            </details>
          ))}
        </div>
      </section>

      {/* ── Final CTA ── */}
      <section className="px-5 sm:px-8 pb-24 pt-4 text-center">
        <h2 className="text-4xl sm:text-5xl md:text-6xl max-w-[18ch] mx-auto" style={{ fontFamily: "var(--font-display)", lineHeight: 1.05 }}>
          Your next chapter starts here.
        </h2>
        <div className="mt-10">
          <Link to="/register" className="inline-block rounded-full px-12 py-4 text-base font-medium text-black transition-transform duration-200 hover:scale-[1.03] active:scale-[0.98]" style={{ background: ACCENT }}>
            Get started
          </Link>
          <p className="mt-4 text-sm" style={{ color: FAINT }}>
            Free forever plan · No credit card
          </p>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="px-5 sm:px-8 py-10" style={{ borderTop: `1px solid ${LINE}` }}>
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-5">
          <Link to="/" className="text-lg" style={{ fontFamily: "var(--font-display)" }}>
            CareerOS
          </Link>
          <nav className="flex items-center gap-6">
            {NAV_LINKS.map(({ label, href }) => (
              <a key={label} href={href} className="text-xs transition-colors hover:text-white" style={{ color: FAINT }}>
                {label}
              </a>
            ))}
          </nav>
          <p className="text-xs" style={{ color: FAINT }}>© 2026 CareerOS. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
