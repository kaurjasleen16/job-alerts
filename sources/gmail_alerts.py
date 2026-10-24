"""Read LinkedIn / Indeed / Naukri alert emails over IMAP and turn them into Jobs.

Setup: create alerts on each site -> they email your Gmail. Enable 2FA on Gmail,
create an App Password, set GMAIL_USER and GMAIL_APP_PASSWORD.
"""
import email
import hashlib
import imaplib
import logging
import os
import re
from email.header import decode_header, make_header
from html.parser import HTMLParser
from models import Job

log = logging.getLogger(__name__)

SENDERS = {
    "linkedin": ("jobalerts-noreply@linkedin.com", "jobs-noreply@linkedin.com", "linkedin.com"),
    "indeed": ("indeed.com",),
    "naukri": ("naukri.com",),
}
LINK_PATTERNS = {
    "linkedin": re.compile(r"linkedin\.com/(comm/)?jobs/view/"),
    "indeed": re.compile(r"indeed\.com/(rc/clk|viewjob|pagead|m/viewjob|cmp/)"),
    "naukri": re.compile(r"naukri\.com/(job-listings|.*-jobs-)"),
}


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self._href, self._text = [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href, self._text = dict(attrs).get("href"), []

    def handle_data(self, data):
        if self._href:
            self._text.append(data.strip())

    def handle_endtag(self, tag):
        if tag == "a" and self._href:
            self.links.append((self._href, " ".join(t for t in self._text if t)))
            self._href = None


def _body_html(msg):
    parts = msg.walk() if msg.is_multipart() else [msg]
    for p in parts:
        if p.get_content_type() == "text/html":
            return p.get_payload(decode=True).decode(p.get_content_charset() or "utf-8", "ignore")
    return ""


def _canonical(url, platform):
    if platform == "linkedin":
        m = re.search(r"/jobs/view/(?:[^/?]*-)?(\d+)", url)
        if m:
            return f"https://www.linkedin.com/jobs/view/{m.group(1)}", m.group(1)
    return url.split("?")[0] if platform != "indeed" else url, hashlib.md5(url.split("&")[0].encode()).hexdigest()[:12]


def fetch_all(lookback_days=2):
    user, pwd = os.getenv("GMAIL_USER"), os.getenv("GMAIL_APP_PASSWORD")
    if not (user and pwd):
        log.info("Gmail not configured; skipping email alerts")
        return
    try:
        box = imaplib.IMAP4_SSL("imap.gmail.com")
        box.login(user, pwd)
        box.select("INBOX")
    except Exception as e:
        log.warning("Gmail login failed: %s", e)
        return
    for platform, senders in SENDERS.items():
        domain = senders[-1]
        typ, data = box.search(None, f'(FROM "{domain}" SINCE "{_since(lookback_days)}")')
        for num in (data[0].split() if typ == "OK" else []):
            typ, raw = box.fetch(num, "(RFC822)")
            if typ != "OK":
                continue
            msg = email.message_from_bytes(raw[0][1])
            subject = str(make_header(decode_header(msg.get("Subject", ""))))
            parser = _Links()
            parser.feed(_body_html(msg))
            seen = set()
            for href, text in parser.links:
                if not LINK_PATTERNS[platform].search(href) or len(text) < 4:
                    continue
                url, jid = _canonical(href, platform)
                if jid in seen:
                    continue
                seen.add(jid)
                yield Job(
                    uid=f"{platform}:{jid}", title=text, company="", url=url,
                    description=subject, source=f"{platform}-alert", remote_flag=True,
                    extra={"from_email_alert": True},
                )
    box.logout()


def _since(days):
    import datetime
    return (datetime.date.today() - datetime.timedelta(days=days)).strftime("%d-%b-%Y")
