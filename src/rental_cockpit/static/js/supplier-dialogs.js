/* Copyright © 2026 Vincent Fournet */
// Supplier page and form. Rates are indicative: they pre-fill a service line
// of an invoice, they are never applied to an amount behind the person's back.

import { openConfirm, openDialog } from "./dialogs.js";
import { html, markup, raw } from "./dom.js";
import { openEntryForm } from "./entry-dialogs.js";
import { icon } from "./icons.js";
import { entryStatePill } from "./views/expenses.js";

const KINDS = ["cleaning", "linen", "travel", "other"];
const UNITS = ["hour", "flat", "set", "unit", "km", "trip"];

function cleanAmount(value) {
  return String(value ?? "").replace(/[\s  €]/g, "");
}

function amountValue(cents) {
  if (cents === null || cents === undefined) return "";
  return (cents / 100).toFixed(2).replace(".", ",").replace(",00", "");
}

function errorBox(message) {
  return markup(html`<div class="error-box" role="alert">${raw(icon("alert"))}<span>${message}</span></div>`);
}

// ------------------------------------------------------------------ page

export async function openSupplier(app, supplierId) {
  const { t } = app.i18n;
  const dialog = openDialog(app, {
    title: t("sup.title"),
    body: html`<div class="loading small"><div class="spinner"></div><span>${t("common.loading")}</span></div>`,
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.close")}</button>`,
    wide: true,
    labelledby: "rc-supplier-title",
  });
  dialog.addEventListener("click", (event) => {
    if (event.target.closest('[data-action="go"]')) dialog.close();
  });
  await fillSupplier(app, dialog, supplierId);
}

