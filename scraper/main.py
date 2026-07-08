"""
Orchestrates the daily job pull:
  1. Load curated companies list
  2. Fetch jobs from each source (Greenhouse / Lever / Ashby boards + RemoteOK)
  3. Apply filters (role, experience level, freshness, salary floor)
  4. Dedup + rank
  5. Trim to top N and write data/jobs.json

Run manually:  python scraper/main.py
Run via cron:  see .github/workflows/daily.yml
"""

import json
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from sources import greenhouse, lever, ashby, remoteok
import filters

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMPANIES_FILE = os.path.join(SCRIPT_DIR, "companies.json")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "..", "docs", "data", "jobs.json")

MAX_AGE_DAYS = 7          # "up to a week old" per your preference
TOP_N = 5                 # daily digest size
MIN_SALARY_LPA = 10.0


def load_companies():
    with open(COMPANIES_FILE, "r") as f:
        data = json.load(f)
    return data.get("companies", [])


def fetch_all_company_board_jobs(companies):
    all_jobs = []
    for entry in companies:
        platform = entry.get("platform")
        token = entry.get("token")
        name = entry.get("name", token)

        if platform == "greenhouse":
            jobs = greenhouse.fetch_jobs(token)
        elif platform == "lever":
            jobs = lever.fetch_jobs(token)
        elif platform == "ashby":
            jobs = ashby.fetch_jobs(token)
        else:
            print(f"[main] unknown platform '{platform}' for {name}, skipping")
            continue

        for job in jobs:
            job["company"] = name  # use friendly display name
        all_jobs.extend(jobs)
        print(f"[main] {name} ({platform}): {len(jobs)} jobs fetched")

    return all_jobs


def main():
    companies = load_companies()
    curated_names = {c["name"].lower() for c in companies}

    print("[main] fetching company career-page boards...")
    board_jobs = fetch_all_company_board_jobs(companies)

    print("[main] fetching RemoteOK...")
    remote_jobs = remoteok.fetch_jobs()
    print(f"[main] RemoteOK: {len(remote_jobs)} jobs fetched")

    all_jobs = board_jobs + remote_jobs
    print(f"[main] total raw jobs collected: {len(all_jobs)}")

    # ---- Filtering pipeline ----
    filtered = [j for j in all_jobs if filters.matches_role(j)]
    print(f"[main] after role filter: {len(filtered)}")

    filtered = [j for j in filtered if filters.matches_experience(j)]
    print(f"[main] after experience filter: {len(filtered)}")

    filtered = [j for j in filtered if filters.is_fresh(j, MAX_AGE_DAYS)]
    print(f"[main] after freshness filter (<= {MAX_AGE_DAYS} days): {len(filtered)}")

    for j in filtered:
        j["work_mode"] = filters.classify_work_mode(j)
        j["salary_tag"] = filters.extract_salary(j)

    filtered = [j for j in filtered if filters.passes_location(j)]
    print(f"[main] after location filter: {len(filtered)}")

    filtered = [j for j in filtered if filters.meets_salary_floor(j, MIN_SALARY_LPA)]
    print(f"[main] after salary floor filter: {len(filtered)}")

    filtered = filters.dedup(filtered)
    print(f"[main] after dedup: {len(filtered)}")

    ranked = filters.rank(filtered, curated_names)
    top_jobs = ranked[:TOP_N]

    # Clean up internal-only fields before writing output
    output_jobs = []
    for j in top_jobs:
        output_jobs.append({
            "title": j.get("title"),
            "company": j.get("company"),
            "location": j.get("location"),
            "work_mode": j.get("work_mode"),
            "salary": j.get("salary_tag"),
            "posted": j.get("posted"),
            "source": j.get("source"),
            "apply_url": j.get("apply_url"),
        })

    result = {
        "generated_at": datetime.datetime.now().astimezone().isoformat(),
        "count": len(output_jobs),
        "jobs": output_jobs,
    }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(result, f, indent=2)

    print(f"[main] wrote {len(output_jobs)} jobs to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
