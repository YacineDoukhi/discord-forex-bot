import os
import json
import feedparser
import requests
from deep_translator import GoogleTranslator
from transformers import pipeline

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
WEBHOOK_URL = os.environ['DISCORD_WEBHOOK_URL']

FEED_URLS = [
    'https://www.forexlive.com/feed',
    'https://www.fxstreet.com/rss/rssfeed.aspx?pid=1270&format=xml',
    'https://www.dailyfx.com/feeds/rss/news'
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

# Initialise le pipeline de summarization Hugging Face
summarizer = pipeline("summarization", model="google/flan-t5-base")

def simplify_and_explain(title_fr: str, summary_fr: str) -> str:
    """
    Utilise un modèle Hugging Face pour simplifier le titre et résumé,
    et fournir une explication claire de l'impact sur EUR/USD.
    """
    text = f"Titre : {title_fr}\nRésumé : {summary_fr}"
    try:
        out = summarizer(
            text,
            max_length=150,
            min_length=40,
            do_sample=False
        )
        return out[0]['summary_text'].strip()
    except Exception as e:
        return f"ℹ️ Impossible de générer l'analyse IA : {e}"

# Charge l’historique des IDs déjà envoyés
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, 'r') as f:
        seen = set(json.load(f))
else:
    seen = set()

def process_feed(url: str, prefix: str = "") -> None:
    """
    Lit un flux RSS, filtre les items déjà vus, génère le résumé IA,
    et envoie uniquement ce dernier + le lien dans Discord.
    """
    feed = feedparser.parse(url)
    for entry in feed.entries:
        entry_id = entry.get('id', entry.link)
        if entry_id in seen:
            continue
        seen.add(entry_id)

        # Traduction du titre et du résumé en français
        title_en   = entry.title
        summary_en = entry.get('summary', '').strip()
        try:
            title_fr   = translator.translate(title_en)
            summary_fr = translator.translate(summary_en) if summary_en else ""
        except Exception:
            title_fr, summary_fr = title_en, summary_en

        # Génération du texte simplifié et explicatif
        ai_text = simplify_and_explain(title_fr, summary_fr)

        # Prépare et envoie uniquement le texte IA + lien
        content = f"{prefix}{ai_text}\n\n{entry.link}"
        payload = {"content": content}
        try:
            requests.post(WEBHOOK_URL, json=payload)
        except Exception as e:
            print(f"Erreur envoi webhook : {e}")

# Parcours des flux RSS Forex
for url in FEED_URLS:
    process_feed(url, prefix="")

# Parcours des flux Twitter
for url in TWITTER_FEED_URLS:
    process_feed(url, prefix="[Tweet] ")

# Sauvegarde de l’historique pour la prochaine exécution
with open(SEEN_FILE, 'w') as f:
    json.dump(list(seen), f)
