/* Copyright © 2026 Vincent Fournet */
// Expense / income page, form, payment, and the categories of « Réglages ».
// Every change goes to the server, which checks the rights and the amounts
// again; the dialogs only explain, collect and show what the server returns.

import { openConfirm, openDialog } from "./dialogs.js";
import { documentsSection, wireDocumentsSection } from "./document-dialogs.js";
import { html, markup, raw } from "./dom.js";
import { icon } from "./icons.js";
import { openReconcile, openSplit } from "./split-dialogs.js";
import { entryStatePill, seriesText } from "./views/expenses.js";

/** "1 234,50 €" typed by a person → "1234,50" for the server (spaces are only grouping). */
function cleanAmount(value) {
  return String(value ?? "").replace(/[\s  €]/g, "");
}

function amountValue(cents) {
  if (cents === null || cents === undefined) return "";
  return (cents / 100).toFixed(2).replace(".", ",").replace(",00", "");
}

function toCents(text) {
  const value = parseFloat(cleanAmount(text).replace(",", "."));
  return Number.isFinite(value) ? Math.round(value * 100) : null;
}

function errorBox(message) {
  return markup(html`<div class="error-box" role="alert">${raw(icon("alert"))}<span>${message}</span></div>`);
}

const TREATMENT_NOTE = {
  operating_expense: "exf.treat.operating_expense",
  operating_income: "exf.treat.operating_income",
  investment: "exf.treat.investment",
  financing: "exf.treat.financing",
  tax: "exf.treat.tax",
  information: "exf.treat.information",
};

async function refreshAfter(app) {
  await app.afterEntryChange();
}

// ------------------------------------------------------------------ entry page

export async function openEntry(app, entryId) {
  const { t } = app.i18n;
  const dialog = openDialog(app, {
    title: t("exd.title"),
    body: html`<div class="loading small"><div class="spinner"></div><span>${t("common.loading")}</span></div>`,
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.close")}</button>`,
    wide: true,
    labelledby: "rc-entry-title",
  });
  let detail;
  try {
    detail = await app.api.get(`/api/entries/${encodeURIComponent(entryId)}`);
  } catch (err) {
    dialog.querySelector(".dbody").innerHTML = errorBox(err.message);
    return;
  }
  fillEntry(app, dialog, detail);
}

