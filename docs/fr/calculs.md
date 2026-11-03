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

## Un séjour, de la saisie à la Synthèse

Un séjour se saisit dans l'écran **Séjours** : bien, arrivée, départ et, si on les connaît, le montant brut payé par le voyageur et la commission de la plateforme. Le **versement net attendu** vaut brut − commission, sauf si un autre montant est saisi (la plateforme a versé autre chose). La taxe de séjour collectée et la caution sont notées à part : **ce ne sont jamais des recettes**.

Exemple (c'est le scénario des tests) : un séjour du 28 septembre au 4 octobre 2026, 600 € bruts, 90 € de commission.

| | Septembre 2026 | Octobre 2026 |
|---|---|---|
| Nuits | 3 | 3 |
| **Activité** — recettes / commission / solde | 300 € / 45 € / 255 € | 300 € / 45 € / 255 € |
| **Factures** — recettes / commission / solde | 600 € / 90 € / 510 € (mois d'arrivée) | 0 € |
| **Trésorerie** — avant le versement | 0 € | 0 € |
| **Trésorerie** — après « versement reçu : 510 € le 5 octobre » | 0 € | 510 € reçus |

La fiche du séjour montre ce découpage, mois par mois, avec la même règle que la Synthèse.

**État du versement** d'un séjour :

| État | Quand |
|---|---|
| Versement attendu | Le séjour n'est pas terminé, rien n'est encore reçu |
| Versement à confirmer | Le séjour est terminé et aucun versement n'est enregistré (il apparaît dans *À vérifier*) |
| Partiellement reçu | Une partie du versement attendu est enregistrée |
| Versement reçu | Le versement attendu est entièrement enregistré |
| Montant à compléter | Le montant brut n'est pas connu : rien ne peut être vérifié |
| Rien à recevoir | Séjour annulé sans montant conservé |

Un versement ne peut pas dépasser ce qui reste attendu : si la plateforme a versé davantage, on corrige d'abord les montants du séjour.

**Annuler un séjour** demande le montant éventuellement conservé (frais d'annulation) et la commission sur ce montant. Le séjour reste visible, sans nuitée ; seul le montant conservé compte, une fois, à la date d'arrivée. Les montants d'avant l'annulation sont gardés : **Rétablir le séjour** les remet. Supprimer un séjour est réservé à une saisie par erreur, sans versement.

## Un séjour importé

Un séjour importé suit exactement les mêmes règles qu'un séjour saisi : l'import ne fait que remplir les mêmes champs.

**Export Airbnb** (« Historique des transactions », en français) :

| Colonne Airbnb | Champ du séjour |
|---|---|
| Code de confirmation | Référence |
| Date de début / Date de fin | Arrivée / départ (le nombre de nuits du fichier doit correspondre) |
| Revenus bruts | Montant brut (à défaut : Montant + Frais de service) |
| Frais de service | Commission |
| Montant | Versement net |
| Taxes reversées par Airbnb | Taxe de séjour collectée (jamais une recette) |
| Date | Date du versement, s'il est déjà passé |

- Les lignes **« Payout »** sont des virements de montants déjà présents sur les lignes de réservation : elles ne sont **jamais comptées une seconde fois**. Les autres types de ligne (ajustements, résolutions…) ne sont pas des réservations : ils sont comptés dans l'aperçu, pas importés.
- Un même code sur plusieurs lignes forme un seul séjour, dont les montants s'additionnent. Si ces lignes ne s'accordent pas sur les dates ou le logement, le séjour est refusé plutôt que deviné.
- L'ordre jour/mois est déduit des dates sans ambiguïté (Airbnb écrit MM/JJ/AAAA) ; un fichier qui mélange les deux est refusé.
- Si brut − frais de service ≠ montant versé, une remarque le signale.

**CSV** : chaque colonne est choisie dans l'aperçu. Montants au format français ou anglais (« 1 234,50 », « 1,234.50 »). Sans colonne de commission, un **taux** peut être indiqué : commission = brut × taux, arrondie au centime le plus proche (demi-centime vers le haut). Exemple : 15 % de 333,33 € = 50,00 € ; 3,5 % de 333,33 € = 11,67 €.

**Versements du fichier** : enregistrés dans la lecture Trésorerie à leur date, une seule fois (même date et même montant déjà enregistrés = ignoré), jamais au-delà du versement attendu, et seulement si leur date est passée.

**Séjour saisi à la main aux mêmes dates** (doublon probable) : le compléter ne remplit que ce qu'il ne savait pas. Si le fichier annonce un autre montant brut ou une autre commission, ceux saisis sont conservés et une remarque le signale ; le versement net du fichier n'est alors pas repris, pour ne pas contredire les montants conservés.

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
