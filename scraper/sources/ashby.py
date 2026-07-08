"""
Pulls job listings from companies hosted on Ashby.
Public endpoint, no auth needed: https://api.ashbyhq.com/posting-api/job-board/{company}

To find a company's Ashby slug:
  1. Their careers page often redirects to jobs.ashbyhq.com/<company>
  2. Test it: https://api.ashbyhq.com/posting-api/job-board/<company>
     If you get JSON back, the slug is correct.
"""

import requests

BASE_URL = "https://api.ashbyhq.com/posting-api/job-board/{company}"


def fetch_jobs(company: str, timeout: int = 15) -> list[dict]:
    """Fetch raw job postings for a single company's Ashby board."""
    url = BASE_URL.format(company=company)
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        print(f"[ashby] failed for '{company}': {e}")
        return []

    jobs = []
    for job in data.get("jobs", []):
        jobs.append({
            "title": job.get("title", ""),
            "company": company,
            "location": job.get("location", "Not specified"),
            "posted": (job.get("publishedAt") or "")[:10],
            "source": "Ashby",
            "apply_url": job.get("jobUrl", ""),
            "raw_content": job.get("descriptionPlain", "") or "",
        })
    return jobs
