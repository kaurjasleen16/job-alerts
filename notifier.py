import html
import logging
import os
import requests

log = logging.getLogger(__name__)


def send_telegram(job, result) -> bool:
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    e = html.escape
    score = int(result.get("score", 0) or 0)
    badge = "🟢" if score >= 85 else "🟡" if score >= 70 else "🟠"
    bar = "█" * (score // 10) + "░" * (10 - score // 10)
    lines = [
        f"🆕 <b>{e(job.title)}</b>",
        f"🏢 {e(job.company or 'See link')}  ·  📍 {e(job.location or 'Remote')}",
        f"{badge} <b>Resume match: {score}%</b>  {bar}",
        f"💬 {e(str(result.get('reason', '')))}",
    ]
    if result.get("matched"):
        lines.append("✅ Matches: " + e(", ".join(map(str, result["matched"]))))
    if result.get("gaps"):
        lines.append("⚠️ Gaps: " + e(", ".join(map(str, result["gaps"]))))
    if result.get("tip"):
        lines.append("💡 " + e(str(result["tip"])))
    lines += [f"🔗 {e(job.url)}", f"<i>via {e(job.source)}</i>"]
    text = "\n".join(lines)
    if not (token and chat):
        print("[NO TELEGRAM CONFIGURED]\n", text)
        return True
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": False},
            timeout=20,
        )
        r.raise_for_status()
        return True
    except Exception as ex:
        log.error("Telegram send failed: %s", ex)
        return False
