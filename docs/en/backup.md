# Backup and restore

A Rental Cockpit backup is **one ZIP file** that holds all of "My data" and nothing else.

| In the backup | Never in the backup |
|---|---|
| Properties, stays, expenses, income, payments, suppliers, categories, imports, history | Passwords (even hashed) |
| PDF documents (original files, named by their SHA-256 fingerprint) | Two-factor secrets and recovery codes |
| Reader accounts and their rights, by name | API keys (Home Assistant) |
| Manifest: version, schema, date, counts, totals, fingerprint of every file | The demo (it is rebuilt on demand) |

> [!WARNING]
> A backup holds **private data** (amounts, stays, invoices). Keep it away from the machine that runs Rental Cockpit, somewhere safe, like a bank statement.

## Create a backup

**Settings → Backup and restore → Create a backup** (administrators). The file is written in `backups/` of the data folder, **read back and checked**, then downloaded by the browser. The "Backups on the server" list lets you download it again or delete it from the server.

From the command line, on the machine that runs Rental Cockpit:

```bash
docker exec rental-cockpit python -m rental_cockpit.cli backup
docker cp rental-cockpit:/data/backups/ ./rental-cockpit-backups/
```

If a document is already missing from private storage, the backup says so and holds everything else.

## Restore a backup

**Settings → Backup and restore → Restore a backup**, then choose the ZIP file.

1. **Check in a test copy.** The archive is unpacked in a separate folder (`restore-staging/`); nothing is changed yet. Every file is compared with its fingerprint and every PDF with its name. The registry is read again and, when it comes from an older version, brought to the current format. The counts and totals are computed again and compared with the manifest. An archive that was changed, is incomplete, foreign or from a newer version is refused, and nothing is restored.
2. **Comparison.** A table shows, for the backup and for your current data, the number of properties, stays, expenses, payments, suppliers and documents, and the totals of expenses, income outside stays and payments.
3. **Confirmation.** Type **REPLACE** (**REMPLACER** in French), then **Replace my data**. Your current data are first saved in a new backup, `avant-restauration-….zip`, on the server. Only then are they replaced.
4. **Result.** Rental Cockpit says whether the totals are the same as in the backup.

The readers' rights come back for the accounts that already exist on this installation, by name. Missing readers are listed: create them, then open their properties to them. Accounts themselves and your own account are never replaced.

The check expires after 30 minutes. The largest backup that can be sent is 2 GiB; set it with `RENTAL_COCKPIT_MAX_BACKUP_MB`. Behind a reverse proxy, allow requests of that size, or restore from the command line.

## Restore after an update that went wrong

These steps are run by the automated tests: `test_command_line_backup_and_restore_after_a_failed_update`.

1. **Before any update**, create a backup and download it.
2. If the new version causes trouble, **go back to the previous image version** (for example `image: ghcr.io/vinzgithub/rental-cockpit:1.0.0` in `docker-compose.yml`). Going back in code does not bring the data back: a database converted by a newer version is never opened by an older one.
3. Stop the application, then restore the backup while it is stopped, from the folder that holds `docker-compose.yml`:

```bash
docker compose stop
# 1. Check only: nothing is changed
docker compose run --rm -T rental-cockpit python -m rental_cockpit.cli restore - < rental-cockpit-sauvegarde-YYYYMMDD-HHMMSS.zip
# 2. If the content shown is the right one: the same command with --yes
docker compose run --rm -T rental-cockpit python -m rental_cockpit.cli restore - --yes < rental-cockpit-sauvegarde-YYYYMMDD-HHMMSS.zip
docker compose start
```

The backup is passed on standard input (`-` and `<`): the container, which does not run as an administrator, does not need the right to read a file of your machine. The first command checks the backup and shows its content (date, version, counts, properties) without changing anything. The second saves the data it replaces in `backups/avant-restauration-….zip`, restores, then says whether the totals are the same.

For a backup already in the data folder, `restore /data/backups/<file>.zip`, without `-T` or `<`, asks you to type REMPLACER (or REPLACE).

When a version changes the data format, Rental Cockpit also writes, before converting, a full copy of the database in `backups/pre-migration-….db`. This extra safety net does not replace a downloaded backup.

## Uninstall without losing data

`docker compose down` stops and removes the container **without deleting** the data volume: your registries, PDFs and backups stay. Permanent deletion is a separate command, `docker compose down -v`, which cannot be undone. Make a backup first.
