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

## Une dépense ou une recette hors séjour

Une écriture a un montant TTC, une date (celle de la facture) et une **catégorie**. Le **traitement** de la catégorie dit où elle compte :

| Traitement | Compté dans | Exemples |
|---|---|---|
| Exploitation | Dépenses (ou Recettes) et solde avant financement | Ménage, linge, réparation, énergie, assurance du bien, abonnement, frais de plateforme |
| Investissement | Investissements, à part | Équipement, travaux d'amélioration |
| Financement | Remboursements d'emprunt, hors solde d'exploitation | Mensualité : capital + intérêts + assurance emprunteur |
| Impôts et taxes | Impôts et taxes, à part | Taxe foncière |
| Information seulement | Aucun total | Dépense gardée pour mémoire |

**Les trois lectures.** En *Activité*, l'écriture compte à sa date, ou jour par jour sur sa **période couverte** si elle en a une (une assurance annuelle de 240 € du 1er novembre 2026 au 1er novembre 2027 compte 19,80 € en novembre : 30 jours de 0,66 €, le reste des centimes étant réparti au plus fort reste). En *Factures*, elle compte à sa date. En *Trésorerie*, seuls ses **paiements** comptent, à leur date et pour leur montant.

**Règlement.** L'état vient toujours des paiements enregistrés :

| État | Quand |
|---|---|
| Payée (Reçue) | Les paiements couvrent tout le montant |
| Partiellement payée (reçue) | Une partie est réglée |
| À payer (À recevoir) | Rien n'est réglé et l'écriture est connue comme due |
| Paiement à confirmer | Rien n'est réglé et on ne sait pas si elle l'est : listée dans *À vérifier* |

Un paiement ne dépasse jamais le reste dû, et le montant d'une écriture ne peut pas descendre sous ce qui est déjà réglé.

