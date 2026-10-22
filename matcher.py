"""Score a job against your resume with an LLM (Anthropic API), with keyword fallback."""
import json
import logging
import os
import re
import requests
from models import Job

log = logging.getLogger(__name__)

PROMPT = """You screen job postings for a candidate. Be strict and realistic.

CANDIDATE RESUME:
{resume}

CANDIDATE PREFERENCES:
{prefs}

JOB:
Title: {title}
Company: {company}
Location: {location}
Source: {source}
Description:
{description}

Score fit 0-100 (skills, seniority, domain, and whether the candidate can actually work
this role remotely from India, considering any country/timezone restrictions).
If the description is missing/short (e.g. only an email alert snippet), judge on title alone and be moderate.
Reply with ONLY JSON:
{{"score": <int 0-100>, "reason": "<max 20 words>",
  "matched": ["<up to 5 job requirements the resume clearly satisfies>"],
  "gaps": ["<up to 3 requirements the resume lacks or only weakly shows>"],
  "tip": "<max 15 words: what to emphasise in the application>",
  "remote_from_india": true|false|null}}"""


def _keyword_score(job: Job, resume: str, cfg) -> dict:
    words = {w for w in re.findall(r"[a-zA-Z+#.]{3,}", resume.lower())}
    skills = {s.lower() for s in cfg.get("skills_keywords", [])}
    text = f"{job.title} {job.description}".lower()
    hits = [s for s in skills if s in text]
    score = int(100 * len(hits) / max(len(skills), 1)) if skills else 50
    miss = [k for k in skills if k not in text][:3]
    return {"score": min(score + 20, 100), "reason": f"keyword match: {', '.join(hits[:6]) or 'none'}",
            "matched": hits[:5], "gaps": miss, "tip": "", "remote_from_india": None}


def score_job(job: Job, resume: str, cfg: dict) -> dict:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return _keyword_score(job, resume, cfg)
    prompt = PROMPT.format(
        resume=resume[:6000], prefs=cfg.get("preferences", ""), title=job.title,
        company=job.company or "(unknown)", location=job.location or "(unspecified)",
        source=job.source, description=(job.description or "")[:5000],
    )
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": cfg.get("llm_model", "claude-haiku-5-5"), "max_tokens": 400,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=60,
        )
        r.raise_for_status()
        text = "".join(b.get("text", "") for b in r.json()["content"])
        return json.loads(re.search(r"\{.*\}", text, re.S).group(0))
    except Exception as e:
        log.warning("LLM scoring failed (%s); using keyword fallback", e)
        return _keyword_score(job, resume, cfg)
