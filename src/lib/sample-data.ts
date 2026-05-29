export type Opportunity = {
  id: string;
  title: string;
  company: string;
  logo: string;
  location: string;
  remote: boolean;
  type: "Internship" | "Full-time" | "Hackathon" | "Scholarship" | "Fellowship" | "Research";
  salary?: string;
  posted: string;
  deadline: string;
  matchScore: number;
  skills: string[];
  companySize: "Startup" | "Mid-size" | "Enterprise";
  matchReasons: string[];
};

export type Application = {
  id: string;
  opportunityId: string;
  title: string;
  company: string;
  logo: string;
  stage: "Saved" | "Applied" | "OA" | "Interview" | "Offer" | "Rejected";
  appliedDate: string;
  nextStep?: string;
  nextDate?: string;
  notes?: string;
};

export type Contact = {
  id: string;
  name: string;
  role: string;
  company: string;
  avatar: string;
  email: string;
  lastContact: string;
  status: "New" | "Reached out" | "Replied" | "Meeting" | "Closed";
};

export type AgentTask = {
  id: string;
  agent: string;
  action: string;
  timestamp: string;
  status: "running" | "complete" | "queued";
};

const logos = ["🟣","🟢","🔵","🟠","🔴","🟡","⚫","⚪","🟤"];

export const opportunities: Opportunity[] = [
  { id: "o1", title: "ML Research Intern", company: "Anthropic", logo: "🟣", location: "San Francisco, CA", remote: true, type: "Internship", salary: "$10k/mo", posted: "2d ago", deadline: "Dec 15", matchScore: 96, skills: ["Python","PyTorch","NLP","Research"], companySize: "Mid-size", matchReasons: ["Strong PyTorch portfolio","Prior NLP research","Open-source contributions"] },
  { id: "o2", title: "Software Engineer, New Grad", company: "Stripe", logo: "🟢", location: "Remote", remote: true, type: "Full-time", salary: "$185k", posted: "1d ago", deadline: "Jan 10", matchScore: 92, skills: ["TypeScript","React","Distributed Systems"], companySize: "Enterprise", matchReasons: ["TypeScript match 95%","Payment systems project"] },
  { id: "o3", title: "Product Engineer", company: "Linear", logo: "🔵", location: "New York, NY", remote: false, type: "Full-time", salary: "$170k", posted: "3d ago", deadline: "Dec 30", matchScore: 89, skills: ["React","Design","TypeScript"], companySize: "Startup", matchReasons: ["Product mindset","Design system experience"] },
  { id: "o4", title: "AI Safety Fellowship", company: "MATS Program", logo: "🟠", location: "Berkeley, CA", remote: false, type: "Fellowship", salary: "$8k stipend", posted: "5d ago", deadline: "Dec 20", matchScore: 88, skills: ["Research","Alignment","Writing"], companySize: "Mid-size", matchReasons: ["AI ethics coursework","Published essays"] },
  { id: "o5", title: "MLH Global Hack Week", company: "Major League Hacking", logo: "🔴", location: "Virtual", remote: true, type: "Hackathon", posted: "1d ago", deadline: "Dec 12", matchScore: 85, skills: ["Full-stack","Creativity"], companySize: "Mid-size", matchReasons: ["3 prior hackathon wins"] },
  { id: "o6", title: "Rhodes Scholarship", company: "Rhodes Trust", logo: "🟡", location: "Oxford, UK", remote: false, type: "Scholarship", salary: "Full tuition + stipend", posted: "1w ago", deadline: "Jan 31", matchScore: 76, skills: ["Leadership","Academics","Service"], companySize: "Enterprise", matchReasons: ["3.9 GPA","Leadership roles"] },
  { id: "o7", title: "Frontend Engineer Intern", company: "Vercel", logo: "⚫", location: "Remote", remote: true, type: "Internship", salary: "$9k/mo", posted: "4d ago", deadline: "Dec 28", matchScore: 94, skills: ["React","Next.js","TypeScript"], companySize: "Mid-size", matchReasons: ["Next.js expert","Open-source PRs"] },
  { id: "o8", title: "Quantitative Researcher", company: "Jane Street", logo: "⚪", location: "New York, NY", remote: false, type: "Full-time", salary: "$220k+", posted: "2d ago", deadline: "Jan 5", matchScore: 81, skills: ["OCaml","Math","Statistics"], companySize: "Enterprise", matchReasons: ["Strong math background"] },
  { id: "o9", title: "NSF REU - Computer Vision", company: "MIT CSAIL", logo: "🟤", location: "Cambridge, MA", remote: false, type: "Research", salary: "$7k stipend", posted: "6d ago", deadline: "Feb 1", matchScore: 90, skills: ["CV","Python","Research"], companySize: "Enterprise", matchReasons: ["Vision project portfolio"] },
  { id: "o10", title: "Founding Engineer", company: "Helia Labs", logo: "🟣", location: "San Francisco, CA", remote: true, type: "Full-time", salary: "$160k + equity", posted: "1d ago", deadline: "Open", matchScore: 87, skills: ["Full-stack","AI","Startup"], companySize: "Startup", matchReasons: ["Founder mindset","Shipped 4 side projects"] },
  { id: "o11", title: "Google Summer of Code", company: "Google", logo: "🟢", location: "Remote", remote: true, type: "Internship", salary: "$6k stipend", posted: "2w ago", deadline: "Mar 20", matchScore: 83, skills: ["Open-source","C++","Python"], companySize: "Enterprise", matchReasons: ["OSS contributions"] },
  { id: "o12", title: "Robotics Research Assistant", company: "Stanford SAIL", logo: "🔵", location: "Palo Alto, CA", remote: false, type: "Research", salary: "$25/hr", posted: "3d ago", deadline: "Dec 22", matchScore: 79, skills: ["ROS","Python","Robotics"], companySize: "Enterprise", matchReasons: ["Embedded experience"] },
];

