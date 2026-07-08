"""
Pulls job listings from companies hosted on Lever.
Public endpoint, no auth needed: https://api.lever.co/v0/postings/{company}?mode=json

To find a company's Lever slug:
  1. Their careers page often redirects to jobs.lever.co/<company>
  2. Test it: https://api.lever.co/v0/postings/<company>?mode=json
     If you get a JSON list of jobs back, the slug is correct.
"""

import requests

BASE_URL = "https://api.lever.co/v0/postings/{company}"


def fetch_jobs(company: str, timeout: int = 15) -> list[dict]:
    """Fetch raw job postings for a single company's Lever board."""
    url = BASE_URL.format(company=company)
    try:
        resp = requests.get(url, params={"mode": "json"}, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        print(f"[lever] failed for '{company}': {e}")
        return []

    jobs = []
    for job in data:
        categories = job.get("categories", {})
        jobs.append({
            "title": job.get("text", ""),
            "company": company,
            "location": categories.get("location", "Not specified"),
            "posted": _epoch_to_date(job.get("createdAt")),
            "source": "Lever",
            "apply_url": job.get("hostedUrl", ""),
            "raw_content": job.get("descriptionPlain", ""),
        })
    return jobs


def _epoch_to_date(ms):
    if not ms:
        return ""
    import datetime
    try:
        return datetime.datetime.utcfromtimestamp(ms / 1000).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return ""
