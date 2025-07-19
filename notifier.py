import os
import json
import feedparser
import requests
from deep_translator import GoogleTranslator

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
WEBHOOK_URL = os.environ['DISCORD_WEBHOOK_URL']
HF_TOKEN    = os.environ['HF_TOKEN']            # Hugging Face token en secret GitHub
HF_MODEL    = "google/flan-t5-base"             # modèle à appeler
# ────────────────────────────────────────────────────────────────────────────────

# Flux RSS Forex
FEED_URLS = [
    'https://www.forexlive.com/feed',
    'https://www.fxstreet.com/rss/rssfeed.aspx?pid=1270&format=xml',
    'https://www.dailyfx.com/feeds/rss/news'
]

TWITTER_USERS = ['kathylienfx','AshrafLaidi','PeterLBrandt','JamieSaettele']
TWITTER_FEED_URLS = [
    f'https://twitrss.me/twitter_user_to_rss/?user={u}' for u in TWITTER_USERS
]

SEEN_FILE = 'seen.json'

# Initialise le traducteur auto→fr
translator = GoogleTranslator(source='auto', target='fr')

# Headers pour HF Inference API
HF_HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}

def hf_summarize(prompt: str) -> str:
    """Appelle l’Inference API HuggingFace pour générer le résumé."""
    resp = requests.post(
        f"https://api-inference.huggingface.co/models/{HF_MODEL}",
        headers=HF_HEADERS,
        json={"inputs": prompt}
    )
    if not resp.ok:
        return f"ℹ️ Erreur HF API : {resp.status_code}"
    data = resp.json()
    # Certains modèles renvoient une liste de dicts :
    if isinstance(data, list) and "generated_text" in data[0]:
        return data[0]["generated_text"].strip()
    # Autre format ?
    return data.get("generated_text", str(data)).strip()

def simplify_and_explain(title_fr: str, summary_fr: str) -> str:
    """
    Construit un prompt et passe à HF pour simplifier + expliquer l’impact EUR/USD.
    """
    prompt = (
        "Tu es un expert Forex très pédagogique. Simplifie ce titre et ce résumé "
        "pour un débutant, et explique la conséquence probable sur la paire EUR/USD.\n\n"
        f"Titre : {title_fr}\nRésumé : {summary_fr}"
    )
    return hf_summarize(prompt)

# Charge l’historique
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, 'r') as f:
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

        # Traduction
        title_en   = entry.title
        summary_en = entry.get('summary', '').strip()
        try:
            title_fr   = translator.translate(title_en)
            summary_fr = translator.translate(summary_en) if summary_en else ""
        except Exception:
            title_fr, summary_fr = title_en, summary_en

        # Génération du texte
        ai_text = simplify_and_explain(title_fr, summary_fr)

        # Envoi Discord
        payload = {"content": f"{prefix}{ai_text}\n\n{entry.link}"}
        try:
            requests.post(WEBHOOK_URL, json=payload)
        except Exception as e:
            print(f"Erreur envoi webhook : {e}")

# Traite tous les flux
for url in FEED_URLS:
    process_feed(url)
for url in TWITTER_FEED_URLS:
    process_feed(url, prefix="[Tweet] ")

# Sauvegarde de l’historique
with open(SEEN_FILE, 'w') as f:
    json.dump(list(seen), f)
