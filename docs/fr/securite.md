# Sécurité et protection des données

## Comptes et sessions

- **Aucun compte par défaut.** La première visite crée l'administrateur ; la page de création est ensuite refusée.
- **Mots de passe** : 10 caractères minimum, hachés avec scrypt (N = 2¹⁴, r = 8, p = 1). Un identifiant inconnu prend autant de temps qu'un mauvais mot de passe.
- **Limitation des essais** : après cinq échecs depuis une même adresse, les tentatives sont refusées pendant cinq minutes. Le message ne dit pas si l'identifiant existe.
- **Session** : cookie signé, `HttpOnly`, `SameSite=Strict`, `Secure` quand `RENTAL_COCKPIT_COOKIE_SECURE=true`. La clé de signature est créée au premier démarrage dans le dossier de données (droits 0600). Chaque compte porte un numéro de version de session : le changement de mot de passe (écran Réglages) l'incrémentera pour déconnecter les autres navigateurs.
- **Double authentification** : codes TOTP (RFC 6238), chaque code n'est accepté qu'une fois. La connexion la gère déjà ; son activation arrive avec l'écran Réglages.

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
- **Textes** : tout ce qui est saisi ou importé est traité comme du texte, jamais comme du HTML.

## Navigateur

- Politique de sécurité du contenu stricte : `default-src 'self'`, aucun script ni style en ligne ou externe, aucun cadre (`frame-ancestors 'none'`).
- `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Permissions-Policy` restrictive, réponses de l'API non mises en cache.
- Polices et icônes servies par l'application : aucune requête vers un autre site.

## Données

- Stockage **local uniquement** : aucune télémétrie, aucun compte éditeur, aucun appel sortant.
- Toutes les données sont dans le dossier `/data` : protégez-le et ses sauvegardes, qui contiennent des informations privées.
- Les données des voyageurs sont limitées au strict utile (un libellé et un nombre de voyageurs).
- Le journal des opérations note l'auteur, la date, l'action, l'élément concerné et le résultat ; il ne contient ni secret ni contenu de PDF. Ce n'est pas un archivage légal certifié.

## Exposition réseau

- Utilisez Rental Cockpit sur votre réseau local ou derrière un VPN.
- Si un accès extérieur est indispensable : proxy inverse en HTTPS, `RENTAL_COCKPIT_COOKIE_SECURE=true`, `FORWARDED_ALLOW_IPS` réglé sur l'adresse du proxy, et double authentification activée dès qu'elle sera disponible.
- L'installation de base n'ouvre aucun port sur votre box.

## Signaler une vulnérabilité

Voir [SECURITY.md](../../SECURITY.md) : signalement privé, jamais dans une issue publique.