async function fillSupplier(app, dialog, supplierId) {
  const { i18n } = app;
  const { t } = i18n;
  let s;
  let entries;
  try {
    [s, entries] = await Promise.all([
      app.api.get(`/api/suppliers/${encodeURIComponent(supplierId)}`),
      app.api.get("/api/entries", { supplier_id: supplierId, view: "all" }),
    ]);
  } catch (err) {
    dialog.querySelector(".dbody").innerHTML = errorBox(err.message);
    return;
  }
  const canWrite = app.canWrite;
  dialog.querySelector(".dhead h2").textContent = s.name;
  const head = dialog.querySelector(".dhead div");
  head.querySelector("p")?.remove();
  if (s.role) head.insertAdjacentHTML("beforeend", markup(html`<p>${s.role}</p>`));
  dialog.querySelector(".dbody").innerHTML = markup(html`
    ${s.archived ? html`<div class="tip">${raw(icon("archive"))}<div><p>${t("sup.archivedNote")}</p></div></div>` : ""}
    <dl class="totals">
      <div><dt>${t("sup.yearLabel", { year: s.year })}</dt><dd class="num">${i18n.money(s.year_total)}</dd></div>
      <div class="${s.to_pay ? "warn" : ""}"><dt>${t("ex.total.toPay")}</dt><dd class="num">${i18n.money(s.to_pay)}</dd></div>
      ${s.unallocated ? html`<div class="warn"><dt>${t("sup.leftToSplit")}</dt><dd class="num">${i18n.money(s.unallocated)}</dd></div>` : ""}
    </dl>
    <section>
      <h3 class="section-title">${t("sup.rates")}</h3>
      ${s.rates.length ? html`<div class="rows">${s.rates.map((r) => html`
        <div class="keyrow"><span class="tile">${raw(icon("tag"))}</span>
          <span><b>${r.label || r.kind_label}</b><small>${r.label ? `${r.kind_label} · ` : ""}${t("sup.per", { unit: r.unit_label })}</small></span>
          <b class="num">${i18n.money(r.unit_price_cents)}</b></div>`)}</div>
        <p class="reading">${raw(icon("info"))}<span>${t("sup.ratesNote")}</span></p>`
        : html`<div class="empty">${raw(icon("info"))}<span>${t("sup.noRate")}</span></div>`}
    </section>
    <section>
      <h3 class="section-title">${t("sup.invoices")} <span class="count">(${entries.entries.length + (entries.more || 0)})</span></h3>
      ${entries.entries.length ? html`<div class="rows">${entries.entries.slice(0, 30).map((e) => html`
        <button type="button" class="keyrow clickable" data-action="entry-open" data-value="${e.id}">
          <span class="tile">${raw(icon("receipt"))}</span>
          <span><b>${e.label}</b><small class="num">${i18n.dateShort(e.date)} · ${e.category}${e.lines ? ` · ${i18n.plural(e.lines, "sup.lineOne", "sup.lineMany")}` : ""}</small></span>
          <span class="end-col"><b class="num">${i18n.money(e.amount)}</b>${entryStatePill(e, t)}</span>
        </button>`)}</div>
        <button type="button" class="linkbtn" data-action="go" data-value="depenses" data-q="${s.name}">${entries.entries.length + (entries.more || 0) > 30
          ? t("sup.seeAllMore", { n: entries.entries.length + (entries.more || 0) }) : t("sup.seeAll")}${raw(icon("chevronRight"))}</button>`
        : html`<div class="empty">${raw(icon("receipt"))}<span>${t("sup.noInvoiceYet")}</span></div>`}
    </section>
    <section>
      <h3 class="section-title">${t("sjd.about")}</h3>
      <dl class="facts-list">
        <div><dt>${t("sup.categories")}</dt><dd>${s.categories.map((c) => c.label).join(", ") || "—"}</dd></div>
        ${s.contact ? html`<div><dt>${t("sup.contact")}</dt><dd class="pre">${s.contact}</dd></div>` : ""}
        ${s.note ? html`<div><dt>${t("sjd.note")}</dt><dd class="pre">${s.note}</dd></div>` : ""}
      </dl>
    </section>`);
  const foot = dialog.querySelector(".dfoot");
  foot.classList.toggle("stay-actions", canWrite);
  foot.innerHTML = markup(canWrite ? html`
    <button type="button" class="btn ghost del" data-archive="${s.archived ? "0" : "1"}">${raw(icon(s.archived ? "repeat" : "archive"))}${t(s.archived ? "sup.restore" : "sup.archive")}</button>
    <button type="button" class="btn ghost" data-edit>${raw(icon("pencil"))}${t("sjd.edit")}</button>
    ${s.archived ? "" : html`<button type="button" class="btn primary" data-invoice>${raw(icon("plus"))}${t("sup.newInvoice")}</button>`}`
    : html`<button type="button" class="btn ghost" data-close>${t("common.close")}</button>`);
  const after = async (message) => {
    if (message) app.toast(message);
    await fillSupplier(app, dialog, supplierId);
    await app.afterSupplierChange();
  };
  dialog.querySelector("[data-edit]")?.addEventListener("click", () => openSupplierForm(app, { supplier: s, onSaved: () => after(t("sup.updated")) }));
  dialog.querySelector("[data-invoice]")?.addEventListener("click", () => {
    dialog.close();
    openEntryForm(app, { kind: "expense", supplierId: s.id, detailed: true });
  });
  dialog.querySelector("[data-archive]")?.addEventListener("click", (event) => {
    const archive = event.currentTarget.dataset.archive === "1";
    const run = async () => {
      await app.api.post(`/api/suppliers/${s.id}/archive`, { archived: archive });
      await after(t(archive ? "sup.archivedDone" : "sup.restored"));
    };
    if (!archive) {
      run().catch((err) => app.toast(err.message, true));
      return;
    }
    openConfirm(app, { title: t("sup.archiveTitle"), text: t("sup.archiveText"), confirm: t("sup.archive"), danger: false, run });
  });
}

// ------------------------------------------------------------------ form

function rateRow(t, rate = {}, index = 0) {
  return html`
    <div class="rate-line" data-rate>
      <div class="field"><label for="rc-r-kind-${index}">${t("svc.kind")}</label>
        <select id="rc-r-kind-${index}" data-r="kind">${KINDS.map((k) => html`<option value="${k}" ${raw(k === (rate.kind || "cleaning") ? "selected" : "")}>${t(`svc.kind.${k}`)}</option>`)}</select></div>
      <div class="field"><label for="rc-r-unit-${index}">${t("svc.unit")}</label>
        <select id="rc-r-unit-${index}" data-r="unit">${UNITS.map((u) => html`<option value="${u}" ${raw(u === (rate.unit || "hour") ? "selected" : "")}>${t(`svc.unit.${u}`)}</option>`)}</select></div>
      <div class="field"><label for="rc-r-price-${index}">${t("svc.price")}</label><input id="rc-r-price-${index}" data-r="unit_price" inputmode="decimal" autocomplete="off" value="${amountValue(rate.unit_price_cents)}"></div>
      <div class="field grow"><label for="rc-r-label-${index}">${t("svc.label")}</label><input id="rc-r-label-${index}" data-r="label" maxlength="80" autocomplete="off" value="${rate.label || ""}"></div>
      <button type="button" class="iconbtn" data-rate-remove aria-label="${t("svc.remove")}">${raw(icon("trash"))}</button>
    </div>`;
}

