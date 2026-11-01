# Sécurité et protection des données

## Comptes et sessions

- **Aucun compte par défaut.** La première visite crée l'administrateur ; la page de création est ensuite refusée.
- **Mots de passe** : 10 caractères minimum, hachés avec scrypt (N = 2¹⁴, r = 8, p = 1). Un identifiant inconnu prend autant de temps qu'un mauvais mot de passe.
- **Limitation des essais** : après cinq échecs depuis une même adresse, les tentatives sont refusées pendant cinq minutes. Le message ne dit pas si l'identifiant existe.
- **Session** : cookie signé, `HttpOnly`, `SameSite=Strict`, `Secure` quand `RENTAL_COCKPIT_COOKIE_SECURE=true`. La clé de signature est créée au premier démarrage dans le dossier de données (droits 0600). Changer de mot de passe, activer ou désactiver la double authentification déconnecte les autres navigateurs du compte.
- **Double authentification** (facultative, recommandée) : dans **Réglages**, après confirmation du mot de passe, un code QR généré par le serveur s'ajoute à une application d'authentification ; un premier code valide l'active. Codes TOTP (RFC 6238 : SHA-1, 6 chiffres, 30 s) avec une période de tolérance ; chaque code n'est accepté qu'une fois. Dix codes de secours à usage unique sont affichés une seule fois et conservés uniquement sous forme d'empreintes SHA-256. La désactiver ou renouveler les codes demande le mot de passe et un code. À la connexion, le mot de passe correct n'ouvre rien : le code est demandé dans les cinq minutes. Le secret TOTP doit rester lisible pour vérifier les codes : il est stocké dans la base, protégez donc le dossier `/data` et ses sauvegardes.
- **Téléphone perdu** et plus de codes de secours : seule une personne qui a accès au serveur peut désactiver la double authentification (`python -m rental_cockpit.cli disable-mfa <identifiant>`, voir [installation.md](installation.md)).

## Droits

| Profil | Peut |
|---|---|
| Administrateur | Configurer, saisir, importer, corriger, sauvegarder et restaurer |
| Lecteur | Consulter uniquement les biens accordés ; ouvrir les PDF seulement si c'est explicitement accordé |
| Non connecté | Rien, sauf la page de connexion |

Les droits sont vérifiés **sur le serveur** à chaque requête. Masquer un bouton n'est jamais une protection. Les totaux ne portent que sur les biens autorisés : un bien caché n'apparaît ni dans une liste ni dans une somme. Un identifiant de bien deviné est refusé.

La démonstration (données fictives) est visible par tout compte connecté et modifiable par les administrateurs seulement.

## Requêtes

- **Jeton anti-CSRF** obligatoire sur toute modification.
- **Opérations idempotentes** : chaque action porte un identifiant unique ; un double clic ou un renvoi réseau n'enregistre qu'une fois.
- **Tout ou rien** : une modification est appliquée à une copie, enregistrée dans une transaction SQLite, puis publiée. En cas d'échec, l'état précédent est conservé et le message le dit.
- **Pas d'écrasement silencieux** : chaque séjour porte un numéro de révision ; une modification faite sur une version dépassée (quelqu'un d'autre a enregistré entre-temps) est refusée et le message invite à recharger.
- **Textes** : tout ce qui est saisi ou importé est traité comme du texte, jamais comme du HTML.

## Imports de fichiers

- Réservés aux **administrateurs** ; jeton anti-CSRF obligatoire, comme toute modification.
- **5 Mio et 20 000 lignes au plus.** Un classeur (.xlsx, .ods), un PDF ou tout fichier binaire est refusé avec un message clair. Encodages acceptés : UTF-8, ou Windows-1252 annoncé dans l'aperçu.
- **Le fichier n'est pas conservé** : il est lu en mémoire à l'aperçu puis à la confirmation ; seule son empreinte SHA-256 est gardée, pour signaler un fichier déjà importé.
- **Rien n'est écrit pendant l'aperçu.** À la confirmation, l'import est recalculé sur les données du moment : s'il ne correspond plus à l'aperçu affiché (quelqu'un a modifié les séjours entre-temps), il est refusé et le nouvel aperçu s'affiche.
- **Noms des voyageurs non conservés** par défaut : seuls la référence, les dates et les montants sont enregistrés, sauf choix explicite.
- **Un import, une ligne de journal** (auteur, date, nombre de séjours et de versements), pour ne pas chasser les entrées plus anciennes du journal.
- **Annulation** du dernier import seulement, et seulement si aucun de ses séjours n'a été modifié depuis : rien de ce qui a été saisi après n'est effacé.

## Exports CSV

- Les exports des dépenses et des séjours ne contiennent que les biens que le compte peut voir, avec les filtres affichés à l'écran. Un lecteur peut exporter ses biens ; il ne peut rien modifier.
- **Formules neutralisées** : un texte qui commencerait par `=`, `+`, `-`, `@`, une tabulation ou un retour chariot est écrit précédé d'une apostrophe. Un libellé saisi ou importé ne peut donc jamais devenir une formule dans le tableur d'un comptable. Les montants sont produits par l'application et écrits comme de simples nombres.
- Le fichier n'est ni conservé sur le serveur ni mis en cache (`Cache-Control: no-store`).

