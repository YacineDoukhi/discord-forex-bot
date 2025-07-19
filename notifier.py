import os
import json
import feedparser
import requests
from deep_translator import GoogleTranslator

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
WEBHOOK_URL = os.environ['DISCORD_WEBHOOK_URL']
HF_TOKEN    = os.environ['HF_TOKEN']                    # ton secret GitHub existant
HF_MODEL    = "sshleifer/distilbart-cnn-12-6"           # modèle pris en charge
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

# Traducteur auto→fr
translator = GoogleTranslator(source='auto', target='fr')

# Header pour l’API HF
HF_HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}

def hf_summarize(prompt: str) -> str:
    """
    Appelle l’Inference API HuggingFace pour générer le résumé/simplification.
    """
    response = requests.post(
        f"https://api-inference.huggingface.co/models/{HF_MODEL}",
        headers=HF_HEADERS,
        json={"inputs": prompt}
    )
    if response.status_code != 200:
        return f"ℹ️ Erreur HF API : {response.status_code}"
    data = response.json()
    # Certains retours sont une liste de dicts contenant "summary_text"
    if isinstance(data, list) and "summary_text" in data[0]:
        return data[0]["summary_text"].strip()
    # Sinon on essaie un autre champ
    return data.get("summary_text", str(data)).strip()

def simplify_and_explain(title_fr: str, summary_fr: str) -> str:
    """
    Formate le prompt et appelle hf_summarize.
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
    """
    Récupère un flux RSS ou Twitter RSS, filtre les déjà vus,
    traduit, génère le résumé IA, et poste uniquement le texte IA + lien.
    """
    feed = feedparser.parse(url)
    for entry in feed.entries:
        entry_id = entry.get('id', entry.link)
        if entry_id in seen:
            continue
        seen.add(entry_id)

        # Traduction FR
        title_en   = entry.title
        summary_en = entry.get('summary', '').strip()
        try:
            title_fr   = translator.translate(title_en)
            summary_fr = translator.translate(summary_en) if summary_en else ""
        except Exception:
            title_fr, summary_fr = title_en, summary_en

        # Génération IA via HF
        ai_text = simplify_and_explain(title_fr, summary_fr)

        # Envoi Discord
        payload = {"content": f"{prefix}{ai_text}\n\n{entry.link}"}
        try:
            requests.post(WEBHOOK_URL, json=payload)
        except Exception as e:
            print(f"Erreur envoi webhook : {e}")

# Parcours des flux standard et Twitter
for url in FEED_URLS:
    process_feed(url)
for url in TWITTER_FEED_URLS:
    process_feed(url, prefix="[Tweet] ")

# Sauvegarde de l’historique
with open(SEEN_FILE, 'w') as f:
    json.dump(list(seen), f)
