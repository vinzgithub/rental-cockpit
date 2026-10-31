# Installation

Rental Cockpit est une application web autonome. Elle tourne dans un conteneur Docker (recommandé) ou dans un processus Python, et garde toutes ses données dans **un seul dossier**.

> Préversion : testée sur Linux x86-64 avec Python 3.13 et un navigateur Chromium récent. L'image Docker est construite automatiquement pour x86-64 et ARM64 (dont Raspberry Pi 4) à chaque modification, et démarrée pour un test réel en x86-64 ; le fonctionnement sur une vraie machine ARM64 reste à confirmer.

## Avec Docker (recommandé)

Les images sont publiées sur le registre de conteneurs de GitHub, pour **x86-64** et **ARM64** :

| Étiquette | Contenu |
|---|---|
| `ghcr.io/vinzgithub/rental-cockpit:edge` | Dernier état de la branche principale — celle qu'utilise `docker-compose.yml` pendant la préversion |
| `ghcr.io/vinzgithub/rental-cockpit:latest` | Dernière version publiée (à partir de la première version étiquetée) |
| `ghcr.io/vinzgithub/rental-cockpit:0.1` (`0.1.x`…) | Une version précise (idem) |

Quand une version sera publiée, remplacez `:edge` par `:latest` dans `docker-compose.yml` pour ne recevoir que des versions publiées.

### En trois commandes

```bash
mkdir rental-cockpit && cd rental-cockpit
curl -fsSLO https://raw.githubusercontent.com/vinzgithub/rental-cockpit/main/docker-compose.yml
docker compose up -d
```

Ouvrez `http://<adresse-de-la-machine>:8080`. La première visite demande de **créer le compte administrateur** : il n'existe aucun compte par défaut.

Le fichier `docker-compose.yml` :

- publie le port `8080` (mettez `"127.0.0.1:8080:8080"` pour n'écouter que sur la machine elle-même) ;
- garde les données dans le volume `rental-cockpit-data` (monté sur `/data`) ;
- lance le conteneur avec un utilisateur sans privilège (UID 10001), un système de fichiers en lecture seule, `cap_drop: ALL` et `no-new-privileges`.

Pensez à régler `TZ` sur votre fuseau horaire (par exemple `Europe/Paris`).

### Sans Compose

```bash
docker run -d --name rental-cockpit --restart unless-stopped \
  -p 8080:8080 -v rental-cockpit-data:/data -e TZ=Europe/Paris \
  --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges:true \
  ghcr.io/vinzgithub/rental-cockpit:edge
```

### Mise à jour

```bash
docker compose pull
docker compose up -d
```

Copiez le volume de données avant une mise à jour (voir plus bas). Une base écrite par une version plus récente n'est jamais ouverte par une version plus ancienne.

### Construire l'image soi-même

```bash
git clone https://github.com/vinzgithub/rental-cockpit.git
cd rental-cockpit
docker compose -f docker-compose.yml -f compose.build.yaml up -d --build
```

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
| `RENTAL_COCKPIT_FRAME_ANCESTORS` | Origines autorisées à afficher l'application dans un cadre (tableau de bord Home Assistant) | aucune |
| `TZ` | Fuseau horaire utilisé pour « aujourd'hui » | celui du système |
| `FORWARDED_ALLOW_IPS` | Adresse de votre proxy inverse, s'il y en a un | — |

## Le dossier de données

| Fichier | Contenu |
|---|---|
| `rental_cockpit.db` | Comptes, droits, clés d'API (empreintes), registre réel et registre de démonstration (SQLite) |
| `.secret_key` | Clé de signature des sessions, créée au premier démarrage (droits 0600) |
| `documents/` | Justificatifs PDF privés (à partir de l'écran Documents) |

**Sauvegarde manuelle** en attendant la sauvegarde intégrée : arrêtez l'application, copiez tout le dossier, redémarrez.

```bash
docker compose stop
docker run --rm -v rental-cockpit_rental-cockpit-data:/data -v "$PWD":/backup alpine \
  tar czf /backup/rental-cockpit-$(date +%F).tar.gz -C /data .
docker compose start
```

Le nom du volume commence par celui du dossier qui contient `docker-compose.yml` (ici `rental-cockpit`) ; `docker volume ls` l'affiche. Cette archive contient des **données privées** : rangez-la en lieu sûr.

## Dépannage du compte

Téléphone perdu et plus de codes de secours, ou mot de passe oublié : depuis la machine qui héberge Rental Cockpit,

```bash
docker exec -it rental-cockpit python -m rental_cockpit.cli disable-mfa <identifiant>
docker exec -it rental-cockpit python -m rental_cockpit.cli reset-password <identifiant>
```

Chaque commande déconnecte tous les navigateurs du compte.

## Désinstallation

`docker compose down` arrête l'application **sans supprimer** le volume de données. Pour tout effacer définitivement : `docker compose down -v` (irréversible).

## Exposition réseau

Gardez Rental Cockpit sur votre réseau local, ou derrière un proxy inverse en HTTPS avec `RENTAL_COCKPIT_COOKIE_SECURE=true` et la double authentification activée. N'ouvrez pas de port sur votre box sans avoir lu [securite.md](securite.md).
