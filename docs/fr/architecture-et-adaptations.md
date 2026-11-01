# Architecture et adaptations

Ce document explique comment Rental Cockpit est construit, ce qui est repris du projet privé d'origine, et ce qui change depuis que Rental Cockpit est une **application autonome**. Il sert de référence avant de décliner les écrans Séjours, Dépenses, Prestataires, Documents et Réglages.

## La décision

Rental Cockpit avait d'abord été prévu comme un module pour Home Assistant. Depuis le 31 octobre 2026, c'est une application web autonome : **Home Assistant n'est nécessaire ni pour l'installation, ni pour l'authentification, ni pour le stockage, ni pour l'interface.**

Le projet privé d'origine n'est ni modifié, ni lu en fonctionnement : le code public est une copie isolée, adaptée et neutralisée (aucun nom de maison, adresse, fournisseur imposé, montant ou document personnel).

## Vue d'ensemble

```
Navigateur ──HTTPS (proxy facultatif)──► Application Rental Cockpit (un processus)
                                          ├─ interface : HTML, CSS, modules JavaScript servis par l'application
                                          ├─ API JSON /api/* : session, contrôle CSRF, droits vérifiés à chaque requête
                                          ├─ API /api/v1/summary : lecture seule, clé d'API ◄── Home Assistant (facultatif)
                                          ├─ moteur métier (Python pur, sans dépendance)
                                          └─ dossier de données /data
                                               ├─ rental_cockpit.db   comptes, droits, clés (empreintes), registre réel, registre de démonstration
                                               ├─ documents/          justificatifs PDF privés (à venir)
                                               └─ .secret_key         clé de signature des sessions (0600)
```

| Couche | Rôle | Fichiers |
|---|---|---|
| Moteur métier | Montants en centimes, dates, biens, séjours, écritures, paiements, prestations ventilées, trois lectures, indicateurs expliqués, démonstration | `src/rental_cockpit/engine/` |
| Stockage | SQLite, une transaction par modification, numéro de révision | `src/rental_cockpit/database.py` |
| Droits | Administrateur, lecteur par bien, accès PDF séparé | `src/rental_cockpit/access.py` |
| Sécurité | Mots de passe scrypt, jeton CSRF, limitation des essais, codes TOTP, codes de secours, clés d'API | `src/rental_cockpit/security.py` |
| Application web | Routes, en-têtes de sécurité, sessions, connexion en deux étapes | `src/rental_cockpit/app.py`, `web.py` |
| Compte | Mot de passe, double authentification, clés d'API | `src/rental_cockpit/account_routes.py` |
| Lien Home Assistant | Résumé en lecture seule pour l'intégration RESTful | `src/rental_cockpit/ha_api.py` |
| Séjours | API des séjours et des versements ; nuits, versement attendu, état du versement et part mois par mois calculés à la volée avec les règles des indicateurs | `src/rental_cockpit/stay_routes.py`, `engine/stays.py` |
| Import | Lecteurs Airbnb et CSV (lecture seule), aperçu comparé au registre, écriture en une transaction, annulation du dernier import | `src/rental_cockpit/import_routes.py`, `engine/imports/` |
| Dépannage | Réinitialiser un mot de passe, désactiver la double authentification depuis le serveur | `src/rental_cockpit/cli.py` |
| Interface | Écrans, textes français/anglais, styles | `src/rental_cockpit/static/` |

Le moteur ne connaît ni le web ni la base de données : il reçoit un registre, applique une opération et renvoie un résultat. C'est ce qui permet de tester chaque règle de calcul seule (`tests/test_indicators.py`, `tests/test_ledger.py`).

## Reprise de la base existante

Inventaire demandé par le cahier des charges (REP 01). Chaque élément est classé : **repris**, **adapté**, **retiré** ou **nouveau**.

### Règles et fonctions reprises du projet d'origine