export const applications: Application[] = [
  { id: "a1", opportunityId: "o1", title: "ML Research Intern", company: "Anthropic", logo: "🟣", stage: "Interview", appliedDate: "Nov 14", nextStep: "Technical interview", nextDate: "Dec 10", notes: "Recruiter loved the alignment paper" },
  { id: "a2", opportunityId: "o2", title: "Software Engineer, New Grad", company: "Stripe", logo: "🟢", stage: "OA", appliedDate: "Nov 20", nextStep: "OA due", nextDate: "Dec 8" },
  { id: "a3", opportunityId: "o3", title: "Product Engineer", company: "Linear", logo: "🔵", stage: "Applied", appliedDate: "Nov 25" },
  { id: "a4", opportunityId: "o7", title: "Frontend Intern", company: "Vercel", logo: "⚫", stage: "Saved", appliedDate: "—" },
  { id: "a5", opportunityId: "o10", title: "Founding Engineer", company: "Helia Labs", logo: "🟣", stage: "Offer", appliedDate: "Oct 30", nextStep: "Decide by", nextDate: "Dec 14", notes: "$170k base + 0.5% equity" },
  { id: "a6", opportunityId: "o8", title: "Quant Researcher", company: "Jane Street", logo: "⚪", stage: "Rejected", appliedDate: "Oct 12", notes: "Post-OA reject. Practice probability puzzles." },
  { id: "a7", opportunityId: "o4", title: "AI Safety Fellowship", company: "MATS", logo: "🟠", stage: "Interview", appliedDate: "Nov 1", nextStep: "Final round", nextDate: "Dec 11" },
  { id: "a8", opportunityId: "o9", title: "NSF REU - CV", company: "MIT CSAIL", logo: "🟤", stage: "Applied", appliedDate: "Nov 28" },
  { id: "a9", opportunityId: "o5", title: "MLH Hack Week", company: "MLH", logo: "🔴", stage: "Saved", appliedDate: "—" },
];

export const contacts: Contact[] = [
  { id: "c1", name: "Maya Patel", role: "University Recruiter", company: "Stripe", avatar: "MP", email: "maya@stripe.com", lastContact: "3d ago", status: "Replied" },
  { id: "c2", name: "Daniel Kim", role: "Engineering Manager", company: "Linear", avatar: "DK", email: "daniel@linear.app", lastContact: "1w ago", status: "Meeting" },
  { id: "c3", name: "Sarah Chen", role: "Research Scientist", company: "Anthropic", avatar: "SC", email: "sarah@anthropic.com", lastContact: "2d ago", status: "Replied" },
  { id: "c4", name: "James O'Connor", role: "CTO", company: "Helia Labs", avatar: "JO", email: "james@helia.dev", lastContact: "Today", status: "Meeting" },
  { id: "c5", name: "Priya Raman", role: "Recruiter", company: "Vercel", avatar: "PR", email: "priya@vercel.com", lastContact: "5d ago", status: "Reached out" },
  { id: "c6", name: "Alex Rivera", role: "Senior Engineer", company: "Google", avatar: "AR", email: "alex@google.com", lastContact: "—", status: "New" },
];

