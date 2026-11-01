/* Copyright © 2026 Vincent Fournet */
// « Dépenses » — expenses and income outside stays, with what is paid and
// what is still due. Every figure (paid, remaining, status, totals) comes
// from /api/entries, computed from the real payments by the server.

import { html, raw } from "../dom.js";
import { icon, propertyIcon } from "../icons.js";

export const ENTRY_VIEWS = ["all", "to_pay", "to_confirm", "to_receive", "archived"];

const STATE_TONE = { unknown: "amber", unpaid: "blue", partial: "amber", paid: "teal" };
const STATE_ICON = { unknown: "help", unpaid: "hourglass", partial: "hourglass", paid: "check" };

export function entryStatePill(entry, t = null) {
  if (t && entry.upcoming && (entry.state === "unpaid" || entry.state === "unknown")) {
    return html`<span class="pill grey">${raw(icon("calendar"))}${t("ex.planned")}</span>`;
  }
  return html`<span class="pill ${STATE_TONE[entry.state] || "grey"}">${raw(icon(STATE_ICON[entry.state] || "info"))}${entry.state_label}</span>`;
}

export function seriesText(v, entry) {
  return entry.series ? v.i18n.t("ex.series", { index: entry.series.index, count: entry.series.count }) : "";
}

/** Query string of the current list, for the CSV export link (same filters as on screen). */
export function exportUrl(v, path, params) {
  const url = new URL(path, window.location.origin);
  for (const [key, value] of Object.entries({ dataset: v.dataset, lang: v.i18n.lang, ...params })) {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, value);
  }
  return url.pathname + url.search;
}

function amountCell(v, e) {
  const { i18n } = v;
  return html`<b class="num">${e.kind === "income" ? "+ " : ""}${i18n.money(e.amount)}</b>`;
}

function stateCell(v, e) {
  const { i18n } = v;
  const detail = e.state === "partial" ? i18n.t("ex.left", { amount: i18n.money(e.remaining) }) : "";
  return html`${e.archived ? html`<span class="pill grey">${raw(icon("archive"))}${i18n.t("ex.archived")}</span>` : entryStatePill(e, i18n.t)}${detail ? html`<small class="num">${detail}</small>` : ""}`;
}

function subline(v, e) {
  return [e.category, e.supplier, seriesText(v, e)].filter(Boolean).join(" · ");
}

function viewTabs(v) {
  const { t } = v.i18n;
  const list = v.entries.data;
  return html`
    <div class="chips" role="tablist" aria-label="${t("ex.viewLabel")}">
      ${ENTRY_VIEWS.map((key) => {
        const count = list?.counts?.[key];
        const selected = v.entries.view === key;
        const warn = (key === "to_confirm" || key === "to_pay") && count;
        return html`<button type="button" role="tab" class="chip ${warn ? "warn" : ""}" aria-selected="${selected ? "true" : "false"}"
          data-action="entries-view" data-value="${key}">${t(`ex.view.${key}`)}${count !== undefined ? html`<span class="n num">${count}</span>` : ""}</button>`;
      })}
    </div>`;
}