function fillEntry(app, dialog, e) {
  const { i18n } = app;
  const { t } = i18n;
  const canWrite = app.canWrite;
  const income = e.kind === "income";
  const editable = canWrite && !e.archived && !e.superseded;
  const split = e.loan_split;

  dialog.querySelector(".dhead h2").textContent = e.label;
  const head = dialog.querySelector(".dhead div");
  head.querySelector("p")?.remove();
  head.insertAdjacentHTML("beforeend", markup(html`<p>${e.property} · ${e.category} · <span class="num">${i18n.dateLong(e.date)}</span></p>`));

  const payments = html`
    <section>
      <h3 class="section-title">${t(income ? "exd.receipts" : "exd.payments")}</h3>
      <div class="rows">
        ${e.payments.length ? e.payments.map((p) => html`
          <div class="keyrow">
            <span class="tile">${raw(icon("coins"))}</span>
            <span><b class="num">${i18n.money(p.amount)}</b><small>${i18n.dateLong(p.date)}${p.method ? ` · ${p.method}` : ""}${p.note ? ` · ${p.note}` : ""}</small></span>
            ${canWrite && !p.shared ? html`<button type="button" class="btn ghost small" data-payment-delete="${p.id}" data-amount="${p.amount}" data-date="${p.date}">${raw(icon("trash"))}${t("sjd.deletePayment")}</button>` : ""}
          </div>`) : html`<div class="empty">${raw(icon("info"))}<span>${t(income ? "exd.noReceipt" : "exd.noPayment")}</span></div>`}
      </div>
      ${editable && e.remaining > 0 ? html`<div class="actions">
        <button type="button" class="btn outline-accent" data-pay>${raw(icon("plus"))}${t(income ? "exd.recordReceipt" : "exd.recordPayment")}</button>
        ${e.state === "unknown" ? html`<button type="button" class="btn ghost" data-declare="unpaid">${raw(icon("hourglass"))}${t(income ? "exd.notReceived" : "exd.notPaid")}</button>` : ""}
        ${e.state === "unpaid" ? html`<button type="button" class="btn ghost" data-declare="unknown">${raw(icon("help"))}${t("exd.dontKnow")}</button>` : ""}
      </div>` : ""}
    </section>`;

  // Detailed invoice: its services, and how they are split between stays (analytical only).
  // An expense already linked to one stay as a whole needs no split (it is that stay's cost).
  const splittable = !income && (e.service_lines.length || e.allocations.length || (!e.stay_id && ["cleaning", "linen", "travel"].includes(e.category_id)));
  const leftToSplit = e.split.reduce((sum, row) => sum + Math.max(row.remaining, 0), 0);
  const lines = splittable ? html`
    <section>
      <h3 class="section-title">${t(e.service_lines.length ? "spl.titleLines" : "spl.title")}</h3>
      <p class="reading">${raw(icon("info"))}<span>${t("spl.intro")}</span></p>
      <div class="split-rows">${e.split.map((row) => html`
        <div class="split-row">
          <div class="split-head"><b>${row.kind_label || e.label}${row.kind_label && row.label && row.label !== row.kind_label ? html` <small>· ${row.label}</small>` : ""}</b>
            <span class="num">${i18n.money(row.amount)}</span></div>
          ${row.allocations.length ? html`<ul class="plain-list notes">${row.allocations.map((a) => html`<li><span class="num">${i18n.money(a.amount)}</span> → ${a.stay_id ? html`<button type="button" class="linkbtn small inline" data-action="stay-open" data-value="${a.stay_id}">${a.stay_label}</button>` : t("spl.noStay")}</li>`)}</ul>` : ""}
          ${row.remaining <= 0 ? html`<small class="done">${raw(icon("check"))}${t("spl.done")}</small>`
            : e.allocations.length ? html`<small class="left num">${t("spl.left", { amount: i18n.money(row.remaining) })}</small>` : html`<small class="muted">${t("spl.notSplit")}</small>`}
        </div>`)}
      </div>
      ${editable ? html`<div class="actions"><button type="button" class="btn outline-accent" data-split>${raw(icon("split"))}${t(e.allocations.length ? "spl.edit" : "spl.open")}</button>
        ${leftToSplit && e.allocations.length ? html`<span class="pill amber">${t("spl.leftTotal", { amount: i18n.money(leftToSplit) })}</span>` : ""}</div>` : ""}
    </section>` : "";

  // An invoice that replaces entries typed by hand for the same services (reconciliation).
  const reconcile = !income && !e.superseded && (e.replaces.length || (editable && (e.service_lines.length || e.invoice_number))) ? html`
    <section>
      <h3 class="section-title">${t("rec.title")}</h3>
      ${e.replaces.length ? html`<div class="rows">${e.replaces.map((r) => html`
        <div class="keyrow">
          <span class="tile">${raw(icon("copy"))}</span>
          <span><b>${r.label}</b><small class="num">${i18n.dateShort(r.date)} · ${i18n.money(r.amount)}${r.payments ? ` · ${t("rec.paidMoved", { amount: i18n.money(r.payments) })}` : ""}</small></span>
          ${canWrite ? html`<button type="button" class="btn ghost small" data-unreconcile="${r.id}">${raw(icon("repeat"))}${t("rec.undo")}</button>` : ""}
        </div>`)}</div>` : html`<p class="reading">${raw(icon("info"))}<span>${t("rec.intro")}</span></p>`}
      ${editable ? html`<div class="actions"><button type="button" class="btn ghost" data-reconcile>${raw(icon("copy"))}${t("rec.open")}</button></div>` : ""}
    </section>` : "";

  dialog.querySelector(".dbody").innerHTML = markup(html`
    <div class="pill-row">
      ${e.archived ? html`<span class="pill grey">${raw(icon("archive"))}${t("ex.archived")}</span>` : entryStatePill(e, t)}
      <span class="pill grey">${raw(icon(income ? "coins" : "receipt"))}${e.kind_label}</span>
      ${e.series ? html`<span class="pill blue">${raw(icon("repeat"))}${seriesText(app.viewModel(), e)}</span>` : ""}
    </div>
    ${e.archived ? html`<div class="tip">${raw(icon("info"))}<div><p>${t("exd.archivedNote")}</p></div></div>` : ""}
    ${e.superseded_by ? html`<div class="tip">${raw(icon("copy"))}<div><p>${t("rec.replacedBy", { label: e.superseded_by.label })}</p>
      <button type="button" class="linkbtn small" data-action="entry-open" data-value="${e.superseded_by.id}" data-close>${t("rec.openInvoice")}</button></div></div>` : ""}
    <section>
      <h3 class="section-title">${t("sjd.amounts")}</h3>
      <dl class="facts-list money-facts">
        <div><dt>${t("exd.amount")}</dt><dd class="num">${i18n.money(e.amount)}</dd></div>
        <div><dt>${t(income ? "exd.received" : "exd.paid")}</dt><dd class="num">${i18n.money(e.paid)}</dd></div>
        ${e.remaining > 0 ? html`<div><dt>${t(income ? "exd.toReceive" : "exd.toPay")}</dt><dd class="num"><b>${i18n.money(e.remaining)}</b></dd></div>` : ""}
        ${split ? html`
          <div><dt>${t("exf.principal")}</dt><dd class="num">${i18n.money(split.principal)}</dd></div>
          <div><dt>${t("exf.interest")}</dt><dd class="num">${i18n.money(split.interest)}</dd></div>
          <div><dt>${t("exf.insurance")}</dt><dd class="num">${i18n.money(split.insurance)}</dd></div>` : ""}
      </dl>
    </section>
    <section>
      <h3 class="section-title">${t("exd.counts")}</h3>
      <p class="reading">${raw(icon("info"))}<span>${t(TREATMENT_NOTE[e.treatment] || "exf.treat.operating_expense")}</span></p>
      <ul class="plain-list notes">
        <li>${e.period_start ? t("exd.activitySpread", { range: i18n.range(e.period_start, e.period_end) }) : t("exd.activityDate", { date: i18n.dateLong(e.date) })}</li>
        <li>${t("exd.invoiceDate", { date: i18n.dateLong(e.date) })}</li>
        <li>${t(income ? "exd.cashIn" : "exd.cashOut")}</li>
      </ul>
    </section>
    ${payments}
    ${lines}
    ${reconcile}
    ${documentsSection(app, e)}
    <section>
      <h3 class="section-title">${t("sjd.about")}</h3>
      <dl class="facts-list">
        <div><dt>${t("exf.category")}</dt><dd>${e.category} <small class="muted">· ${e.treatment_label}</small></dd></div>
        ${e.supplier ? html`<div><dt>${t("exf.supplier")}</dt><dd>${e.supplier}</dd></div>` : ""}
        ${e.invoice_number ? html`<div><dt>${t("exf.invoice")}</dt><dd>${e.invoice_number}</dd></div>` : ""}
        ${e.stay_label ? html`<div><dt>${t("exf.stay")}</dt><dd><button type="button" class="linkbtn" data-action="stay-open" data-value="${e.stay_id}">${e.stay_label}</button></dd></div>` : ""}
        ${e.note ? html`<div><dt>${t("sjd.note")}</dt><dd class="pre">${e.note}</dd></div>` : ""}
        <div><dt>${t("sjd.trace")}</dt><dd>${t("sjd.created", { date: i18n.dateShort((e.created_at || "").slice(0, 10)) })}${e.history.length ? ` · ${i18n.plural(e.history.length, "sjd.changedOnce", "sjd.changedMany")}` : ""}</dd></div>
      </dl>
    </section>`);

  const foot = dialog.querySelector(".dfoot");
  foot.classList.toggle("stay-actions", canWrite);
  foot.innerHTML = markup(canWrite ? html`
    ${e.deletable ? html`<button type="button" class="btn ghost danger-text del" data-delete>${raw(icon("trash"))}${t("exd.delete")}</button>` : ""}
    ${e.superseded ? "" : html`<button type="button" class="btn ghost" data-archive="${e.archived ? "0" : "1"}">${raw(icon("archive"))}${t(e.archived ? "exd.unarchive" : "exd.archive")}</button>`}
    ${editable ? html`<button type="button" class="btn primary" data-edit>${raw(icon("pencil"))}${t("sjd.edit")}</button>` : ""}`
    : html`<button type="button" class="btn ghost" data-close>${t("common.close")}</button>`);

  const reopen = async (result, message) => {
    if (message) app.toast(message);
    if (result?.detail) fillEntry(app, dialog, result.detail);
    await refreshAfter(app);
  };
  const body = (extra = {}) => ({ dataset: app.api.dataset, lang: i18n.lang, op_id: app.newOpId(), ...extra });
  dialog.querySelector("[data-edit]")?.addEventListener("click", () => openEntryForm(app, { entry: e, onSaved: reopen }));
  dialog.querySelector("[data-pay]")?.addEventListener("click", () => openEntryPayment(app, e, reopen));
  dialog.querySelector("[data-split]")?.addEventListener("click", () => openSplit(app, e, reopen));
  dialog.querySelector("[data-reconcile]")?.addEventListener("click", () => openReconcile(app, e, reopen));
  wireDocumentsSection(app, dialog, e, reopen);
  dialog.querySelectorAll("[data-unreconcile]").forEach((button) => button.addEventListener("click", () => openConfirm(app, {
    title: t("rec.undoTitle"), text: t("rec.undoText"), confirm: t("rec.undo"), danger: false,
    run: async () => reopen(await app.api.post(`/api/entries/${e.id}/unreconcile`, { entry_id: button.dataset.unreconcile, revision: e.revision }), t("rec.undone")),
  })));
  dialog.querySelectorAll("[data-declare]").forEach((button) => button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      reopen(await app.api.request("PATCH", `/api/entries/${e.id}`, { body: body({ payment_declared: button.dataset.declare, revision: e.revision }) }),
        t("exd.declared"));
    } catch (err) {
      app.toast(err.message, true);
      button.disabled = false;
    }
  }));
  dialog.querySelector("[data-archive]")?.addEventListener("click", (event) => {
    const archive = event.currentTarget.dataset.archive === "1";
    const run = async () => reopen(await app.api.post(`/api/entries/${e.id}/archive`, { archived: archive }), t(archive ? "exd.archived" : "exd.unarchived"));
    if (!archive) {
      run().catch((err) => app.toast(err.message, true));
      return;
    }
    openConfirm(app, { title: t("exd.archiveTitle"), text: t("exd.archiveText"), confirm: t("exd.archive"), danger: false, run });
  });
  dialog.querySelector("[data-delete]")?.addEventListener("click", () => openConfirm(app, {
    title: t("exd.deleteTitle"), text: t("exd.deleteText"), confirm: t("exd.delete"),
    run: async () => {
      await app.api.request("DELETE", `/api/entries/${e.id}`, { body: body() });
      dialog.close();
      app.toast(t("exd.deleted"));
      await refreshAfter(app);
    },
  }));
  dialog.querySelectorAll("[data-payment-delete]").forEach((button) => button.addEventListener("click", () => openConfirm(app, {
    title: t("sjp.deleteTitle"),
    text: t("sjp.deleteText", { amount: i18n.money(Number(button.dataset.amount)), date: i18n.dateLong(button.dataset.date) }),
    confirm: t("sjx.confirm"),
    run: async () => reopen(await app.api.request("DELETE", `/api/payments/${button.dataset.paymentDelete}`, { body: body() }), t("sjp.deleted")),
  })));
  keepFocusInside(dialog);
}

