"""Public ATS endpoints: Greenhouse, Lever, Ashby, SmartRecruiters."""
import logging
import requests
from models import Job

log = logging.getLogger(__name__)
HEADERS = {"User-Agent": "personal-job-alert/1.0"}


def _get(url, **kw):
    r = requests.get(url, headers=HEADERS, timeout=25, **kw)
    r.raise_for_status()
    return r.json()


def greenhouse(slug):
    data = _get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
    for j in data.get("jobs", []):
        yield Job(
            uid=f"gh:{slug}:{j['id']}", title=j["title"], company=slug,
            url=j["absolute_url"], location=(j.get("location") or {}).get("name", ""),
            source="greenhouse",
            detail_url=f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{j['id']}",
        )


def lever(slug):
    data = _get(f"https://api.lever.co/v0/postings/{slug}", params={"mode": "json"})
    for j in data:
        cats = j.get("categories") or {}
        yield Job(
            uid=f"lever:{slug}:{j['id']}", title=j["text"], company=slug,
            url=j["hostedUrl"], location=cats.get("location", "") or "",
            description=j.get("descriptionPlain", ""), source="lever",
            remote_flag=(j.get("workplaceType") == "remote"),
        )


def ashby(slug):
    data = _get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
    for j in data.get("jobs", []):
        yield Job(
            uid=f"ashby:{slug}:{j['id']}", title=j["title"], company=slug,
            url=j.get("jobUrl", ""), location=j.get("location", "") or "",
            description=j.get("descriptionPlain", ""), source="ashby",
            remote_flag=bool(j.get("isRemote")),
        )


def smartrecruiters(slug):
    data = _get(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings", params={"limit": 100})
    for j in data.get("content", []):
        loc = j.get("location") or {}
        place = ", ".join(x for x in [loc.get("city"), loc.get("country")] if x)
        yield Job(
            uid=f"sr:{slug}:{j['id']}", title=j["name"], company=slug,
            url=f"https://jobs.smartrecruiters.com/{slug}/{j['id']}",
            location=place, source="smartrecruiters", remote_flag=bool(loc.get("remote")),
        )


FETCHERS = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby, "smartrecruiters": smartrecruiters}


def fetch_all(companies: dict, seeded: set):
    """companies = {"greenhouse": [slugs], ...}. Polls in parallel.

    A company seen for the first time is flagged job.extra['seed_only']=True so its existing
    backlog is recorded silently instead of flooding you with old postings.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    tasks = [(a, s) for a, slugs in (companies or {}).items() for s in (slugs or []) if a in FETCHERS]

    def run(task):
        a, slug = task
        return task, list(FETCHERS[a](slug))

    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = [ex.submit(run, t) for t in tasks]
        for f in as_completed(futs):
            try:
                (a, slug), jobs = f.result()
            except Exception as e:
                log.debug("company poll failed: %s", e)   # dead slugs are expected; stay quiet
                continue
            key = f"{a}:{slug}"
            first = key not in seeded
            for j in jobs:
                j.extra["seed_only"] = first
                if not j.company or j.company == slug:
                    j.company = slug
                yield j
            seeded.add(key)


def fill_description(job: Job):
    """Lazy-load description for ATSs whose list endpoint omits it."""
    if job.description or not job.detail_url:
        return
    try:
        d = _get(job.detail_url)
        import html, re
        txt = html.unescape(d.get("content", ""))
        job.description = re.sub(r"<[^>]+>", " ", txt)
    except Exception as e:
        log.warning("detail fetch failed %s: %s", job.detail_url, e)
