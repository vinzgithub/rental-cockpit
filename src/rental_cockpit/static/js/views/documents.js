/* Copyright © 2026 Vincent Fournet */
// « Justificatifs » — the private PDFs and the expenses they justify. A document
// counts in no total (the expense does); joining or detaching one never changes
// an expense. The list comes from /api/documents, filtered by the server on the
// properties whose PDFs the account was granted.

import { documentPill } from "../document-dialogs.js";
import { html, raw } from "../dom.js";
import { icon } from "../icons.js";

function documentCard(v, d) {
  const { i18n } = v;
  const { t } = i18n;
  const facts = [d.supplier, d.invoice_number, d.invoice_date ? i18n.dateShort(d.invoice_date) : ""].filter(Boolean);
  const linked = d.entries.length
    ? (d.entries.length === 1 ? t("doc.linkedTo", { label: d.entries[0].label }) : i18n.plural(d.entries.length, "doc.linkedOne", "doc.linkedMany"))
    : t("doc.notLinked");
  return html`
    <button type="button" class="doc-card clickable" data-action="document-open" data-value="${d.id}" aria-label="${t("doc.openLabel", { name: d.filename })}">
      <span class="tile">${raw(icon("file"))}</span>
      <span class="body">
        <span class="stay-title"><b>${d.filename}</b></span>
        <span class="when">${facts.length ? facts.join(" · ") : t("doc.noFacts")}</span>
        <span class="facts">${d.property} · ${linked}</span>
        <span class="money-line">${documentPill(t, d)}</span>
      </span>
      <span class="end-col"><b class="num">${d.amount !== null && d.amount !== undefined ? i18n.money(d.amount) : "—"}</b><span class="chev">${raw(icon("chevronRight"))}</span></span>
    </button>`;
}

export function renderDocuments(v) {
  const { i18n, canWrite } = v;
  const { t } = i18n;
  const data = v.documents.data;
  const view = v.documents.view;
  let body;
  if (!data) {
    body = html`<div class="loading small"><div class="spinner"></div><span>${t("common.loading")}</span></div>`;
  } else if (!data.documents.length) {
    body = html`<div class="empty">${raw(icon("file"))}<span>${v.documents.q ? t("doc.emptySearch", { q: v.documents.q }) : t(`doc.empty.${view}`)}</span>
      ${canWrite && view === "all" && !v.documents.q ? html`<span class="empty-actions"><button type="button" class="btn ghost small" data-action="invoice-import">${raw(icon("upload"))}${t("doc.importTitle")}</button></span>` : ""}</div>`;
  } else {
    body = html`<div class="doc-grid">${data.documents.map((d) => documentCard(v, d))}</div>`;
  }
  return html`
    <header class="pagehead stacked">
      <div class="headline">
        <div><h1>${t("nav.justificatifs")}</h1><p class="sub">${t("doc.sub")}</p></div>
        ${canWrite ? html`<div class="head-actions"><button type="button" class="btn primary" data-action="invoice-import">${raw(icon("upload"))}${t("doc.importTitle")}</button></div>` : ""}
      </div>
      <label class="search">
        <span class="sr-only">${t("doc.search")}</span>
        ${raw(icon("search", "lead"))}
        <input type="search" data-input="documents-q" value="${v.documents.q}" placeholder="${t("doc.search")}" autocomplete="off" maxlength="80">
      </label>
    </header>
    <div class="chips" role="tablist" aria-label="${t("doc.viewLabel")}">
      ${["all", "incomplete"].map((key) => html`<button type="button" role="tab" class="chip" aria-selected="${view === key ? "true" : "false"}"
        data-action="documents-view" data-value="${key}">${t(`doc.view.${key}`)}${data ? html`<span class="n num">${data.counts[key]}</span>` : ""}</button>`)}
    </div>
    <p class="reading">${raw(icon("info"))}<span>${t("doc.hint")}</span></p>
    ${data?.hidden ? html`<p class="reading">${raw(icon("lock"))}<span>${i18n.plural(data.hidden, "doc.hiddenListOne", "doc.hiddenListMany")}</span></p>` : ""}
    <section aria-live="polite">${body}</section>`;
}
