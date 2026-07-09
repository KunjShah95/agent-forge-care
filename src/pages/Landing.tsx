import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

const VIDEO_URL =
  "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260314_131748_f2ca2a28-fed7-44c8-b9a9-bd9acdd5ec31.mp4";

const NAV_LINKS = [
  { label: "Home",     href: "#",        active: true },
  { label: "Studio",   href: "#tools" },
  { label: "About",    href: "#mission" },
  { label: "Journal",  href: "#process" },
  { label: "Reach Us", href: "#cta" },
];

const TOOLS = [
  {
    num: "01",
    name: "Resume Studio",
    tagline: "Rewritten with purpose",
    desc: "Each resume tailored to the role — keyword-matched, voice-preserved, ATS-ready. Not polished. Positioned.",
  },
  {
    num: "02",
    name: "Interview Prep",
    tagline: "Walk in ready",
    desc: "Mock sessions shaped around your background. Real feedback, model answers, and no generic scripts.",
  },
  {
    num: "03",
    name: "Research Agent",
    tagline: "Know before you go",
    desc: "Deep company briefs — culture signals, recent news, interview patterns, and the things Glassdoor won't say.",
  },
  {
    num: "04",
    name: "Opportunity Monitor",
    tagline: "Never miss a signal",
    desc: "Agents scan 50+ sources around the clock and surface roles that fit before the window closes.",
  },
  {
    num: "05",
    name: "Networking Hub",
    tagline: "Warm introductions",
    desc: "Outreach drafts, relationship tracking, follow-up timing — the infrastructure for connections that actually land.",
  },
  {
    num: "06",
    name: "Career Coach",
    tagline: "Strategy over hustle",
    desc: "Honest, data-backed guidance built on your actual situation — not a motivational template.",
  },
];

const STEPS = [
  {
    num: "01",
    title: "Share your vision",
    desc: "Tell the system where you want to go and what you've built so far. That's all it needs to begin.",
  },
  {
    num: "02",
    title: "Agents get to work",
    desc: "Eight specialists discover roles, research companies, optimize materials, and track every deadline — without being asked twice.",
  },
  {
    num: "03",
    title: "You make the moves",
    desc: "With full intelligence in hand, not guesswork. The work is done. You choose what matters.",
  },
];

const STATS = [
  { value: "24/7", label: "Opportunity monitoring" },
  { value: "8",    label: "Specialist agents" },
  { value: "50+",  label: "Sources scanned daily" },
  { value: "78%",  label: "Match accuracy" },
];

const MARQUEE_ITEMS = [
  "Discover", "Build", "Connect", "Thrive",
  "Discover", "Build", "Connect", "Thrive",
];

const MUTED = "hsl(240, 4%, 66%)";
const BORDER = "rgba(255,255,255,0.08)";
const CARD_BG = "rgba(255,255,255,0.03)";

function useReveal<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          obs.disconnect();
        }
      },
      { threshold: 0.1 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return { ref, visible };
}

function Reveal({
  children,
  delay = 0,
  className = "",
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  const { ref, visible } = useReveal<HTMLDivElement>();
  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? "translateY(0)" : "translateY(28px)",
        transition: `opacity 0.75s ease-out ${delay}s, transform 0.75s ease-out ${delay}s`,
      }}
    >
      {children}
    </div>
  );
}

