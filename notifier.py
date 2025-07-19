import os
import json
import feedparser
import requests
from datetime import datetime

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
WEBHOOK_URL = os.environ['DISCORD_WEBHOOK_URL']
FEED_URLS   = [
    'https://www.forexlive.com/feed',
    'https://www.fxstreet.com/rss/rssfeed.aspx?pid=1270&format=xml',
    'https://www.dailyfx.com/feeds/rss/news',
]
SEEN_FILE = 'seen.json'
# ────────────────────────────────────────────────────────────────────────────────

# Charge l'historique des articles déjà notifiés
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, 'r') as f:
        seen = set(json.load(f))
else:
    seen = set()

for url in FEED_URLS:
    feed = feedparser.parse(url)
    for entry in feed.entries:
        entry_id = entry.get('id', entry.link)
        if entry_id in seen:
            continue
        seen.add(entry_id)

        # Prépare et envoie la notification via Webhook
        title   = entry.title
        summary = entry.get('summary', '').strip()
        link    = entry.link
        payload = {
            "content": (
                f"**{title}**\n"
                f"{summary}\n"
                f"{link}"
            )
        }
        try:
            requests.post(WEBHOOK_URL, json=payload)
        except Exception as e:
            print(f"Erreur envoi webhook : {e}")

# Sauvegarde l’historique pour ne pas renvoyer deux fois le même article
with open(SEEN_FILE, 'w') as f:
    json.dump(list(seen), f)
