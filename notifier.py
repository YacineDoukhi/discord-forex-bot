import os
import json
import feedparser
import requests
from deep_translator import GoogleTranslator
from openai import OpenAI

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
WEBHOOK_URL    = os.environ['DISCORD_WEBHOOK_URL']
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']

# Initialise le client OpenAI v1
client = OpenAI(api_key=OPENAI_API_KEY)

FEED_URLS = [
    'https://www.forexlive.com/feed',
    'https://www.fxstreet.com/rss/rssfeed.aspx?pid=1270&format=xml',
    'https://www.dailyfx.com/feeds/rss/news',
]

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

# Charge l’historique
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, 'r') as f:
        seen = set(json.load(f))
else:
    seen = set()

def simplify_and_explain(title_fr: str, summary_fr: str) -> str:
    """
    Appelle l'API v1 pour simplifier et expliquer l'impact sur EUR/USD.
    """
    prompt = (
        "Tu es un expert Forex très pédagogique.\n"
        "Simplifie ce titre et ce résumé pour un débutant, "
        "et explique la conséquence probable sur EUR/USD.\n\n"
        f"Titre : {title_fr}\n"
        f"Résumé : {summary_fr}"
    )
    # Nouvelle syntaxe v1.x
    resp = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful Forex market analyst."},
            {"role": "user",   "content": prompt}
        ],
        temperature=0.7,
        max_tokens=300
    )
    # Le résultat se trouve dans resp.choices[0].message.content
    return resp.choices[0].message.content.strip()

def process_feed(url: str, prefix: str = "") -> None:
    feed = feedparser.parse(url)
    for entry in feed.entries:
        entry_id = entry.get('id', entry.link)
        if entry_id in seen:
            continue
        seen.add(entry_id)

        # Traduction des textes
        title_en = entry.title
        summary_en = entry.get('summary', '').strip()
        try:
            title_fr = translator.translate(title_en)
            summary_fr = translator.translate(summary_en) if summary_en else ""
        except Exception:
            title_fr, summary_fr = title_en, summary_en

        # Génération IA avec la nouvelle interface
        try:
            ai_text = simplify_and_explain(title_fr, summary_fr)
        except Exception as e:
            ai_text = f"ℹ️ Impossible de générer l'analyse IA : {e}"

        # Envoi uniquement du texte IA + lien
        content = f"{prefix}{ai_text}\n\n{entry.link}"
        try:
            requests.post(WEBHOOK_URL, json={"content": content})
        except Exception as e:
            print(f"Erreur webhook : {e}")

# Parcours des flux classiques et Twitter
for url in FEED_URLS:
    process_feed(url, prefix="")
for url in TWITTER_FEED_URLS:
    process_feed(url, prefix="[Tweet] ")

# Sauvegarde de l’historique
with open(SEEN_FILE, 'w') as f:
    json.dump(list(seen), f)