| Élément du projet d'origine | Statut | Dans Rental Cockpit |
|---|---|---|
| Registre des dépenses et des recettes, distinction exploitation / trésorerie / information | Adapté | Catégories configurables avec un *traitement* explicite (exploitation, investissement, financement, impôts, information) |
| Calcul de rentabilité par année d'activité, sans double comptage des versements nets | Adapté | Trois lectures (Activité, Factures, Trésorerie) ; le versement net d'un séjour n'est jamais ajouté aux recettes déjà reconnues |
| Capital d'emprunt hors exploitation, intérêts et assurance séparés | Adapté | Mensualité décomposable en capital, intérêts et assurance ; jamais comptée deux fois |
| Répartition d'un séjour par nuit, fenêtre arrivée → départ | Adapté | Répartition nuit par nuit au centime près (méthode du plus fort reste) |
| Justificatifs PDF : contrôle de structure, refus du contenu actif, empreinte SHA-256, doublons binaires et métier, annulation de la dernière opération | À reprendre | Écran Documents |
| Facture d'un prestataire de ménage : lignes ménage / linge / déplacement, ventilation par séjour égale au TTC, rapprochement des saisies manuelles | Adapté (règles) · à reprendre (écran) | Prestations génériques : n'importe quel prestataire, n'importe quel tarif ; message « 10 € de déplacement restent à affecter » |
| Import CSV Airbnb : en-têtes vérifiés, ordre des dates détecté, lignes de versement ignorées, garde-fous anti-doublon | Repris (L2) | Séjours → Importer : aperçu sans écriture, doublons, contrôles, annulation du dernier import ; version du lecteur enregistrée avec chaque import ; CSV générique ajouté |
| Lecteurs de factures propres à certains fournisseurs du projet d'origine | Retiré | Non publiés (PRE 06) ; un lecteur générique propose des champs « à vérifier » |
| Fonctions propres au logement d'origine : suivi d'énergie et d'équipements, caméras, plan 3D, planification patrimoniale, assistance automatique, pont entre plusieurs installations | Retiré | Hors périmètre public |
| Comptes, sessions, droits, démonstration séparée, explication de chaque indicateur | Nouveau | Voir ci-dessous |

### Du module Home Assistant à l'application autonome

| Élément | Avant (module Home Assistant) | Maintenant (application autonome) | Statut |
|---|---|---|---|
| Moteur métier | `engine/` | `engine/`, identique | **Repris tel quel** |
| Démonstration | Registre séparé | Registre séparé ; le mois précédant le mois d'exemple est une activité fictive ordinaire, les évolutions sont calculées | Adapté |
| Interface | Panneau de la barre latérale de Home Assistant, rendu dans un *shadow DOM* | Page autonome ; feuille de style servie par l'application ; navigation propre (barre latérale, onglets ou barre basse) | Adapté |
| Échanges | Commandes WebSocket de Home Assistant | API JSON `/api/*` sur HTTP | Remplacé |
| Identité | Utilisateurs de Home Assistant | Comptes propres : premier administrateur créé à la première visite, aucun compte par défaut | Remplacé |
| Droits | Administrateur HA = administrateur | Rôle administrateur ou lecteur ; biens accordés et accès PDF dans la table `grants` | Adapté |
| Stockage | Fichier JSON dans la configuration HA | Base SQLite unique, transaction par modification | Remplacé |
| Installation | HACS et assistant d'intégration | Image Docker publiée (`ghcr.io`, x86-64 et ARM64) avec Docker Compose, ou `pip install` et `uvicorn` | Remplacé |
| Lien avec Home Assistant | Le module était dans Home Assistant | Facultatif : Home Assistant lit un résumé avec une clé en lecture seule ; il peut aussi afficher l'interface dans un tableau de bord *Page web* | Nouveau |
| Langue | Celle de l'utilisateur HA | Choix dans l'application (mémorisé dans le navigateur), sinon langue du navigateur | Adapté |
| Fuseau horaire | Celui de Home Assistant | Celui du processus (`TZ`), jamais imposé | Adapté |

La double navigation (barre latérale de Home Assistant + celle de Rental Cockpit) disparaît avec l'application autonome.

### Lien facultatif avec Home Assistant

Home Assistant n'est plus nécessaire, mais il reste un bon endroit pour **afficher** quelques chiffres et **déclencher** des automatisations (chauffer la veille d'une arrivée). Le lien est volontairement limité :

