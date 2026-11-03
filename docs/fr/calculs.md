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

## Trois vues de la Synthèse

La Synthèse s'ouvre sur **Mon argent**. Les deux autres vues sont à un clic. Les règles de calcul sont les mêmes partout : seule la présentation change.

| Vue | Question posée | Ce qu'elle montre | Méthode utilisée |
|---|---|---|---|
| **Mon argent** (par défaut) | Quel argent est entré et sorti, que reste-t-il à recevoir ou à payer ? | Encaissé, Payé, Solde de la période ; Reste à payer et À recevoir à la fin de la période | Par date de paiement |
| **Performance locative** | Qu'a produit la location ? | Recettes des nuitées, Commissions, Résultat locatif ; nuitées, taux d'occupation, revenu moyen par nuit, autres recettes et dépenses ; évolution des douze mois de l'année | Par nuit occupée |
| **Analyse comptable** | Comment rattacher chaque montant à une période ? | Les trois méthodes ci-dessous, au choix, avec le solde avant et après financement | Au choix |

**Encaissé** = versements envoyés par les plateformes + paiements reçus, à leur date. **Payé** = dépenses, mensualités d'emprunt, impôts et équipements payés, à leur date. **Solde de la période** = Encaissé − Payé : c'est le mouvement d'argent de la période, pas un bénéfice.

**Résultat locatif** = Recettes des nuitées + Autres recettes − Commissions − Autres dépenses, avant emprunt et impôts.

### Versement envoyé, versement crédité

Une plateforme envoie un versement, puis la banque le crédite quelques jours plus tard. Rental Cockpit compte un versement **le jour où la plateforme l'envoie**, sous le libellé « Versements envoyés par les plateformes ». Quand l'export donne la date limite d'arrivée sur le compte (Airbnb : « Arrivée au plus tard le »), elle est gardée avec le versement. Elle est affichée sous chaque ligne de « Comment est calculé ce montant ? ». Exemple : un versement Airbnb envoyé le 31 octobre et attendu au plus tard le 6 novembre compte en octobre, avec la mention « arrivée sur le compte au plus tard le 6 nov. ».

### Les trois méthodes de rattachement (Analyse comptable)

| Méthode | Question posée | Séjour | Dépense | Paiement |
|---|---|---|---|---|
| **Par nuit occupée** | Qu'a produit la location pendant la période ? | Recettes et commission réparties nuit par nuit | À sa date, ou jour par jour sur sa période couverte (une assurance annuelle par exemple) | Ignoré |
| **Par date de séjour ou de facture** | Quels séjours commencent et quelles factures sont datées dans la période ? | À la date d'arrivée | À la date de la facture | Ignoré |
| **Par date de paiement** | Quel argent a réellement bougé ? | Versements envoyés ou sommes reçues, à leur date | Paiements effectués, à leur date | Compté |

La méthode utilisée est toujours affichée. Les chiffres de deux méthodes ne sont jamais additionnés.

Cas particuliers :

- **Séjour annulé** : aucune nuitée ; un éventuel montant conservé compte une fois, à la date d'arrivée.
- **Ajustement ou remboursement** : compté à sa propre date, sans effacer le montant initial.
- **Commission de plateforme** : dépense d'exploitation par nuit occupée et par date de séjour. Par date de paiement, elle n'apparaît pas comme un paiement, car elle est déjà déduite du versement reçu.

## Un séjour, de la saisie à la Synthèse

Un séjour se saisit dans l'écran **Séjours** : bien, arrivée, départ et, si on les connaît, le montant brut payé par le voyageur et la commission de la plateforme. Le **versement net attendu** vaut brut − commission, sauf si un autre montant est saisi (la plateforme a versé autre chose). La taxe de séjour collectée et la caution sont notées à part : **ce ne sont jamais des recettes**.

