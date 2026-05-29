# AgentForge Career OS

AgentForge is an AI-powered career operating system that helps people discover internships, jobs, research programs, hackathons, scholarships, and networking opportunities — then turns those results into a guided action plan.

## What it does

- Finds and ranks opportunities based on a user’s profile, goals, and preferences
- Uses specialized agents for internships, jobs, research, resume tailoring, interview prep, networking, and monitoring
- Maintains memory for skills, target locations, applications, interview notes, and career goals
- Runs a daily discovery loop so the system keeps working even when the user is not searching manually

## Product vision

The product is designed as a planner-first multi-agent system:

1. The user states a goal.
2. A planner breaks the goal into subtasks.
3. Domain agents search, score, prepare, and track outcomes.
4. A memory layer stores preferences and outcomes so future recommendations improve.

## Frontend structure

- `src/pages/Landing.tsx` — product story, architecture, agent fleet, workflow, and roadmap
- `src/pages/Dashboard.tsx` — daily planner view, matches, application pipeline, and activity feed
- `src/pages/Onboarding.tsx` — captures profile, skills, preferences, and goals

## Suggested core agents

- Planner Agent
- Internship Agent
- Job Agent
- Research Agent
- Resume Agent
- Interview Agent
- Networking Agent
- Opportunity Monitor

## Next steps

- Connect the frontend to a backend search/memory service
- Add persisted user profiles and application tracking
- Add source adapters for internship/job sites and company career pages
- Add notifications for new matches and deadlines
- Expand interview prep and networking automation

## Notes

For the full concept and system breakdown, see `docs/product-vision.md`.
