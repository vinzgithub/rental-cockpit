# Lien avec Home Assistant (facultatif)

Rental Cockpit fonctionne seul. Si vous utilisez Home Assistant, vous pouvez **en plus** afficher ses chiffres dans vos tableaux de bord et déclencher des automatisations (chauffage avant une arrivée, rappel des paiements à confirmer…).

Le lien passe par une **API en lecture seule**, protégée par une clé. Home Assistant la lit avec l'[intégration RESTful](https://www.home-assistant.io/integrations/rest/), déjà incluse : rien à installer.

- Une clé lit **ce que son compte peut lire** (les mêmes biens, les données réelles uniquement) et ne peut **rien modifier**.
- Elle est affichée une seule fois, puis conservée uniquement sous forme d'empreinte.
- Elle se révoque à tout moment dans **Réglages → Home Assistant et API**.

## 1. Créer une clé

Dans Rental Cockpit : **Réglages → Home Assistant et API → Créer une clé**. Copiez la ligne proposée : elle ne sera plus jamais affichée.

## 2. La ranger dans `secrets.yaml`

```yaml
rental_cockpit_authorization: "Bearer rc_COLLEZ-VOTRE-CLE-ICI"
```

## 3. Ajouter les capteurs dans `configuration.yaml`

Remplacez l'adresse par celle de votre Rental Cockpit (elle est affichée dans **Réglages**).

```yaml
rest:
  - resource: http://rental-cockpit.lan:8080/api/v1/summary?lang=fr
    headers:
      Authorization: !secret rental_cockpit_authorization
    scan_interval: 900
    sensor:
      - name: Location recettes du mois
        unique_id: rental_cockpit_month_revenue
        value_template: "{{ value_json.month.revenue }}"
        unit_of_measurement: "EUR"
        device_class: monetary
      - name: Location solde du mois
        unique_id: rental_cockpit_month_balance
        value_template: "{{ value_json.month.balance_before_financing }}"
        unit_of_measurement: "EUR"
        device_class: monetary
        json_attributes_path: "$.month"
        json_attributes: [revenue, expenses, balance_after_financing, nights, complete]
      - name: Location occupation du mois
        unique_id: rental_cockpit_month_occupancy
        value_template: "{{ ((value_json.month.occupancy or 0) * 100) | round(0) }}"
        unit_of_measurement: "%"
      - name: Location à payer
        unique_id: rental_cockpit_to_pay
        value_template: "{{ value_json.to_pay }}"
        unit_of_measurement: "EUR"
        device_class: monetary
      - name: Location à vérifier
        unique_id: rental_cockpit_to_check
        value_template: "{{ value_json.to_check }}"
        json_attributes: [to_check_items]
      - name: Location prochaine arrivée
        unique_id: rental_cockpit_next_arrival
        value_template: "{{ value_json.next_stay.start if value_json.next_stay else none }}"
        device_class: date
        json_attributes: [next_stay]
    binary_sensor:
      - name: Location occupée ce soir
        unique_id: rental_cockpit_occupied_tonight
        value_template: "{{ value_json.occupied_tonight > 0 }}"
        device_class: occupancy
      - name: Location arrivée demain
        unique_id: rental_cockpit_arrival_tomorrow
        value_template: "{{ value_json.properties | selectattr('arrival_tomorrow') | list | count > 0 }}"
```

Redémarrez Home Assistant (ou rechargez les entités RESTful). Les entités `sensor.location_…` et `binary_sensor.location_…` apparaissent.

**Un bien en particulier** : ajoutez `&property_id=<identifiant>` à l'adresse, ou filtrez la liste `properties` dans un modèle, par exemple :

```yaml
value_template: "{{ value_json.properties | selectattr('name', 'eq', 'Studio du port') | map(attribute='occupied_tonight') | first }}"
```

## 4. Automatisations

Préchauffer la veille d'une arrivée :

```yaml
automation:
  - alias: "Location : préchauffer la veille d'une arrivée"
    triggers:
      - trigger: time
        at: "16:00:00"
    conditions:
      - condition: state
        entity_id: binary_sensor.location_arrivee_demain
        state: "on"
    actions:
      - action: climate.set_temperature
        target:
          entity_id: climate.sejour          # votre thermostat
        data:
          temperature: 20
```

Être prévenu quand des données sont à vérifier :

```yaml
  - alias: "Location : données à vérifier"
    triggers:
      - trigger: numeric_state
        entity_id: sensor.location_a_verifier
        above: 0
    actions:
      - action: notify.mobile_app_mon_telephone   # votre service de notification
        data:
          title: "Rental Cockpit"
          message: >
            {{ states('sensor.location_a_verifier') }} élément(s) à vérifier :
            {{ state_attr('sensor.location_a_verifier', 'to_check_items') | map(attribute='title') | join(', ') }}
```

## 5. Une carte

```yaml
type: entities
title: Location
entities:
  - sensor.location_recettes_du_mois
  - sensor.location_solde_du_mois
  - sensor.location_occupation_du_mois
  - binary_sensor.location_occupee_ce_soir
  - sensor.location_prochaine_arrivee
  - sensor.location_a_payer
  - sensor.location_a_verifier
```

## Afficher toute l'interface dans Home Assistant (facultatif)

Vous pouvez ajouter Rental Cockpit comme tableau de bord **Page web** dans Home Assistant. Pour que le navigateur l'accepte :

- servez les deux en HTTPS, sous le même domaine (par exemple `ha.exemple.fr` et `location.exemple.fr`), pour que le cookie de connexion fonctionne dans le cadre ;
- autorisez Home Assistant à afficher Rental Cockpit : `RENTAL_COCKPIT_FRAME_ANCESTORS="https://ha.exemple.fr"` et `RENTAL_COCKPIT_COOKIE_SECURE=true`.

Sans cette variable, Rental Cockpit refuse d'être affiché dans un cadre.

## Référence de l'API

`GET /api/v1/summary` — en-tête `Authorization: Bearer <clé>`. Paramètres facultatifs : `property_id` (un seul bien), `lang` (`fr` ou `en`, pour les intitulés).

Montants en euros avec deux décimales ; un montant inconnu vaut `null`, jamais 0. Les chiffres du mois et de l'année suivent la lecture **Activité**.

| Champ | Contenu |
|---|---|
| `today`, `generated_at` | Date du jour (fuseau du serveur) et heure de génération |
| `month`, `year` | `revenue`, `expenses`, `balance_before_financing`, `balance_after_financing`, `nights`, `occupancy` (0 à 1), `complete`, `start`, `end` |
| `cash_month` | `received` (sommes reçues), `balance_after_financing` — lecture Trésorerie du mois |
| `to_pay`, `to_receive` | Dépenses non payées, versements attendus non reçus |
| `to_check`, `to_check_items` | Nombre et liste des données à vérifier (`kind`, `count`, `title`) |
| `occupied_tonight`, `arrivals_today`, `departures_today` | Nombre de biens concernés |
| `next_stay` | Prochain séjour : `property`, `start`, `end`, `nights`, `guests`, `status`, `in_progress` — ou `null` |
| `properties[]` | Par bien : `id`, `name`, `occupied_tonight`, `arrival_today`, `departure_today`, `arrival_tomorrow`, `guests_tonight`, `current_stay_end`, `next_arrival`, `next_arrival_guests`, `month` (`revenue`, `expenses`, `balance_before_financing`) |

Réponses : `401` sans clé valide, `403` pour un bien non accessible au compte de la clé.