Exemple (c'est le scénario des tests) : un séjour du 28 septembre au 4 octobre 2026, 600 € bruts, 90 € de commission.

| | Septembre 2026 | Octobre 2026 |
|---|---|---|
| Nuits | 3 | 3 |
| **Par nuit occupée** — recettes / commission / solde | 300 € / 45 € / 255 € | 300 € / 45 € / 255 € |
| **Par date de séjour** — recettes / commission / solde | 600 € / 90 € / 510 € (mois d'arrivée) | 0 € |
| **Par date de paiement** (Mon argent) — avant le versement | 0 € | 0 € |
| **Par date de paiement** (Mon argent) — après « versement reçu : 510 € le 5 octobre » | 0 € | 510 € encaissés |

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

**Une réservation annulée mais indemnisée** (le voyageur annule tard, la plateforme verse quand même un dédommagement) est un séjour annulé dont le montant conservé est ce dédommagement. L'argent compte, les nuits non. Exemple (c'est le scénario des tests) : une réservation de cinq nuits à partir du 18 mai, annulée et indemnisée 220 € bruts (8,20 € de commission, 211,80 € versés), puis une autre réservation pour la nuit du 22 mai. En mai : **1 nuitée** (celle du 22), recettes 220 + 125 = 345 € par nuit occupée, 211,80 + 120,50 € encaissés. Aucun chevauchement n'est compté.

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

- Les lignes **« Payout »** sont des virements de montants déjà présents sur les lignes qui les suivent (même date) : elles ne sont **jamais comptées une seconde fois**. Chacune est en revanche **vérifiée au centime** contre les lignes qu'elle paie, et donne la date d'envoi et la date d'arrivée sur le compte (« Arrivée au plus tard le »).
- Les autres lignes ne sont jamais ignorées en silence (voir ci-dessous).
- Un même code sur plusieurs lignes forme un seul séjour, dont les montants s'additionnent. Si ces lignes ne s'accordent pas sur les dates ou le logement, le séjour est refusé plutôt que deviné.
- L'ordre jour/mois est déduit des dates sans ambiguïté (Airbnb écrit MM/JJ/AAAA) ; un fichier qui mélange les deux est refusé.
- Si brut − frais de service ≠ montant versé, une remarque le signale.

**CSV** : chaque colonne est choisie dans l'aperçu. Montants au format français ou anglais (« 1 234,50 », « 1,234.50 »). Sans colonne de commission, un **taux** peut être indiqué : commission = brut × taux, arrondie au centime le plus proche (demi-centime vers le haut). Exemple : 15 % de 333,33 € = 50,00 € ; 3,5 % de 333,33 € = 11,67 €.

**Versements du fichier** : enregistrés à leur date d'envoi, une seule fois (même date et même montant déjà enregistrés = ignoré), jamais au-delà du versement attendu, et seulement si leur date est passée.

### Les opérations Airbnb qui ne sont pas des réservations

| Type de ligne Airbnb | Devient | Catégorie | Réglée |
|---|---|---|---|
| Versement de résolution (dont remboursement des dommages AirCover) | Recette hors séjour, 0 nuit | Indemnisation (dommages, résolution) | À la date du versement qui la paie |
| Crédit divers (prime, geste de la plateforme) | Recette hors séjour | Prime ou crédit de la plateforme | À la date du versement |
| Régularisation de la résolution, montant négatif | Dépense : un remboursement à un voyageur, retenu par Airbnb | Remboursement à un voyageur | Par retenue sur le versement, à sa date |
| Type inconnu | Montré avec son montant, **rien n'est écrit sans votre choix** | Autres recettes ou Autre dépense | À la date du versement |

Le **versement** et l'**opération** qu'il paie sont une seule somme : seule l'opération est enregistrée, avec un paiement à la date du versement. Chaque opération est reconnue à son type, sa réservation, sa date et son montant : un réimport n'ajoute rien, et annuler l'import la retire.

Exemple (c'est le scénario des tests, données fictives) : en octobre, six versements Airbnb pour **1 355,00 €**. Cinq paient des réservations (1 260,00 €), un paie un remboursement des dommages AirCover (95,00 €). L'import crée cinq séjours et une recette « Indemnisation Airbnb » de 95,00 €, sans séjour ni nuit. *Encaissé* d'octobre : 1 355,00 €.

**Bilan des versements.** Avant tout import, l'aperçu additionne les versements du fichier, par nature (séjours, indemnisations, crédits, retenues, opérations à vérifier) et par mois d'envoi. Il dit quelles sommes versées **ne seraient pas enregistrées** (ligne écartée, en erreur ou sans bien) : tant qu'elles le sont, les résultats de la période ne sont pas complets.

**Chevauchement.** Quand deux réservations du fichier se chevauchent, les **deux** lignes le signalent. Chacune propose « Annulé, montant encaissé conservé », pour celle qu'Airbnb a annulée en la dédommageant (voir « Une réservation annulée mais indemnisée »).

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

**Les trois méthodes.** *Par nuit occupée*, l'écriture compte à sa date, ou jour par jour sur sa **période couverte** si elle en a une (une assurance annuelle de 240 € du 1er novembre 2026 au 1er novembre 2027 compte 19,80 € en novembre : 30 jours de 0,66 €, le reste des centimes étant réparti au plus fort reste). *Par date de facture*, elle compte à sa date. *Par date de paiement* (Mon argent), seuls ses **paiements** comptent, à leur date et pour leur montant.

**Règlement.** L'état vient toujours des paiements enregistrés :

| État | Quand |
|---|---|
| Payée (Reçue) | Les paiements couvrent tout le montant |
| Partiellement payée (reçue) | Une partie est réglée |
| À payer (À recevoir) | Rien n'est réglé et l'écriture est connue comme due |
| Paiement à confirmer | Rien n'est réglé et on ne sait pas si elle l'est : listée dans *À vérifier* |

Un paiement ne dépasse jamais le reste dû, et le montant d'une écriture ne peut pas descendre sous ce qui est déjà réglé.

Exemple (c'est le scénario des tests) : réparation de 300 € datée du 10 octobre 2026, à payer, puis paiement de 100 € le 12 octobre. En octobre : par nuit occupée et par date de facture, 300 € de dépenses ; par date de paiement (*Payé* de Mon argent), 100 € ; il reste 200 € à payer.

**Mensualités.** Une série mensuelle crée une écriture par mois, à la même date (le 31 devient le dernier jour d'un mois plus court). Chaque échéance se règle à part. Une échéance datée après aujourd'hui est *prévue* : elle n'est pas encore dans « À payer » de l'écran Dépenses. Si capital, intérêts et assurance sont saisis, leur somme doit égaler l'échéance ; la Synthèse les détaille sous **Remboursements d'emprunt**. Exemple : 500 € = 350 € de capital + 120 € d'intérêts + 30 € d'assurance ; en octobre, solde avant financement inchangé, solde après financement diminué de 500 €.

**Archiver** retire une écriture de tous les totaux sans l'effacer ; ses paiements sont conservés. **Supprimer** n'est possible que pour une écriture sans paiement ni justificatif.

## Une facture de prestataire

**Prestations.** Une facture peut être détaillée en lignes : ménage, linge, déplacement, autre, remise, taxe, ajustement. Une ligne a un montant, ou une quantité et un prix unitaire (montant = quantité × prix, qui doit tomber juste au centime : rien n'est arrondi en douce). Une remise est négative ; un ajustement peut l'être et exige une justification. **La somme des lignes doit égaler le montant de la facture**, sinon rien n'est enregistré. Les tarifs d'un prestataire pré-remplissent un prix unitaire, ils ne modifient jamais un montant. La facture reste **une seule dépense** : c'est elle qui compte, quelle que soit la méthode.

**Répartition entre les séjours.** Chaque prestation (ménage, linge, déplacement, autre) peut être affectée, en un ou plusieurs morceaux, à des séjours du même bien (seuls les séjours non annulés sont proposés) ; une remise, une taxe ou un ajustement suivent la facture. La somme affectée à une prestation ne dépasse jamais son montant. Le séjour proposé est celui dont le départ tombe le jour de l'intervention, à défaut celui en cours ce jour-là. La répartition **n'ajoute aucune dépense** : elle dit quels séjours une dépense a servis. Une prestation déjà répartie ne peut être retirée de la facture qu'après avoir modifié sa répartition. Une facture répartie en partie est listée dans *À vérifier* avec le montant restant.

**Rapprochement.** Une facture peut remplacer des dépenses saisies à la main pour les mêmes prestations. Sont proposées les dépenses du même bien, de la catégorie de la facture ou de ses prestations, datées entre la première intervention (à défaut, un mois avant le mois de la facture) et la date de la facture, sans prestataire ou du même prestataire. Sont toujours refusées : une dépense d'un autre bien, une recette, une dépense archivée, détaillée, déjà remplacée ou qui en remplace d'autres. Le total remplacé ne dépasse pas le montant de la facture. Les saisies remplacées sortent de tous les totaux ; leurs paiements sont **reportés sur la facture** (à leur date d'origine : *Payé* ne change donc pas) et ne peuvent pas dépasser son montant. Le rapprochement s'annule saisie par saisie : elle revient avec ses paiements. Une facture qui remplace des saisies ne peut être ni supprimée ni archivée avant d'avoir annulé ces rapprochements, et son montant ne peut pas descendre sous le total remplacé.

**Coûts et marge d'un séjour.** Les coûts affectés à un séjour sont ses parts de factures réparties, plus les dépenses rattachées au séjour entier (sans répartition). **Marge après coûts = versement net attendu − coûts affectés** ; elle n'est pas calculée pour un séjour annulé ou dont le montant est inconnu.

Exemple (c'est le scénario des tests) : séjour A du 28 septembre au 4 octobre 2026 (600 €, commission 90 €, versement attendu 510 €) et séjour B du 10 au 13 octobre (300 €, commission 45 €, versement attendu 255 €). Deux ménages saisis à la main et payés : 45 € le 4 octobre, 35 € le 13 octobre. Le prestataire envoie ensuite sa facture du 20 octobre : **150 €** = 4 h de ménage à 25 € le 4 octobre + 4 lots de linge à 10 € le 13 octobre + 10 € de déplacement le 13 octobre.

| Étape | Dépenses d'octobre hors commissions (par nuit, par date de facture) | Payé en octobre | Reste à payer |
|---|---|---|---|
| Facture saisie | 45 + 35 + 150 = 230 € | 80 € payés | 150 € |
| Répartition : ménage → A, linge et déplacement → B | 230 € (inchangé) | 80 € | 150 € |
| Rapprochement des deux ménages | **150 €** : comptée une fois | 80 € (paiements reportés, mêmes dates) | 150 − 80 = **70 €** |
| Rétablir le ménage du 4 octobre | 45 + 150 = 195 € | 80 € | 150 − 35 = 115 € |

Après répartition : séjour A, coûts 100 €, marge 510 − 100 = **410 €** ; séjour B, coûts 50 €, marge 255 − 50 = **205 €**.

## Un justificatif

Un justificatif (PDF) **ne compte dans aucun total** : c'est la dépense qui compte. Joindre un PDF à une dépense, le détacher ou le supprimer ne crée, ne modifie ni ne supprime aucune dépense, avec aucune méthode. Une dépense qui a un justificatif ne peut pas être supprimée, seulement archivée (ou détachée de son justificatif d'abord).

**Doublons.** Avant d'enregistrer une dépense depuis une facture, sur tous les biens :

| Cas | Règle | Effet |
|---|---|---|
| Même fichier | Même empreinte SHA-256, quel que soit le nom du fichier | Certain : refusé, lien vers la dépense existante |
| Même référence | Même prestataire et même numéro de facture (« F-018 », « f 018 » et « F018 » sont le même numéro) | Certain : refusé, lien vers la dépense existante |
| Semblable | Même prestataire, même date et même montant, l'une des deux factures sans numéro | Probable : enregistré seulement après « J'ai vérifié : c'est une autre facture » |
| Montant seul | Même montant, rien d'autre en commun | Jamais un doublon |

Une facture d'un autre numéro, même au même montant et à la même date, n'est pas un doublon.

**À compléter.** Un justificatif est listé dans *À vérifier* tant qu'il n'est joint à aucune dépense ou qu'il lui manque le prestataire ou le montant.

## Les indicateurs

| Indicateur | Formule | Exclut |
|---|---|---|
| **Encaissé** (Mon argent) | Versements envoyés par les plateformes + paiements reçus, à leur date | Séjours pas encore versés (À recevoir), commissions déjà retenues |
| **Payé** (Mon argent) | Dépenses, mensualités, impôts et équipements payés, à leur date | Commissions retenues par la plateforme, dépenses non payées (Reste à payer) |
| **Solde de la période** (Mon argent) | Encaissé − Payé | Ce n'est pas un bénéfice fiscal |
| **Recettes des nuitées** (Performance) | Montant brut des séjours réparti nuit par nuit + ajustements | Commissions, taxes de séjour, recettes hors séjours |
| **Commissions** (Performance) | Commissions des plateformes, réparties comme les séjours | Autres frais |
| **Autres recettes** / **Autres dépenses** (Performance) | Recettes hors séjours (indemnisations, primes…) / dépenses d'exploitation hors commissions | Emprunt, impôts, équipements |
| **Résultat locatif** (Performance) | Recettes des nuitées + Autres recettes − Commissions − Autres dépenses | Financement, impôts, investissements |
| **Recettes** (Analyse comptable) | Recettes des séjours + ajustements + autres recettes | Taxes collectées pour un tiers, dépôts de garantie, versements nets déjà comptés |
| **Dépenses** | Commissions + dépenses d'exploitation | Emprunt, impôts et taxes, équipements, écritures « information seulement » |
| **Solde avant financement** | Recettes − Dépenses | Financement, impôts, investissements. Ce n'est pas un bénéfice fiscal |
| **Investissements** | Équipements et dépenses ponctuelles | Jamais transformés en charge récurrente |
| **Impôts et taxes** | Catégorie Impôts et taxes | Taxes de séjour collectées pour un tiers |
| **Financement** | Mensualités d'emprunt, décomposées en capital, intérêts et assurance quand c'est connu | Jamais comptée deux fois |
| **Solde après financement** (par nuit, par date de séjour) | Solde avant financement − Financement | |
| **Trésorerie après financement** (par date de paiement) | Sommes reçues − tous les paiements effectués | |
| **Nuitées** | Nuits des séjours non annulés dans la période | Jour de départ, séjours annulés |
| **Taux d'occupation** | Nuitées ÷ nuits disponibles | Périodes d'indisponibilité, jours avant le début d'activité |
| **Revenu moyen par nuit** (par nuit occupée) | Recettes des séjours ÷ nuitées | Ajustements, autres recettes |
| **À payer** | Dépenses datées avant la fin de la période − paiements enregistrés | Écritures archivées |
| **À recevoir** | Versement attendu des séjours + recettes hors séjours − sommes reçues | Séjours au montant inconnu (listés à vérifier), séjours provisoires |

**Évolutions.** Le pourcentage affiché sous un indicateur compare la période avec la précédente (mois précédent, année précédente, ou même durée juste avant), calculée avec la même méthode et les mêmes règles.

**Évolution mensuelle** (Performance locative) : les douze mois de l'année de la période, chacun calculé par nuit occupée avec les mêmes règles que les indicateurs. Un mois choisi devient la période affichée. Sans valeur de référence, aucun pourcentage n'est affiché.

## Exemple vérifiable

Pour un mois : 1 000 € de recettes d'activité, 30 € de commission, 80 € de ménage, 20 € de linge, 10 € de déplacement et 60 € de réparation.

- Solde avant financement : 1 000 − 30 − 80 − 20 − 10 − 60 = **800 €**.
- Si tout est payé dans le mois et qu'une mensualité d'emprunt de 200 € est décaissée : *Mon argent* affiche Encaissé **970 €** (versement net, commission déduite), Payé **370 €** (170 € de dépenses + 200 € d'emprunt), Solde de la période **600 €**.
- Si les paiements ont lieu le mois suivant, *Mon argent* change ; la *Performance locative* ne change pas.

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
| **Versement envoyé** | Versement d'une plateforme, compté le jour où elle l'envoie ; il arrive sur le compte quelques jours plus tard. |
| **Indemnisation** | Somme versée par une plateforme pour des dommages ou une résolution (AirCover) : une recette hors séjour, sans nuitée. |
