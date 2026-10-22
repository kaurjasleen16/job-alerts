"""Find new company career pages from job links we already see, so coverage keeps growing."""
import re

PATTERNS = {
    "greenhouse": re.compile(r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_board\?for=)?([a-z0-9_-]+)", re.I),
    "lever": re.compile(r"jobs\.lever\.co/([a-z0-9_-]+)", re.I),
    "ashby": re.compile(r"jobs\.ashbyhq\.com/([a-z0-9_.%-]+)", re.I),
    "smartrecruiters": re.compile(r"(?:careers|jobs)\.smartrecruiters\.com/([A-Za-z0-9_-]+)", re.I),
}
IGNORE = {"embed", "jobs", "www", "api", "v1", "boards"}


def extract(job):
    blob = " ".join([job.url or "", job.extra.get("raw", "")])
    found = {}
    for ats, pat in PATTERNS.items():
        for slug in pat.findall(blob):
            slug = slug.lower() if ats != "smartrecruiters" else slug
            if slug.lower() not in IGNORE:
                found.setdefault(ats, set()).add(slug)
    return found
