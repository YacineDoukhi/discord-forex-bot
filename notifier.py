import os
import json
import feedparser
import requests
from deep_translator import GoogleTranslator
from transformers import pipeline

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
WEBHOOK_URL = os.environ['DISCORD_WEBHOOK_URL']
SEEN_FILE   = 'seen.json'
# ────────────────────────────────────────────────────────────────────────────────

FEED_URLS = [
    'https://www.forexlive.com/feed',
    'https://www.fxstreet.com/rss/rssfeed.aspx?pid=1270&format=xml',
    'https://www.dailyfx.com/feeds/rss/news',
]
TWITTER_USERS     = ['kathylienfx','AshrafLaidi','PeterLBrandt','JamieSaettele']
TWITTER_FEED_URLS = [f'https://twitrss.me/twitter_user_to_rss/?user={u}' for u in TWITTER_USERS]

translator = GoogleTranslator(source='auto', target='fr')
# Pipeline local : summarization
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

def simplify_and_explain(title_fr: str, summary_fr: str) -> str:
    prompt = (
        "Tu es un expert Forex très pédagogique.\n"
        "Simplifie ce titre et ce résumé pour un débutant, "
        "et explique la conséquence probable sur la paire EUR/USD.\n\n"
        f"Titre : {title_fr}\nRésumé : {summary_fr}"
    )
    try:
        out = summarizer(prompt, max_length=150, min_length=40, do_sample=False)
        return out[0]['summary_text'].strip()
    except Exception as e:
        return f"ℹ️ Erreur pipeline local : {e}"

# Charge l’historique
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE,'r') as f:
        seen = set(json.load(f))
else:
    seen = set()

def process_feed(url: str, prefix: str = "") -> None:
    feed = feedparser.parse(url)
    for entry in feed.entries:
        eid = entry.get('id', entry.link)
        if eid in seen:
            continue
        seen.add(eid)

        title_en   = entry.title
        summary_en = entry.get('summary','').strip()
        try:
            title_fr   = translator.translate(title_en)
            summary_fr = translator.translate(summary_en) if summary_en else ""
        except:
            title_fr, summary_fr = title_en, summary_en

        ai_text = simplify_and_explain(title_fr, summary_fr)
        payload = {"content": f"{prefix}{ai_text}\n\n{entry.link}"}
        try:
            requests.post(WEBHOOK_URL, json=payload)
        except Exception as e:
            print(f"Erreur webhook : {e}")

# Traite tous les flux
for u in FEED_URLS:
    process_feed(u)
for u in TWITTER_FEED_URLS:
    process_feed(u, prefix="[Tweet] ")

# Sauvegarde
with open(SEEN_FILE,'w') as f:
    json.dump(list(seen), f)
