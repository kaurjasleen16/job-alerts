# Remote Job Alerts

Polls company career sites (Greenhouse/Lever/Ashby/SmartRecruiters), remote job boards, and your
LinkedIn/Indeed/Naukri alert emails; scores each new job against your resume with an LLM; sends
matches to Telegram.

## Setup (about 15 minutes)

1. **Telegram bot**: message @BotFather -> `/newbot` -> copy the token. Send any message to your
   bot, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy `chat.id`.
2. **Anthropic API key** from console.anthropic.com (Haiku costs a few cents/day at this volume).
3. **LinkedIn / Indeed / Naukri**: create job alerts (keywords + Remote filter, frequency
   "instant"/"daily" as offered) delivered to a Gmail address. In Gmail: enable 2-Step Verification,
   then create an **App Password** (myaccount.google.com/apppasswords). Also enable IMAP in Gmail settings.
4. **Edit `config.yaml`**: title keywords, preferences, and your target companies.
   To find a company's ATS slug, open its careers page and look at the apply URL
   (`boards.greenhouse.io/<slug>`, `jobs.lever.co/<slug>`, `jobs.ashbyhq.com/<slug>`).
5. **Push to GitHub** and add repository secrets (Settings -> Secrets -> Actions):
   `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `ANTHROPIC_API_KEY`, `GMAIL_USER`,
   `GMAIL_APP_PASSWORD`, `RESUME_TEXT` (paste your resume text).
6. Run the workflow once manually (Actions -> job-alerts -> Run workflow). The first run only records
   existing jobs. From then on you get alerts for new postings.

## Notes
- Private repos get 2,000 free Actions minutes/month: use `*/30` cron there. Public repos are unlimited
  (keep your resume in the `RESUME_TEXT` secret, not in the repo).
- Local test: `pip install -r requirements.txt && python main.py` (set env vars first; without
  Telegram configured, alerts print to the console).
- Email alerts carry only a title + link, so they are not resume-scored in depth and arrive as fast as
  the platform emails you.

## Coverage ("all companies that hire remotely in India / work from anywhere")
- 7 remote boards are polled every run (Remotive, RemoteOK, We Work Remotely, Himalayas, Jobicy, Arbeitnow,
  and Adzuna India if you add free `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` secrets).
- Company discovery is on: every Greenhouse/Lever/Ashby/SmartRecruiters link found in those jobs is saved to
  `company_state.json` and that company's career page is watched from the next run. The watch list grows over time.
- A newly watched company's existing jobs are recorded silently; only postings that appear afterwards alert you.
- Not covered: companies on Workday or custom-built career pages (add per-company scrapers if needed).
