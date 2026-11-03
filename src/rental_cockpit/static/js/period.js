/* Copyright © 2026 Vincent Fournet */
// Period picker shared by the screens: « ◀  Octobre 2026  ▶ ».
//
// A period is a key: « m:2026-10 » (a month), « y:2026 » (a year),
// « r:2026-10-05:2026-11-05 » (from a day to the day after the last one) or
// « all » (every date, only where a screen allows it). The arrows move by
// the same length; the middle button opens a panel with the twelve months
// of a year, the arrows of the year, « Mois actuel », the whole year and,
// where it is useful, a free period. Everything is a real button: keyboard,
// screen reader and touch work the same way.

import { html, raw } from "./dom.js";
import { icon } from "./icons.js";

const pad = (n) => String(n).padStart(2, "0");

export function boundsOf(key) {
  const [kind, a, b] = String(key || "").split(":");
  if (kind === "y") return { start: `${a}-01-01`, end: `${Number(a) + 1}-01-01` };
  if (kind === "r") return { start: a, end: b };
  if (kind === "m") {
    const [y, m] = a.split("-").map(Number);
    return { start: `${a}-01`, end: m === 12 ? `${y + 1}-01-01` : `${y}-${pad(m + 1)}-01` };
  }
  return null;
}

function addDays(iso, days) {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

/** The key one step before (``-1``) or after (``1``) ``key``. */
export function stepKey(key, step) {
  const [kind, a] = String(key || "").split(":");
  if (kind === "y") return `y:${Number(a) + step}`;
  if (kind === "m") {
    const [y, m] = a.split("-").map(Number);
    const index = y * 12 + (m - 1) + step;
    return `m:${Math.floor(index / 12)}-${pad((index % 12) + 1)}`;
  }
  if (kind === "r") {
    const { start, end } = boundsOf(key);
    const days = Math.round((new Date(`${end}T00:00:00Z`) - new Date(`${start}T00:00:00Z`)) / 86400000);
    return `r:${addDays(start, step * days)}:${addDays(end, step * days)}`;
  }
  return key;
}

export function yearOf(key, today) {
  const [kind, a] = String(key || "").split(":");
  if (kind === "y") return Number(a);
  if (kind === "m" || kind === "r") return Number(a.slice(0, 4));
  return Number(today.slice(0, 4));
}

export function periodLabel(i18n, key) {
  const [kind, a, b] = String(key || "").split(":");
  if (kind === "y") return i18n.t("filter.year", { year: a });
  if (kind === "m") return i18n.month(`${a}-01`);
  if (kind === "r") return `${i18n.dateShort(a)} → ${i18n.dateShort(addDays(b, -1))}`;
  return i18n.t("period.all");
}

/**
 * The control. ``target`` names the screen value it changes (``overview`` or
 * ``entries``); ``open`` says whether its panel is shown; ``panelYear`` is the
 * year the panel shows; ``allowAll`` adds « Toutes les dates »;
 * ``allowRange`` adds the free period.
 */
export function periodControl(i18n, { target, value, open, panelYear, today, allowAll = false, allowRange = false }) {
  const { t } = i18n;
  const label = periodLabel(i18n, value);
  const stepping = value !== "all";
  const thisMonth = `m:${today.slice(0, 7)}`;
  const months = Array.from({ length: 12 }, (_, i) => `m:${panelYear}-${pad(i + 1)}`);
  const range = boundsOf(value);
  return html`
    <div class="period" data-period="${target}">
      <button type="button" class="iconbtn period-step" data-action="period-step" data-target="${target}" data-value="-1" ${raw(stepping ? "" : "disabled")} aria-label="${t("period.prev")}">${raw(icon("chevronRight", "flip"))}</button>
      <button type="button" class="period-open" data-action="period-open" data-target="${target}" aria-expanded="${open ? "true" : "false"}" aria-haspopup="dialog" aria-controls="rc-period-${target}" aria-label="${t("period.choose", { period: label })}">
        ${raw(icon("calendar", "lead"))}<span class="num">${label}</span>${raw(icon("chevronDown", "chev"))}
      </button>
      <button type="button" class="iconbtn period-step" data-action="period-step" data-target="${target}" data-value="1" ${raw(stepping ? "" : "disabled")} aria-label="${t("period.next")}">${raw(icon("chevronRight"))}</button>
      ${open ? html`
        <div class="period-panel" id="rc-period-${target}" role="dialog" aria-label="${t("period.panel")}">
          <div class="pp-year">
            <button type="button" class="iconbtn" data-action="period-year" data-target="${target}" data-value="-1" aria-label="${t("period.prevYear")}">${raw(icon("chevronRight", "flip"))}</button>
            <b class="num" aria-live="polite">${panelYear}</b>
            <button type="button" class="iconbtn" data-action="period-year" data-target="${target}" data-value="1" aria-label="${t("period.nextYear")}">${raw(icon("chevronRight"))}</button>
          </div>
          <div class="pp-months">
            ${months.map((key) => html`<button type="button" class="pp-month ${key === thisMonth ? "today" : ""}" data-action="period-pick" data-target="${target}" data-value="${key}" aria-pressed="${key === value ? "true" : "false"}" aria-label="${i18n.month(`${key.slice(2)}-01`)}">${i18n.monthShort(`${key.slice(2)}-01`)}</button>`)}
          </div>
          <div class="pp-quick">
            <button type="button" class="btn ghost small" data-action="period-pick" data-target="${target}" data-value="y:${panelYear}" aria-pressed="${value === `y:${panelYear}` ? "true" : "false"}">${t("period.wholeYear", { year: panelYear })}</button>
            <button type="button" class="btn ghost small" data-action="period-pick" data-target="${target}" data-value="${thisMonth}">${t("period.now")}</button>
            ${allowAll ? html`<button type="button" class="btn ghost small" data-action="period-pick" data-target="${target}" data-value="all" aria-pressed="${value === "all" ? "true" : "false"}">${t("period.all")}</button>` : ""}
          </div>
          ${allowRange ? html`
            <form class="pp-range" data-form="period-range" data-target="${target}">
              <span class="pp-range-title">${t("period.range")}</span>
              <label><span>${t("period.from")}</span><input type="date" name="from" required value="${range?.start || ""}"></label>
              <label><span>${t("period.to")}</span><input type="date" name="to" required value="${range ? addDays(range.end, -1) : ""}"></label>
              <button type="submit" class="btn small">${t("period.show")}</button>
            </form>` : ""}
        </div>` : ""}
    </div>`;
}

/** A free period typed by the person, as a key, or ``null`` when it is not a valid one. */
export function rangeKey(from, to) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(from) || !/^\d{4}-\d{2}-\d{2}$/.test(to) || to < from) return null;
  return `r:${from}:${addDays(to, 1)}`;
}
