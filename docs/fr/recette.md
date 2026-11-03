# Recette de la version 1.0

Chaque critère bloquant du cahier des charges (§ 11), avec ce qui le vérifie. Les tests automatiques tournent à chaque modification, sur Python 3.11, 3.12 et 3.13, plus un Chromium réel pour les parcours (`tests/e2e`). Toutes les données sont fictives.

| Critère | Résultat attendu | Vérification automatique | Vérification manuelle |
|---|---|---|---|
| **T01** Installation neuve | Installation documentée sur x86-64 et ARM64, sans copie de données privées | Image Docker construite pour `linux/amd64` et `linux/arm64` à chaque PR ; conteneur en lecture seule et sans privilège démarré, `/healthz`, sauvegarde en ligne de commande et restauration application arrêtée vérifiées ; image ARM64 lancée sous émulation | Installation sur un poste x86-64 (instances de recette des PR) ; **essai sur Raspberry Pi 4 (ARM64) à faire par la recette** |
| **T02** Neutralité | Aucune donnée personnelle ni montant réel dans le dépôt, ses archives et sa démonstration | `scripts/check_public_data.py` (CI) ; démonstration générée (`tests/test_demo.py`) | Relecture des captures (toutes issues de la démonstration ou de données fictives) |
| **T03** Calculs | 1 000 € → 800 € avant financement, 600 € de trésorerie | `test_documented_example_T03` | Mois d'exemple de la démonstration |
| **T04** PDF complet | Prévisualiser, créer, consulter et télécharger un PDF aux octets identiques | `test_create_an_expense_from_an_invoice`, `test_invoice_to_expense_duplicate_attach_and_detach` (téléchargement comparé octet par octet) | Scénario de la PR L5 |
| **T05** Doublons | Réimport renommé, autre binaire équivalent, double clic, deux validations parallèles : aucune double charge | `test_create_an_expense_from_an_invoice` (même fichier renommé, même référence, cas probable, double clic, seconde validation refusée) ; `test_same_file_again_changes_nothing`, `test_property_creation_double_click_creates_one` | Scénario de la PR L5 (étapes 2 et 5) |
| **T06** Séparation des actions | Joindre ou détacher un PDF ne crée ni ne supprime une dépense ; rapprochement sans double comptage | `test_attach_and_detach_never_change_the_expense`, `test_reconciliation_replaces_entries_typed_by_hand`, `test_supplier_invoice_split_and_reconciled` | Scénarios des PR L4 et L5 |
| **T07** Droits | Commandes, PDF et exports refusés à un utilisateur interdit, y compris pour un identifiant deviné | `test_rights_on_documents`, `test_reader_account_from_creation_to_deletion`, `test_api_supplier_edit_archive_and_rights`, `test_unknown_property_is_refused_not_leaked`, `test_changes_without_csrf_token_are_refused` | Compte lecteur créé depuis les Réglages |
| **T08** Imports | CSV valide accepté, lignes ambiguës expliquées, réimport idempotent, format inconnu refusé | `tests/test_imports.py` (42 tests), dont `test_same_file_again_changes_nothing`, `test_airbnb_reader_refuses_another_export`, `test_api_rejects_unreadable_and_oversized_files` | Scénario de la PR L2 |
| **T09** Prestations | Ménage, linge, déplacement ; facture multi-séjours ; sommes réparties égales au TTC | `tests/test_suppliers.py`, `test_supplier_invoice_split_and_reconciled` | Scénario de la PR L4 |
| **T10** Incidents | Échec de stockage, espace insuffisant, interruption, jeton expiré : état cohérent et message utile | `tests/test_incidents.py` (disque plein à l'enregistrement et pour un PDF, interruption après l'écriture du fichier, aperçu et restauration expirés, jeton CSRF périmé) | — |
| **T11** Sauvegarde | Restauration complète sur une autre installation, documents lisibles et totaux identiques | `test_backup_restored_on_another_installation`, `test_command_line_backup_and_restore_after_a_failed_update`, `test_damaged_or_foreign_backups_are_refused` ; dans l'image Docker, restauration en ligne de commande application arrêtée (CI) | Sauvegarde téléchargée puis restaurée sur une autre instance de recette ([sauvegarde.md](sauvegarde.md)) |
| **T12** Utilisabilité | Clavier, lecteur d'écran, mobile et parcours débutants vérifiés | `tests/e2e/test_accessibility.py` (axe-core sur chaque écran et les principales fenêtres, ordinateur et 360 px, lien « Aller au contenu »), contrôles « tient sur un téléphone » de chaque parcours | **Parcours débutants par au moins cinq personnes extérieures** (créer un bien, saisir une dépense, retrouver son PDF, expliquer un indicateur) : à organiser |

## Premier rapport de recette : anomalies et corrections

Le rapport intermédiaire du 3 novembre 2026 a relevé deux anomalies financières et six points d'ergonomie. Chacun est corrigé, avec son test. Les tests utilisent un export Airbnb fictif construit comme un vrai (`tests/fixtures/airbnb_operations_fr.csv`) ; aucune donnée réelle n'est dans le dépôt.

