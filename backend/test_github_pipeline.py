"""End-to-end test: Run the full GitHub enrichment pipeline on a real profile."""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

async def main():
    test_url = "https://github.com/torvalds"

    print("=" * 70)
    print("[TEST] GITHUB ENRICHMENT PIPELINE -- E2E TEST")
    print(f"   Profile: {test_url}")
    print("=" * 70)

    from app.services.profile_scraper import (
        scrape_github_profile,
        scrape_github_commits,
        scrape_github_contributions,
        scrape_github_oss_contributions,
        analyze_github_for_skills,
        analyze_commit_history,
    )

    # ---- 1. Profile + Repos ----
    print("\n\n[STEP 1] scrape_github_profile() ... ", end="", flush=True)
    profile = await scrape_github_profile(test_url)
    if "error" in profile:
        print(f"FAILED: {profile['error']}")
        return
    print("OK")
    p = profile.get("profile", {})
    repos = profile.get("repositories", [])
    print(f"   Username: {profile.get('username')}")
    print(f"   Name: {p.get('name')}")
    print(f"   Bio: {str(p.get('bio', 'N/A'))[:120]}...")
    print(f"   Location: {p.get('location')}")
    print(f"   Followers: {p.get('followers')}")
    print(f"   Public repos: {p.get('public_repos')}")
    print(f"   Total stars: {profile.get('total_stars')}")
    print(f"   Languages: {', '.join(list(profile.get('languages', {}).keys())[:8])}")
    print(f"   Top repos (by stars):")
    for r in repos[:5]:
        print(f"     stars={r.get('stars', 0):>5}  {r.get('name')}  ({r.get('language', 'N/A')})")

    # ---- 2. Skill Analysis ----
    print("\n\n[STEP 2] analyze_github_for_skills() ... ", end="", flush=True)
    skills = await analyze_github_for_skills(profile)
    if "error" in skills:
        print(f"FAILED: {skills['error']}")
    else:
        print("OK")
        print(f"   Source: {skills.get('_source', 'N/A')}")
        sks = skills.get('skills', [])
        print(f"   Skills ({len(sks)}): {', '.join(sks[:10])}")
        print(f"   Primary languages: {', '.join(skills.get('primary_languages', []))}")
        print(f"   Experience level: {skills.get('experience_level')}")
        print(f"   Summary: {str(skills.get('summary', 'N/A'))[:200]}")

    # ---- 3. Commit History ----
    print("\n\n[STEP 3] scrape_github_commits() ... ", end="", flush=True)
    commits = await scrape_github_commits(test_url)
    if "error" in commits:
        print(f"FAILED: {commits['error']}")
    else:
        print("OK")
        print(f"   Total commits tracked: {commits.get('total_commits')}")
        print(f"   Total unique commits: {commits.get('total_unique_commits')}")
        print(f"   Active repos: {len(commits.get('commits_by_repo', {}))}")
        lang_keys = list(commits.get('commit_languages', {}).keys())[:5]
        print(f"   Languages in commits: {', '.join(lang_keys)}")
        print(f"   Avg commits/day: {commits.get('average_commits_per_day')}")
        freq = commits.get("commit_frequency", {})
        dow = freq.get("by_day_of_week", {})
        if dow:
            print(f"   Day-of-week: {', '.join(f'{d}: {c}' for d, c in dow.items())}")
        msgs = commits.get("commit_messages", [])
        print(f"   Sample commits ({min(3, len(msgs))}):")
        for msg in msgs[:3]:
            print(f"     - {str(msg)[:80]}")

    # ---- 4. Contribution Graph ----
    print("\n\n[STEP 4] scrape_github_contributions() ... ", end="", flush=True)
    contribs = await scrape_github_contributions(test_url)
    if "error" in contribs:
        print(f"FAILED: {contribs['error']}")
    else:
        print("OK")
        print(f"   Total contributions (1yr): {contribs.get('total_contributions')}")
        print(f"   Current streak: {contribs.get('current_streak')} days")
        print(f"   Longest streak: {contribs.get('longest_streak')} days")
        top_months = contribs.get("top_contribution_months", [])
        if top_months:
            print(f"   Top months:")
            for m in top_months[:4]:
                print(f"     - {m.get('month')}: {m.get('count')} contributions")
        cal = contribs.get("contribution_calendar", [])
        if cal:
            non_zero = [d for d in cal if d.get("count", 0) > 0]
            print(f"   Calendar entries: {len(cal)} days ({len(non_zero)} with contributions)")

    # ---- 5. OSS Contributions ----
    print("\n\n[STEP 5] scrape_github_oss_contributions() ... ", end="", flush=True)
    oss = await scrape_github_oss_contributions(test_url)
    if "error" in oss:
        print(f"FAILED: {oss['error']}")
    else:
        print("OK")
        print(f"   Total PRs: {oss.get('total_prs')}")
        print(f"   Total Issues: {oss.get('total_issues')}")
        print(f"   OSS PRs (external repos): {len(oss.get('pull_requests', []))}")
        print(f"   Repos contributed to: {len(oss.get('repos_contributed_to', []))}")
        for pr in oss.get("pull_requests", [])[:3]:
            print(f"     - [{pr.get('state')}] {pr.get('repo')}: {str(pr.get('title', ''))[:80]}")
        print(f"   Summary: {oss.get('summary', 'N/A')}")

    # ---- 6. Commit Analysis ----
    print("\n\n[STEP 6] analyze_commit_history() ... ", end="", flush=True)
    analysis = await analyze_commit_history(
        commit_data=commits if "error" not in commits else None,
        contribution_data=contribs if "error" not in contribs else None,
        oss_data=oss if "error" not in oss else None,
    )
    if "error" in analysis:
        print(f"FAILED: {analysis['error']}")
    else:
        print("OK")
        print(f"   Source: {analysis.get('_source', 'N/A')}")
        print(f"   Coding frequency: {analysis.get('coding_frequency')}")
        print(f"   Preferred work days: {', '.join(analysis.get('preferred_work_days', []))}")
        print(f"   Commit quality: {analysis.get('commit_quality')}")
        print(f"   Project focus: {analysis.get('project_focus')}")
        print(f"   OSS participation: {analysis.get('oss_participation')}")
        print(f"   Consistency score: {analysis.get('consistency_score')}/100")
        print(f"   Summary: {str(analysis.get('summary', 'N/A'))[:200]}")

    # ---- Summary ----
    print("\n" + "=" * 70)
    results = {}
    results["profile"] = "FAIL" if "error" in profile else "PASS"
    results["skills"] = "FAIL" if "error" in skills else "PASS"
    results["commits"] = "FAIL" if "error" in commits else "PASS"
    results["contribs"] = "FAIL" if "error" in contribs else "PASS"
    results["oss"] = "FAIL" if "error" in oss else "PASS"
    results["analysis"] = "FAIL" if "error" in analysis else "PASS"
    passed = sum(1 for v in results.values() if v == "PASS")
    total = len(results)
    print(f"\n   RESULTS: {passed}/{total} steps passed")
    for name, status in results.items():
        print(f"     [{status}] {name}")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