function toolbar(v) {
  const { i18n, properties, state } = v;
  const { t } = i18n;
  const years = v.entries.data?.years || [];
  return html`
    <div class="entries-tools">
      <label class="select has-lead">
        <span class="sr-only">${t("filter.property")}</span>
        ${raw(icon("home", "lead"))}
        <select data-change="property">
          <option value="all" ${raw(state.propertyId === "all" ? "selected" : "")}>${t("filter.all")}</option>
          ${properties.map((p) => html`<option value="${p.id}" ${raw(state.propertyId === p.id ? "selected" : "")}>${p.name}</option>`)}
        </select>
        ${raw(icon("chevronDown", "chev"))}
      </label>
      <label class="select has-lead">
        <span class="sr-only">${t("ex.kindLabel")}</span>
        ${raw(icon("filter", "lead"))}
        <select data-change="entries-kind">
          ${["", "expense", "income"].map((k) => html`<option value="${k}" ${raw(v.entries.kind === k ? "selected" : "")}>${t(`ex.kind.${k || "all"}`)}</option>`)}
        </select>
        ${raw(icon("chevronDown", "chev"))}
      </label>
      <label class="select has-lead">
        <span class="sr-only">${t("ex.yearLabel")}</span>
        ${raw(icon("calendar", "lead"))}
        <select data-change="entries-year">
          <option value="" ${raw(!v.entries.year ? "selected" : "")}>${t("ex.allYears")}</option>
          ${[...new Set([...years, v.entries.year].filter(Boolean))].map((y) => html`<option value="${y}" ${raw(v.entries.year === y ? "selected" : "")}>${y}</option>`)}
        </select>
        ${raw(icon("chevronDown", "chev"))}
      </label>
      <label class="search">
        <span class="sr-only">${t("ex.search")}</span>
        ${raw(icon("search", "lead"))}
        <input type="search" data-input="entries-q" value="${v.entries.q}" placeholder="${t("ex.search")}" autocomplete="off" maxlength="80">
      </label>
    </div>`;
}

function totalsStrip(v) {
  const { i18n } = v;
  const { t } = i18n;
  const data = v.entries.data;
  if (!data || !data.entries.length) return "";
  const tot = data.totals;
  const kind = v.entries.kind;
  const cells = [];
  if (kind !== "income") cells.push(["ex.total.expenses", tot.expenses, ""], ["ex.total.toPay", tot.to_pay, tot.to_pay ? "warn" : ""]);
  if (kind !== "expense" && (tot.income || kind === "income")) cells.push(["ex.total.income", tot.income, ""], ["ex.total.toReceive", tot.to_receive, ""]);
  if (tot.upcoming) cells.push(["ex.total.upcoming", tot.upcoming, ""]);
  return html`
    <dl class="totals" aria-label="${t("ex.totalsLabel")}">
      ${cells.map(([key, value, tone]) => html`<div class="${tone}"><dt>${t(key)}</dt><dd class="num">${i18n.money(value)}</dd></div>`)}
    </dl>`;
}

function table(v, rows) {
  const { i18n } = v;
  const { t } = i18n;
  return html`
    <table class="table entries-list">
      <thead><tr>
        <th scope="col">${t("ex.col.label")}</th><th scope="col">${t("stays.property")}</th><th scope="col">${t("ex.col.date")}</th>
        <th scope="col" class="amt">${t("ex.col.amount")}</th><th scope="col">${t("ex.col.payment")}</th>
        <th scope="col"><span class="sr-only">${t("stays.actions")}</span></th>
      </tr></thead>
      <tbody>${rows.map((e, index) => html`
        ${e.upcoming && !rows[index - 1]?.upcoming ? html`<tr class="group-row"><td colspan="6">${t("ex.upcoming")}</td></tr>` : ""}
        <tr class="clickable ${e.kind}" data-action="entry-open" data-value="${e.id}">
          <td class="c-title"><b>${e.label}</b><small>${subline(v, e)}</small></td>
          <td><span class="propcell">${raw(propertyIcon(e.property_kind))}<span>${e.property}</span></span></td>
          <td class="num nowrap">${i18n.dateShort(e.date)}${e.period_start ? html`<small>${i18n.range(e.period_start, e.period_end)}</small>` : ""}</td>
          <td class="amt">${amountCell(v, e)}${e.treatment !== "operating_expense" && e.treatment !== "operating_income" ? html`<small>${e.treatment_label}</small>` : ""}</td>
          <td class="payment">${stateCell(v, e)}</td>
          <td><button type="button" class="iconbtn" data-action="entry-open" data-value="${e.id}" aria-label="${t("ex.open", { label: e.label })}">${raw(icon("chevronRight"))}</button></td>
        </tr>`)}
      </tbody>
    </table>`;
}

