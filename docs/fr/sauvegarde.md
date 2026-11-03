# Sauvegarde et restauration

Une sauvegarde Rental Cockpit est **un fichier ZIP** qui contient tout « Mes données » et rien d'autre.

| Dans la sauvegarde | Jamais dans la sauvegarde |
|---|---|
| Biens, séjours, dépenses, recettes, paiements, prestataires, catégories, imports, historique | Mots de passe (même chiffrés) |
| Justificatifs PDF (fichiers d'origine, nommés par leur empreinte SHA-256) | Codes de double authentification et codes de secours |
| Comptes lecteurs et leurs droits, par nom | Clés d'API (Home Assistant) |
| Manifeste : version, schéma, date, nombres, totaux, empreinte de chaque fichier | La démonstration (elle se reconstruit à la demande) |

> [!WARNING]
> Une sauvegarde contient des **données privées** (montants, séjours, factures). Gardez-la hors de la machine qui héberge Rental Cockpit, à l'abri, comme un relevé bancaire.

## Créer une sauvegarde

**Réglages → Sauvegarde et restauration → Créer une sauvegarde** (administrateurs). Le fichier est écrit dans `backups/` du dossier de données, **relu et vérifié**, puis téléchargé par le navigateur. La liste « Sauvegardes sur le serveur » permet de le télécharger à nouveau ou de le supprimer du serveur.

En ligne de commande, depuis la machine qui héberge Rental Cockpit :

```bash
docker exec rental-cockpit python -m rental_cockpit.cli backup
docker cp rental-cockpit:/data/backups/ ./sauvegardes-rental-cockpit/
```

Si un justificatif manque déjà dans le stockage privé, la sauvegarde le signale ; elle contient tout le reste.

## Restaurer une sauvegarde

**Réglages → Sauvegarde et restauration → Restaurer une sauvegarde**, puis choisissez le fichier ZIP.

1. **Vérification dans une copie de recette.** L'archive est décompressée dans un dossier à part (`restore-staging/`). Rien n'est encore modifié. Chaque fichier est comparé à son empreinte et chaque PDF à son nom. Le registre est relu et, s'il vient d'une version plus ancienne, converti au format actuel. Les nombres et les totaux sont recalculés et comparés au manifeste. Une archive modifiée, incomplète, étrangère ou venant d'une version plus récente est refusée, et rien n'est restauré.
2. **Comparaison.** Un tableau montre, pour la sauvegarde et pour vos données actuelles, le nombre de biens, de séjours, de dépenses, de paiements, de prestataires et de justificatifs, ainsi que les totaux des dépenses, des recettes hors séjours et des paiements.
3. **Confirmation.** Tapez **REMPLACER** (**REPLACE** en anglais), puis **Remplacer mes données**. Vos données actuelles sont d'abord enregistrées dans une nouvelle sauvegarde, `avant-restauration-….zip`, sur le serveur. Ensuite seulement, elles sont remplacées.
4. **Résultat.** Rental Cockpit indique si les totaux sont identiques à ceux de la sauvegarde.

Les droits des lecteurs sont rétablis pour les comptes qui existent déjà sur cette installation, par nom. Les lecteurs absents sont listés : créez-les, puis ouvrez-leur leurs biens. Les comptes eux-mêmes et votre propre compte ne sont jamais remplacés.

La vérification expire après 30 minutes. La taille maximale d'une sauvegarde envoyée est de 2 Gio ; elle se règle avec `RENTAL_COCKPIT_MAX_BACKUP_MB`. Derrière un proxy inverse, autorisez des requêtes de cette taille, ou restaurez en ligne de commande.

## Restaurer après une mise à jour qui s'est mal passée

Ces étapes sont exécutées par les tests automatiques : `test_command_line_backup_and_restore_after_a_failed_update`.

1. **Avant toute mise à jour**, créez une sauvegarde et téléchargez-la.
2. Si la nouvelle version pose problème, **revenez à la version précédente de l'image** (par exemple `image: ghcr.io/vinzgithub/rental-cockpit:1.0.0` dans `docker-compose.yml`). Revenir au code ne ramène pas les données : une base convertie par une version plus récente n'est jamais ouverte par une plus ancienne.
3. Arrêtez l'application, puis restaurez la sauvegarde avec l'application arrêtée, depuis le dossier qui contient `docker-compose.yml` :

```bash
docker compose stop
# 1. Vérification seule : rien n'est modifié
docker compose run --rm -T rental-cockpit python -m rental_cockpit.cli restore - < rental-cockpit-sauvegarde-AAAAMMJJ-HHMMSS.zip
# 2. Si le contenu affiché est le bon : la même commande avec --yes
docker compose run --rm -T rental-cockpit python -m rental_cockpit.cli restore - --yes < rental-cockpit-sauvegarde-AAAAMMJJ-HHMMSS.zip
docker compose start
```

La sauvegarde est transmise par l'entrée standard (`-` et `<`) : le conteneur, qui ne tourne pas en administrateur, n'a pas besoin du droit de lire un fichier de votre machine. La première commande vérifie la sauvegarde et affiche son contenu (date, version, nombres, biens) sans rien modifier. La seconde enregistre les données remplacées dans `backups/avant-restauration-….zip`, restaure, puis dit si les totaux sont identiques.

Pour une sauvegarde déjà présente dans le dossier de données, `restore /data/backups/<fichier>.zip`, sans `-T` ni `<`, demande de taper REMPLACER.

Quand une version change le format des données, Rental Cockpit écrit aussi, avant de les convertir, une copie complète de la base dans `backups/pre-migration-….db`. Ce filet de sécurité supplémentaire ne remplace pas une sauvegarde téléchargée.

## Désinstaller sans perdre ses données

`docker compose down` arrête et retire le conteneur, **sans supprimer** le volume de données : vos registres, vos PDF et vos sauvegardes restent. La suppression définitive est une commande séparée, `docker compose down -v`, irréversible. Faites une sauvegarde avant.