Exemple (c'est le scénario des tests) : réparation de 300 € datée du 10 octobre 2026, à payer, puis paiement de 100 € le 12 octobre. En octobre : *Activité* et *Factures* comptent 300 € de dépenses ; *Trésorerie* compte 100 € ; il reste 200 € à payer.

**Mensualités.** Une série mensuelle crée une écriture par mois, à la même date (le 31 devient le dernier jour d'un mois plus court). Chaque échéance se règle à part. Une échéance datée après aujourd'hui est *prévue* : elle n'est pas encore dans « À payer » de l'écran Dépenses. Si capital, intérêts et assurance sont saisis, leur somme doit égaler l'échéance ; la Synthèse les détaille sous **Remboursements d'emprunt**. Exemple : 500 € = 350 € de capital + 120 € d'intérêts + 30 € d'assurance ; en octobre, solde avant financement inchangé, solde après financement diminué de 500 €.

**Archiver** retire une écriture de tous les totaux sans l'effacer ; ses paiements sont conservés. **Supprimer** n'est possible que pour une écriture sans paiement ni justificatif.

## Une facture de prestataire

**Prestations.** Une facture peut être détaillée en lignes : ménage, linge, déplacement, autre, remise, taxe, ajustement. Une ligne a un montant, ou une quantité et un prix unitaire (montant = quantité × prix, qui doit tomber juste au centime : rien n'est arrondi en douce). Une remise est négative ; un ajustement peut l'être et exige une justification. **La somme des lignes doit égaler le montant de la facture**, sinon rien n'est enregistré. Les tarifs d'un prestataire pré-remplissent un prix unitaire, ils ne modifient jamais un montant. La facture reste **une seule dépense** : c'est elle qui compte dans les trois lectures.

**Répartition entre les séjours.** Chaque prestation (ménage, linge, déplacement, autre) peut être affectée, en un ou plusieurs morceaux, à des séjours du même bien (seuls les séjours non annulés sont proposés) ; une remise, une taxe ou un ajustement suivent la facture. La somme affectée à une prestation ne dépasse jamais son montant. Le séjour proposé est celui dont le départ tombe le jour de l'intervention, à défaut celui en cours ce jour-là. La répartition **n'ajoute aucune dépense** : elle dit quels séjours une dépense a servis. Une prestation déjà répartie ne peut être retirée de la facture qu'après avoir modifié sa répartition. Une facture répartie en partie est listée dans *À vérifier* avec le montant restant.

**Rapprochement.** Une facture peut remplacer des dépenses saisies à la main pour les mêmes prestations. Sont proposées les dépenses du même bien, de la catégorie de la facture ou de ses prestations, datées entre la première intervention (à défaut, un mois avant le mois de la facture) et la date de la facture, sans prestataire ou du même prestataire. Sont toujours refusées : une dépense d'un autre bien, une recette, une dépense archivée, détaillée, déjà remplacée ou qui en remplace d'autres. Le total remplacé ne dépasse pas le montant de la facture. Les saisies remplacées sortent de tous les totaux ; leurs paiements sont **reportés sur la facture** (à leur date d'origine, la Trésorerie ne change donc pas) et ne peuvent pas dépasser son montant. Le rapprochement s'annule saisie par saisie : elle revient avec ses paiements. Une facture qui remplace des saisies ne peut être ni supprimée ni archivée avant d'avoir annulé ces rapprochements, et son montant ne peut pas descendre sous le total remplacé.

**Coûts et marge d'un séjour.** Les coûts affectés à un séjour sont ses parts de factures réparties, plus les dépenses rattachées au séjour entier (sans répartition). **Marge après coûts = versement net attendu − coûts affectés** ; elle n'est pas calculée pour un séjour annulé ou dont le montant est inconnu.

Exemple (c'est le scénario des tests) : séjour A du 28 septembre au 4 octobre 2026 (600 €, commission 90 €, versement attendu 510 €) et séjour B du 10 au 13 octobre (300 €, commission 45 €, versement attendu 255 €). Deux ménages saisis à la main et payés : 45 € le 4 octobre, 35 € le 13 octobre. Le prestataire envoie ensuite sa facture du 20 octobre : **150 €** = 4 h de ménage à 25 € le 4 octobre + 4 lots de linge à 10 € le 13 octobre + 10 € de déplacement le 13 octobre.

| Étape | Dépenses d'octobre hors commissions (Activité, Factures) | Trésorerie d'octobre | Reste à payer |
|---|---|---|---|
| Facture saisie | 45 + 35 + 150 = 230 € | 80 € payés | 150 € |
| Répartition : ménage → A, linge et déplacement → B | 230 € (inchangé) | 80 € | 150 € |
| Rapprochement des deux ménages | **150 €** : comptée une fois | 80 € (paiements reportés, mêmes dates) | 150 − 80 = **70 €** |
| Rétablir le ménage du 4 octobre | 45 + 150 = 195 € | 80 € | 150 − 35 = 115 € |

Après répartition : séjour A, coûts 100 €, marge 510 − 100 = **410 €** ; séjour B, coûts 50 €, marge 255 − 50 = **205 €**.

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
| **À payer** | Dépenses datées avant la fin de la période − paiements enregistrés | Écritures archivées |
| **À recevoir** | Versement attendu des séjours + recettes hors séjours − sommes reçues | Séjours au montant inconnu (listés à vérifier), séjours provisoires |

**Évolutions.** Le pourcentage affiché sous un indicateur compare la période avec la précédente (mois précédent, année précédente, ou même durée juste avant), calculée avec la même lecture et les mêmes règles. Sans valeur de référence, aucun pourcentage n'est affiché.

## Exemple vérifiable

Pour un mois : 1 000 € de recettes d'activité, 30 € de commission, 80 € de ménage, 20 € de linge, 10 € de déplacement et 60 € de réparation.

- Solde avant financement : 1 000 − 30 − 80 − 20 − 10 − 60 = **800 €**.
- Si tout est payé dans le mois et qu'une mensualité d'emprunt de 200 € est décaissée : sommes reçues 970 € (versement net, commission déduite), paiements 170 € + 200 € ; trésorerie après financement **600 €**.
- Si les paiements ont lieu le mois suivant, la Trésorerie change ; la lecture Activité ne change pas.

Le mois d'exemple de la démonstration reproduit exactement ces chiffres ; le test `test_documented_example_T03` les vérifie.

Exemple de prestations : une facture de 150 € comprend 100 € de ménage, 40 € de linge et 10 € de déplacement ; 90 € sont affectés au séjour A et 60 € au séjour B. Le tableau annuel conserve **une** dépense de 150 €, pas 300 €. La démonstration contient cette facture, déjà répartie (voir « Une facture de prestataire »).

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
