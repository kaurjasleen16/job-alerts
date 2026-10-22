import re
from models import Job


def _has_any(text, words):
    t = text.lower()
    return any(w.lower() in t for w in words or [])


def title_ok(job: Job, cfg) -> bool:
    t = job.title
    if cfg.get("exclude_title_keywords") and _has_any(t, cfg["exclude_title_keywords"]):
        return False
    inc = cfg.get("include_title_keywords")
    # email alerts are already matched by the platform; only apply exclusions
    if job.extra.get("from_email_alert"):
        return True
    return _has_any(t, inc) if inc else True


def remote_and_region_ok(job: Job, cfg) -> bool:
    if job.extra.get("from_email_alert"):
        return True
    loc = job.location.lower()
    head = f"{loc} {job.title} {job.description[:800]}".lower()
    is_remote = job.remote_flag or _has_any(head, ["remote", "work from home", "wfh", "work from anywhere", "wfa", "anywhere", "distributed", "fully distributed"])
    if cfg.get("remote_only", True) and not is_remote:
        return False
    if _has_any(head, cfg.get("blocked_region_phrases")):
        return False
    allowed = cfg.get("allowed_region_phrases") or []
    # If the location field names a specific place, require it to be allowed.
    generic = {"", "remote", "worldwide", "anywhere", "global", "remote - worldwide", "work from anywhere", "remote - anywhere", "100% remote", "fully remote"}
    if loc.strip() not in generic and allowed and not _has_any(loc, allowed):
        return False
    return True
