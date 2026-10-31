# Feuille de route

Rental Cockpit avance par lots courts. Chaque écran est proposé en captures pour validation du rendu avant d'être généralisé.

| Lot | Contenu | État |
|---|---|---|
| **1. Fondations** | Inventaire du projet d'origine, moteur de calcul isolé et testé, démonstration fictive séparée | ✅ Fait |
| **1 bis. Application autonome** | Comptes, sessions, droits, stockage SQLite, Docker, Synthèse et accueil | ✅ Fait — préversion 0.1.0 |
| **1 ter. Compte, installation, Home Assistant** | Double authentification (TOTP, codes de secours), réglages du compte, images Docker publiées (x86-64, ARM64), lien facultatif avec Home Assistant (clés en lecture seule, résumé JSON) | ✅ Fait — préversion 0.1.0 |
| **2. Saisie** | Séjours, Dépenses et paiements, Prestataires avec répartition d'une facture | À venir |
| **3. Justificatifs et imports** | Documents PDF (contrôle, doublons, téléchargement protégé), import Airbnb repris, import CSV générique avec prévisualisation | À venir |
| **4. Réglages et sauvegarde** | Lecteurs et droits par bien, catégories, sauvegarde vérifiée et restauration, diagnostic | À venir |
| **5. Version publique** | Essai sur une vraie machine ARM64, tests débutants, audit complet du dépôt, critères T01 à T12, première version étiquetée | À venir |

Abritel (et d'autres plateformes) ne seront annoncés qu'après analyse d'exports authentiques et anonymisés : aucun format n'est deviné.

## Décisions en attente

- Licence.
- Date de la première version étiquetée (elle publie l'image `latest`).