/** After the page of a dialog is redrawn, the keyboard focus stays in it (never lost on the page behind). */
export function keepFocusInside(dialog) {
  if (dialog.open && !dialog.contains(document.activeElement)) dialog.querySelector(".dhead [data-close]")?.focus();
}

// ------------------------------------------------------------------ form

const LINE_KINDS = ["cleaning", "linen", "travel", "other", "discount", "tax", "adjustment"];
const LINE_UNITS = ["hour", "flat", "set", "unit", "km", "trip"];

/** One service line of a detailed invoice (the server checks again that the lines add up to the amount). */
function lineRow(t, line = {}, index = 0) {
  const qty = line.quantity ?? "";
  return html`
    <div class="svc-line" data-line="${line.id || `n${index}`}">
      <div class="field f-kind"><label for="rc-l-kind-${index}">${t("svc.kind")}</label>
        <select id="rc-l-kind-${index}" data-l="kind">${LINE_KINDS.map((k) => html`<option value="${k}" ${raw(k === (line.kind || "cleaning") ? "selected" : "")}>${t(`svc.kind.${k}`)}</option>`)}</select></div>
      <div class="field f-label"><label for="rc-l-label-${index}">${t("svc.label")}</label><input id="rc-l-label-${index}" data-l="label" maxlength="120" autocomplete="off" value="${line.label || ""}"></div>
      <div class="field f-qty"><label for="rc-l-qty-${index}">${t("svc.qty")}</label><input id="rc-l-qty-${index}" data-l="quantity" inputmode="decimal" autocomplete="off" value="${qty}"></div>
      <div class="field f-unit"><label for="rc-l-unit-${index}">${t("svc.unit")}</label>
        <select id="rc-l-unit-${index}" data-l="unit"><option value="">—</option>${LINE_UNITS.map((u) => html`<option value="${u}" ${raw(u === line.unit ? "selected" : "")}>${t(`svc.unit.${u}`)}</option>`)}</select></div>
      <div class="field f-price"><label for="rc-l-price-${index}">${t("svc.price")}</label><input id="rc-l-price-${index}" data-l="unit_price" inputmode="decimal" autocomplete="off" value="${amountValue(line.unit_price_cents)}"></div>
      <div class="field f-amount"><label for="rc-l-amount-${index}">${t("svc.amount")}</label><input id="rc-l-amount-${index}" data-l="amount" inputmode="decimal" autocomplete="off" value="${line.unit_price_cents && qty ? "" : amountValue(line.amount)}"></div>
      <div class="field f-date"><label for="rc-l-date-${index}">${t("svc.date")}</label><input id="rc-l-date-${index}" data-l="intervention_date" type="date" value="${line.intervention_date || ""}"></div>
      <div class="field f-note" data-note-field ${raw(line.kind === "adjustment" || line.note ? "" : "hidden")}><label for="rc-l-note-${index}">${t("svc.note")}</label><input id="rc-l-note-${index}" data-l="note" maxlength="200" autocomplete="off" value="${line.note || ""}"></div>
      <button type="button" class="iconbtn f-del" data-line-remove aria-label="${t("svc.remove")}">${raw(icon("trash"))}</button>
    </div>`;
}

