<div align="center">

# Rental Cockpit

### Suivre sa location saisonnière et comprendre chaque chiffre

**Biens · Séjours · Dépenses · Justificatifs · Prestataires · Résultats expliqués**

🇬🇧 [Read in English](README.md)

<img src="docs/images/fr/overview-desktop.png" alt="Synthèse de Rental Cockpit sur ordinateur, avec des données de démonstration fictives" width="100%">

<sub>Les captures montrent la démonstration intégrée : deux biens fictifs, des prestataires « Démo » et des montants inventés.</sub>

**Auto-hébergé · Local d'abord · Bilingue français / anglais · Aucun service externe requis**

</div>

---

> [!IMPORTANT]
> **Préversion 0.1.0, en cours de développement.** L'écran **Synthèse** fonctionne de bout en bout (comptes, démonstration, indicateurs expliqués, création d'un bien). Les écrans Séjours, Dépenses, Prestataires, Documents et Réglages arrivent ensuite, dans le même style. Ce n'est pas encore une version stable : n'y confiez pas votre seule copie de données réelles.

## Pour qui ?

Pour un particulier qui loue un ou plusieurs logements (location saisonnière ou classique) et veut suivre ses recettes et ses dépenses, conserver ses justificatifs et **comprendre** chaque résultat, sans apprendre la comptabilité ni confier ses données à un service en ligne.

Rental Cockpit est une application web autonome que vous installez chez vous (un conteneur Docker ou un simple processus Python). Elle ne dépend d'aucun autre logiciel pour l'installation, l'authentification, le stockage ou l'interface.

## Ce qui fonctionne aujourd'hui

| | |
|---|---|
| **Premier démarrage guidé** | Aucun compte par défaut : la première visite crée le compte administrateur. Ensuite, deux choix explicites : *Utiliser mes données* ou *Explorer la démonstration*. |
| **Démonstration séparée** | Les données fictives vivent dans leur propre registre et ne touchent jamais vos données réelles. Un bandeau permanent la signale. |
| **Trois lectures des chiffres** | *Activité* (ce que la location a produit, séjours répartis nuit par nuit), *Factures* (chaque document à sa date), *Trésorerie* (l'argent réellement reçu ou payé). Elles ne sont jamais mélangées. |
| **« Comment est calculé ce montant ? »** | Chaque indicateur affiche sa formule, la période, les biens inclus, ce qui est exclu et **toutes les lignes utilisées**. |
| **Évolutions calculées** | Les pourcentages comparent la période à la précédente avec les mêmes règles. |
| **À vérifier** | Ce qui empêche un résultat d'être définitif : paiements inconnus, séjours sans montant, versements non reçus, sommes restant à affecter. |
| **Mes biens** | Recettes, dépenses et solde par bien ; création d'un bien en quelques secondes. |
| **Ordinateur, tablette, téléphone** | Barre latérale, onglets en haut ou barre en bas selon la largeur. |

<table>
<tr>
<td width="50%"><img src="docs/images/fr/explain.png" alt="Explication d'un indicateur : formule, période, exclusions et lignes utilisées"></td>
<td width="25%"><img src="docs/images/fr/overview-phone.png" alt="Synthèse sur téléphone"></td>
<td width="25%"><img src="docs/images/fr/first-account.png" alt="Création du premier compte administrateur"></td>
</tr>
</table>

## Règles de calcul en bref

- Les montants sont stockés en **centimes entiers** : aucun arrondi flottant, les totaux se rapprochent au centime.
- Un séjour du 10 au 12 juin compte **deux nuits** : le jour du départ n'est pas une nuit.
- Une valeur inconnue n'est **jamais affichée comme zéro** : le résultat est signalé incomplet.
- Une échéance, la mention « paiement comptant » ou un PDF **ne valent pas paiement**.
- Une facture répartie entre plusieurs séjours reste **une seule dépense**.
- Le *solde avant financement* exclut emprunt, impôts et investissements ; ce n'est **pas un bénéfice fiscal**.

Exemple vérifiable (il est reproduit dans le mois d'exemple de la démonstration) : 1 000 € de recettes − 30 € de commission − 80 € de ménage − 20 € de linge − 10 € de déplacement − 60 € de réparation = **800 €** avant financement ; avec une mensualité de 200 € payée le même mois, la trésorerie après financement est de **600 €**.

Détails : [docs/fr/calculs.md](docs/fr/calculs.md).

## Installation

**Avec Docker Compose** (recommandé) :

```bash
git clone https://github.com/vinzgithub/rental-cockpit.git
cd rental-cockpit
docker compose up -d --build
```

Ouvrez ensuite `http://<adresse-de-la-machine>:8080` et créez le compte administrateur.

**Sans Docker** (Python 3.11 ou plus récent) :

```bash
pip install .
RENTAL_COCKPIT_DATA_DIR=./data uvicorn --factory rental_cockpit.app:create_app --host 127.0.0.1 --port 8080
```

Toutes les options, la mise à jour et la sauvegarde manuelle : [docs/fr/installation.md](docs/fr/installation.md).

## Confidentialité et sécurité

- Les données restent dans un seul dossier (`/data`) : une base SQLite et, plus tard, les PDF privés. Aucune télémétrie, aucun appel sortant.
- Mots de passe hachés (scrypt), session signée `HttpOnly` et `SameSite=Strict`, jeton anti-CSRF sur chaque modification, verrouillage après cinq échecs de connexion, politique de sécurité du contenu stricte (aucun script ni style externe ou en ligne).
- Les droits sont vérifiés sur le serveur à chaque requête : un lecteur ne voit que les biens qui lui sont accordés, et l'accès aux PDF est une permission distincte.
- Gardez l'application sur votre réseau local ou derrière un proxy HTTPS ; ne l'ouvrez pas directement sur Internet.

Voir [SECURITY.md](SECURITY.md) et [docs/fr/securite.md](docs/fr/securite.md).

## Documentation

| Document | Contenu |
|---|---|
| [Installation](docs/fr/installation.md) | Docker, Python, variables, mise à jour, sauvegarde du dossier de données |
| [Guide de démarrage](docs/fr/guide.md) | Les dix premières minutes, avec la démonstration |
| [Règles de calcul](docs/fr/calculs.md) | Les trois lectures, chaque indicateur, glossaire |
| [Architecture et adaptations](docs/fr/architecture-et-adaptations.md) | Ce qui est repris du projet d'origine, ce qui change avec une application autonome |
| [Sécurité](docs/fr/securite.md) | Comptes, droits, données, exposition réseau |
| [Feuille de route](docs/fr/feuille-de-route.md) | Écrans et lots à venir |

## Licence

**À définir.** Aucune licence n'est encore accordée sur ce code ; tant qu'une licence n'est pas publiée dans ce dépôt, les droits d'auteur s'appliquent par défaut.

Les polices incluses (Source Serif 4 et Inter) sont distribuées sous SIL Open Font License 1.1 : voir [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Copyright © 2026 Vincent Fournet
