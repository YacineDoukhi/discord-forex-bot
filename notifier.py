import os
import json
import feedparser
import requests
from datetime import datetime
from googletrans import Translator

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
    # ajoute ici les autres handles que tu veux
]

# Génère les URLs TwitRSS.me
TWITTER_FEED_URLS = [
    f'https://twitrss.me/twitter_user_to_rss/?user={user}'
    for user in TWITTER_USERS
]

# On garde tout dans le même historique
SEEN_FILE = 'seen.json'
# ────────────────────────────────────────────────────────────────────────────────

translator = Translator()

# Charge l'historique
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, 'r') as f:
        seen = set(json.load(f))
else:
    seen = set()

def process_feed(url, is_twitter=False):
    """
    Récupère les items d'un flux, filtre les déjà vus et envoie.
    is_twitter : pour afficher « [Tweet] » ou non.
    """
    feed = feedparser.parse(url)
    for entry in feed.entries:
        eid = entry.get('id', entry.link)
        if eid in seen:
            continue
        seen.add(eid)

        title_en   = entry.title
        summary_en = entry.get('summary', '').strip()

        # Traduction
        try:
            title_fr   = translator.translate(title_en, dest='fr').text
            summary_fr = translator.translate(summary_en, dest='fr').text
        except Exception:
            title_fr, summary_fr = title_en, summary_en

        prefix = "[Tweet] " if is_twitter else ""
        content = (
            f"**{prefix}{title_fr}**\n"
            f"{summary_fr}\n"
            f"{entry.link}"
        )
        payload = {"content": content}

        try:
            requests.post(WEBHOOK_URL, json=payload)
        except Exception as e:
            print(f"Erreur lors de l'envoi webhook : {e}")

# Parcours des flux standard
for url in FEED_URLS:
    process_feed(url, is_twitter=False)

# Parcours des flux Twitter
for url in TWITTER_FEED_URLS:
    process_feed(url, is_twitter=True)

# Sauvegarde l'historique
with open(SEEN_FILE, 'w') as f:
    json.dump(list(seen), f)
