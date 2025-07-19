import os
import json
import feedparser
import requests
from datetime import datetime
from deep_translator import GoogleTranslator
import openai

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
WEBHOOK_URL     = os.environ['DISCORD_WEBHOOK_URL']
OPENAI_API_KEY  = os.environ['OPENAI_API_KEY']
openai.api_key  = OPENAI_API_KEY

# Flux RSS Forex classiques
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

# Traducteur auto→fr
translator = GoogleTranslator(source='auto', target='fr')

# Charge l’historique pour ne pas republier deux fois la même source
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, 'r') as f:
        seen = set(json.load(f))
else:
    seen = set()

def simplify_and_explain(title_fr: str, summary_fr: str) -> str:
    """
    Appelle OpenAI pour simplifier et expliquer l'impact sur EUR/USD.
    """
    prompt = (
        "Tu es un expert Forex très pédagogique.\n"
        "Simplifie ce titre et ce résumé pour qu'un débutant comprenne, "
        "et explique la conséquence probable sur la paire EUR/USD.\n\n"
        f"Titre : {title_fr}\n"
        f"Résumé : {summary_fr}"
    )
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful Forex market analyst."},
            {"role": "user",   "content": prompt}
        ],
        temperature=0.7,
        max_tokens=300
    )
    return response.choices[0].message.content.strip()

def process_feed(url: str, prefix: str = "") -> None:
    """
    Récupère les items d'un flux RSS, filtre les déjà vus, génère l'analyse IA
    et envoie uniquement le texte IA + lien dans Discord.
    """
    feed = feedparser.parse(url)
    for entry in feed.entries:
        eid = entry.get('id', entry.link)
        if eid in seen:
            continue
        seen.add(eid)

        # Traduire le titre et le résumé en français
        title_en   = entry.title
        summary_en = entry.get('summary', '').strip()
        try:
            title_fr   = translator.translate(title_en)
            summary_fr = translator.translate(summary_en) if summary_en else ""
        except Exception:
