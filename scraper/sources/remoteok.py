"""
Pulls remote job listings from RemoteOK's public API.
https://remoteok.com/api  -> returns a JSON array; first element is metadata, skip it.

No auth needed, but RemoteOK asks that you set a descriptive User-Agent
and not hammer the endpoint (we call it once per day, so we're fine).
"""

import requests

URL = "https://remoteok.com/api"
HEADERS = {"User-Agent": "job-search-automation (personal use, daily digest)"}


def fetch_jobs(timeout: int = 15) -> list[dict]:
    try:
        resp = requests.get(URL, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        print(f"[remoteok] failed: {e}")
        return []

    jobs = []
    for job in data:
        if "id" not in job:
            continue  # skip the metadata/legal-notice first element
        jobs.append({
            "title": job.get("position", ""),
            "company": job.get("company", ""),
            "location": job.get("location", "Remote"),
            "posted": (job.get("date") or "")[:10],
            "source": "RemoteOK",
            "apply_url": job.get("url", ""),
            "raw_content": job.get("description", "") or "",
            "salary_min": job.get("salary_min"),
            "salary_max": job.get("salary_max"),
        })
    return jobs
