import json
import logging
import os
import sys
from pathlib import Path

import yaml

import discovery
import filters
import matcher
import notifier
from sources import ats, boards, gmail_alerts

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("job-alerts")

ROOT = Path(__file__).parent
SEEN_FILE = ROOT / "seen_jobs.json"
STATE_FILE = ROOT / "company_state.json"   # {"discovered": {ats: [slugs]}, "seeded": ["ats:slug"]}
MAX_SEEN = 40000
MAX_DISCOVERED = 1500


def load_resume():
    if os.getenv("RESUME_TEXT"):
        return os.environ["RESUME_TEXT"]
    p = ROOT / "resume.md"
    return p.read_text() if p.exists() else ""


def main():
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text())
    resume = load_resume()
    first_run = not SEEN_FILE.exists()
    seen = set(json.loads(SEEN_FILE.read_text())) if not first_run else set()
    seed_all = first_run and not cfg.get("alert_on_first_run", False)
    if seed_all:
        log.info("First run: recording existing jobs silently (no alerts).")

    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {"discovered": {}, "seeded": []}
    seeded = set(state["seeded"])
    # merge configured companies with auto-discovered ones
    companies = {a: set(v or []) for a, v in (cfg.get("companies") or {}).items()}
    if cfg.get("discover_companies", True):
        for a, v in state["discovered"].items():
            companies.setdefault(a, set()).update(v)
    companies = {a: sorted(v) for a, v in companies.items()}
    log.info("Watching %d company career boards", sum(len(v) for v in companies.values()))

    def all_jobs():
        yield from ats.fetch_all(companies, seeded)
        yield from boards.fetch_all(cfg.get("boards"), cfg.get("search_queries"))
        yield from gmail_alerts.fetch_all(cfg.get("gmail_lookback_days", 2))

    new, sent, found_new_cos = 0, 0, 0
    max_alerts = cfg.get("max_alerts_per_run", 25)
    known = {a: set(v) for a, v in companies.items()}
    total_discovered = sum(len(v) for v in state["discovered"].values())

    for job in all_jobs():
        # snowball: learn new company career pages from links in jobs we see
        if cfg.get("discover_companies", True) and not job.source.startswith(("greenhouse", "lever", "ashby", "smartrecruiters")):
            for a, slugs in discovery.extract(job).items():
                for slug in slugs:
                    if slug not in known.get(a, set()) and total_discovered < MAX_DISCOVERED:
                        state["discovered"].setdefault(a, []).append(slug)
                        known.setdefault(a, set()).add(slug)
                        total_discovered += 1
                        found_new_cos += 1
        if job.uid in seen:
            continue
        seen.add(job.uid)
        new += 1
        if seed_all or job.extra.get("seed_only"):
            continue
        if not filters.title_ok(job, cfg):
            continue
        ats.fill_description(job)
        if not filters.remote_and_region_ok(job, cfg):
            continue
        result = matcher.score_job(job, resume, cfg)
        if result.get("remote_from_india") is False:
            continue
        if int(result.get("score", 0)) >= cfg.get("min_score", 70) and sent < max_alerts:
            if notifier.send_telegram(job, result):
                sent += 1

    SEEN_FILE.write_text(json.dumps(sorted(seen)[-MAX_SEEN:]))
    state["seeded"] = sorted(seeded)
    STATE_FILE.write_text(json.dumps(state))
    log.info("Done. new=%d alerts_sent=%d new_companies_discovered=%d", new, sent, found_new_cos)


if __name__ == "__main__":
    sys.exit(main())
