# Copyright © 2026 Vincent Fournet
"""Registry schema migrations.

Each step turns schema ``n`` into ``n + 1`` and is tested on a copy. A
registry written by a *newer* version is never loaded: the product refuses
to start on it rather than risk misreading it (SAU 02).
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from .schema import SCHEMA_VERSION, default_categories, empty_registry


def _v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    """Schema 2: every stay gets a booking channel.

    Imported Airbnb stays are Airbnb bookings; for anything else the channel
    was never recorded, so it becomes « Autre » rather than a guess.
    """
    for stay in data.get("stays", {}).values():
        if not stay.get("channel"):
            stay["channel"] = "airbnb" if stay.get("source") == "airbnb" else "other"
    return data


STEPS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {
    1: _v1_to_v2,
}


class SchemaTooNew(Exception):
    def __init__(self, schema: int) -> None:
        super().__init__(schema)
        self.schema = schema


def migrate(raw: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Return ``(registry, changed)``. Missing collections are added, never removed."""
    data = deepcopy(raw)
    schema = int(data.get("schema") or 1)
    if schema > SCHEMA_VERSION:
        raise SchemaTooNew(schema)
    changed = False
    while schema < SCHEMA_VERSION:
        data = STEPS[schema](data)
        schema += 1
        data["schema"] = schema
        changed = True
    template = empty_registry()
    for key, value in template.items():
        if key not in data:
            data[key] = value
            changed = True
    for key, value in template["settings"].items():
        data["settings"].setdefault(key, value)
    for category_id, category in default_categories().items():
        if category_id not in data["categories"]:
            data["categories"][category_id] = category
            changed = True
    return data, changed