| Point | Constat | Correction | Vérification automatique |
|---|---|---|---|
| **ANO-001** Remboursement AirCover ignoré | Les lignes « Versement de résolution » n'étaient pas importées : les versements d'un mois ne se retrouvaient pas | Chaque « Payout » est rapproché au centime des lignes qu'il paie ; indemnisations, crédits et retenues deviennent des recettes ou des dépenses ; un type inconnu est à vérifier ; bilan des versements avant import | `test_a_aircover_refund_is_one_income_without_nights` (TEST-A), `test_c_october_payouts_add_up_with_the_refund_apart` (TEST-C), `test_adjustment_withheld_from_a_payout_and_platform_credit`, `test_unknown_type_is_shown_with_its_amount_and_needs_a_choice`, `test_airbnb_operations_and_cancelled_booking` (navigateur) |
| **ANO-002** Réservation annulée mais indemnisée | Seuls « Créer le séjour » et « Ne pas importer » étaient proposés | Troisième choix « Annulé, montant encaissé conservé » : l'argent compte, les nuits non ; proposé sur les deux lignes d'un chevauchement | `test_b_cancelled_but_paid_booking_keeps_the_money_not_the_nights` (TEST-B) |
| **ERGO-001** Trois lectures au même niveau | « Activité », « Factures », « Trésorerie » peu compréhensibles | Synthèse en trois vues : *Mon argent* par défaut, *Performance locative*, *Analyse comptable* (méthodes renommées) ; moteur inchangé | `test_views_say_what_they_add_up` (TEST-E) |
| **ERGO-002** Versement envoyé ou crédité | La Trésorerie affirmait un argent reçu | Libellé « Versements envoyés par les plateformes » ; date d'arrivée bancaire gardée et affichée | `test_a_aircover_refund_is_one_income_without_nights` (date d'arrivée enregistrée) |
| **ERGO-003** Sélecteur de période | Longue liste à parcourir | `◀ Octobre 2026 ▶`, grille des mois, flèches de l'année, mois actuel, année, période libre ; le même sur Dépenses | `test_period_picker_with_the_mouse_and_the_keyboard`, `test_expenses_use_the_same_picker`, `test_period_picker_on_a_phone` (TEST-D) |
| **ERGO-004** Explications sur téléphone | Formule horizontale, colonnes comprimées, défilement | Plein écran sur téléphone, calcul en liste, lignes en cartes jusqu'à 720 px, un seul défilement | `test_every_explanation_fits_a_phone` à 360×760, 390×844 et 760×360, sur toutes les vues et méthodes (TEST-F) |
| **ERGO-005** Copie en HTTP | Les boutons de copie ne fonctionnaient pas | Consigne visible à côté de chaque secret, sélection en un appui, HTTPS conseillé, échec dit dans la fenêtre | `test_copy_by_hand_is_offered_on_plain_http` |
| **ERGO-006** Liens et notifications | Écrans « bientôt disponible », icônes sans effet | Vérifié dans la 1.0.0 : aucun écran « bientôt » ; chaque alerte ouvre sa liste | `test_every_link_and_alert_leads_somewhere`, `test_bell_opens_the_things_to_check` |

Les régressions (TEST-G) sont couvertes par la suite complète, rejouée à chaque modification.

## Qualité

**QUA 01** — L'interface n'appelle que des routes qui existent : `test_interface_calls_only_existing_routes`. Chaque route de modification exige une session, le jeton CSRF et le rôle administrateur. Ses tests de contrat sont dans les fichiers de tests de chaque livraison.

**QUA 02** — Mesures sur un conteneur Linux x86-64 (Python 3.13, SQLite), avec 10 000 écritures, 2 000 séjours, 3 334 paiements et 4 biens fictifs (`tests/test_performance.py` garde une version réduite de ce jeu) :

| Opération | Durée |
|---|---|
| Synthèse d'un mois, d'une année ou de six ans (chaque lecture) | 0,13 à 0,23 s |
| Liste des dépenses (toutes) | 0,16 s |
| Liste des séjours (tous) | 0,06 s |
| Aperçu d'un import CSV de 18 000 lignes | 0,3 s (écriture : 1,5 s) |
| Sauvegarde complète | 0,6 s |

Objectifs du cahier des charges : Synthèse en moins de 2 s, aperçu d'un CSV de 5 000 lignes en moins de 10 s. Aucun calcul ne demande Internet.

## Limites connues de la 1.0

- Pas d'OCR : un PDF scanné se décrit à la main.
- Un justificatif appartient à un seul bien ; la ventilation explicite d'une facture entre biens viendra plus tard.
- Abritel et les autres plateformes ne seront ajoutés qu'à partir d'exports authentiques anonymisés.
- La sauvegarde est déclenchée à la main (Réglages ou ligne de commande) : pas encore de sauvegarde planifiée.
