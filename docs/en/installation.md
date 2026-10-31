# Installation

Rental Cockpit is a standalone web application. It runs in a Docker container or a Python process, and keeps all its data in **one folder**.

> Preview 0.1.0: tested on Linux x86-64 with Python 3.13 and a recent Chromium browser. The Docker image and ARM64 machines (Raspberry Pi 4) still have to be validated before a stable release.

## With Docker Compose (recommended)

Requirements: Docker and Docker Compose.

```bash
git clone https://github.com/vinzgithub/rental-cockpit.git
cd rental-cockpit
docker compose up -d --build
```

Open `http://<machine-address>:8080`. The first visit asks you to **create the administrator account**: there is no default account.

The provided `docker-compose.yml`:

- publishes port `8080` (change it to `"127.0.0.1:8080:8080"` to listen on the machine only);
- keeps data in the `rental-cockpit-data` volume (mounted on `/data`);
- runs the container as an unprivileged user with a read-only filesystem, `cap_drop: ALL` and `no-new-privileges`.

### Upgrading

```bash
cd rental-cockpit
git pull
docker compose up -d --build
```

Copy the data volume before any upgrade (see below). A database written by a newer version is never opened by an older one.

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
| `TZ` | Time zone used for "today" | the system's |
| `FORWARDED_ALLOW_IPS` | Address of your reverse proxy, if any | — |

## The data folder

| File | Content |
|---|---|
| `rental_cockpit.db` | Accounts, rights, real registry and demo registry (SQLite) |
| `.secret_key` | Session signing key, created on first start (mode 0600) |
| `documents/` | Private PDF documents (from the Documents screen on) |

**Manual backup** until the Settings screen exists: stop the app, copy the whole folder, start again.

```bash
docker compose stop
docker run --rm -v rental-cockpit_rental-cockpit-data:/data -v "$PWD":/backup alpine \
  tar czf /backup/rental-cockpit-$(date +%F).tar.gz -C /data .
docker compose start
```

This archive holds **private data**: keep it somewhere safe.

## Uninstalling

`docker compose down` stops the application **without deleting** the data volume. To erase everything permanently: `docker compose down -v` (cannot be undone).

## Network exposure

Keep Rental Cockpit on your local network, or behind an HTTPS reverse proxy with `RENTAL_COCKPIT_COOKIE_SECURE=true`. Do not open a port on your router without reading [security.md](security.md).
