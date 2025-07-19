import os
import json
from datetime import datetime
import feedparser
import discord
from discord import Intents
from discord.ext import commands, tasks
import openai

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
# Token Discord et variables d'environnement
DISCORD_TOKEN   = os.getenv('DISCORD_TOKEN')
OPENAI_API_KEY  = os.getenv('OPENAI_API_KEY')
CHANNEL_ID      = int(os.getenv('1395968117720612935'))

# Configure l'API OpenAI
openai.api_key = OPENAI_API_KEY

# Flux RSS à surveiller
FEED_URLS = [
    'https://www.forexlive.com/feed',
    'https://www.fxstreet.com/rss/rssfeed.aspx?pid=1270&format=xml',
    'https://www.dailyfx.com/feeds/rss/news',
]

# Mots-clés pour filtrer les actualités pertinentes EUR/USD
KEYWORDS = [
    'forex', 'eur', 'usd', 'euro', 'dollar',
    'fed', 'ecb', 'bce', 'taux', 'interest rate',
    'inflation', 'policy', 'bank', 'trading'
]

SEEN_FILE = 'seen_entries.json'
# ────────────────────────────────────────────────────────────────────────────────

# Charge l'historique des articles déjà notifiés
if os.path.exists(SEEN_FILE):
    with open(SEEN_FILE, 'r') as f:
        seen_entries = set(json.load(f))
else:
    seen_entries = set()

# Initialise le bot Discord avec les intents par défaut
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Connecté en tant que {bot.user} (ID : {bot.user.id})')
    check_feeds.start()

@tasks.loop(minutes=1)
async def check_feeds():
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print(f"⚠️ Canal {CHANNEL_ID} introuvable")
        return

    new_entries = []
    # Parcours des flux et filtrage
    for url in FEED_URLS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            entry_id = entry.get('id') or entry.link
            if entry_id in seen_entries:
                continue
            title   = entry.title
            summary = entry.get('summary', '')
            text    = (title + ' ' + summary).lower()
            # Filtre par mots-clés
            if not any(kw in text for kw in KEYWORDS):
                continue
            seen_entries.add(entry_id)
            new_entries.append((entry, summary))

    # Persiste l'état
    with open(SEEN_FILE, 'w') as f:
        json.dump(list(seen_entries), f)

    # Envoi des notifications avec analyse IA
    for entry, summary in new_entries:
        title     = entry.title
        link      = entry.link
        published = entry.get('published', datetime.utcnow().isoformat())

        # Génération d'une analyse par OpenAI
        prompt = (
            f"Tu es un analyste Forex. Pour l'actualité suivante, "
            f"explique les conséquences potentielles sur le marché EUR/USD :\n\n"
            f"Title: {title}\nSummary: {summary}\n"
        )
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful and concise Forex market analyst."},
                    {"role": "user",   "content": prompt}
                ],
                temperature=0.7,
                max_tokens=250
            )
            analysis = response.choices[0].message.content.strip()
        except Exception as e:
            analysis = "❌ Erreur IA: impossible de générer l'analyse."

        msg = (
            f"**NOUVELLE ACTU FOREX**\n"
            f"**{title}**\n"
            f"Publié: {published}\n{link}\n\n"
            f"**Analyse IA :**\n{analysis}"
        )
        await channel.send(msg)

@bot.command(name='feeds')
async def list_feeds(ctx):
    """Affiche les flux RSS suivis."""
    reply = "Flux RSS surveillés :\n" + "\n".join(f"- {u}" for u in FEED_URLS)
    await ctx.send(reply)

@bot.command(name='addfeed')
@commands.has_permissions(administrator=True)
async def add_feed(ctx, url: str):
    """Ajoute un flux RSS."""
    if url in FEED_URLS:
        await ctx.send("Ce flux est déjà surveillé.")
    else:
        FEED_URLS.append(url)
        await ctx.send(f"Flux ajouté : {url}")

@bot.command(name='removefeed')
@commands.has_permissions(administrator=True)
async def remove_feed(ctx, url: str):
    """Supprime un flux RSS."""
    if url in FEED_URLS:
        FEED_URLS.remove(url)
        await ctx.send(f"Flux supprimé : {url}")
    else:
        await ctx.send("Flux non trouvé.")

if __name__ == '__main__':
    bot.run(DISCORD_TOKEN)