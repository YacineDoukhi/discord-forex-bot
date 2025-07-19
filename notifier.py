import os, json, feedparser, requests
from datetime import datetime
import openai

# Configuration depuis GitHub Secrets
WEBHOOK_URL   = os.environ['DISCORD_WEBHOOK_URL']
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
FEED_URLS     = [
    'https://www.forexlive.com/feed',
    'https://www.fxstreet.com/rss/rssfeed.aspx?pid=1270&format=xml',
    'https://www.dailyfx.com/feeds/rss/news',
]
SEEN_FILE = 'seen.json'

# Init OpenAI
openai.api_key = OPENAI_API_KEY

# Charge les articles déjà vus
if os.path.exists(SEEN_FILE):
    seen = set(json.load(open(SEEN_FILE)))
else:
    seen = set()

for url in FEED_URLS:
    feed = feedparser.parse(url)
    for e in feed.entries:
        eid = e.get('id', e.link)
        if eid in seen:
            continue
        seen.add(eid)

        # Génère l'analyse IA
        prompt = (
            f"Actu Forex : {e.title}\n\n"
            f"Résumé : {e.get('summary','')}\n\n"
            "Explique les conséquences possibles sur EUR/USD."
        )
        resp = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role":"system","content":"Tu es un expert Forex."},
                {"role":"user","content":prompt}
            ],
            max_tokens=250
        )
        analysis = resp.choices[0].message.content.strip()

        # Envoie sur Discord via webhook
        payload = {
            "content": f"**{e.title}**\n{analysis}\n{e.link}"
        }
        requests.post(WEBHOOK_URL, json=payload)

# Sauvegarde l’historique
with open(SEEN_FILE, 'w') as f:
    json.dump(list(seen), f)
