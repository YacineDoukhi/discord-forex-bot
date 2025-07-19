import os
import json
import feedparser
import requests
from deep_translator import GoogleTranslator

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
WEBHOOK_URL = os.environ['DISCORD_WEBHOOK_URL']
HF_TOKEN    = os.environ['HF_TOKEN']                    # Hugging Face token
HF_MODEL    = "sshleifer/distilbart-cnn-12-6"           # Modèle supporté par Inference API
SEEN_FILE   = 'seen.json'
# ────────────────────────────────────────────────────────────────────────────────

# Flux RSS Forex
FEED_URLS = [
    'https://www.forexlive.com/feed',
    'https://www.fxstreet.com/rss/rssfeed.aspx?pid=1270&format=xml',
    'https://www.dailyfx.com/feeds/rss/news'
]

# Comptes Twitter pro Forex
TWITTER_USERS     = ['kathylienfx','AshrafLaidi','PeterLBrandt','JamieSaettele']
TWITTER_FEED_URLS = [
    f'https://twitrss.me/twitter_user_to_rss/?user={u}'
    for u in TWITTER_USERS
]

# Traducteur auto→fr
translator = GoogleTranslator(source='auto', target='fr')

# En‑têtes pour l’API HF
HF_HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type":  "application/json"
}

def hf_summarize(prompt: str) -> str:
    """
    Appelle l’Inference API HF et logue les détails en cas de 403.
    """
    url = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
    resp = requests.post(url, headers=HF_HEADERS, json={"inputs": prompt})

    if resp.status_code != 200:
        # Debug complet dans les logs Actions
        print("=== HF DEBUG START ===")
        print("URL:               ", url)
        print("Token (prefix5):   ", HF_TOKEN[:5], "…")
        print("Status code:       ", resp.status_code)
        print("Response body:\n", resp.text)
        print("=== HF DEBUG END ===")
        return f"ℹ️ Erreur HF API : {resp.status_code}"

    data = resp.json()
    # Si liste de dicts avec summary_text
    if isinstance(data, list) and "summary_text" in data[0]:
        return data[0]["summary_text"].strip()
    # Sinon tenter autre clé
    return data.get("summary_text", str(data)).strip()

def simplify_and_explain(title_fr: str, summary_fr: str) -> str:
    """
    Construit un prompt pédagogique et le passe à hf_summarize().
    """
    prompt = (
        "Tu es un expert Forex très pédagogique. Simplifie ce titre et ce résumé "
        "pour un débutant, et explique la conséquence probable sur la paire EUR/USD.\n\n"
        f"Titre   : {title_fr}\n"
        f"Résumé  : {summary_fr}"
    )
    return hf_summarize(prompt)

# Charge l’historique des IDs déjà envoyés
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, 'r') as f:
        seen = set(json.load(f))
else:
    seen = set()

def process_feed(url: str, prefix: str = "") -> None:
    """
    Récupère un flux RSS, filtre les déjà vus, traduit, génère le
    résumé/expli IA puis poste uniquement le texte IA + lien.
    """
    feed = feedparser.parse(url)
    for entry in feed.entries:
        entry_id = entry.get('id', entry.link)
        if entry_id in seen:
            continue
        seen.add(entry_id)

        # Traduction
        title_en   = entry.title
        summary_en = entry.get('summary', '').strip()
        try:
            title_fr   = translator.translate(title_en)
            summary_fr = translator.translate(summary_en) if summary_en else ""
        except Exception:
            title_fr, summary_fr = title_en, summary_en

        # Génération IA
        ai_text = simplify_and_explain(title_fr, summary_fr)

        # Envoi Discord
        content = f"{prefix}{ai_text}\n\n{entry.link}"
        try:
            requests.post(WEBHOOK_URL, json={"content": content})
        except Exception as e:
            print(f"Erreur envoi webhook : {e}")

# Traiter les flux RSS Forex
for url in FEED_URLS:
    process_feed(url)

# Traiter les flux Twitter
for url in TWITTER_FEED_URLS:
    process_feed(url, prefix="[Tweet] ")

# Sauvegarde de l’historique
with open(SEEN_FILE, 'w') as f:
    json.dump(list(seen), f)
