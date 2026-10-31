# Installation

Rental Cockpit est une application web autonome. Elle tourne dans un conteneur Docker ou dans un processus Python, et garde toutes ses données dans **un seul dossier**.

> Préversion 0.1.0 : testée sur Linux x86-64 avec Python 3.13 et dans un navigateur Chromium récent. L'image Docker et les machines ARM64 (Raspberry Pi 4) restent à valider avant une version stable.

## Avec Docker Compose (recommandé)

Prérequis : Docker et Docker Compose.

```bash
git clone https://github.com/vinzgithub/rental-cockpit.git
cd rental-cockpit
docker compose up -d --build
```

Ouvrez `http://<adresse-de-la-machine>:8080`. La première visite demande de **créer le compte administrateur** : il n'existe aucun compte par défaut.

Le fichier `docker-compose.yml` fourni :

- publie le port `8080` (modifiable : `"127.0.0.1:8080:8080"` pour n'écouter que sur la machine elle-même) ;
- garde les données dans le volume `rental-cockpit-data` (monté sur `/data`) ;
- lance le conteneur avec un utilisateur sans privilège, un système de fichiers en lecture seule, `cap_drop: ALL` et `no-new-privileges`.

### Mise à jour

```bash
cd rental-cockpit
git pull
docker compose up -d --build
```

Avant toute mise à jour, faites une copie du volume de données (voir plus bas). Une base écrite par une version plus récente n'est jamais ouverte par une version plus ancienne.

## Sans Docker

Prérequis : Python 3.11 ou plus récent.

```bash
git clone https://github.com/vinzgithub/rental-cockpit.git
cd rental-cockpit
python3 -m venv .venv
. .venv/bin/activate
pip install .
RENTAL_COCKPIT_DATA_DIR="$HOME/rental-cockpit-data" \
  uvicorn --factory rental_cockpit.app:create_app --host 127.0.0.1 --port 8080
```

Gardez **un seul processus** (`--workers 1`, la valeur par défaut) : l'application est la seule autorité sur ses données.

## Variables d'environnement

| Variable | Rôle | Par défaut |
|---|---|---|
| `RENTAL_COCKPIT_DATA_DIR` | Dossier des données | `./data` (`/data` dans l'image) |
| `RENTAL_COCKPIT_COOKIE_SECURE` | `true` quand l'application est servie en HTTPS | `false` |
| `RENTAL_COCKPIT_DEFAULT_LOCALE` | Langue proposée avant la connexion (`fr` ou `en`) | `fr` |
| `RENTAL_COCKPIT_SESSION_MAX_AGE` | Durée d'une session, en secondes | `604800` (7 jours) |
| `TZ` | Fuseau horaire utilisé pour « aujourd'hui » | celui du système |
| `FORWARDED_ALLOW_IPS` | Adresse de votre proxy inverse, s'il y en a un | — |

## Le dossier de données

| Fichier | Contenu |
|---|---|
| `rental_cockpit.db` | Comptes, droits, registre réel et registre de démonstration (SQLite) |
| `.secret_key` | Clé de signature des sessions, créée au premier démarrage (droits 0600) |
| `documents/` | Justificatifs PDF privés (à partir de l'écran Documents) |

**Sauvegarde manuelle** en attendant l'écran Réglages : arrêtez l'application, copiez tout le dossier, redémarrez.

```bash
docker compose stop
docker run --rm -v rental-cockpit_rental-cockpit-data:/data -v "$PWD":/backup alpine \
  tar czf /backup/rental-cockpit-$(date +%F).tar.gz -C /data .
docker compose start
```

Cette archive contient des **données privées** : rangez-la en lieu sûr.

## Désinstallation

`docker compose down` arrête l'application **sans supprimer** le volume de données. Pour tout effacer définitivement : `docker compose down -v` (irréversible).

## Exposition réseau

Gardez Rental Cockpit sur votre réseau local, ou derrière un proxy inverse en HTTPS avec `RENTAL_COCKPIT_COOKIE_SECURE=true`. N'ouvrez pas de port sur votre box sans avoir lu [securite.md](securite.md).
