# Feuille de route

Rental Cockpit avance par lots courts. Chaque écran est proposé en captures pour validation du rendu avant d'être généralisé.

| Lot | Contenu | État |
|---|---|---|
| **1. Fondations** | Inventaire du projet d'origine, moteur de calcul isolé et testé, démonstration fictive séparée | ✅ Fait |
| **1 bis. Application autonome** | Comptes, sessions, droits, stockage SQLite, Docker, Synthèse et accueil | ✅ Fait — préversion 0.1.0 |
| **2. Saisie** | Séjours, Dépenses et paiements, Prestataires avec répartition d'une facture | À venir |
| **3. Justificatifs et imports** | Documents PDF (contrôle, doublons, téléchargement protégé), import Airbnb repris, import CSV générique avec prévisualisation | À venir |
| **4. Réglages et sauvegarde** | Lecteurs et droits par bien, double authentification, catégories, sauvegarde vérifiée et restauration, diagnostic | À venir |
| **5. Version publique** | Image Docker x86-64 et ARM64, tests débutants, audit complet du dépôt, critères T01 à T12 | À venir |

Abritel (et d'autres plateformes) ne seront annoncés qu'après analyse d'exports authentiques et anonymisés : aucun format n'est deviné.

## Décisions en attente

- Licence.
- Image Docker publiée ou construction locale seulement.
- Lien facultatif avec Home Assistant (lecture seule), jamais requis.
