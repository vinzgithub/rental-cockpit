# Feuille de route

Rental Cockpit avance par **livraisons** courtes et utilisables. Chaque livraison est une demande de fusion (PR) testable seule, avec son image Docker de test (`ghcr.io/vinzgithub/rental-cockpit:pr-<numéro>`), un scénario chiffré et des tests automatiques. Elle n'est fusionnée qu'après validation par les vérificateurs.

| Livraison | Version | Contenu | État |
|---|---|---|---|
| Fondations | 0.1.0 | Application autonome : comptes, droits, double authentification, Synthèse et trois lectures, démonstration séparée, lien Home Assistant, images Docker | ✅ Publiée |
| **L0** — corrections de l'audit | 0.1.1 | Menu sans écran vide, bascule Mes données / Démo, cloche, explications lisibles sur téléphone, copie en HTTP, tests navigateur | En validation |
| **L1** — Séjours | 0.2.0 | Créer, modifier, annuler, rétablir et supprimer des séjours ; canal de réservation ; versements reçus ; fiche séjour avec sa part dans la Synthèse ; migration du format de données avec copie automatique | En validation |
| **L2** — Import | 0.3.0 | Import Airbnb (lecteur repris et adapté) et CSV générique : prévisualisation sans écriture, doublons détectés, commissions (taux pour un CSV), contrôles avant confirmation, validation en une fois, annulation du dernier import | En validation |
| **L3** — Dépenses et règlements | 0.4.0 | Dépenses et recettes hors séjours, paiements partiels, à payer / à recevoir, mensualités d'emprunt, catégories, export CSV | À venir |
| **L4** — Prestataires | 0.5.0 | Prestataires et tarifs, facture à plusieurs prestations répartie entre séjours | À venir |
| **L5** — Justificatifs | 0.6.0 | PDF contrôlés, doublons, lien avec les dépenses, téléchargement après contrôle des droits | À venir |
| **L6** — Version 1.0 | 1.0.0 | Sauvegarde et restauration vérifiées, comptes lecteurs, passe accessibilité et mobile, essai ARM64, recette complète | À venir |

La priorité P0 (utilisable au quotidien) est atteinte à la 0.4.0. Abritel (et d'autres plateformes) ne seront annoncés qu'après analyse d'exports authentiques et anonymisés : aucun format n'est deviné.

## Décisions en attente

- Licence.