## Prestataires

- Les prestataires sont communs à tous les biens. Un lecteur les voit avec les totaux (factures, reste à payer, à répartir) calculés **sur ses seuls biens** : les factures d'un bien qui ne lui est pas ouvert n'apparaissent dans aucun total.
- Créer, modifier, archiver un prestataire, détailler, répartir ou rapprocher une facture : administrateurs seulement, avec le jeton CSRF, le numéro de révision et l'identifiant d'opération habituels.
- Un rapprochement est entièrement vérifié avant toute écriture (même bien, montants, paiements) : en cas de refus, rien n'a changé.

## Justificatifs PDF

- **Contrôle du fichier** : structure PDF réelle (pas l'extension), 8 Mio et 200 pages au plus, ouverture sans mot de passe (un PDF qui limite seulement l'impression est accepté), refus de tout script, action de lancement, envoi de formulaire ou fichier intégré. Le PDF est seulement analysé, jamais exécuté ; une analyse qui dure plus de 20 secondes est abandonnée, et les limites de décompression de la bibliothèque pypdf s'appliquent.
- **Aperçu sans écriture** : le fichier vérifié attend en mémoire, pour le seul compte qui l'a envoyé, 10 minutes au plus (12 fichiers et 64 Mio en tout). Rien n'est écrit sur le disque avant la confirmation.
- **Stockage privé** : l'original est écrit une seule fois sous son empreinte SHA-256, dans `documents/` (`demo-documents/` pour la démonstration) du dossier de données, dossier 0700 et fichiers 0600, écriture exclusive et synchronisée, liens symboliques refusés. Ce dossier n'est jamais servi comme fichiers statiques.
- **Consultation** : uniquement par l'API, après contrôle de la session et des droits. Le fichier est relu et comparé à son empreinte avant chaque envoi : un fichier modifié ou absent n'est jamais servi, l'erreur le dit. En-têtes : `Content-Type: application/pdf`, `X-Content-Type-Options: nosniff`, `Cache-Control: no-store, private`.
- **Droits** : l'accès aux PDF d'un bien est une autorisation distincte de l'accès au bien. Un lecteur sans cette autorisation voit qu'une dépense a un justificatif, jamais son contenu ni son nom. Envoyer, joindre, détacher, décrire ou supprimer : administrateurs seulement, avec le jeton CSRF.
- **Cohérence** : la dépense, le justificatif et la ligne de journal sont enregistrés dans une même transaction ; si elle échoue, le fichier nouvellement écrit est retiré. Un fichier laissé par une interruption est supprimé au démarrage suivant. Le journal garde l'action et le début de l'empreinte, jamais le contenu du PDF.

## Navigateur

- Politique de sécurité du contenu stricte : `default-src 'self'`, aucun script ni style en ligne ou externe, aucun affichage dans un cadre par défaut (`frame-ancestors 'none'`).
- `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Permissions-Policy` restrictive, réponses de l'API non mises en cache.
- Polices et icônes servies par l'application : aucune requête vers un autre site.

## Clés d'API (Home Assistant)

- **Lecture seule** : une clé lit le résumé de `/api/v1/summary` avec les droits de son compte (mêmes biens, données réelles uniquement) et ne peut rien modifier.
- Affichée une seule fois, conservée uniquement sous forme d'empreinte SHA-256, révocable à tout moment ; la date de dernière lecture est visible.
- Dix clés actives au maximum par compte. Voir [home-assistant.md](home-assistant.md).
- L'application refuse d'être affichée dans un cadre, sauf pour les origines listées dans `RENTAL_COCKPIT_FRAME_ANCESTORS`.

## Données

- Stockage **local uniquement** : aucune télémétrie, aucun compte éditeur, aucun appel sortant.
- Toutes les données sont dans le dossier `/data` : protégez-le et ses sauvegardes, qui contiennent des informations privées. Cela vaut aussi pour `backups/`, où une copie complète de la base est écrite avant chaque migration de format.
- Les données des voyageurs sont limitées au strict utile (un libellé et un nombre de voyageurs). À l'import, leur nom n'est repris que si vous le demandez.
- Le journal des opérations note l'auteur, la date, l'action, l'élément concerné et le résultat ; il ne contient ni secret ni contenu de PDF. Ce n'est pas un archivage légal certifié.

## Exposition réseau

- Utilisez Rental Cockpit sur votre réseau local ou derrière un VPN.
- Si un accès extérieur est indispensable : proxy inverse en HTTPS, `RENTAL_COCKPIT_COOKIE_SECURE=true`, `FORWARDED_ALLOW_IPS` réglé sur l'adresse du proxy, et double authentification activée. Le proxy doit accepter des requêtes de 8 Mio pour l'import (le fichier voyage encodé avec ses choix).
- L'installation de base n'ouvre aucun port sur votre box.

## Signaler une vulnérabilité

Voir [SECURITY.md](../../SECURITY.md) : signalement privé, jamais dans une issue publique.
