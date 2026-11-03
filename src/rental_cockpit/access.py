# Copyright © 2026 Vincent Fournet
"""Who may see and do what (SEC 01, SEC 02).

Identity comes from the application's own accounts. Every request is checked
here, on the server: hiding a button in the interface is never a protection.

* An administrator configures, records, imports, corrects, backs up and
  restores.
* A reader sees only the properties an administrator granted; opening PDF
  documents is a separate permission.
* Somebody who is not signed in sees nothing but the sign-in page.
* The fictional demo can be viewed by any signed-in account and changed by
  administrators only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .engine.errors import RCError


@dataclass
class Access:
    user_id: str
    is_admin: bool
    property_ids: set[str] = field(default_factory=set)
    documents: set[str] = field(default_factory=set)
    dataset: str = "real"

    @property
    def role(self) -> str:
        if self.is_admin:
            return "admin"
        return "reader" if self.property_ids else "none"

    def require_admin(self) -> None:
        if not self.is_admin:
            raise RCError("forbidden")

    def require_property(self, property_id: str) -> None:
        if property_id not in self.property_ids:
            raise RCError("forbidden_property")

    def sees_documents(self, property_id: str) -> bool:
        return property_id in self.property_ids and property_id in self.documents

    def require_documents(self, property_id: str) -> None:
        self.require_property(property_id)
        if property_id not in self.documents:
            raise RCError("forbidden_documents")


def access_for(user: Any, grants: dict[str, bool], data: dict[str, Any], dataset: str) -> Access:
    """Rights of one account on one registry. ``grants`` maps property id → PDF access."""
    user_id = str(user["id"])
    all_properties = set(data.get("properties", {}))
    if user["role"] == "admin":
        return Access(user_id, True, all_properties, set(all_properties), dataset)
    if dataset == "demo":
        return Access(user_id, False, all_properties, set(all_properties), dataset)
    allowed = {pid for pid in grants if pid in all_properties}
    return Access(user_id, False, allowed, {pid for pid in allowed if grants[pid]}, dataset)
