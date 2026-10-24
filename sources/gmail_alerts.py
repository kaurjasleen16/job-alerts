Claude
Detailing alert setup steps for Naukri and Indeed accounts
Menus on these sites change from time to time, so a button may be in a slightly different place from what I describe.

Naukri
Log in at naukri.com and search for a job title, such as Business Analyst.
On the results page, set the filters:
Work mode: choose “Work from home” or “Remote”.
Freshness: choose “Last 1 day” if offered.
Experience: set your range.
Click Create Job Alert. It’s usually a button or bell icon near the top of the results or beside the filters.
Name the alert, choose the email address (use your Gmail, or the one that forwards to it), and select the fastest frequency available. Naukri alerts are often a daily digest rather than instant.
Save, and repeat for each title: Product Analyst, Business Transformation, ServiceNow Business Analyst, AI Product Analyst.
You can manage alerts from your profile menu under Settings or Manage job alerts.

Indeed (use in.indeed.com)
Sign in and search with Business Analyst under “What” and Remote under “Where”.
Add filters such as “Remote” and “Date posted: last 24 hours / 3 days” if shown.
On the results page, turn on Email me jobs for this search, or click Create alert. Enter your Gmail address and confirm.
Choose the frequency. Pick “Instantly” or “As soon as posted” if it’s offered, otherwise “Daily”.
Repeat for each job title.
To change or delete alerts, open your profile icon > Settings > Job alerts, or the “Alerts” page.

Make sure the emails reach the automation
Create the alerts using your Gmail address. If your Naukri or Indeed account uses a different email, either add the Gmail address in the alert settings or set that account to forward to Gmail.
After creating each alert, check that a confirmation or first alert email arrives. If it lands in Spam, open it and click Not spam.
Gmail’s Promotions tab is fine, because the automation reads your whole inbox. It only reads emails from the last 2 days.
Check the first real emails
I built the email reader for LinkedIn, Indeed and Naukri from their usual link formats, without testing it on real emails from your account. When you’ve received the first alert from each site, check that your Telegram alerts include jobs from them. If nothing shows up after a day, open one alert email, copy its text with your name and email removed, and send it to me. I’ll adjust the reader to match.

1792845691195_image.png
i got this error after running the code

Diagnosing a failed workflow run from limited log details.
Diagnosing a failed workflow run from limited log details.
The warning and the notice in your screenshot are harmless and are not what failed. The real error is in the job log, which this page doesn’t show. “Process completed with exit code 1” only says that some step failed, and it failed after 6 seconds, so it stopped early, probably while installing or starting the script.

To find the actual error:

Click the run box in the middle of your screenshot.
Find the step with the red ❌ and click it to expand it.
Copy the last 10 to 15 lines of red text and send them to me. Replace any token or password with xxxx.
The most likely cause is the folder structure. If you dragged the whole job-alerts folder into GitHub, your files are inside a subfolder named job-alerts/. The workflow looks for requirements.txt and main.py in the repo’s top level, so it fails within seconds.

To check, open your repo’s main page. You should see main.py, config.yaml, requirements.txt and the sources folder directly in the list, next to .github. If instead you see a single folder called job-alerts, the files are one level too deep.

To fix that: open the repo, click the job-alerts subfolder, and for each file use the three-dots menu > Rename, then change the name from job-alerts/main.py to just main.py. Do this for each file, or delete the repo’s contents and upload again by opening the unzipped folder first and dragging in the files and the sources folder, not the outer folder.

Other possible causes are a file that didn’t upload (such as sources/ats.py) or a typo in the workflow file. The log will show which one it is, so please send those lines.

1792845773823_image.png
Ran a command, shared files
This error is more specific than my earlier guess. Your main files uploaded correctly, because the path shows main.py at the top level of the repo and the earlier imports worked. What’s missing is the sources folder, which probably didn’t upload when you dragged files in.

Fix: create the three files inside a sources folder on GitHub

I’ve attached them as ats.py, boards.py and gmail_alerts.py. Do this for each one:

In your repo, click Add file > Create new file.
In the name box, type sources/ats.py. Typing the / makes the folder.
Open the attached ats.py in a text editor, copy everything, and paste it into the large editor box.
Click Commit changes, then Commit changes again.
Repeat for sources/boards.py and sources/gmail_alerts.py. You don’t need __init__.py, because Python finds the folder without it.

Check before re-running: open your repo’s main page, click the sources folder, and confirm it lists ats.py, boards.py and gmail_alerts.py.

Then re-run: go to Actions > job-alerts > Run workflow. If you get a new error, send me the red text from the failed step, as you did this time.

Ats
PY
Boards
PY
Gmail alerts
PY



Claude is AI and can make mistakes. Please double-check responses.
Gmail alerts · PY
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
 

Claude finished the response
