# Guide de démarrage — les dix premières minutes

Ce parcours utilise la **démonstration** : rien de ce que vous faites ici ne touche vos données réelles.

## 1. Créer le compte administrateur

À la première ouverture, Rental Cockpit demande un identifiant et un mot de passe (10 caractères minimum). Ce compte peut tout configurer. Aucun compte n'existe par défaut.

![Création du premier compte](../images/fr/first-account.png)

## 2. Choisir : vos données ou la démonstration

L'écran d'accueil présente les cinq étapes de la prise en main et deux choix :

- **Utiliser mes données** : vous commencez vide et créez votre premier bien ;
- **Explorer la démonstration** : deux biens fictifs, un an d'activité inventée.

Chaque étape peut être reprise plus tard. Choisissez la démonstration.

![Écran d'accueil](../images/fr/welcome.png)

## 3. Lire la Synthèse

Un bandeau rappelle en permanence que les données sont fictives. La période proposée est le **mois d'exemple** de la démonstration, qui reproduit l'exemple de la documentation :

- Recettes **1 000 €**, Dépenses **200 €**, Solde avant financement **800 €** ;
- Appartement A : 600 € / 120 € / 480 € ; Studio B : 400 € / 80 € / 320 €.

Sous chaque montant, le pourcentage compare avec le mois précédent, qui est une activité fictive ordinaire.

![Synthèse](../images/fr/overview-desktop.png)

## 4. Changer de lecture

En haut, **Activité / Factures / Trésorerie** change la règle de calcul, pas les données :

- en **Trésorerie**, les recettes deviennent les *sommes reçues* (970 € : la commission est déjà déduite) ;
- le solde avant financement reste 800 € quand tout est payé dans le mois.

Une phrase sous les boutons rappelle toujours ce que mesure la lecture choisie.

## 5. Comprendre un montant

Cliquez sur **Comment est calculé ce montant ?** sous le solde. La fenêtre montre :

- l'équation Recettes − Dépenses = Solde ;
- la formule, la période, la lecture, les biens inclus et ce qui est exclu ;
- **toutes les lignes utilisées**, avec la règle appliquée à chacune (« Réparti nuit par nuit sur le séjour », « Compté à sa date »…) et le total.

![Explication du solde](../images/fr/explain.png)

## 6. Ce qui reste à vérifier

La carte **À vérifier** liste ce qui empêche un résultat d'être définitif. Dans la démonstration : des dépenses de ménage du mois précédent dont le paiement n'est pas encore confirmé. Un clic ouvre ces dépenses dans l'écran **Dépenses**, vue *Paiement à confirmer*.

## 7. Passer à vos données

Le bandeau propose **Utiliser mes données**. Vous arrivez sur un espace vide avec les étapes de démarrage : créez votre premier bien (seul le nom est obligatoire). La démonstration reste disponible et séparée : la bascule **Mes données / Démo** est en bas de la barre latérale (dans la fenêtre du compte sur téléphone, et dans Réglages).

## 8. Saisir un séjour

**Séjours → Ajouter un séjour** : choisissez le bien, l'arrivée et le départ. Sous les dates, Rental Cockpit indique déjà comment les nuits se répartissent (« 3 nuits en septembre · 3 nuits en octobre »). Renseignez, si vous les connaissez, le montant brut payé par le voyageur et la commission de la plateforme : le versement net attendu est calculé. Un montant inconnu reste vide : il n'est jamais compté comme 0.

La fiche du séjour montre ensuite :

- les montants, ce qui est déjà reçu et ce qui reste à recevoir ;
- **ce que le séjour compte dans la Synthèse**, mois par mois ;
- les versements reçus, avec **Enregistrer un versement** quand l'argent arrive ;
- **Modifier**, **Annuler le séjour** (avec le montant éventuellement conservé) et, pour une saisie par erreur, **Supprimer**.

Dans la Synthèse, « 1 versement à confirmer » mène directement à la liste des séjours à vérifier.

![Liste des séjours](../images/fr/stays-desktop.png)

![Fiche d'un séjour](../images/fr/stay-detail.png)

## 9. Importer un fichier

Plutôt que de tout saisir, **Séjours → Importer** (ou **Ajouter → Un fichier de réservations**) :

1. **Fichier** : choisissez *Airbnb* pour l'export « Historique des transactions » en français, tel qu'Airbnb le fournit, ou *Autre fichier CSV* (Booking.com, Abritel, tableur…), puis choisissez ou déposez le fichier.
2. **Vérification** : rien n'est encore enregistré. Pour un CSV, vérifiez la colonne choisie pour chaque information grâce à l'exemple affiché ; indiquez la plateforme et, si le fichier n'a pas de commission, son taux. Rattachez chaque logement du fichier à l'un de vos biens. Chaque ligne dit ce qui se passera :
   - *Nouveau* : le séjour sera créé ;
   - *Mis à jour* : un séjour déjà importé change (le détail « avant → après » est affiché) ;
   - *Doublon probable* : un séjour saisi à la main a les mêmes dates — par défaut, il est **complété** avec ce qu'il ne savait pas (référence, commission…), ce que vous saisissez est conservé ; vous pouvez aussi créer un autre séjour ou ignorer la ligne ;
   - *Déjà à jour*, *Sans bien*, *Erreur* : rien ne sera écrit, et la raison est donnée.

   Les remarques signalent ce qui mérite un coup d'œil : chevauchement, dates indisponibles, arrivée avant le début d'activité, versement déjà enregistré ou supérieur à l'attendu.
3. **Résultat** : le nombre de séjours créés, mis à jour, complétés et de versements enregistrés. **Annuler cet import** remet tout comme avant, tant qu'aucun de ces séjours n'a été modifié ; c'est aussi possible plus tard depuis **Imports précédents**.

Réimporter le même fichier ne crée rien en double : tout est *Déjà à jour*. Les choix (colonnes, biens, taux) sont mémorisés pour le fichier suivant. Les noms des voyageurs ne sont repris que si vous cochez l'option.

![Aperçu d'un import Airbnb](../images/fr/import-preview.png)

## 10. Saisir une dépense et la régler

**Dépenses → Ajouter une dépense** (ou **Ajouter → Une dépense**) : choisissez le bien, la catégorie — son traitement s'affiche dessous : exploitation, investissement, financement, impôts —, le libellé, le montant TTC et la date de la facture. Indiquez ensuite le **règlement** :

- *Déjà payée* : un paiement du montant total est enregistré à la date indiquée ;
- *À payer* : le montant compte dans « Reste à payer » ;
- *Je ne sais pas encore* : la dépense apparaît dans **Paiement à confirmer**. Rien n'est supposé payé.

Quand l'argent part, ouvrez la dépense puis **Enregistrer un paiement** : un paiement partiel est possible, jamais au-delà du reste dû. La lecture Trésorerie compte chaque paiement à sa date.

Pour un **emprunt**, choisissez la catégorie *Remboursement d'emprunt*, saisissez la décomposition capital / intérêts / assurance (vérifiée en direct) et cochez **Répéter chaque mois** : une écriture par mois est créée, chacune réglée à part. Les échéances dont la date n'est pas encore venue sont *Prévues*, regroupées sous « À venir » et hors de « À payer ». Dans la Synthèse, elles comptent en **Remboursements d'emprunt**, hors solde d'exploitation.

Pour une **assurance annuelle** ou un abonnement payé d'avance, cochez **Couvre une période** : la lecture Activité la répartit jour par jour.

Une recette hors séjour (remboursement, location ponctuelle) s'ajoute avec **Ajouter une recette** et suit les mêmes règles, en « À recevoir ».

Une écriture faite par erreur se **supprime** tant qu'elle n'a pas de paiement ; sinon, **Archivez-la** : elle sort de tous les totaux et reste consultable. Les catégories se créent, se renomment et s'archivent dans **Réglages → Catégories**. **Exporter** télécharge la liste affichée au format CSV, pour un tableur ou votre comptable.

![Liste des dépenses](../images/fr/expenses-desktop.png)

![Fiche d'une dépense réglée en partie](../images/fr/expense-detail.png)

## 11. Prestataires et factures détaillées

**Prestataires → Ajouter un prestataire** : nom, activité, catégories habituelles (proposées d'office pour ses factures), **tarifs indicatifs** (ménage à l'heure, lot de linge…), contact et note. Un tarif ne fait que pré-remplir le prix unitaire d'une prestation : il n'est jamais appliqué à un montant de facture.

La fiche du prestataire montre ses factures de l'année, ce qui reste à payer, ce qui reste à répartir, ses tarifs et ses factures récentes ; **Les retrouver dans Dépenses** ouvre la liste complète.

**Nouvelle facture** (depuis la fiche) ouvre le formulaire de dépense avec le prestataire et sa catégorie déjà choisis. Cochez **Détailler les prestations de la facture** et ajoutez une ligne par prestation : nature (ménage, linge, déplacement, autre, remise, taxe, ajustement), libellé, quantité, unité, prix unitaire ou montant, **date d'intervention**. Le total des lignes est vérifié en direct : il doit égaler le montant de la facture, à défaut d'un **ajustement** dont la justification est obligatoire. La facture reste **une seule dépense**.

Sur la fiche de la facture, **Répartir entre les séjours** affecte chaque prestation à un ou plusieurs séjours du même bien. Le séjour dont le départ tombe le jour de l'intervention est proposé d'office (à défaut, le séjour en cours ce jour-là). La répartition est une **analyse** : elle n'ajoute aucune dépense. Une facture répartie en partie est signalée dans *À vérifier*, avec le montant restant.

Si vous aviez déjà saisi à la main un ménage après chaque départ, **Rapprocher des saisies faites à la main** propose les dépenses du même bien, de même nature et de la période de la facture. Les saisies cochées sortent des totaux, leurs paiements sont reportés sur la facture : rien n'est compté deux fois. **Rétablir la saisie** annule un rapprochement.

La fiche d'un séjour affiche enfin ses **coûts affectés** et sa **marge après coûts** (versement net attendu − coûts).

![Prestataires](../images/fr/suppliers-desktop.png)

![Facture détaillée en prestations, tarif pré-rempli](../images/fr/invoice-form.png)

![Répartition des prestations entre les séjours](../images/fr/invoice-split.png)

![Facture répartie et rapprochée des saisies faites à la main](../images/fr/invoice-reconciled.png)

![Coûts affectés et marge d'un séjour](../images/fr/stay-costs.png)

## 12. Justificatifs PDF

Deux entrées, selon ce que vous avez sous la main :

- **Créer une dépense depuis une facture** (écran **Justificatifs**, bouton de l'écran **Dépenses**, ou **Ajouter → Une facture PDF**) : choisissez ou déposez le PDF. Le serveur le vérifie, puis lit son texte et propose la date, le montant TTC, le numéro de facture et le prestataire s'il fait partie de vos prestataires. Chaque valeur proposée porte « À vérifier » ; ce qui n'a pas été trouvé reste vide, et un PDF scanné sans texte se saisit à la main. Choisissez le bien, la catégorie et le règlement, puis **Créer la dépense** : la dépense et son justificatif sont enregistrés ensemble.
- **Ajouter un justificatif à cette dépense** (fiche d'une dépense) : le PDF est joint sans rien changer à la dépense. Il reprend son prestataire, son numéro, sa date et son montant.

**Vérifications.** Le fichier doit être un vrai PDF (pas seulement porter l'extension), de 8 Mio et 200 pages au plus. Il doit s'ouvrir sans mot de passe et ne contenir ni script ni fichier intégré. Rien n'est enregistré avant votre confirmation, et la vérification expire après 10 minutes.

**Doublons.** Le même fichier, même renommé, ou une facture du même prestataire avec le même numéro est un doublon certain : la création est refusée et **Ouvrir la dépense** mène à l'existante. Même prestataire, même date et même montant sans numéro pour les distinguer : doublon probable, vous confirmez après vérification. Un montant seul ne suffit jamais. Un même PDF peut justifier plusieurs dépenses du bien : il est alors joint sans copie.

L'écran **Justificatifs** liste tous les PDF (vue **À compléter** : non joints à une dépense, ou sans prestataire ou montant). La fiche d'un justificatif permet de l'**ouvrir**, de le **télécharger** (octets identiques à l'original), de le **joindre** à une autre dépense du bien, de le **détacher** (la dépense ne change pas, le justificatif reste reconnu) ou, s'il n'est joint à rien, de le **supprimer**.

![Justificatifs](../images/fr/documents-desktop.png)

![Créer une dépense depuis une facture : champs proposés « À vérifier »](../images/fr/invoice-import.png)

![Le même fichier envoyé une seconde fois](../images/fr/invoice-duplicate.png)

![Justificatif joint à une dépense](../images/fr/expense-documents.png)

![Fiche d'un justificatif](../images/fr/document-page.png)

## 13. Protéger votre compte

Dans **Réglages → Double authentification → Activer** :

1. confirmez votre mot de passe ;
2. scannez le code QR avec une application d'authentification (Aegis, Google Authenticator, 2FAS, Bitwarden…), ou saisissez la clé à la main, puis tapez le code à six chiffres affiché ;
3. rangez les **dix codes de secours** (copier, télécharger) : chacun ouvre une seule connexion si vous perdez votre téléphone. La fenêtre ne se ferme qu'une fois la case « J'ai rangé ces codes en lieu sûr » cochée.

À la connexion suivante, le code est demandé après le mot de passe. Les autres navigateurs ouverts sur ce compte sont déconnectés.

![Activation de la double authentification](../images/fr/mfa-setup.png)

## 14. Home Assistant (facultatif)

Dans **Réglages → Home Assistant et API → Créer une clé**, Rental Cockpit affiche une fois la ligne à coller dans `secrets.yaml`. L'adresse à indiquer dans Home Assistant est affichée juste au-dessus. La suite (capteurs, carte, automatisations) : [home-assistant.md](home-assistant.md).

![Réglages : compte, double authentification activée, clé pour Home Assistant](../images/fr/settings-desktop.png)

## Sur téléphone

La même Synthèse s'affiche en une colonne, le solde en premier, avec une barre de navigation en bas. Sur écran tactile, les commandes visent 44 × 44 pixels.

<img src="../images/fr/overview-phone.png" alt="Synthèse sur téléphone" width="260"> <img src="../images/fr/stays-phone.png" alt="Séjours sur téléphone" width="260"> <img src="../images/fr/import-phone.png" alt="Import sur téléphone" width="260"> <img src="../images/fr/expenses-phone.png" alt="Dépenses sur téléphone" width="260"> <img src="../images/fr/suppliers-phone.png" alt="Fiche d'un prestataire sur téléphone" width="260"> <img src="../images/fr/documents-phone.png" alt="Justificatifs sur téléphone" width="260"> <img src="../images/fr/settings-phone.png" alt="Réglages sur téléphone" width="260">