function cards(v, rows) {
  const { i18n } = v;
  const { t } = i18n;
  return html`
    <div class="entries-list-cards">${rows.map((e, index) => html`
      ${e.upcoming && !rows[index - 1]?.upcoming ? html`<p class="group-title">${t("ex.upcoming")}</p>` : ""}
      <button type="button" class="stay-card entry-card clickable ${e.kind}" data-action="entry-open" data-value="${e.id}" aria-label="${t("ex.open", { label: e.label })}">
        <span class="tile">${raw(icon(e.kind === "income" ? "coins" : "receipt"))}</span>
        <span class="body">
          <span class="stay-title"><b>${e.label}</b></span>
          <span class="when">${subline(v, e)}</span>
          <span class="facts"><span>${raw(icon("home"))}${e.property}</span><span class="num">${raw(icon("calendar"))}${i18n.dateShort(e.date)}</span></span>
          <span class="money-line">${amountCell(v, e)}${stateCell(v, e)}</span>
        </span>
        <span class="chev">${raw(icon("chevronRight"))}</span>
      </button>`)}
    </div>`;
}

export function renderExpenses(v) {
  const { i18n, canWrite } = v;
  const { t } = i18n;
  const data = v.entries.data;
  const view = v.entries.view;
  const filtered = v.entries.q || v.entries.kind || v.entries.year;
  let body;
  if (!v.properties.length && data) {
    body = html`<div class="empty">${raw(icon("home"))}<span>${t(canWrite ? "sj.noProperty" : "sj.noAccess")}</span>
      ${canWrite ? html`<button type="button" class="btn ghost small" data-action="add-property">${raw(icon("plus"))}${t("add.property")}</button>` : ""}</div>`;
  } else if (!data) {
    body = html`<div class="loading small"><div class="spinner"></div><span>${t("common.loading")}</span></div>`;
  } else if (!data.entries.length) {
    const message = filtered ? t("ex.emptyFiltered") : t(`ex.empty.${view}`);
    body = html`<div class="empty">${raw(icon(view === "all" || view === "archived" ? "receipt" : "checkCircle"))}<span>${message}</span>
      ${canWrite && !filtered && view === "all" ? html`<span class="empty-actions"><button type="button" class="btn ghost small" data-action="entry-new" data-value="expense">${raw(icon("plus"))}${t("ex.addExpense")}</button></span>` : ""}</div>`;
  } else {
    body = html`${table(v, data.entries)}${cards(v, data.entries)}
      ${data.more ? html`<p class="reading">${raw(icon("info"))}<span>${t("ex.more", { n: data.more })}</span></p>` : ""}`;
  }
  const params = { view, property_id: v.state.propertyId, kind: v.entries.kind, year: v.entries.year, q: v.entries.q };
  return html`
    <header class="pagehead stacked">
      <div class="headline">
        <div><h1>${t("nav.depenses")}</h1><p class="sub">${t("ex.sub")}</p></div>
        ${v.properties.length ? html`<div class="head-actions">
          <a class="btn ghost" href="${exportUrl(v, "/api/export/entries.csv", params)}" download>${raw(icon("download"))}${t("ex.export")}</a>
          ${canWrite ? html`
            <button type="button" class="btn ghost" data-action="invoice-import">${raw(icon("file"))}${t("ex.fromInvoice")}</button>
            <button type="button" class="btn ghost" data-action="entry-new" data-value="income">${raw(icon("plus"))}${t("ex.addIncome")}</button>
            <button type="button" class="btn primary" data-action="entry-new" data-value="expense">${raw(icon("plus"))}${t("ex.addExpense")}</button>` : ""}
        </div>` : ""}
      </div>
      ${toolbar(v)}
    </header>
    ${viewTabs(v)}
    <p class="reading">${raw(icon("info"))}<span>${t(`ex.hint.${view}`)}</span></p>
    ${totalsStrip(v)}
    <section class="card stays-card entries-card" aria-live="polite">${body}</section>`;
}
