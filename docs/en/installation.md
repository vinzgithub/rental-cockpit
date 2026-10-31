# Installation

Rental Cockpit is a standalone web application. It runs in a Docker container (recommended) or a Python process, and keeps all its data in **one folder**.

> Preview: tested on Linux x86-64 with Python 3.13 and a recent Chromium browser. The Docker image is built automatically for x86-64 and ARM64 (including Raspberry Pi 4) on every change, and started for a real test on x86-64; running on a real ARM64 machine is still to be confirmed.

## With Docker (recommended)

Images are published on GitHub's container registry for **x86-64** and **ARM64**:

| Tag | Content |
|---|---|
| `ghcr.io/vinzgithub/rental-cockpit:latest` | Latest released version — the one `docker-compose.yml` uses |
| `ghcr.io/vinzgithub/rental-cockpit:0.1` | Stays on 0.1.x versions |
| `ghcr.io/vinzgithub/rental-cockpit:0.1.0` | A specific version |
| `ghcr.io/vinzgithub/rental-cockpit:edge` | Latest state of the main branch, to try what is coming |

### In three commands

```bash
mkdir rental-cockpit && cd rental-cockpit
curl -fsSLO https://raw.githubusercontent.com/vinzgithub/rental-cockpit/main/docker-compose.yml
docker compose up -d
```

Open `http://<machine-address>:8080`. The first visit asks you to **create the administrator account**: there is no default account.

The `docker-compose.yml` file:

- publishes port `8080` (use `"127.0.0.1:8080:8080"` to listen on the machine only);
- keeps data in the `rental-cockpit-data` volume (mounted on `/data`);
- runs the container as an unprivileged user (UID 10001) with a read-only filesystem, `cap_drop: ALL` and `no-new-privileges`.

Remember to set `TZ` to your time zone (for example `Europe/Paris`).

### Without Compose

```bash
docker run -d --name rental-cockpit --restart unless-stopped \
  -p 8080:8080 -v rental-cockpit-data:/data -e TZ=Europe/Paris \
  --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges:true \
  ghcr.io/vinzgithub/rental-cockpit:latest
```

### Upgrading

```bash
docker compose pull
docker compose up -d
```

Copy the data volume before an upgrade (see below). When a new version changes the data format, Rental Cockpit also writes a full copy of the database to `backups/` before converting it. A database written by a newer version is never opened by an older one.

### Building the image yourself

```bash
git clone https://github.com/vinzgithub/rental-cockpit.git
cd rental-cockpit
docker compose -f docker-compose.yml -f compose.build.yaml up -d --build
```

## Without Docker

Requirements: Python 3.11 or newer.

```bash
git clone https://github.com/vinzgithub/rental-cockpit.git
cd rental-cockpit
python3 -m venv .venv
. .venv/bin/activate
pip install .
RENTAL_COCKPIT_DATA_DIR="$HOME/rental-cockpit-data" \
  uvicorn --factory rental_cockpit.app:create_app --host 127.0.0.1 --port 8080
```

Keep **one process** (`--workers 1`, the default): the application is the only authority over its data.

## Environment variables

| Variable | Role | Default |
|---|---|---|
| `RENTAL_COCKPIT_DATA_DIR` | Data folder | `./data` (`/data` in the image) |
| `RENTAL_COCKPIT_COOKIE_SECURE` | `true` when served over HTTPS | `false` |
| `RENTAL_COCKPIT_DEFAULT_LOCALE` | Language offered before signing in (`fr` or `en`) | `fr` |
| `RENTAL_COCKPIT_SESSION_MAX_AGE` | Session length, in seconds | `604800` (7 days) |
| `RENTAL_COCKPIT_FRAME_ANCESTORS` | Origins allowed to show the app in a frame (Home Assistant dashboard) | none |
| `TZ` | Time zone used for "today" | the system's |
| `FORWARDED_ALLOW_IPS` | Address of your reverse proxy, if any | — |

## The data folder

| File | Content |
|---|---|
| `rental_cockpit.db` | Accounts, rights, API keys (hashes), real registry and demo registry (SQLite) |
| `.secret_key` | Session signing key, created on first start (mode 0600) |
| `backups/` | Automatic copies of the database made before each data format migration (`pre-migration-v1-to-v2-….db`) |
| `documents/` | Private PDF documents (from the Documents screen on) |

**Manual backup** until the built-in backup exists: stop the app, copy the whole folder, start again.

```bash
docker compose stop
docker run --rm -v rental-cockpit_rental-cockpit-data:/data -v "$PWD":/backup alpine \
  tar czf /backup/rental-cockpit-$(date +%F).tar.gz -C /data .
docker compose start
```

The volume name starts with the name of the folder holding `docker-compose.yml` (here `rental-cockpit`); `docker volume ls` shows it. This archive holds **private data**: keep it somewhere safe.

## Account recovery

Lost phone and no recovery code left, or forgotten password: on the machine running Rental Cockpit,

```bash
docker exec -it rental-cockpit python -m rental_cockpit.cli disable-mfa <username>
docker exec -it rental-cockpit python -m rental_cockpit.cli reset-password <username>
```

Each command signs out every browser of the account.

## Uninstalling

`docker compose down` stops the application **without deleting** the data volume. To erase everything permanently: `docker compose down -v` (cannot be undone).

## Network exposure

Keep Rental Cockpit on your local network, or behind an HTTPS reverse proxy with `RENTAL_COCKPIT_COOKIE_SECURE=true` and two-factor sign-in turned on. Do not open a port on your router without reading [security.md](security.md).
