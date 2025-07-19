# Discord Forex Notifier

Bot Discord qui surveille des flux RSS Forex et envoie des notifications sur la paire EUR/USD, 
avec analyse IA des conséquences sur le marché.

## Prérequis

- Python 3.8+
- Un compte Discord et un bot créé dans le Developer Portal
- Une clé API OpenAI

## Fichiers

- `notifier.py`          — le script principal du bot
- `requirements.txt`     — liste des dépendances
- `Procfile`             — instruction pour Railway
- `.gitignore`           — fichiers/dossiers à ignorer par Git

## Déploiement sur Railway

1. Pousse ce repo sur GitHub (`main` branch).
2. Sur [Railway.app](https://railway.app), crée un nouveau projet **Deploy from GitHub** et sélectionne ce repo.
3. Dans **Settings → Variables**, ajoute :
   - `DISCORD_TOKEN`       → ton token Discord
   - `DISCORD_CHANNEL_ID`  → l’ID du canal Discord
   - `OPENAI_API_KEY`      → ta clé API OpenAI
4. Railway build et lance automatiquement le worker.
5. Vérifie les **Logs** pour t’assurer que le bot se connecte.

Ton bot tourne maintenant **24/7** gratuitement !