export async function openSupplierForm(app, { supplier = null, onSaved = null } = {}) {
  const { t } = app.i18n;
  let meta = app.state.suppliers?.data;
  if (!meta?.categories) {
    try { meta = await app.api.get("/api/suppliers"); } catch (err) { app.toast(err.message, true); return; }
  }
  const chosen = new Set((supplier?.categories || []).map((c) => c.id));
  const dialog = openDialog(app, {
    title: t(supplier ? "sup.formEdit" : "sup.formNew"),
    subtitle: t("sup.formSub"),
    wide: true,
    body: html`
      <form class="form-grid" novalidate>
        <div class="field"><label for="rc-sp-name">${t("sup.name")}</label><input id="rc-sp-name" name="name" required maxlength="120" autocomplete="off" value="${supplier?.name || ""}"></div>
        <div class="field"><label for="rc-sp-role">${t("sup.role")}</label><input id="rc-sp-role" name="role" maxlength="120" autocomplete="off" value="${supplier?.role || ""}" placeholder="${t("sup.rolePh")}"></div>
        <fieldset class="wide amounts">
          <legend>${t("sup.categories")}</legend>
          <div class="check-grid">${meta.categories.map((c) => html`<label class="check-line"><input type="checkbox" name="categories" value="${c.id}" ${raw(chosen.has(c.id) ? "checked" : "")}><span>${c.label}</span></label>`)}</div>
          <p class="reading">${t("sup.categoriesHelp")}</p>
        </fieldset>
        <fieldset class="wide amounts">
          <legend>${t("sup.rates")}</legend>
          <div data-rates>${(supplier?.rates || []).map((r, i) => rateRow(t, r, i))}</div>
          <div class="svc-foot"><button type="button" class="btn ghost small" data-rate-add>${raw(icon("plus"))}${t("sup.addRate")}</button></div>
          <p class="reading">${t("sup.ratesNote")}</p>
        </fieldset>
        <div class="field wide"><label for="rc-sp-contact">${t("sup.contact")}</label><textarea id="rc-sp-contact" name="contact" rows="2" maxlength="240">${supplier?.contact || ""}</textarea><span class="help">${t("sup.contactHelp")}</span></div>
        <div class="field wide"><label for="rc-sp-note">${t("sjd.note")}</label><textarea id="rc-sp-note" name="note" rows="2" maxlength="600">${supplier?.note || ""}</textarea></div>
        <div class="wide" data-error aria-live="assertive"></div>
      </form>`,
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.cancel")}</button><button type="button" class="btn primary" data-save>${raw(icon("check"))}${t("sup.save")}</button>`,
  });
  const form = dialog.querySelector("form");
  const save = dialog.querySelector("[data-save]");
  const op = app.newOpId();
  let count = supplier?.rates?.length || 0;
  dialog.querySelector("[data-rate-add]").addEventListener("click", () => {
    dialog.querySelector("[data-rates]").insertAdjacentHTML("beforeend", markup(rateRow(t, {}, count)));
    count += 1;
    dialog.querySelector("[data-rate]:last-child select").focus();
  });
  dialog.querySelector("[data-rates]").addEventListener("click", (event) => {
    event.target.closest("[data-rate-remove]")?.closest("[data-rate]").remove();
  });
  const submit = async () => {
    const body = {
      name: form.name.value.trim(), role: form.role.value.trim(), contact: form.contact.value, note: form.note.value,
      categories: [...form.querySelectorAll("input[name=categories]:checked")].map((input) => input.value),
      rates: [...dialog.querySelectorAll("[data-rate]")].map((row) => ({
        kind: row.querySelector("[data-r=kind]").value, unit: row.querySelector("[data-r=unit]").value,
        unit_price: cleanAmount(row.querySelector("[data-r=unit_price]").value), label: row.querySelector("[data-r=label]").value.trim(),
      })),
    };
    save.disabled = true;
    try {
      const result = supplier
        ? await app.api.request("PATCH", `/api/suppliers/${supplier.id}`, { body: { ...body, revision: supplier.revision, dataset: app.api.dataset, lang: app.i18n.lang, op_id: op } })
        : await app.api.post("/api/suppliers", { ...body, op_id: op });
      dialog.close();
      if (onSaved) await onSaved(result);
      else {
        app.toast(t("sup.created", { name: result.detail.name }));
        await app.afterSupplierChange();
        openSupplier(app, result.detail.id);
      }
    } catch (err) {
      dialog.querySelector("[data-error]").innerHTML = errorBox(err.message);
      save.disabled = false;
    }
  };
  save.addEventListener("click", submit);
  form.addEventListener("submit", (event) => { event.preventDefault(); submit(); });
  form.name.focus();
}
