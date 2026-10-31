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

La carte **À vérifier** liste ce qui empêche un résultat d'être définitif. Dans la démonstration : des dépenses de ménage du mois précédent dont le paiement n'est pas encore confirmé.

## 7. Passer à vos données

Le bandeau propose **Utiliser mes données**. Vous arrivez sur un espace vide avec les étapes de démarrage : créez votre premier bien (seul le nom est obligatoire). La démonstration reste disponible et séparée.

## 8. Protéger votre compte

Dans **Réglages → Double authentification → Activer** :

1. confirmez votre mot de passe ;
2. scannez le code QR avec une application d'authentification (Aegis, Google Authenticator, 2FAS, Bitwarden…), ou saisissez la clé à la main, puis tapez le code à six chiffres affiché ;
3. rangez les **dix codes de secours** (copier, télécharger) : chacun ouvre une seule connexion si vous perdez votre téléphone. La fenêtre ne se ferme qu'une fois la case « J'ai rangé ces codes en lieu sûr » cochée.

À la connexion suivante, le code est demandé après le mot de passe. Les autres navigateurs ouverts sur ce compte sont déconnectés.

![Activation de la double authentification](../images/fr/mfa-setup.png)

## 9. Home Assistant (facultatif)

Dans **Réglages → Home Assistant et API → Créer une clé**, Rental Cockpit affiche une fois la ligne à coller dans `secrets.yaml`. L'adresse à indiquer dans Home Assistant est affichée juste au-dessus. La suite (capteurs, carte, automatisations) : [home-assistant.md](home-assistant.md).

![Réglages : compte, double authentification activée, clé pour Home Assistant](../images/fr/settings-desktop.png)

## Sur téléphone

La même Synthèse s'affiche en une colonne, le solde en premier, avec une barre de navigation en bas. Sur écran tactile, les commandes visent 44 × 44 pixels.

<img src="../images/fr/overview-phone.png" alt="Synthèse sur téléphone" width="320"> <img src="../images/fr/settings-phone.png" alt="Réglages sur téléphone" width="320">