export default function Landing() {
  return (
    <div
      style={{
        background: "hsl(201, 100%, 13%)",
        fontFamily: "var(--font-body)",
        color: "white",
      }}
    >
      {/* ── Hero ── */}
      <section className="min-h-screen relative overflow-hidden">
        <video
          autoPlay
          loop
          muted
          playsInline
          className="absolute inset-0 w-full h-full object-cover z-0"
        >
          <source src={VIDEO_URL} type="video/mp4" />
        </video>

        <div className="relative z-10 flex flex-col min-h-screen">
          {/* Nav */}
          <nav className="px-8 py-6">
            <div className="max-w-7xl mx-auto flex items-center justify-between">
              <Link
                to="/"
                className="text-3xl tracking-tight text-white"
                style={{ fontFamily: "var(--font-display)" }}
              >
                Velorah<sup className="text-xs">®</sup>
              </Link>

              <ul className="hidden md:flex items-center gap-8">
                {NAV_LINKS.map(({ label, href, active }) => (
                  <li key={label}>
                    <a
                      href={href}
                      style={{ color: active ? "white" : MUTED }}
                      className="text-sm transition-colors duration-200 hover:text-white"
                    >
                      {label}
                    </a>
                  </li>
                ))}
              </ul>

              <a href="#cta">
                <button className="liquid-glass rounded-full px-6 py-2.5 text-sm text-white transition-transform duration-200 hover:scale-[1.03] cursor-pointer">
                  Begin Journey
                </button>
              </a>
            </div>
          </nav>

          {/* Hero content */}
          <div className="flex flex-col items-center text-center px-6 pt-32 pb-40">
            <h1
              className="animate-fade-rise text-5xl sm:text-7xl md:text-8xl font-normal max-w-7xl"
              style={{
                fontFamily: "var(--font-display)",
                lineHeight: 0.95,
                letterSpacing: "-2.46px",
              }}
            >
              Where{" "}
              <em className="not-italic" style={{ color: MUTED }}>
                dreams
              </em>{" "}
              rise{" "}
              <em className="not-italic" style={{ color: MUTED }}>
                through the silence.
              </em>
            </h1>

            <p
              className="animate-fade-rise-delay mt-8 max-w-2xl text-base sm:text-lg leading-relaxed"
              style={{ color: MUTED }}
            >
              We're designing tools for deep thinkers, bold creators, and quiet
              rebels. Amid the chaos, we build digital spaces for sharp focus
              and inspired work.
            </p>

            <a href="#cta" className="animate-fade-rise-delay-2 mt-12">
              <button className="liquid-glass rounded-full px-14 py-5 text-base text-white transition-transform duration-200 hover:scale-[1.03] cursor-pointer">
                Begin Journey
              </button>
            </a>
          </div>
        </div>
      </section>

      {/* ── Marquee strip ── */}
      <div
        className="overflow-hidden py-6"
        style={{ borderTop: `1px solid ${BORDER}`, borderBottom: `1px solid ${BORDER}` }}
      >
        <div className="flex w-max animate-marquee select-none">
          {[...MARQUEE_ITEMS, ...MARQUEE_ITEMS].map((item, i) => (
            <span
              key={i}
              className="px-10 text-sm tracking-[0.2em] uppercase"
              style={{ color: MUTED }}
            >
              {item}
              <span className="mx-10 opacity-30">·</span>
            </span>
          ))}
        </div>
      </div>

      {/* ── Mission ── */}
      <section
        id="mission"
        className="px-8 py-32"
        style={{ borderBottom: `1px solid ${BORDER}` }}
      >
        <div className="max-w-7xl mx-auto grid md:grid-cols-2 gap-16 items-start">
          <Reveal>
            <p
              className="text-4xl sm:text-5xl leading-tight"
              style={{ fontFamily: "var(--font-display)", lineHeight: 1.1 }}
            >
              <em className="not-italic" style={{ color: MUTED }}>
                The best career moves
              </em>{" "}
              aren't made in a rush.
            </p>
          </Reveal>

          <Reveal delay={0.15}>
            <p
              className="text-base sm:text-lg leading-relaxed mb-8"
              style={{ color: MUTED }}
            >
              They're made with clarity, the right intelligence, and time to
              think. Velorah gives you an eight-agent system that handles the
              search, the prep, and the research — so you can focus on what only
              you can do.
            </p>
            <ul className="space-y-4">
              {[
                "Eight specialists. One shared memory. Zero repetition.",
                "Runs continuously — you come back to results, not tasks.",
              ].map((point) => (
                <li
                  key={point}
                  className="flex items-start gap-3 text-sm"
                  style={{ color: MUTED }}
                >
                  <span className="mt-1.5 h-1 w-1 rounded-full flex-shrink-0 bg-white opacity-40" />
                  {point}
                </li>
              ))}
            </ul>
          </Reveal>
        </div>
      </section>

      {/* ── Tools ── */}
      <section id="tools" className="px-8 py-32" style={{ borderBottom: `1px solid ${BORDER}` }}>
        <div className="max-w-7xl mx-auto">
          <Reveal className="mb-16">
            <span
              className="text-xs tracking-[0.2em] uppercase"
              style={{ color: MUTED }}
            >
              What we build
            </span>
            <h2
              className="mt-4 text-4xl sm:text-5xl font-normal"
              style={{ fontFamily: "var(--font-display)", lineHeight: 1.05 }}
            >
              Six tools. One direction.
            </h2>
          </Reveal>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-px"
            style={{ border: `1px solid ${BORDER}` }}>
            {TOOLS.map((tool, i) => (
              <Reveal key={tool.num} delay={i * 0.07}>
                <div
                  className="p-8 h-full flex flex-col gap-4 transition-colors duration-300"
                  style={{ background: CARD_BG, borderRight: `1px solid ${BORDER}`, borderBottom: `1px solid ${BORDER}` }}
                  onMouseEnter={(e) =>
                    ((e.currentTarget as HTMLDivElement).style.background =
                      "rgba(255,255,255,0.06)")
                  }
                  onMouseLeave={(e) =>
                    ((e.currentTarget as HTMLDivElement).style.background = CARD_BG)
                  }
                >
                  <span
                    className="text-xs tracking-widest font-mono"
                    style={{ color: MUTED }}
                  >
                    {tool.num}
                  </span>
                  <div>
                    <h3
                      className="text-xl font-normal mb-1"
                      style={{ fontFamily: "var(--font-display)" }}
                    >
                      {tool.name}
                    </h3>
                    <p className="text-sm italic" style={{ color: MUTED }}>
                      {tool.tagline}
                    </p>
                  </div>
                  <p className="text-sm leading-relaxed mt-auto" style={{ color: MUTED }}>
                    {tool.desc}
                  </p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── Process ── */}
      <section id="process" className="px-8 py-32" style={{ borderBottom: `1px solid ${BORDER}` }}>
        <div className="max-w-7xl mx-auto">
          <Reveal className="mb-16">
            <span
              className="text-xs tracking-[0.2em] uppercase"
              style={{ color: MUTED }}
            >
              How it works
            </span>
            <h2
              className="mt-4 text-4xl sm:text-5xl font-normal"
              style={{ fontFamily: "var(--font-display)", lineHeight: 1.05 }}
            >
              Three steps.{" "}
              <em className="not-italic" style={{ color: MUTED }}>
                Then clarity.
              </em>
            </h2>
          </Reveal>

          <div className="grid md:grid-cols-3 gap-12">
            {STEPS.map((step, i) => (
              <Reveal key={step.num} delay={i * 0.12}>
                <div
                  className="pb-8"
                  style={{ borderBottom: `1px solid ${BORDER}` }}
                >
                  <span
                    className="text-xs tracking-widest font-mono block mb-6"
                    style={{ color: MUTED }}
                  >
                    {step.num}
                  </span>
                  <h3
                    className="text-2xl font-normal mb-4"
                    style={{ fontFamily: "var(--font-display)" }}
                  >
                    {step.title}
                  </h3>
                  <p className="text-sm leading-relaxed" style={{ color: MUTED }}>
                    {step.desc}
                  </p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ── Stats ── */}
      <section className="px-8 py-24" style={{ borderBottom: `1px solid ${BORDER}` }}>
        <div className="max-w-7xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-px"
          style={{ border: `1px solid ${BORDER}` }}>
          {STATS.map((stat, i) => (
            <Reveal key={stat.label} delay={i * 0.08}>
              <div
                className="px-8 py-10 text-center"
                style={{ background: CARD_BG, borderRight: `1px solid ${BORDER}` }}
              >
                <p
                  className="text-5xl font-normal mb-2"
                  style={{ fontFamily: "var(--font-display)" }}
                >
                  {stat.value}
                </p>
                <p className="text-xs tracking-wide uppercase" style={{ color: MUTED }}>
                  {stat.label}
                </p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ── CTA ── */}
      <section id="cta" className="px-8 py-40 text-center">
        <Reveal>
          <span
            className="text-xs tracking-[0.2em] uppercase block mb-6"
            style={{ color: MUTED }}
          >
            Ready when you are
          </span>
          <h2
            className="text-5xl sm:text-6xl md:text-7xl font-normal max-w-3xl mx-auto mb-12"
            style={{
              fontFamily: "var(--font-display)",
              lineHeight: 1.0,
              letterSpacing: "-1.5px",
            }}
          >
            Your next chapter{" "}
            <em className="not-italic" style={{ color: MUTED }}>
              starts here.
            </em>
          </h2>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link to="/register">
              <button className="liquid-glass rounded-full px-12 py-4 text-base text-white transition-transform duration-200 hover:scale-[1.03] cursor-pointer">
                Begin Journey
              </button>
            </Link>
            <Link
              to="/login"
              className="text-sm transition-colors duration-200 px-6 py-4"
              style={{ color: MUTED }}
              onMouseEnter={(e) => ((e.currentTarget as HTMLAnchorElement).style.color = "white")}
              onMouseLeave={(e) => ((e.currentTarget as HTMLAnchorElement).style.color = MUTED)}
            >
              Already a member →
            </Link>
          </div>
        </Reveal>
      </section>

      {/* ── Footer ── */}
      <footer
        className="px-8 py-10"
        style={{ borderTop: `1px solid ${BORDER}` }}
      >
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
          <Link
            to="/"
            className="text-xl tracking-tight text-white"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Velorah<sup className="text-xs">®</sup>
          </Link>

          <nav className="flex items-center gap-8">
            {NAV_LINKS.map(({ label, href }) => (
              <a
                key={label}
                href={href}
                className="text-xs tracking-wide transition-colors duration-200 hover:text-white"
                style={{ color: MUTED }}
              >
                {label}
              </a>
            ))}
          </nav>

          <p className="text-xs" style={{ color: MUTED }}>
            © 2026 Velorah. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
