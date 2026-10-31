# Copyright © 2026 Vincent Fournet
"""Read-only API for Home Assistant (optional, never required).

``GET /api/v1/summary`` with ``Authorization: Bearer <key>``. A key is
created by an account in « Réglages », reads exactly what that account may
read (same rights as the interface, real data only) and can change nothing.
Home Assistant's built-in RESTful integration turns the answer into sensors:
see docs/fr/home-assistant.md.

Amounts are in euros with two decimals (what Home Assistant sensors expect);
an unknown amount is ``null``, never a misleading zero.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from . import __version__
from .engine import indicators
from .engine.indicators import expected_payout, month_period
from .security import token_hash
from .web import Services, access, lang_of, utc_now


def eur(cents: int | None) -> float | None:
    return None if cents is None else round(cents / 100, 2)


def _figures(result: dict[str, Any]) -> dict[str, Any]:
    ind = result["indicators"]
    return {
        "start": result["period"]["start"],
        "end": result["period"]["end"],
        "revenue": eur(ind["revenue"]["value"]),
        "expenses": eur(ind["operating_expenses"]["value"]),
        "balance_before_financing": eur(ind["operating_balance"]["value"]),
        "balance_after_financing": eur(ind["balance_after_financing"]["value"]),
        "nights": ind["nights"]["value"],
        "occupancy": ind["occupancy"]["value"],
        "complete": bool(ind["revenue"]["complete"]),
    }


def summary(data: dict[str, Any], property_ids: set[str], today: date, lang: str) -> dict[str, Any]:
    month_start, month_end = month_period(today.year, today.month)
    year_start, year_end = date(today.year, 1, 1), date(today.year + 1, 1, 1)
    month = indicators.compute(data, property_ids=property_ids, start=month_start, end=month_end, mode="activity", lang=lang, today=today, compare=False)
    year = indicators.compute(data, property_ids=property_ids, start=year_start, end=year_end, mode="activity", lang=lang, today=today, compare=False)
    cash = indicators.compute(data, property_ids=property_ids, start=month_start, end=month_end, mode="cash", lang=lang, today=today, compare=False)

    stays = [s for s in data.get("stays", {}).values() if s["property_id"] in property_ids and s["status"] != "cancelled"]
    tomorrow = today + timedelta(days=1)
    properties = []
    for pid in sorted(property_ids, key=lambda p: data["properties"][p]["name"].casefold()):
        prop = data["properties"][pid]
        own = [s for s in stays if s["property_id"] == pid]
        current = next((s for s in own if s["start"] <= today.isoformat() < s["end"]), None)
        upcoming = sorted((s for s in own if s["start"] > today.isoformat()), key=lambda s: s["start"])
        figures = month["by_property"].get(pid, {"revenue": 0, "expenses": 0, "balance": 0})
        properties.append({
            "id": pid,
            "name": prop["name"],
            "archived": bool(prop.get("archived")),
            "occupied_tonight": current is not None,
            "arrival_today": any(s["start"] == today.isoformat() for s in own),
            "departure_today": any(s["end"] == today.isoformat() for s in own),
            "arrival_tomorrow": any(s["start"] == tomorrow.isoformat() for s in own),
            "guests_tonight": (current or {}).get("guests"),
            "current_stay_end": (current or {}).get("end"),
            "next_arrival": upcoming[0]["start"] if upcoming else None,
            "next_arrival_guests": upcoming[0].get("guests") if upcoming else None,
            "month": {"revenue": eur(figures["revenue"]), "expenses": eur(figures["expenses"]), "balance_before_financing": eur(figures["balance"])},
        })
    nxt = month["upcoming_stays"][0] if month["upcoming_stays"] else None
    pending = [s for s in stays if s["start"] <= today.isoformat() and expected_payout(s) is None]
    return {
        "version": __version__,
        "generated_at": utc_now(),
        "today": today.isoformat(),
        "currency": "EUR",
        "reading": "activity",
        "month": _figures(month),
        "year": _figures(year),
        "cash_month": {
            "received": eur(cash["indicators"]["revenue"]["value"]),
            "balance_after_financing": eur(cash["indicators"]["balance_after_financing"]["value"]),
        },
        "to_pay": eur(month["indicators"]["to_pay"]["value"]),
        "to_receive": eur(month["indicators"]["to_receive"]["value"]),
        "to_check": sum(item["count"] for item in month["to_check"] if item["severity"] != "info"),
        "to_check_items": [{"kind": item["kind"], "count": item["count"], "title": item["title"]} for item in month["to_check"]],
        "stays_without_amount": len(pending),
        "occupied_tonight": sum(1 for p in properties if p["occupied_tonight"]),
        "arrivals_today": sum(1 for p in properties if p["arrival_today"]),
        "departures_today": sum(1 for p in properties if p["departure_today"]),
        "next_stay": None if nxt is None else {
            "property": nxt["property"], "start": nxt["start"], "end": nxt["end"], "nights": nxt["nights"],
            "guests": nxt["guests"], "status": nxt["status"], "in_progress": nxt["timing"] == "in_progress",
        },
        "properties": properties,
    }


def register_ha_routes(app: FastAPI, services: Services) -> None:
    @app.get("/api/v1/summary")
    async def api_summary(request: Request):
        scheme, _, token = request.headers.get("authorization", "").partition(" ")
        user = services.db.user_for_api_key(token_hash(token.strip()), utc_now()) if scheme.lower() == "bearer" and token.strip() else None
        if user is None:
            return JSONResponse({"error": "unauthorized"}, status_code=401, headers={"WWW-Authenticate": "Bearer"})
        acc = access(services, user, "real")
        selected = set(acc.property_ids)
        wanted = request.query_params.get("property_id")
        if wanted:
            if wanted not in selected:
                return JSONResponse({"error": "forbidden_property"}, status_code=403)
            selected = {wanted}
        data = services.registries["real"].snapshot()
        lang = lang_of(request)
        return await run_in_threadpool(summary, data, selected, services.today(), lang)
