import os
import json
import feedparser
import requests
from datetime import datetime
from deep_translator import GoogleTranslator

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
WEBHOOK_URL = os.environ['DISCORD_WEBHOOK_URL']

# Flux RSS classiques
FEED_URLS = [
    'https://www.forexlive.com/feed',
    'https://www.fxstreet.com/rss/rssfeed.aspx?pid=1270&format=xml',
    'https://www.dailyfx.com/feeds/rss/news',
]

# Comptes Twitter pro Forex à surveiller
TWITTER_USERS = [
    'kathylienfx',
    'AshrafLaidi',
    'PeterLBrandt',
    'JamieSaettele'
]
TWITTER_FEED_URLS = [
    f'https://twitrss.me/twitter_user_to_rss/?user={user}'
    for user in TWITTER_USERS
]

SEEN_FILE = 'seen.json'
# ────────────────────────────────────────────────────────────────────────────────

# Initialise le traducteur (auto → français)
translator = GoogleTranslator(source='auto', target='fr')

# Charge l’historique
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, 'r') as f:
        seen = set(json.load(f))
else:
    seen = set()

def process_feed(url, prefix_label=""):
    feed = feedparser.parse(url)
    for entry in feed.entries:
        eid = entry.get('id', entry.link)
        if eid in seen:
            continue
        seen.add(eid)

        # Texte original
        title_en   = entry.title
        summary_en = entry.get('summary', '').strip()

        # Traduction
        try:
            title_fr   = translator.translate(title_en)
            summary_fr = translator.translate(summary_en) if summary_en else ""
        except Exception:
            title_fr, summary_fr = title_en, summary_en

        content = (
            f"{prefix_label}**{title_fr}**\n"
            f"{summary_fr}\n"
            f"{entry.link}"
        )
        payload = {"content": content}

        try:
            requests.post(WEBHOOK_URL, json=payload)
        except Exception as e:
            print(f"Erreur webhook : {e}")

# Parcours des flux classiques
for url in FEED_URLS:
    process_feed(url, prefix_label="")

# Parcours des flux Twitter
for url in TWITTER_FEED_URLS:
    process_feed(url, prefix_label="[Tweet] ")

# Sauvegarde de l’historique
with open(SEEN_FILE, 'w') as f:
    json.dump(list(seen), f)
