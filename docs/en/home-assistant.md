# Link with Home Assistant (optional)

Rental Cockpit works on its own. If you use Home Assistant, you can **also** show its figures on your dashboards and trigger automations (heating before an arrival, a reminder about payments to confirm…).

The link is a **read-only API** protected by a key. Home Assistant reads it with the [RESTful integration](https://www.home-assistant.io/integrations/rest/), already included: nothing to install.

- A key reads **what its account can read** (the same properties, real data only) and can **change nothing**.
- It is shown once, then kept only as a fingerprint.
- It can be revoked at any time in **Settings → Home Assistant and API**.

## 1. Create a key

In Rental Cockpit: **Settings → Home Assistant and API → Create a key**. Copy the line shown: it will never be shown again.

## 2. Store it in `secrets.yaml`

```yaml
rental_cockpit_authorization: "Bearer rc_PASTE-YOUR-KEY-HERE"
```

## 3. Add the sensors to `configuration.yaml`

Replace the address with your Rental Cockpit's (it is shown in **Settings**).

```yaml
rest:
  - resource: http://rental-cockpit.lan:8080/api/v1/summary?lang=en
    headers:
      Authorization: !secret rental_cockpit_authorization
    scan_interval: 900
    sensor:
      - name: Rental month revenue
        unique_id: rental_cockpit_month_revenue
        value_template: "{{ value_json.month.revenue }}"
        unit_of_measurement: "EUR"
        device_class: monetary
      - name: Rental month balance
        unique_id: rental_cockpit_month_balance
        value_template: "{{ value_json.month.balance_before_financing }}"
        unit_of_measurement: "EUR"
        device_class: monetary
        json_attributes_path: "$.month"
        json_attributes: [revenue, expenses, balance_after_financing, nights, complete]
      - name: Rental month occupancy
        unique_id: rental_cockpit_month_occupancy
        value_template: "{{ ((value_json.month.occupancy or 0) * 100) | round(0) }}"
        unit_of_measurement: "%"
      - name: Rental to pay
        unique_id: rental_cockpit_to_pay
        value_template: "{{ value_json.to_pay }}"
        unit_of_measurement: "EUR"
        device_class: monetary
      - name: Rental to check
        unique_id: rental_cockpit_to_check
        value_template: "{{ value_json.to_check }}"
        json_attributes: [to_check_items]
      - name: Rental next arrival
        unique_id: rental_cockpit_next_arrival
        value_template: "{{ value_json.next_stay.start if value_json.next_stay else none }}"
        device_class: date
        json_attributes: [next_stay]
    binary_sensor:
      - name: Rental occupied tonight
        unique_id: rental_cockpit_occupied_tonight
        value_template: "{{ value_json.occupied_tonight > 0 }}"
        device_class: occupancy
      - name: Rental arrival tomorrow
        unique_id: rental_cockpit_arrival_tomorrow
        value_template: "{{ value_json.properties | selectattr('arrival_tomorrow') | list | count > 0 }}"
```

Restart Home Assistant (or reload the RESTful entities). The `sensor.rental_…` and `binary_sensor.rental_…` entities appear.

**One property only**: add `&property_id=<identifier>` to the address, or filter the `properties` list in a template, for example:

```yaml
value_template: "{{ value_json.properties | selectattr('name', 'eq', 'Harbour flat') | map(attribute='occupied_tonight') | first }}"
```

## 4. Automations

Pre-heat the day before an arrival:

```yaml
automation:
  - alias: "Rental: pre-heat the day before an arrival"
    triggers:
      - trigger: time
        at: "16:00:00"
    conditions:
      - condition: state
        entity_id: binary_sensor.rental_arrival_tomorrow
        state: "on"
    actions:
      - action: climate.set_temperature
        target:
          entity_id: climate.living_room     # your thermostat
        data:
          temperature: 20
```

Be told when data needs checking:

```yaml
  - alias: "Rental: data to check"
    triggers:
      - trigger: numeric_state
        entity_id: sensor.rental_to_check
        above: 0
    actions:
      - action: notify.mobile_app_my_phone   # your notification service
        data:
          title: "Rental Cockpit"
          message: >
            {{ states('sensor.rental_to_check') }} item(s) to check:
            {{ state_attr('sensor.rental_to_check', 'to_check_items') | map(attribute='title') | join(', ') }}
```

## 5. A card

```yaml
type: entities
title: Rental
entities:
  - sensor.rental_month_revenue
  - sensor.rental_month_balance
  - sensor.rental_month_occupancy
  - binary_sensor.rental_occupied_tonight
  - sensor.rental_next_arrival
  - sensor.rental_to_pay
  - sensor.rental_to_check
```

## Showing the whole interface inside Home Assistant (optional)

You can add Rental Cockpit as a **Webpage** dashboard in Home Assistant. For the browser to accept it:

- serve both over HTTPS under the same domain (for example `ha.example.org` and `rental.example.org`) so the sign-in cookie works inside the frame;
- allow Home Assistant to show Rental Cockpit: `RENTAL_COCKPIT_FRAME_ANCESTORS="https://ha.example.org"` and `RENTAL_COCKPIT_COOKIE_SECURE=true`.

Without that variable, Rental Cockpit refuses to be shown in a frame.

## API reference

`GET /api/v1/summary` — header `Authorization: Bearer <key>`. Optional parameters: `property_id` (one property), `lang` (`fr` or `en`, for titles).

Amounts in euros with two decimals; an unknown amount is `null`, never 0. Month and year figures are computed **per night occupied** (the Overview's *Rental performance*).

| Field | Content |
|---|---|
| `today`, `generated_at` | Today's date (server time zone) and generation time |
| `month`, `year` | `revenue`, `expenses`, `balance_before_financing`, `balance_after_financing`, `nights`, `occupancy` (0 to 1), `complete`, `start`, `end` |
| `cash_month` | `received` (money received), `balance_after_financing` — by payment date, like "My money" |
| `to_pay`, `to_receive` | Unpaid expenses, expected payouts not received |
| `to_check`, `to_check_items` | Number and list of data to check (`kind`, `count`, `title`) |
| `occupied_tonight`, `arrivals_today`, `departures_today` | Number of properties concerned |
| `next_stay` | Next stay: `property`, `start`, `end`, `nights`, `guests`, `status`, `in_progress` — or `null` |
| `properties[]` | Per property: `id`, `name`, `occupied_tonight`, `arrival_today`, `departure_today`, `arrival_tomorrow`, `guests_tonight`, `current_stay_end`, `next_arrival`, `next_arrival_guests`, `month` (`revenue`, `expenses`, `balance_before_financing`) |

Responses: `401` without a valid key, `403` for a property the key's account cannot see.
