# Règles de calcul

Rental Cockpit est un outil de **suivi de gestion**. Ses résultats ne sont ni une déclaration fiscale, ni un bilan certifié, ni un conseil juridique.

## Principes

- **Montants exacts.** Tout est stocké en centimes entiers. Quand un montant est réparti (par nuit, par jour), la répartition se fait une seule fois pour tout le séjour ou toute la période couverte, par la méthode du plus fort reste : les parts de deux mois consécutifs redonnent toujours le total, au centime.
- **Euros uniquement** dans cette version. Une autre devise est refusée plutôt que convertie.
- **Périodes inclusives au début, exclusives à la fin.** Un séjour du 10 au 12 juin représente deux nuits ; le 12 est le jour du départ.
- **Inconnu n'est pas zéro.** Un séjour sans montant n'est pas compté comme 0 € : l'indicateur est marqué *incomplet* et le séjour apparaît dans *À vérifier*.
- **Rien n'est supposé payé.** Une échéance, la mention « paiement comptant » ou un PDF ne valent pas paiement. Seul un paiement enregistré (date et montant) compte en trésorerie.
- **Une facture reste une dépense.** La répartir entre plusieurs séjours explique à quoi elle a servi ; cela ne crée aucune charge supplémentaire.
- **Les corrections gardent leur historique** : valeur précédente, auteur et date.

## Les trois lectures

| Lecture | Question posée | Séjour | Dépense | Paiement |
|---|---|---|---|---|
| **Activité** | Qu'a produit la location pendant la période ? | Recettes et commission réparties nuit par nuit | À sa date, ou jour par jour sur sa période couverte (une assurance annuelle par exemple) | Ignoré |
| **Factures** | Quels documents sont datés dans la période ? | À la date d'arrivée | À la date de la facture | Ignoré |
| **Trésorerie** | Quel argent a réellement bougé ? | Sommes reçues, à leur date | Paiements effectués, à leur date | Compté |

La lecture choisie est toujours affichée. Les chiffres de deux lectures ne sont jamais additionnés.

Cas particuliers :

- **Séjour annulé** : aucune nuitée ; un éventuel montant conservé compte une fois, à la date d'arrivée.
- **Ajustement ou remboursement** : compté à sa propre date, sans effacer le montant initial.
- **Commission de plateforme** : dépense d'exploitation en Activité et en Factures. En Trésorerie elle n'apparaît pas comme un paiement, car elle est déjà déduite du versement reçu.

## Les indicateurs

| Indicateur | Formule | Exclut |
|---|---|---|
| **Recettes** (*Sommes reçues* en Trésorerie) | Recettes des séjours + ajustements + autres recettes | Taxes collectées pour un tiers, dépôts de garantie, versements nets déjà comptés |
| **Dépenses** | Commissions + dépenses d'exploitation | Emprunt, impôts et taxes, équipements, écritures « information seulement » |
| **Solde avant financement** | Recettes − Dépenses | Financement, impôts, investissements. Ce n'est pas un bénéfice fiscal |
| **Investissements** | Équipements et dépenses ponctuelles | Jamais transformés en charge récurrente |
| **Impôts et taxes** | Catégorie Impôts et taxes | Taxes de séjour collectées pour un tiers |
| **Financement** | Mensualités d'emprunt, décomposées en capital, intérêts et assurance quand c'est connu | Jamais comptée deux fois |
| **Solde après financement** (Activité, Factures) | Solde avant financement − Financement | |
| **Trésorerie après financement** (Trésorerie) | Sommes reçues − tous les paiements effectués | |
| **Nuitées** | Nuits des séjours non annulés dans la période | Jour de départ, séjours annulés |
| **Taux d'occupation** | Nuitées ÷ nuits disponibles | Périodes d'indisponibilité, jours avant le début d'activité |
| **Revenu moyen par nuit** (Activité) | Recettes des séjours ÷ nuitées | Ajustements, autres recettes |
| **À payer** | Dépenses − paiements enregistrés | |
| **À recevoir** | Versement attendu des séjours − sommes reçues | Séjours au montant inconnu (listés à vérifier) |

**Évolutions.** Le pourcentage affiché sous un indicateur compare la période avec la précédente (mois précédent, année précédente, ou même durée juste avant), calculée avec la même lecture et les mêmes règles. Sans valeur de référence, aucun pourcentage n'est affiché.

## Exemple vérifiable

Pour un mois : 1 000 € de recettes d'activité, 30 € de commission, 80 € de ménage, 20 € de linge, 10 € de déplacement et 60 € de réparation.

- Solde avant financement : 1 000 − 30 − 80 − 20 − 10 − 60 = **800 €**.
- Si tout est payé dans le mois et qu'une mensualité d'emprunt de 200 € est décaissée : sommes reçues 970 € (versement net, commission déduite), paiements 170 € + 200 € ; trésorerie après financement **600 €**.
- Si les paiements ont lieu le mois suivant, la Trésorerie change ; la lecture Activité ne change pas.

Le mois d'exemple de la démonstration reproduit exactement ces chiffres ; le test `test_documented_example_T03` les vérifie.

Exemple de prestations : une facture de 150 € comprend 100 € de ménage, 40 € de linge et 10 € de déplacement ; 90 € sont affectés au séjour A et 60 € au séjour B. Le tableau annuel conserve **une** dépense de 150 €, pas 300 €.

## Glossaire

| Terme | Sens dans Rental Cockpit |
|---|---|
| **Recette** | Montant gagné par la location (hébergement, frais de ménage facturés au voyageur, autres recettes). |
| **Commission** | Frais retenus par une plateforme sur une réservation. |
| **Versement** | Argent effectivement reçu de la plateforme ou du voyageur. |
| **Paiement** | Argent effectivement payé, avec une date et un montant. |
| **Facture** | Document daté qui justifie une dépense. |
| **Dépense** | Écriture qui compte dans les résultats, avec ou sans facture jointe. |
| **Justificatif** | Fichier PDF joint à une dépense ; le joindre ne crée ni ne modifie aucune dépense. |
| **Ventilation** | Répartition d'une dépense entre séjours ou prestations, sans nouvelle charge. |
| **Occupation** | Part des nuits disponibles réellement louées. |
| **Trésorerie** | Argent reçu moins argent payé, à la date des mouvements. |
