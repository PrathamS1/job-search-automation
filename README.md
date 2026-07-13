# Daily Job Search Automation

Pulls fresh (≤7 day old) job listings matching your preferences — web dev / SWE / frontend /
UI-UX roles, ~1 year experience, remote-first (hybrid if salary justifies the city), 10+ LPA —
from company career pages (Greenhouse, Lever, Ashby) and RemoteOK, filters + dedupes + ranks
them, and writes the top 10 to `docs/data/jobs.json` once a day via GitHub Actions.

**Sources deliberately excluded:** LinkedIn and Naukri. Both block/prohibit automated scraping
in their Terms of Service — including them would risk your account and isn't something I'll
build. This pulls only from sources with genuinely public, allowed access.

## Setup (one-time)

1. **Push this to a new GitHub repo** (public, so GitHub Pages works for free):
   ```bash
   cd job-search-automation
   git init
   git add .
   git commit -m "Initial setup"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<repo-name>.git
   git push -u origin main
   ```

2. **Verify/expand `scraper/companies.json`.**
   The tokens in there are starter guesses for well-known companies — some may be wrong or
   outdated. For each company you care about:
   - Find their careers page.
   - If Greenhouse-hosted, the URL contains `boards.greenhouse.io/<token>` or
     `job-boards.greenhouse.io/<token>`.
   - If Lever-hosted: `jobs.lever.co/<token>`.
   - If Ashby-hosted: `jobs.ashbyhq.com/<token>`.
   - Test the token by opening the matching API URL in your browser (URLs are documented at
     the top of each file in `scraper/sources/`). If you get JSON job data back, it's correct.
   - Add as many companies as you like — this list doubles as your "good company" ranking
     boost, so the more you curate, the better matches you'll surface first.

3. **Enable GitHub Pages**: repo Settings → Pages → Deploy from branch → `main` → `/docs` (or
   `/root` if you restructure). Your page will be live at
   `https://<your-username>.github.io/<repo-name>/`.

4. **Trigger the first run manually**: repo → Actions tab → "Daily Job Search" → Run workflow.
   This populates `data/jobs.json` for the first time instead of waiting for the next 8 AM IST
   cron tick.

## Running locally (optional, for testing)
```bash
cd scraper
pip install -r requirements.txt
python main.py
```
This writes to `../data/jobs.json` directly, so you can preview `site/index.html` locally
before pushing.

## How filtering works (scraper/filters.py)
- **Role match**: keyword match against title + description for web dev / SWE / frontend / UI-UX terms.
- **Experience match**: keeps postings with junior/fresher/1-2yr signals, or no seniority signal
  at all; drops ones explicitly marked senior/staff/lead with no junior signal.
- **Freshness**: keeps postings ≤7 days old (configurable via `MAX_AGE_DAYS` in `main.py`).
- **Salary**: best-effort text extraction (₹/LPA/lakh patterns). If no salary is stated — common
  in Indian postings — the job is kept rather than dropped, tagged "Not disclosed" so you can
  judge for yourself.
- **Dedup**: fuzzy title-matching within the same company, so reposts don't eat your daily 10.
- **Ranking**: curated companies first → remote before hybrid → most recent first.

## Honest limitations
- Not every company runs Greenhouse/Lever/Ashby — some use custom/other ATS systems this
  doesn't support. You'd need to write a new module in `scraper/sources/` for those (same
  pattern as the existing ones).
- Salary detection is text-pattern matching, not guaranteed — many listings simply don't state
  pay, and that can't be fixed by scraping harder.
- "10 jobs/day" is a target, not a guarantee — on quiet days, fewer genuinely fresh + matching
  postings may exist. The script won't pad the list with stale or irrelevant jobs to hit 10.
- I could not live-test the actual API calls from my current environment (network-restricted
  sandbox), so I validated the filtering/ranking logic against realistic sample data instead.
  Test the real fetch calls yourself after your first push — if a specific company's token is
  wrong you'll see `[greenhouse] failed for '<token>': ...` in the Action logs, which tells you
  exactly what to fix.
