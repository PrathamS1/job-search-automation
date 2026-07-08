"""
Filtering, deduplication, ranking, and salary-tagging logic.

Design decisions (so this stays maintainable):
- Everything works off the `raw_content` field (job description text) plus title/location.
- Salary detection is best-effort text matching. Many Indian job posts don't
  disclose salary at all -- those aren't dropped, just marked "Not disclosed"
  so you can judge for yourself instead of losing real openings.
- "Freshness" cutoff is configurable (default 7 days per your preference).
"""

import re
import datetime
from difflib import SequenceMatcher

ROLE_KEYWORDS = [
    "web developer", "web development", "software engineer", "software developer",
    "frontend", "front-end", "front end", "ui/ux", "ui ux", "ux designer",
    "ui designer", "product designer", "react developer", "javascript developer",
    "full stack", "fullstack", "sde", "swe",
]

REMOTE_KEYWORDS = ["remote", "work from home", "wfh", "distributed"]
HYBRID_KEYWORDS = ["hybrid"]

JUNIOR_KEYWORDS = [
    "junior", "entry level", "entry-level", "graduate", "associate",
    "0-1 year", "0-2 years", "1 year", "1-2 years", "1-3 years", "fresher",
]
SENIOR_EXCLUDE_KEYWORDS = [
    "senior", "staff", "principal", "lead", "10+ years", "8+ years",
    "7+ years", "6+ years", "5+ years", "director", "vp ", "head of",
]

SALARY_PATTERN = re.compile(
    r"(?:₹|rs\.?|inr)?\s?([\d,.]+)\s?(lpa|lakh|lakhs)", re.IGNORECASE
)


def matches_role(job: dict) -> bool:
    text = f"{job.get('title','')} {job.get('raw_content','')}".lower()
    return any(kw in text for kw in ROLE_KEYWORDS)


def matches_experience(job: dict) -> bool:
    """
    Best-effort: include if it looks junior/fresher-friendly, or if no
    seniority signal is present at all (many postings don't state a level).
    Exclude only if it explicitly reads senior/lead and shows no junior signal.
    """
    text = f"{job.get('title','')} {job.get('raw_content','')}".lower()
    has_junior_signal = any(kw in text for kw in JUNIOR_KEYWORDS)
    has_senior_signal = any(kw in text for kw in SENIOR_EXCLUDE_KEYWORDS)
    if has_senior_signal and not has_junior_signal:
        return False
    return True


def classify_work_mode(job: dict) -> str:
    text = f"{job.get('title','')} {job.get('location','')} {job.get('raw_content','')}".lower()
    if any(kw in text for kw in REMOTE_KEYWORDS):
        return "Remote"
    if any(kw in text for kw in HYBRID_KEYWORDS):
        return "Hybrid"
    return "On-site"


def extract_salary(job: dict) -> str:
    if job.get("salary_min") and job.get("salary_max"):
        return f"${job['salary_min']:,} - ${job['salary_max']:,} (USD, RemoteOK)"
    text = job.get("raw_content", "") or ""
    match = SALARY_PATTERN.search(text)
    if match:
        return match.group(0).strip()
    return "Not disclosed"

def meets_salary_floor(job: dict, min_lpa: float = 10.0) -> bool:
    """
    Best-effort filter: only DROPS a job if a salary is explicitly stated
    AND it's clearly below the floor. If salary isn't disclosed, we keep
    the job (can't verify, but shouldn't lose real openings over it).
    """
    salary_str = job.get("salary_tag", "")
    if salary_str == "Not disclosed":
        return True
    numbers = re.findall(r"[\d.]+", salary_str.replace(",", ""))
    if not numbers:
        return True
    try:
        value = float(numbers[0])
    except ValueError:
        return True
    if "lakh" in salary_str.lower() or "lpa" in salary_str.lower():
        return value >= min_lpa
    return True  # unit unclear (e.g. USD RemoteOK) -- don't drop, just show as-is


def is_fresh(job: dict, max_age_days: int = 7) -> bool:
    posted = job.get("posted")
    if not posted:
        return True  # unknown date -- keep rather than drop
    try:
        posted_date = datetime.datetime.strptime(posted, "%Y-%m-%d").date()
    except ValueError:
        return True
    age = (datetime.date.today() - posted_date).days
    return age <= max_age_days


def dedup(jobs: list[dict]) -> list[dict]:
    """Remove near-duplicate postings (same company + very similar title)."""
    unique = []
    for job in jobs:
        is_dup = False
        for seen in unique:
            if seen["company"].lower() == job["company"].lower():
                similarity = SequenceMatcher(
                    None, seen["title"].lower(), job["title"].lower()
                ).ratio()
                if similarity > 0.85:
                    is_dup = True
                    break
        if not is_dup:
            unique.append(job)
    return unique


def rank(jobs: list[dict], curated_companies: set) -> list[dict]:
    """
    Sort priority (earlier = ranked higher):
      1. Curated 'good' companies first
      2. Remote before hybrid before on-site
      3. Most recently posted first
    """
    mode_rank = {"Remote": 0, "Hybrid": 1, "On-site": 2}

    return sorted(
        jobs,
        key=lambda j: (
            0 if j["company"].lower() in curated_companies else 1,
            mode_rank.get(j.get("work_mode"), 2),
            j.get("posted") or "0000-00-00",
        ),
        reverse=False,
    )
