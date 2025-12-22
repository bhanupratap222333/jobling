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
from collections import defaultdict

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

# ---- Sites Config ----
SITES_JSON = os.getenv("SITES_JSON")

if not SITES_JSON:
    raise Exception("❌ SITES_JSON env variable missing")

try:
    SITES = json.loads(SITES_JSON)
except Exception:
    raise Exception("❌ Invalid SITES_JSON format")

MAX_PER_CATEGORY = 10
HASH_FILE = "seen_signal.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# ===============================
# HELPERS
# ===============================

def get_hash(text):
    return hashlib.md5(text.encode("utf-8")).hexdigest()

STOP_WORDS = [
    "apply", "online", "download", "notification",
    "latest", "exam", "post", "declared", "out"
]

def normalize_title(title):
    t = title.lower()
    t = re.sub(r'[^a-z0-9 ]', ' ', t)
    words = [w for w in t.split() if w not in STOP_WORDS]
    return " ".join(words[:6])

def detect_category(title):
    t = title.lower()
    if "answer key" in t:
        return "Answer Key"
    if "result" in t:
        return "Result"
    if "admit" in t or "hall ticket" in t:
        return "Admit Card"
    return "Latest Job"

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
# LOAD OLD HASHES
# ===============================

seen = set()
if os.path.exists(HASH_FILE):
    with open(HASH_FILE, "r", encoding="utf-8") as f:
        seen = set(f.read().splitlines())

# ===============================
# SCRAPE
# ===============================

new_items = []
category_count = defaultdict(int)

for site in SITES:
    try:
        r = requests.get(site["url"], headers=HEADERS, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception:
        continue

    for a in soup.find_all("a", href=True):
        title = a.get_text(strip=True)
        if not title or len(title) < 12:
            continue

        category = detect_category(title)
        key = normalize_title(title) + "_" + category
        h = get_hash(key)

        if h in seen:
            continue

        if category_count[category] >= MAX_PER_CATEGORY:
            continue

        seen.add(h)
        category_count[category] += 1

        new_items.append({
            "title": title,
            "category": category,
            "site": site["name"],
            "date": datetime.now().strftime("%d-%m-%Y"),
            "link": urljoin(site["url"], a["href"])
        })

# ===============================
# SEND EMAIL ALERT
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
