"""
Pulls job listings from companies hosted on Greenhouse.
Public endpoint, no auth needed: https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true

To find a company's board token:
  1. Go to their careers page (often careers.company.com or company.com/careers)
  2. If it's a Greenhouse-hosted board, the URL or page source will contain
     "boards.greenhouse.io/<token>" or "job-boards.greenhouse.io/<token>"
  3. Test it: https://boards-api.greenhouse.io/v1/boards/<token>/jobs
     If you get a JSON list of jobs back, the token is correct.
"""

import requests

BASE_URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


def fetch_jobs(token: str, timeout: int = 15) -> list[dict]:
    """Fetch raw job postings for a single company's Greenhouse board."""
    url = BASE_URL.format(token=token)
    try:
        resp = requests.get(url, params={"content": "true"}, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        print(f"[greenhouse] failed for '{token}': {e}")
        return []

    jobs = []
    for job in data.get("jobs", []):
        jobs.append({
            "title": job.get("title", ""),
            "company": token,
            "location": (job.get("location") or {}).get("name", "Not specified"),
            "posted": job.get("updated_at", "")[:10],
            "source": "Greenhouse",
            "apply_url": job.get("absolute_url", ""),
            "raw_content": job.get("content", ""),  # HTML description, used for keyword/salary matching
        })
    return jobs