- une seule route, `GET /api/v1/summary`, en lecture seule ; aucune route d'écriture n'accepte une clé ;
- une clé appartient à un compte et lit exactement ce que ce compte peut lire (mêmes biens, données réelles) ;
- la clé est affichée une seule fois, conservée sous forme d'empreinte SHA-256, révocable ;
- côté Home Assistant, rien à installer : l'intégration RESTful incluse suffit (exemples dans [home-assistant.md](home-assistant.md)).

Afficher toute l'interface dans Home Assistant reste possible, à condition d'autoriser explicitement son origine (`RENTAL_COCKPIT_FRAME_ANCESTORS`).

## Effets sur le cahier des charges

| Exigence | Adaptation |
|---|---|
| CAD 01 | « Intégration Home Assistant » devient « application web autonome ». L'application web indépendante n'est plus hors périmètre : c'est le produit. |
| UX 03 | Inchangée dans l'esprit : aucun fichier de configuration à éditer, aucun compte externe, aucun jeton d'un autre serveur, aucun service extérieur. |
| SEC 01 | L'identité vient des comptes de l'application. Chaque requête et chaque téléchargement restent contrôlés côté serveur. |
| SEC 02, SEC 03, SEC 05, SEC 06, SEC 07 | Inchangées. |
| TEC 02 | Une instance = un processus (un seul *worker*), seule autorité financière. |
| TEC 03 | HACS est remplacé par une image Docker publiée (Docker Compose) et par une installation Python documentée. |
| TEC 04 | L'assistant de démarrage est dans l'application : premier compte, puis choix *Utiliser mes données* / *Explorer la démonstration*. |
| TEC 05 | La recette Docker devient la méthode principale ; adresse et port d'écoute sont visibles dans `docker-compose.yml`. |
| TEC 06 | Plateformes à tester : image x86-64 et ARM64 (Raspberry Pi 4). Il n'y a plus de version de Home Assistant à suivre. |
| T01 | Installation neuve par Docker sur x86-64 et ARM64. |
| T07 | S'applique aux comptes de l'application ; des tests d'API vérifient le refus sans session, sans jeton CSRF et pour un bien deviné. |
| SAU 01 | La sauvegarde comprendra comptes et droits, sans la clé de session ; l'inclusion des empreintes de mots de passe reste à décider. |

## Adaptations restantes avant de décliner les autres écrans

| Écran | Côté serveur | Côté interface |
|---|---|---|
| **Séjours** | Fait (L1) : création, modification, annulation avec montant conservé, rétablissement, versements. Fait (L2) : import Airbnb (lecteur repris, export français vérifié uniquement) et CSV générique avec association des colonnes et taux de commission, prévisualisation sans écriture, contrôle avant confirmation, annulation du dernier import | Fait : liste filtrable, fiche séjour, import en trois étapes, imports précédents. À venir : coûts affectés (L4) |
| **Dépenses** | API écritures, paiements, archivage, filtres ; export CSV avec formules neutralisées | Tableau avec statuts explicites (« Paiement à confirmer », « Payée »…), saisie rapide, actions visibles |
| **Prestataires** | API prestataires et tarifs indicatifs ; facture multi-prestations ; rapprochement des saisies existantes | « Répartir une facture » : détail des services, répartition par séjour, contrôle « 150 € affectés sur 150 € » |
| **Documents** | Téléversement HTTP (8 Mio), contrôle PDF avec *pypdf* (ajouté à ce moment-là), empreinte, doublons binaires et métier, téléchargement après contrôle des droits | « Vérifier la facture » : fichier → vérification → enregistrement ; « Cette facture est déjà enregistrée » |
| **Réglages** | Fait : mot de passe, double authentification, clés d'API. À venir : comptes lecteurs, droits par bien et accès PDF, catégories, sauvegarde / vérification / restauration, diagnostic | Écrans correspondants ; langue ; réinitialisation de la démonstration |
| Transverse | Migrations versionnées du format de données, avec copie automatique de la base avant conversion (première : v1 → v2, canal de réservation) ; image `edge` publiée à chaque modification de la branche principale, image `latest` à chaque version étiquetée ; intégration continue | Accessibilité vérifiée (clavier, lecteur d'écran, 360 px) sur chaque écran |

## Points encore ouverts

- Licence du projet.
- Contenu exact des sauvegardes (comptes, empreintes de mots de passe, secrets de double authentification, clés d'API).
