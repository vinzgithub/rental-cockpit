/* Copyright © 2026 Vincent Fournet */
// « Prestataires » — the people and companies who work for the rentals, their
// indicative rates and their invoices. Totals (this year, left to pay, left to
// split between stays) come from /api/suppliers, computed by the server.

import { html, raw } from "../dom.js";
import { icon } from "../icons.js";

function supplierCard(v, s) {
  const { i18n } = v;
  const { t } = i18n;
  const facts = [
    s.entries ? i18n.plural(s.entries, "sup.invoiceOne", "sup.invoiceMany") : t("sup.noInvoice"),
    s.year_total ? t("sup.yearTotal", { year: s.year, amount: i18n.money(s.year_total) }) : "",
  ].filter(Boolean);
  return html`
    <button type="button" class="supplier-card clickable" data-action="supplier-open" data-value="${s.id}" aria-label="${t("sup.open", { name: s.name })}">
      <span class="tile">${raw(icon("users"))}</span>
      <span class="body">
        <span class="stay-title"><b>${s.name}</b>${s.archived ? html`<span class="pill grey">${raw(icon("archive"))}${t("sup.archived")}</span>` : ""}</span>
        ${s.role ? html`<span class="when">${s.role}</span>` : ""}
        ${s.categories.length ? html`<span class="tags">${s.categories.map((c) => html`<span class="tag">${c.label}</span>`)}</span>` : ""}
        <span class="facts num">${facts.join(" · ")}</span>
        ${s.to_pay || s.to_confirm || s.unallocated ? html`<span class="money-line">
          ${s.to_pay ? html`<span class="pill blue">${raw(icon("hourglass"))}${t("sup.toPay", { amount: i18n.money(s.to_pay) })}</span>` : ""}
          ${s.to_confirm ? html`<span class="pill amber">${raw(icon("help"))}${i18n.plural(s.to_confirm, "sup.toConfirmOne", "sup.toConfirmMany")}</span>` : ""}
          ${s.unallocated ? html`<span class="pill amber">${raw(icon("split"))}${t("sup.toSplit", { amount: i18n.money(s.unallocated) })}</span>` : ""}
        </span>` : ""}
      </span>
      <span class="chev">${raw(icon("chevronRight"))}</span>
    </button>`;
}

export function renderSuppliers(v) {
  const { i18n, canWrite } = v;
  const { t } = i18n;
  const data = v.suppliers.data;
  const view = v.suppliers.view;
  let body;
  if (!data) {
    body = html`<div class="loading small"><div class="spinner"></div><span>${t("common.loading")}</span></div>`;
  } else if (!data.suppliers.length) {
    body = html`<div class="empty">${raw(icon("users"))}<span>${v.suppliers.q ? t("sup.emptySearch", { q: v.suppliers.q }) : t(`sup.empty.${view}`)}</span>
      ${canWrite && view === "active" && !v.suppliers.q ? html`<span class="empty-actions"><button type="button" class="btn ghost small" data-action="supplier-new">${raw(icon("plus"))}${t("sup.add")}</button></span>` : ""}</div>`;
  } else {
    body = html`<div class="supplier-grid">${data.suppliers.map((s) => supplierCard(v, s))}</div>`;
  }
  return html`
    <header class="pagehead stacked">
      <div class="headline">
        <div><h1>${t("nav.prestataires")}</h1><p class="sub">${t("sup.sub")}</p></div>
        ${canWrite ? html`<div class="head-actions"><button type="button" class="btn primary" data-action="supplier-new">${raw(icon("plus"))}${t("sup.add")}</button></div>` : ""}
      </div>
      <label class="search">
        <span class="sr-only">${t("sup.search")}</span>
        ${raw(icon("search", "lead"))}
        <input type="search" data-input="suppliers-q" value="${v.suppliers.q}" placeholder="${t("sup.search")}" autocomplete="off" maxlength="80">
      </label>
    </header>
    <div class="chips" role="tablist" aria-label="${t("sup.viewLabel")}">
      ${["active", "archived"].map((key) => html`<button type="button" role="tab" class="chip" aria-selected="${view === key ? "true" : "false"}"
        data-action="suppliers-view" data-value="${key}">${t(`sup.view.${key}`)}${data ? html`<span class="n num">${data.counts[key]}</span>` : ""}</button>`)}
    </div>
    <p class="reading">${raw(icon("info"))}<span>${t("sup.hint")}</span></p>
    <section aria-live="polite">${body}</section>`;
}
