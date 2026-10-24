"""Remote job boards with free APIs / RSS. Each Job keeps raw HTML in extra['raw'] for company discovery."""
import logging
import os
import re
import xml.etree.ElementTree as ET
import requests
from models import Job

log = logging.getLogger(__name__)
HEADERS = {"User-Agent": "personal-job-alert/1.0"}
TAG = re.compile(r"<[^>]+>")


def _clean(s):
    return TAG.sub(" ", s or "")


def _get(url, **kw):
    r = requests.get(url, headers=HEADERS, timeout=25, **kw)
    r.raise_for_status()
    return r


def remotive(queries):
    for q in queries or [""]:
        for j in _get("https://remotive.com/api/remote-jobs", params={"search": q}).json().get("jobs", []):
            yield Job(uid=f"remotive:{j['id']}", title=j["title"], company=j["company_name"], url=j["url"],
                      location=j.get("candidate_required_location", ""), description=_clean(j.get("description")),
                      source="remotive", remote_flag=True, extra={"raw": (j.get("description") or "")[:6000]})


def remoteok(_q):
    for j in _get("https://remoteok.com/api").json():
        if not isinstance(j, dict) or "id" not in j:
            continue
        yield Job(uid=f"remoteok:{j['id']}", title=j.get("position", ""), company=j.get("company", ""),
                  url=j.get("url", ""), location=j.get("location", ""), description=_clean(j.get("description")),
                  source="remoteok", remote_flag=True,
                  extra={"raw": (j.get("description") or "")[:6000] + " " + (j.get("apply_url") or "")})


def weworkremotely(_q):
    for f in ["https://weworkremotely.com/remote-jobs.rss",
              "https://weworkremotely.com/categories/remote-business-management-and-finance-jobs.rss",
              "https://weworkremotely.com/categories/remote-product-jobs.rss",
              "https://weworkremotely.com/categories/remote-programming-jobs.rss"]:
        try:
            root = ET.fromstring(_get(f).content)
        except Exception as e:
            log.warning("wwr %s failed: %s", f, e)
            continue
        for it in root.iter("item"):
            title = it.findtext("title") or ""
            company, _, role = title.partition(":")
            link = it.findtext("link") or ""
            yield Job(uid=f"wwr:{link}", title=(role or title).strip(), company=company.strip(), url=link,
                      location=it.findtext("region") or "", description=_clean(it.findtext("description")),
                      source="weworkremotely", remote_flag=True, extra={"raw": (it.findtext("description") or "")[:6000]})


def himalayas(_q):
    for j in _get("https://himalayas.app/jobs/api", params={"limit": 100}).json().get("jobs", []):
        url = j.get("applicationLink") or j.get("guid") or ""
        yield Job(uid=f"himalayas:{j.get('guid') or url}", title=j.get("title", ""), company=j.get("companyName", ""),
                  url=url, location=", ".join(j.get("locationRestrictions") or []) or "Worldwide",
                  description=_clean(j.get("description") or j.get("excerpt")), source="himalayas",
                  remote_flag=True, extra={"raw": url + " " + (j.get("description") or "")[:6000]})


def jobicy(_q):
    for j in _get("https://jobicy.com/api/v2/remote-jobs", params={"count": 100}).json().get("jobs", []):
        geo = j.get("jobGeo", "")
        yield Job(uid=f"jobicy:{j['id']}", title=j.get("jobTitle", ""), company=j.get("companyName", ""),
                  url=j.get("url", ""), location=", ".join(geo) if isinstance(geo, list) else geo,
                  description=_clean(j.get("jobDescription") or j.get("jobExcerpt")), source="jobicy",
                  remote_flag=True, extra={"raw": (j.get("jobDescription") or "")[:6000]})


def arbeitnow(_q):
    for j in _get("https://www.arbeitnow.com/api/job-board-api").json().get("data", []):
        if not j.get("remote"):
            continue
        yield Job(uid=f"arbeitnow:{j['slug']}", title=j.get("title", ""), company=j.get("company_name", ""),
                  url=j.get("url", ""), location=j.get("location", "") or "Remote", description=_clean(j.get("description")),
                  source="arbeitnow", remote_flag=True)


def adzuna(queries):
    """Optional: free key at developer.adzuna.com -> ADZUNA_APP_ID / ADZUNA_APP_KEY. Covers India listings."""
    app_id, app_key = os.getenv("ADZUNA_APP_ID"), os.getenv("ADZUNA_APP_KEY")
    if not (app_id and app_key):
        return
    for q in queries or []:
        r = _get("https://api.adzuna.com/v1/api/jobs/in/search/1",
                 params={"app_id": app_id, "app_key": app_key, "results_per_page": 50,
                         "what": f"{q} remote", "sort_by": "date", "content-type": "application/json"})
        for j in r.json().get("results", []):
            yield Job(uid=f"adzuna:{j['id']}", title=j.get("title", ""), company=(j.get("company") or {}).get("display_name", ""),
                      url=j.get("redirect_url", ""), location=(j.get("location") or {}).get("display_name", ""),
                      description=_clean(j.get("description")), source="adzuna")


BOARDS = {"remotive": remotive, "remoteok": remoteok, "weworkremotely": weworkremotely, "himalayas": himalayas,
          "jobicy": jobicy, "arbeitnow": arbeitnow, "adzuna": adzuna}


def fetch_all(enabled, queries):
    for name in enabled or []:
        fn = BOARDS.get(name)
        if not fn:
            continue
        try:
            yield from fn(queries)
        except Exception as e:
            log.warning("board %s failed: %s", name, e)
