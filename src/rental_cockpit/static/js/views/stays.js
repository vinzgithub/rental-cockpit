/* Copyright © 2026 Vincent Fournet */
// « Séjours » — every booking with its dates, amounts and payout.
// The list comes from /api/stays: figures such as nights, expected payout or
// money received are computed by the server with the same rules as the
// Overview, never here.

import { html, raw } from "../dom.js";
import { icon, propertyIcon } from "../icons.js";

export const STAY_VIEWS = ["active", "past", "attention", "cancelled", "all"];

const STATE_TONE = { cancelled: "grey", provisional: "amber", upcoming: "teal", in_progress: "blue", finished: "grey" };
const STATE_ICON = { cancelled: "ban", provisional: "hourglass", upcoming: "calendar", in_progress: "moon", finished: "check" };
const PAYOUT_TONE = { none: "grey", unknown: "amber", expected: "grey", to_confirm: "amber", partial: "amber", received: "teal" };
const PAYOUT_ICON = { none: "ban", unknown: "alert", expected: "hourglass", to_confirm: "hourglass", partial: "hourglass", received: "check" };

export function statePill(stay) {
  return html`<span class="pill ${STATE_TONE[stay.state] || "grey"}">${raw(icon(STATE_ICON[stay.state] || "calendar"))}${stay.state_label}</span>`;
}

export function payoutPill(stay) {
  return html`<span class="pill ${PAYOUT_TONE[stay.payout_state] || "grey"}">${raw(icon(PAYOUT_ICON[stay.payout_state] || "info"))}${stay.payout_label}</span>`;
}

export function stayTitle(v, stay) {
  return stay.guest_label || stay.external_ref || v.i18n.t("sj.untitled", { date: v.i18n.dateShort(stay.start) });
}

function payoutCell(v, stay) {
  const { i18n } = v;
  const detail = stay.payout_state === "partial"
    ? i18n.t("sj.received", { received: i18n.money(stay.received), expected: i18n.money(stay.expected_payout) })
    : stay.expected_payout !== null && stay.payout_state !== "none" ? i18n.money(stay.expected_payout) : "";
  return html`${payoutPill(stay)}${detail ? html`<small class="num">${detail}</small>` : ""}`;
}

function guestsText(v, n) {
  return n ? v.i18n.plural(n, "props.guest", "props.guests") : "—";
}

function viewTabs(v) {
  const { t } = v.i18n;
  const list = v.stays.data;
  return html`
    <div class="chips" role="tablist" aria-label="${t("sj.viewLabel")}">
      ${STAY_VIEWS.map((key) => {
        const count = list?.counts?.[key];
        const selected = v.stays.view === key;
        return html`<button type="button" role="tab" class="chip ${key === "attention" && count ? "warn" : ""}" aria-selected="${selected ? "true" : "false"}"
          data-action="stays-view" data-value="${key}">${t(`sj.view.${key}`)}${count !== undefined ? html`<span class="n num">${count}</span>` : ""}</button>`;
      })}
    </div>`;
}

function toolbar(v) {
  const { i18n, properties, state } = v;
  const { t } = i18n;
  return html`
    <div class="stays-tools">
      <label class="select has-lead">
        <span class="sr-only">${t("filter.property")}</span>
        ${raw(icon("home", "lead"))}
        <select data-change="property">
          <option value="all" ${raw(state.propertyId === "all" ? "selected" : "")}>${t("filter.all")}</option>
          ${properties.map((p) => html`<option value="${p.id}" ${raw(state.propertyId === p.id ? "selected" : "")}>${p.name}</option>`)}
        </select>
        ${raw(icon("chevronDown", "chev"))}
      </label>
      <label class="search">
        <span class="sr-only">${t("sj.search")}</span>
        ${raw(icon("search", "lead"))}
        <input type="search" data-input="stays-q" value="${v.stays.q}" placeholder="${t("sj.search")}" autocomplete="off" maxlength="80">
      </label>
    </div>`;
}