export const agentActivity: AgentTask[] = [
  { id: "t1", agent: "Planner Agent", action: "Coordinating weekly opportunity scan across 7 agents", timestamp: "Just now", status: "running" },
  { id: "t2", agent: "Opportunity Monitor", action: "Found 12 new matches above 80% threshold", timestamp: "2 min ago", status: "complete" },
  { id: "t3", agent: "Resume Agent", action: "Tailored resume for Anthropic ML Intern role", timestamp: "15 min ago", status: "complete" },
  { id: "t4", agent: "Interview Agent", action: "Generated 8 mock questions for Stripe OA", timestamp: "1h ago", status: "complete" },
  { id: "t5", agent: "Networking Agent", action: "Drafted outreach to 3 Linear engineers", timestamp: "3h ago", status: "complete" },
  { id: "t6", agent: "Research Agent", action: "Compiling Anthropic interview insights", timestamp: "Queued", status: "queued" },
  { id: "t7", agent: "Job Agent", action: "Scanning 240 new postings on Hacker News Who's Hiring", timestamp: "5h ago", status: "complete" },
];

export const pipelineData = [
  { stage: "Saved", count: 18 },
  { stage: "Applied", count: 12 },
  { stage: "OA", count: 5 },
  { stage: "Interview", count: 3 },
  { stage: "Offer", count: 1 },
];

export const weeklyActivity = [
  { day: "Mon", applications: 3, interviews: 1 },
  { day: "Tue", applications: 5, interviews: 0 },
  { day: "Wed", applications: 2, interviews: 2 },
  { day: "Thu", applications: 4, interviews: 1 },
  { day: "Fri", applications: 6, interviews: 0 },
  { day: "Sat", applications: 1, interviews: 0 },
  { day: "Sun", applications: 0, interviews: 1 },
];

export const skillDemand = [
  { skill: "TypeScript", demand: 92 },
  { skill: "Python", demand: 88 },
  { skill: "React", demand: 85 },
  { skill: "AI/ML", demand: 78 },
  { skill: "Rust", demand: 64 },
  { skill: "Go", demand: 58 },
];

export const funnelData = [
  { name: "Applied", value: 42, rate: "100%" },
  { name: "OA", value: 18, rate: "43%" },
  { name: "Interview", value: 9, rate: "21%" },
  { name: "Offer", value: 3, rate: "7%" },
];

export const upcomingDeadlines = [
  { id: "d1", title: "Stripe OA", company: "Stripe", date: "Dec 8", urgent: true },
  { id: "d2", title: "Anthropic Interview", company: "Anthropic", date: "Dec 10", urgent: true },
  { id: "d3", title: "MATS Final Round", company: "MATS Program", date: "Dec 11", urgent: false },
  { id: "d4", title: "Helia Offer Decision", company: "Helia Labs", date: "Dec 14", urgent: false },
  { id: "d5", title: "Anthropic App Closes", company: "Anthropic", date: "Dec 15", urgent: false },
];

export const interviewQuestions = {
  Behavioral: [
    "Tell me about a time you led a team through ambiguity.",
    "Describe your most impactful project and the tradeoffs.",
    "How do you handle disagreement with a manager?",
    "Walk me through a failure and what you learned.",
  ],
  Technical: [
    "Design a URL shortener that handles 1B requests/day.",
    "Implement LRU cache in TypeScript.",
    "Explain how React reconciliation works.",
    "Find the longest palindromic substring.",
  ],
  "System Design": [
    "Design Twitter's timeline service.",
    "How would you build a real-time collaborative editor?",
    "Architect a global CDN.",
  ],
  "ML/AI": [
    "Explain attention vs convolution.",
    "How do you evaluate an LLM?",
    "Design a recommendation system for opportunities.",
  ],
};

export const companies = [
  { id: "c1", name: "Anthropic", logo: "🟣", industry: "AI Research", size: "500-1000", glassdoor: 4.6, notes: "Mission-driven. Values alignment research." },
  { id: "c2", name: "Stripe", logo: "🟢", industry: "Fintech", size: "5000+", glassdoor: 4.5, notes: "Strong engineering culture. Writing intensive." },
  { id: "c3", name: "Linear", logo: "🔵", industry: "Productivity", size: "50-100", glassdoor: 4.8, notes: "Design obsessed. Small senior team." },
  { id: "c4", name: "Vercel", logo: "⚫", industry: "Dev Tools", size: "200-500", glassdoor: 4.4, notes: "Frontend leaders. Remote-first." },
  { id: "c5", name: "Helia Labs", logo: "🟣", industry: "AI Agents", size: "5-10", glassdoor: 4.9, notes: "Early stage. High equity upside." },
];
