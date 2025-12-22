import requests
from bs4 import BeautifulSoup
import hashlib
import os
import re
import smtplib
import json
from email.mime.text import MIMEText
from datetime import datetime
from urllib.parse import urljoin

# ===============================
# CONFIG (FROM ENV)
# ===============================

# ---- Email Config ----
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

if not EMAIL_FROM or not EMAIL_TO or not EMAIL_PASSWORD:
    raise Exception("❌ EMAIL env variables missing")

# ---- Sources Config ----
SOURCES_JSON = os.getenv("SOURCES_JSON")

if not SOURCES_JSON:
    raise Exception("❌ SOURCES_JSON env variable missing")

try:
    SOURCES = json.loads(SOURCES_JSON)
except Exception:
    raise Exception("❌ Invalid SOURCES_JSON format")

HASH_FILE = "seen_signal.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# ===============================
# HELPERS (SAME LOGIC)
# ===============================

def clean_title(t):
    t = re.sub(r'\s+', ' ', t)
    return t.strip()

def detect_category(title):
    t = title.lower()
    if "answer key" in t:
        return "Answer Key"
    if "result" in t:
        return "Result"
    if "admit" in t or "hall ticket" in t:
        return "Admit Card"
    return "Latest Job"

def make_hash(site, title, category):
    key = f"{site}_{title}_{category}"
    return hashlib.md5(key.encode("utf-8")).hexdigest()

def send_email(items):
    body = "Hello Bhanu,\n\nNew government updates found:\n\n"

    for item in items:
        body += (
            "----------------------------------\n"
            f"Title    : {item['title']}\n"
            f"Category : {item['category']}\n"
            f"Source   : {item['site']}\n"
            f"Date     : {item['date']}\n"
            f"Link     : {item['link']}\n"
        )

    body += "\nPlease verify from official websites.\n\n– Jobling Auto Bot"

    msg = MIMEText(body)
    msg["Subject"] = f"🔔 {len(items)} New Govt Job Alert"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(EMAIL_FROM, EMAIL_PASSWORD)
    server.send_message(msg)
    server.quit()

# ===============================
# LOAD OLD HASHES (DUPLICATE SAFE)
# ===============================

seen = set()
if os.path.exists(HASH_FILE):
    with open(HASH_FILE, "r", encoding="utf-8") as f:
        seen = set(f.read().splitlines())

# ===============================
# SCRAPING (PAGES WISE – SAME AS BEFORE)
# ===============================

new_items = []

for source in SOURCES:
    for page in source["pages"]:
        try:
            r = requests.get(page, headers=HEADERS, timeout=20)
            soup = BeautifulSoup(r.text, "html.parser")
        except Exception:
            continue

        for a in soup.find_all("a", href=True):
            title = clean_title(a.get_text())
            if not title or len(title) < 15:
                continue

            link = urljoin(page, a["href"])
            category = detect_category(title)
            h = make_hash(source["site"], title, category)

            # ✅ DUPLICATE CHECK
            if h in seen:
                continue

            seen.add(h)

            new_items.append({
                "title": title,
                "category": category,
                "site": source["site"],
                "date": datetime.now().strftime("%d-%m-%Y"),
                "link": link
            })

# ===============================
# SEND EMAIL
# ===============================

if new_items:
    send_email(new_items)
    print(f"📧 Email sent | New items: {len(new_items)}")
else:
    print("😴 No new updates")

# ===============================
# SAVE HASHES
# ===============================

with open(HASH_FILE, "w", encoding="utf-8") as f:
    for h in seen:
        f.write(h + "\n")