function table(v, stays) {
  const { i18n } = v;
  const { t } = i18n;
  return html`
    <table class="table stays-list">
      <thead><tr>
        <th scope="col">${t("sj.col.stay")}</th><th scope="col">${t("stays.property")}</th><th scope="col">${t("sj.col.dates")}</th>
        <th scope="col">${t("stays.guests")}</th><th scope="col" class="amt">${t("sj.col.amount")}</th>
        <th scope="col">${t("sj.col.payout")}</th><th scope="col">${t("sj.col.state")}</th><th scope="col"><span class="sr-only">${t("stays.actions")}</span></th>
      </tr></thead>
      <tbody>${stays.map((s) => html`
        <tr class="clickable" data-action="stay-open" data-value="${s.id}">
          <td class="c-title"><b>${stayTitle(v, s)}</b><small>${s.channel_label}${s.external_ref && s.guest_label ? ` · ${s.external_ref}` : ""}</small></td>
          <td><span class="propcell">${raw(propertyIcon(s.property_kind))}<span>${s.property}</span></span></td>
          <td class="num nowrap">${i18n.range(s.start, s.end)}<small>${i18n.plural(s.nights, "stays.night", "stays.nights")}</small></td>
          <td class="num nowrap" aria-label="${guestsText(v, s.guests)}"><span class="propcell">${raw(icon("users"))}<span>${s.guests || "—"}</span></span></td>
          <td class="amt num">${s.amounts.gross === null ? html`<span class="muted">—</span>` : i18n.money(s.amounts.gross)}</td>
          <td class="payout">${payoutCell(v, s)}</td>
          <td>${statePill(s)}</td>
          <td><button type="button" class="iconbtn" data-action="stay-open" data-value="${s.id}" aria-label="${t("sj.open", { date: i18n.dateLong(s.start) })}">${raw(icon("chevronRight"))}</button></td>
        </tr>`)}
      </tbody>
    </table>`;
}

function cards(v, stays) {
  const { i18n } = v;
  const { t } = i18n;
  return html`
    <div class="stays-list-cards">${stays.map((s) => html`
      <button type="button" class="stay-card clickable" data-action="stay-open" data-value="${s.id}" aria-label="${t("sj.open", { date: i18n.dateLong(s.start) })}">
        <span class="tile">${raw(propertyIcon(s.property_kind))}</span>
        <span class="body">
          <span class="stay-title"><b>${stayTitle(v, s)}</b>${statePill(s)}</span>
          <span class="when num">${i18n.range(s.start, s.end)}</span>
          <span class="facts"><span>${raw(icon("home"))}${s.property}</span><span>${raw(icon("moon"))}${i18n.plural(s.nights, "stays.night", "stays.nights")}</span><span>${raw(icon("users"))}${guestsText(v, s.guests)}</span></span>
          <span class="money-line"><b class="num">${s.amounts.gross === null ? t("sj.noAmount") : i18n.money(s.amounts.gross)}</b>${payoutPill(s)}</span>
        </span>
        <span class="chev">${raw(icon("chevronRight"))}</span>
      </button>`)}
    </div>`;
}

export function renderStays(v) {
  const { i18n, canWrite } = v;
  const { t } = i18n;
  const data = v.stays.data;
  const view = v.stays.view;
  let body;
  if (!v.properties.length && data) {
    body = html`<div class="empty">${raw(icon("home"))}<span>${t(canWrite ? "sj.noProperty" : "sj.noAccess")}</span>
      ${canWrite ? html`<button type="button" class="btn ghost small" data-action="add-property">${raw(icon("plus"))}${t("add.property")}</button>` : ""}</div>`;
  } else if (!data) {
    body = html`<div class="loading small"><div class="spinner"></div><span>${t("common.loading")}</span></div>`;
  } else if (!data.stays.length) {
    const message = v.stays.q ? t("sj.emptySearch", { q: v.stays.q }) : t(`sj.empty.${view}`);
    body = html`<div class="empty">${raw(icon(view === "attention" ? "checkCircle" : "calendar"))}<span>${message}</span>
      ${canWrite && !v.stays.q && (view === "active" || view === "all") ? html`<button type="button" class="btn ghost small" data-action="stay-new">${raw(icon("plus"))}${t("sj.add")}</button>` : ""}</div>`;
  } else {
    body = html`${table(v, data.stays)}${cards(v, data.stays)}`;
  }
  return html`
    <header class="pagehead">
      <div class="headline">
        <div><h1>${t("nav.sejours")}</h1><p class="sub">${t("sj.sub")}</p></div>
        ${canWrite && v.properties.length ? html`<button type="button" class="btn primary" data-action="stay-new">${raw(icon("plus"))}${t("sj.add")}</button>` : ""}
      </div>
      ${toolbar(v)}
    </header>
    ${viewTabs(v)}
    <p class="reading">${raw(icon("info"))}<span>${t(`sj.hint.${view}`)}</span></p>
    <section class="card stays-card" aria-live="polite">${body}</section>`;
}