function lineAmount(row) {
  const get = (key) => row.querySelector(`[data-l="${key}"]`).value;
  const typed = toCents(get("amount"));
  const qty = parseFloat(String(get("quantity")).replace(",", "."));
  const price = toCents(get("unit_price"));
  let cents = typed ?? (Number.isFinite(qty) && price !== null ? Math.round(qty * price) : null);
  if (cents !== null && get("kind") === "discount" && cents > 0) cents = -cents;
  return cents;
}

export async function openEntryForm(app, { entry = null, kind = "expense", propertyId = null, supplierId = null, detailed = false, onSaved = null } = {}) {
  const { i18n } = app;
  const { t } = i18n;
  kind = entry?.kind || kind;
  const income = kind === "income";
  let meta = app.state.entries.data;
  if (!meta?.categories) {
    try { meta = await app.api.get("/api/entries", { view: "archived" }); } catch (err) { app.toast(err.message, true); return; }
  }
  const props = (app.viewModel().properties || []).filter((p) => !p.archived || p.id === entry?.property_id);
  const categories = meta.categories.filter((c) => c.kind === kind && (!c.archived || c.id === entry?.category_id));
  const suppliers = (meta.suppliers || []).filter((s) => !s.archived || s.id === entry?.supplier_id);
  const chosen = entry?.property_id || propertyId || (app.state.propertyId !== "all" ? app.state.propertyId : props[0]?.id);
  const groups = [...new Set(categories.map((c) => c.treatment))];
  const split = entry?.loan_split || {};
  const today = app.session.today;
  const supplierChosen = entry?.supplier_id || supplierId || "";
  const supplierCategory = suppliers.find((sp) => sp.id === supplierChosen)?.categories?.[0];
  const initialLines = entry?.service_lines || [];
  const dialog = openDialog(app, {
    title: t(entry ? (income ? "exf.titleEditIncome" : "exf.titleEdit") : (income ? "exf.titleNewIncome" : supplierId ? "exf.titleInvoice" : "exf.titleNew")),
    subtitle: !entry && supplierId ? t("exf.subInvoice", { name: suppliers.find((sp) => sp.id === supplierId)?.name || "" }) : t(income ? "exf.subIncome" : "exf.sub"),
    wide: true,
    body: html`
      <form class="form-grid" novalidate>
        <div class="field"><label for="rc-e-prop">${t("sjf.property")}</label>
          <select id="rc-e-prop" name="property_id" ${raw(entry ? "disabled" : "")}>${props.map((p) => html`<option value="${p.id}" ${raw(p.id === chosen ? "selected" : "")}>${p.name}</option>`)}</select></div>
        <div class="field"><label for="rc-e-cat">${t("exf.category")}</label>
          <select id="rc-e-cat" name="category_id">${groups.map((g) => html`<optgroup label="${categories.find((c) => c.treatment === g).treatment_label}">
            ${categories.filter((c) => c.treatment === g).map((c) => html`<option value="${c.id}" data-treatment="${c.treatment}" ${raw(c.id === (entry?.category_id || supplierCategory || (income ? "other_income" : "other_expense")) ? "selected" : "")}>${c.label}</option>`)}
          </optgroup>`)}</select>
          <span class="help" data-treatment-note></span></div>
        <div class="field wide"><label for="rc-e-label">${t("exf.label")}</label><input id="rc-e-label" name="label" required maxlength="140" autocomplete="off" value="${entry?.label || ""}" placeholder="${t(income ? "exf.labelPhIncome" : "exf.labelPh")}"></div>
        <div class="field"><label for="rc-e-amount">${t("exf.amount")}</label><input id="rc-e-amount" name="amount" required inputmode="decimal" autocomplete="off" value="${amountValue(entry?.amount)}" aria-describedby="rc-e-amount-h"><span class="help" id="rc-e-amount-h">${t("exf.amountHelp")}</span></div>
        <div class="field"><label for="rc-e-date">${t(income ? "exf.dateIncome" : "exf.date")}</label><input id="rc-e-date" name="date" type="date" required value="${entry?.date || today}" aria-describedby="rc-e-date-h"><span class="help" id="rc-e-date-h">${t("exf.dateHelp")}</span></div>
        ${entry ? "" : html`
          <fieldset class="wide amounts pay-choice">
            <legend>${t("exf.payment")}</legend>
            <div class="choice-row" role="radiogroup">
              ${["paid", "unpaid", "unknown"].map((k) => html`<label class="pay-option"><input type="radio" name="payment" value="${k}" ${raw(k === "unknown" ? "checked" : "")}><span>${t(`exf.pay.${income ? "in" : "out"}.${k}`)}</span></label>`)}
            </div>
            <div class="form-grid" data-paid-fields hidden>
              <div class="field"><label for="rc-e-paydate">${t("exf.paidDate")}</label><input id="rc-e-paydate" name="paid_date" type="date" value="${today}"></div>
              <div class="field"><label for="rc-e-method">${t("sjp.method")}</label><input id="rc-e-method" name="payment_method" maxlength="40" autocomplete="off" placeholder="${t("sjp.methodPh")}"></div>
            </div>
            <p class="reading" data-pay-help></p>
          </fieldset>`}
        <fieldset class="wide amounts" data-split hidden>
          <legend>${t("exf.split")}</legend>
          <div class="form-grid three">
            ${["principal", "interest", "insurance"].map((k) => html`<div class="field"><label for="rc-e-${k}">${t(`exf.${k}`)}</label><input id="rc-e-${k}" name="${k}" inputmode="decimal" autocomplete="off" value="${amountValue(split[k])}"></div>`)}
          </div>
          <p class="reading" data-split-help>${t("exf.splitHelp")}</p>
        </fieldset>
        ${suppliers.length ? html`<div class="field"><label for="rc-e-sup">${t("exf.supplier")}</label>
          <select id="rc-e-sup" name="supplier_id"><option value="">—</option>${suppliers.map((s) => html`<option value="${s.id}" ${raw(s.id === supplierChosen ? "selected" : "")}>${s.name}</option>`)}</select></div>` : ""}
        <div class="field"><label for="rc-e-inv">${t("exf.invoice")}</label><input id="rc-e-inv" name="invoice_number" maxlength="80" autocomplete="off" value="${entry?.invoice_number || ""}"></div>
        <div class="field"><label for="rc-e-stay">${t("exf.stay")}</label><select id="rc-e-stay" name="stay_id"><option value="">—</option></select><span class="help">${t("exf.stayHelp")}</span></div>
        ${income ? "" : html`<div class="wide">
          <label class="check-line"><input type="checkbox" name="detailed" ${raw(initialLines.length || detailed ? "checked" : "")}><span>${t("svc.detail")}<small>${t("svc.detailHelp")}</small></span></label>
          <div class="svc-lines" data-lines ${raw(initialLines.length || detailed ? "" : "hidden")}>
            <div data-line-rows>${(initialLines.length ? initialLines : [{}]).map((line, index) => lineRow(t, line, index))}</div>
            <div class="svc-foot"><button type="button" class="btn ghost small" data-line-add>${raw(icon("plus"))}${t("svc.add")}</button><p class="reading" data-lines-total></p></div>
          </div>
        </div>`}
        <div class="wide">
          <label class="check-line"><input type="checkbox" name="has_period" ${raw(entry?.period_start ? "checked" : "")}><span>${t("exf.period")}<small>${t("exf.periodHelp")}</small></span></label>
          <div class="form-grid" data-period ${raw(entry?.period_start ? "" : "hidden")}>
            <div class="field"><label for="rc-e-ps">${t("exf.periodStart")}</label><input id="rc-e-ps" name="period_start" type="date" value="${entry?.period_start || ""}"></div>
            <div class="field"><label for="rc-e-pe">${t("exf.periodEnd")}</label><input id="rc-e-pe" name="period_end" type="date" value="${entry?.period_end || ""}"></div>
          </div>
        </div>
        ${entry ? "" : html`<div class="wide">
          <label class="check-line"><input type="checkbox" name="repeat"><span>${t("exf.repeat")}<small>${t("exf.repeatHelp")}</small></span></label>
          <div class="form-grid" data-repeat hidden>
            <div class="field"><label for="rc-e-months">${t("exf.months")}</label><input id="rc-e-months" name="repeat_months" type="number" min="2" max="36" inputmode="numeric" value="12"></div>
            <p class="reading" data-repeat-help></p>
          </div>
        </div>`}
        <div class="field wide"><label for="rc-e-note">${t("sjd.note")}</label><textarea id="rc-e-note" name="note" rows="2" maxlength="600">${entry?.note || ""}</textarea></div>
        <div class="wide" data-error aria-live="assertive"></div>
      </form>`,
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.cancel")}</button><button type="button" class="btn primary" data-save>${raw(icon("check"))}${t("exf.save")}</button>`,
  });
  const form = dialog.querySelector("form");
  const save = dialog.querySelector("[data-save]");
  const errorEl = dialog.querySelector("[data-error]");
  const op = app.newOpId();
  let stays = [];

  const loadStays = async () => {
    const pid = form.property_id.value;
    try {
      stays = (await app.api.get("/api/stays", { view: "all", property_id: pid })).stays.filter((s) => s.status !== "cancelled");
    } catch (_) { stays = []; }
    fillStays();
  };
  const fillStays = () => {
    const select = form.stay_id;
    const day = form.date.value;
    const near = stays.filter((s) => s.id === entry?.stay_id || !day || (s.end >= addDays(day, -45) && s.start <= addDays(day, 45)));
    select.innerHTML = markup(html`<option value="">—</option>${near.map((s) => html`<option value="${s.id}" ${raw(s.id === (select.dataset.value ?? entry?.stay_id) ? "selected" : "")}>${s.guest_label || s.external_ref || i18n.range(s.start, s.end)} · ${i18n.range(s.start, s.end)}</option>`)}`);
  };
  form.stay_id.addEventListener("change", () => { form.stay_id.dataset.value = form.stay_id.value; });

  let lineCount = Math.max(initialLines.length, 1);
  const lineRows = () => [...dialog.querySelectorAll("[data-line-rows] .svc-line")];
  const supplierRates = () => (suppliers.find((sp) => sp.id === form.supplier_id?.value)?.rates || []);
  dialog.querySelector("[data-line-add]")?.addEventListener("click", () => {
    dialog.querySelector("[data-line-rows]").insertAdjacentHTML("beforeend", markup(lineRow(t, { intervention_date: lineRows().at(-1)?.querySelector('[data-l="intervention_date"]').value || "" }, lineCount)));
    lineCount += 1;
    lineRows().at(-1)?.querySelector('[data-l="kind"]').focus();
    refresh();
  });
  dialog.querySelector("[data-line-rows]")?.addEventListener("click", (event) => {
    if (!event.target.closest("[data-line-remove]")) return;
    event.target.closest(".svc-line").remove();
    refresh();
  });
  // An indicative rate of the supplier pre-fills the unit price; it is never applied behind the person's back.
  dialog.querySelector("[data-line-rows]")?.addEventListener("change", (event) => {
    const row = event.target.closest(".svc-line");
    if (!row || !["kind", "unit"].includes(event.target.dataset.l)) return;
    const price = row.querySelector('[data-l="unit_price"]');
    const rate = supplierRates().find((r) => r.kind === row.querySelector('[data-l="kind"]').value && r.unit === row.querySelector('[data-l="unit"]').value);
    if (rate && !price.value) {
      price.value = amountValue(rate.unit_price_cents);
      price.title = t("svc.rateUsed");
    }
    refresh();
  });

  const refresh = () => {
    const option = form.category_id.selectedOptions[0];
    const treatment = option?.dataset.treatment || "";
    dialog.querySelector("[data-treatment-note]").textContent = t(TREATMENT_NOTE[treatment] || "exf.treat.operating_expense");
    dialog.querySelector("[data-split]").hidden = treatment !== "financing";
    dialog.querySelector("[data-period]").hidden = !form.has_period.checked;
    const amount = toCents(form.amount.value);
    if (treatment === "financing") {
      const parts = ["principal", "interest", "insurance"].map((k) => toCents(form[k].value));
      const known = parts.filter((p) => p !== null);
      const helpEl = dialog.querySelector("[data-split-help]");
      helpEl.textContent = known.length === 3 && amount !== null
        ? t(known.reduce((a, b) => a + b, 0) === amount ? "exf.splitOk" : "exf.splitOff", { split: i18n.money(known.reduce((a, b) => a + b, 0)), total: i18n.money(amount) })
        : t("exf.splitHelp");
      helpEl.classList.toggle("bad", known.length === 3 && amount !== null && known.reduce((a, b) => a + b, 0) !== amount);
    }
    if (form.detailed) {
      dialog.querySelector("[data-lines]").hidden = !form.detailed.checked;
      const amounts = lineRows().map(lineAmount);
      const totalEl = dialog.querySelector("[data-lines-total]");
      for (const [index, row] of lineRows().entries()) {
        const input = row.querySelector('[data-l="amount"]');
        input.placeholder = amounts[index] !== null && !input.value ? amountValue(Math.abs(amounts[index])) : "";
      }
      for (const row of lineRows()) {
        const note = row.querySelector("[data-note-field]");
        note.hidden = row.querySelector('[data-l="kind"]').value !== "adjustment" && !row.querySelector('[data-l="note"]').value;
      }
      const sum = amounts.reduce((acc, value) => acc + (value || 0), 0);
      const empty = amount === null && amounts.every((value) => value === null);
      const ok = amount !== null && sum === amount;
      totalEl.textContent = !form.detailed.checked ? "" : empty ? t("svc.totalHelp")
        : t(ok ? "svc.totalOk" : "svc.totalOff", { lines: i18n.money(sum), total: i18n.money(amount ?? 0), diff: i18n.money(Math.abs((amount ?? 0) - sum)) });
      totalEl.classList.toggle("bad", form.detailed.checked && !empty && !ok);
    }
    if (!entry) {
      const pay = form.payment.value;
      dialog.querySelector("[data-paid-fields]").hidden = pay !== "paid";
      const repeat = form.repeat.checked;
      dialog.querySelector("[data-repeat]").hidden = !repeat;
      dialog.querySelector("[data-pay-help]").textContent = t(`exf.payHelp.${pay}${repeat && pay === "paid" ? "Series" : ""}`);
      if (repeat) {
        const months = Math.min(Math.max(parseInt(form.repeat_months.value, 10) || 0, 0), 36);
        const last = form.date.value && months >= 2 ? addMonths(form.date.value, months - 1) : "";
        dialog.querySelector("[data-repeat-help]").textContent = last && amount !== null
          ? t("exf.repeatSummary", { n: months, amount: i18n.money(amount), last: i18n.dateLong(last), total: i18n.money(amount * months) }) : "";
      }
    }
  };
  form.addEventListener("input", (event) => {
    if (event.target.name === "date") fillStays();
    refresh();
  });
  form.addEventListener("change", (event) => {
    if (event.target.name === "property_id") loadStays();
    refresh();
  });
  refresh();
  loadStays();

  const submit = async () => {
    const data = Object.fromEntries(new FormData(form).entries());
    const treatment = form.category_id.selectedOptions[0]?.dataset.treatment;
    const body = {
      category_id: data.category_id, label: data.label.trim(), amount: cleanAmount(data.amount), date: data.date,
      invoice_number: data.invoice_number.trim(), note: data.note, stay_id: data.stay_id || "",
      period_start: form.has_period.checked ? data.period_start : "", period_end: form.has_period.checked ? data.period_end : "",
    };
    if (form.supplier_id) body.supplier_id = data.supplier_id || "";
    if (form.detailed?.checked) {
      body.lines = lineRows().map((row) => {
        const get = (key) => row.querySelector(`[data-l="${key}"]`).value.trim();
        const line = { kind: get("kind"), label: get("label"), quantity: get("quantity"), unit: get("unit"),
                       unit_price: cleanAmount(get("unit_price")), amount: cleanAmount(get("amount")), intervention_date: get("intervention_date"), note: get("note") };
        if (!row.dataset.line.startsWith("n")) line.id = row.dataset.line;  // keeps the split between stays of an existing line
        return line;
      });
    } else if (entry?.service_lines?.length) {
      body.lines = [];
    }
    if (treatment === "financing") {
      const parts = Object.fromEntries(["principal", "interest", "insurance"].map((k) => [k, cleanAmount(data[k])]));
      body.loan_split = Object.values(parts).some(Boolean) ? parts : null;
    } else if (entry?.loan_split) {
      body.loan_split = null;
    }
    if (!entry) {
      Object.assign(body, { property_id: data.property_id, kind });
      if (data.payment === "paid") Object.assign(body, { paid: true, paid_date: data.paid_date || data.date, payment_method: data.payment_method.trim() });
      else body.payment_declared = data.payment;
      if (form.repeat.checked) body.repeat_months = Number(data.repeat_months);
    } else {
      body.revision = entry.revision;
    }
    save.disabled = true;
    errorEl.innerHTML = "";
    try {
      const result = entry
        ? await app.api.request("PATCH", `/api/entries/${entry.id}`, { body: { ...body, dataset: app.api.dataset, lang: i18n.lang, op_id: op } })
        : await app.api.post("/api/entries", { ...body, op_id: op });
      dialog.close();
      const message = result.series ? t("exf.savedSeries", { n: result.series.entries.length }) : t(entry ? "sjf.updated" : "exf.saved");
      if (onSaved) await onSaved(result, message);
      else {
        app.toast(message);
        await refreshAfter(app);
        if (result.detail) openEntry(app, result.detail.id);
      }
    } catch (err) {
      errorEl.innerHTML = errorBox(err.message);
      save.disabled = false;
    }
  };
  save.addEventListener("click", submit);
  form.addEventListener("submit", (event) => { event.preventDefault(); submit(); });
  (entry ? form.label : props.length > 1 ? form.property_id : form.category_id).focus();
}

function addDays(iso, days) {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

function addMonths(iso, months) {
  const [y, m, d] = iso.split("-").map(Number);
  const index = y * 12 + (m - 1) + months;
  const year = Math.floor(index / 12);
  const month = index % 12;
  const last = new Date(Date.UTC(year, month + 1, 0)).getUTCDate();
  return `${year}-${String(month + 1).padStart(2, "0")}-${String(Math.min(d, last)).padStart(2, "0")}`;
}

// ------------------------------------------------------------------ payment

function openEntryPayment(app, entry, onDone) {
  const { i18n } = app;
  const { t } = i18n;
  const income = entry.kind === "income";
  const dialog = openDialog(app, {
    title: t(income ? "exp.titleIn" : "exp.title"),
    subtitle: entry.label,
    body: html`
      <form class="form-grid" novalidate>
        <div class="field"><label for="rc-ep-date">${t("sjp.date")}</label><input id="rc-ep-date" name="date" type="date" required value="${app.session.today}"></div>
        <div class="field"><label for="rc-ep-amount">${t("sjp.amount")}</label><input id="rc-ep-amount" name="amount" inputmode="decimal" autocomplete="off" value="${amountValue(entry.remaining)}" aria-describedby="rc-ep-amount-h">
          <span class="help" id="rc-ep-amount-h">${t(income ? "exp.amountHelpIn" : "exp.amountHelp", { amount: i18n.money(entry.remaining) })}</span></div>
        <div class="field"><label for="rc-ep-method">${t("sjp.method")}</label><input id="rc-ep-method" name="method" maxlength="40" autocomplete="off" placeholder="${t("sjp.methodPh")}"></div>
        <div class="field"><label for="rc-ep-note">${t("sjd.note")}</label><input id="rc-ep-note" name="note" maxlength="300" autocomplete="off"></div>
        <p class="reading wide">${raw(icon("info"))}<span>${t("exp.help")}</span></p>
        <div class="wide" data-error aria-live="assertive"></div>
      </form>`,
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.cancel")}</button><button type="button" class="btn primary" data-save>${raw(icon("check"))}${t("sjp.save")}</button>`,
  });
  const form = dialog.querySelector("form");
  const save = dialog.querySelector("[data-save]");
  const op = app.newOpId();
  const submit = async () => {
    save.disabled = true;
    try {
      const result = await app.api.post(`/api/entries/${entry.id}/payments`, {
        date: form.date.value, amount: cleanAmount(form.amount.value), method: form.method.value.trim(), note: form.note.value.trim(), op_id: op,
      });
      dialog.close();
      await onDone(result, t(income ? "exp.doneIn" : "exp.done"));
    } catch (err) {
      dialog.querySelector("[data-error]").innerHTML = errorBox(err.message);
      save.disabled = false;
    }
  };
  save.addEventListener("click", submit);
  form.addEventListener("submit", (event) => { event.preventDefault(); submit(); });
  form.amount.focus();
}

// ------------------------------------------------------------------ categories (Réglages)

export function openCategoryForm(app, { category = null } = {}) {
  const { t } = app.i18n;
  const treatments = app.state.categories?.treatments || { expense: [], income: [] };
  const dialog = openDialog(app, {
    title: t(category ? "cat.titleEdit" : "cat.titleNew"),
    subtitle: t(category ? "cat.subEdit" : "cat.sub"),
    body: html`
      <form class="form-grid" novalidate>
        ${category ? "" : html`<div class="field"><label for="rc-c-kind">${t("cat.kind")}</label>
          <select id="rc-c-kind" name="kind">${["expense", "income"].map((k) => html`<option value="${k}">${t(`ex.kind.${k}`)}</option>`)}</select></div>`}
        <div class="field ${category ? "wide" : ""}"><label for="rc-c-label">${t("cat.label")}</label>
          <input id="rc-c-label" name="label" maxlength="60" autocomplete="off" value="${category?.custom_label || (category && !category.builtin ? category.label : "")}" placeholder="${category?.default_label || ""}" ${raw(category?.builtin ? "" : "required")}>
          ${category?.builtin ? html`<span class="help">${t("cat.defaultHelp", { label: category.default_label })}</span>` : ""}</div>
        ${category?.builtin ? "" : html`<div class="field wide"><label for="rc-c-treat">${t("cat.treatment")}</label><select id="rc-c-treat" name="treatment"></select><span class="help" data-treatment-note></span></div>`}
        <div class="wide" data-error aria-live="assertive"></div>
      </form>`,
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.cancel")}</button><button type="button" class="btn primary" data-save>${raw(icon("check"))}${t("cat.save")}</button>`,
  });
  const form = dialog.querySelector("form");
  const save = dialog.querySelector("[data-save]");
  const op = app.newOpId();
  const fillTreatments = () => {
    if (!form.treatment) return;
    const kind = category?.kind || form.kind.value;
    const current = category?.treatment || form.treatment.value;
    form.treatment.innerHTML = markup(html`${treatments[kind].map((tr) => html`<option value="${tr.id}" ${raw(tr.id === current ? "selected" : "")}>${tr.label}</option>`)}`);
    dialog.querySelector("[data-treatment-note]").textContent = t(TREATMENT_NOTE[form.treatment.value] || "exf.treat.operating_expense");
  };
  form.addEventListener("change", fillTreatments);
  fillTreatments();
  const submit = async () => {
    const data = Object.fromEntries(new FormData(form).entries());
    save.disabled = true;
    try {
      const result = category
        ? await app.api.request("PATCH", `/api/categories/${category.id}`, { body: { label: data.label.trim(), ...(data.treatment ? { treatment: data.treatment } : {}), dataset: app.api.dataset, lang: app.i18n.lang, op_id: op } })
        : await app.api.post("/api/categories", { kind: data.kind, treatment: data.treatment, label: data.label.trim(), op_id: op });
      dialog.close();
      app.toast(t(category ? "cat.updated" : "cat.created"));
      await app.afterCategoryChange(result.categories);
    } catch (err) {
      dialog.querySelector("[data-error]").innerHTML = errorBox(err.message);
      save.disabled = false;
    }
  };
  save.addEventListener("click", submit);
  form.addEventListener("submit", (event) => { event.preventDefault(); submit(); });
  form.label.focus();
}

export async function toggleCategory(app, category) {
  const { t } = app.i18n;
  try {
    const result = await app.api.request("PATCH", `/api/categories/${category.id}`,
      { body: { archived: !category.archived, dataset: app.api.dataset, lang: app.i18n.lang, op_id: app.newOpId() } });
    app.toast(t(category.archived ? "cat.restored" : "cat.archivedDone"));
    await app.afterCategoryChange(result.categories);
  } catch (err) {
    app.toast(err.message, true);
  }
}
