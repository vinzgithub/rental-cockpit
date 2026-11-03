/* Copyright © 2026 Vincent Fournet */
// « Justificatifs » : add a PDF to an expense, create an expense from an invoice,
// and the page of a document. The server checks the PDF (format, size, active
// content), keeps the original private with its SHA-256 and writes nothing
// before the person confirms. Joining or detaching a PDF never changes an expense.

import { openConfirm, openDialog } from "./dialogs.js";
import { html, markup, raw } from "./dom.js";
import { openEntry } from "./entry-dialogs.js";
import { icon } from "./icons.js";

function errorBox(message) {
  return markup(html`<div class="error-box" role="alert">${raw(icon("alert"))}<span>${message}</span></div>`);
}

function cleanAmount(value) {
  return String(value ?? "").replace(/[\s  €]/g, "");
}

function amountValue(cents) {
  if (cents === null || cents === undefined) return "";
  return (cents / 100).toFixed(2).replace(".", ",").replace(",00", "");
}

const MAX_BYTES = 8 * 1024 * 1024;

/** The file picker of both flows: a PDF chosen or dropped, checked by the server. */
function dropzone(t, chosen) {
  return html`
    <label class="dropzone ${chosen ? "has-file" : ""}" data-drop>
      <input type="file" class="sr-only" accept="application/pdf,.pdf" data-pdf>
      <span class="tile">${raw(icon(chosen ? "file" : "upload"))}</span>
      <span><b>${chosen || t("doc.choose")}</b><small>${t("doc.drop")}</small></span>
    </label>
    <p class="reading">${raw(icon("shieldCheck"))}<span>${t("doc.safe")}</span></p>`;
}

function wireDrop(dialog, onFile) {
  const zone = () => dialog.querySelector("[data-drop]");
  dialog.addEventListener("change", (event) => {
    if (event.target.matches("[data-pdf]")) onFile(event.target.files?.[0]);
  });
  dialog.addEventListener("dragover", (event) => {
    if (!zone()) return;
    event.preventDefault();
    zone().classList.add("over");
  });
  dialog.addEventListener("dragleave", (event) => {
    if (!dialog.contains(event.relatedTarget)) zone()?.classList.remove("over");
  });
  dialog.addEventListener("drop", (event) => {
    if (!zone()) return;
    event.preventDefault();
    zone().classList.remove("over");
    onFile(event.dataTransfer?.files?.[0]);
  });
}

function fileCard(app, checked, attach = false) {
  const { i18n } = app;
  const { t } = i18n;
  return html`
    <div class="imp-file">
      <span class="tile">${raw(icon("file"))}</span>
      <span><b>${checked.filename}</b><small class="num">${i18n.plural(checked.pages, "doc.pageOne", "doc.pageMany")} · ${i18n.size(checked.size)} · ${t("doc.checked")}</small></span>
      <button type="button" class="btn ghost small" data-change-file>${raw(icon("repeat"))}${t("doc.changeFile")}</button>
    </div>
    ${checked.text_found ? "" : html`<div class="tip">${raw(icon("info"))}<div><p>${t(attach ? "doc.noTextAttach" : "doc.noText")}</p></div></div>`}`;
}

/** Existing documents or expenses the invoice may duplicate, with a way to open them (UX 06). */
function duplicatesBox(app, dups, { blocking = true } = {}) {
  const { i18n } = app;
  const { t } = i18n;
  const line = (d) => html`
    <li><span>${d.reason_label} · <b>${d.label}</b>${d.date ? ` · ${i18n.dateShort(d.date)}` : ""}${d.amount !== null && d.amount !== undefined ? ` · ${i18n.money(d.amount)}` : ""}${d.property ? ` · ${d.property}` : ""}${d.archived ? ` · ${t("doc.dupArchived")}` : ""}</span>
      ${d.entry_id ? html`<button type="button" class="linkbtn small" data-action="entry-open" data-value="${d.entry_id}">${t("doc.openExpense")}</button>`
        : html`<button type="button" class="linkbtn small" data-open-document="${d.document_id}">${t("doc.openDocument")}</button>`}</li>`;
  return html`
    ${dups.certain.length ? html`<div class="${blocking ? "error-box" : "tip warn"} dup-box" role="alert">${raw(icon("alert"))}<div>
      <p><b>${t(blocking ? "doc.dupCertain" : "doc.dupCertainInfo")}</b></p><ul class="plain-list">${dups.certain.map(line)}</ul></div></div>` : ""}
    ${dups.probable.length ? html`<div class="tip warn dup-box">${raw(icon("help"))}<div>
      <p><b>${t("doc.dupProbable")}</b></p><ul class="plain-list">${dups.probable.map(line)}</ul>
      ${blocking ? html`<label class="check-line"><input type="checkbox" data-confirm-probable><span>${t("doc.dupConfirm")}</span></label>` : ""}</div></div>` : ""}`;
}

async function sendPdf(app, file, query) {
  const { t } = app.i18n;
  if (!file) return null;
  if (file.size > MAX_BYTES) throw new Error(t("doc.tooLarge"));
  return app.api.upload("/api/documents/preview", file, query);
}

// ------------------------------------------------------------------ « Ajouter un justificatif à cette dépense »

export function openAttach(app, entry, onDone) {
  const { i18n } = app;
  const { t } = i18n;
  const s = { checked: null, busy: false, error: "" };
  const op = app.newOpId();
  const dialog = openDialog(app, {
    title: t("doc.attachTitle"),
    subtitle: `${entry.label} · ${i18n.money(entry.amount)} · ${i18n.dateShort(entry.date)}`,
    wide: true,
    body: "",
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.cancel")}</button><button type="button" class="btn primary" data-save disabled>${raw(icon("link"))}${t("doc.attach")}</button>`,
  });
  const save = dialog.querySelector("[data-save]");

  const render = () => {
    const c = s.checked;
    let body;
    if (!c) {
      body = html`${dropzone(t, "")}${s.busy ? html`<div class="loading small"><div class="spinner"></div><span>${t("doc.checking")}</span></div>` : ""}`;
    } else if (c.already_attached) {
      body = html`${fileCard(app, c, true)}${raw(errorBox(t("doc.alreadyAttached")))}`;
    } else if (c.existing_document) {
      body = html`${fileCard(app, c, true)}
        <div class="tip">${raw(icon("link"))}<div><p><b>${t("doc.sameFileTitle")}</b></p><p>${t("doc.sameFileText", { list: c.existing_document.entries.map((e) => e.label).join(", ") || t("doc.notLinked") })}</p></div></div>`;
    } else {
      body = html`${fileCard(app, c, true)}
        <p class="reading">${raw(icon("info"))}<span>${t("doc.attachIntro")}</span></p>
        <dl class="facts-list">
          <div><dt>${t("exf.supplier")}</dt><dd>${entry.supplier || "—"}</dd></div>
          <div><dt>${t("exf.invoice")}</dt><dd>${entry.invoice_number || "—"}</dd></div>
          <div><dt>${t("exf.date")}</dt><dd class="num">${i18n.dateLong(entry.date)}</dd></div>
          <div><dt>${t("exd.amount")}</dt><dd class="num">${i18n.money(entry.amount)}</dd></div>
        </dl>
        ${duplicatesBox(app, c.duplicates, { blocking: false })}`;
    }
    dialog.querySelector(".dbody").innerHTML = markup(html`${body}${s.error ? raw(errorBox(s.error)) : ""}`);
    save.disabled = !c || c.already_attached || s.busy;
    save.innerHTML = markup(html`${raw(icon("link"))}${t(c?.existing_document ? "doc.attachSame" : "doc.attach")}`);
  };

  const choose = async (file) => {
    if (!file) return;
    s.busy = true; s.error = ""; render();
    try {
      s.checked = await sendPdf(app, file, { entry_id: entry.id });
    } catch (err) {
      s.error = err.message;
    }
    s.busy = false;
    render();
  };
  wireDrop(dialog, choose);
  dialog.addEventListener("click", (event) => {
    if (event.target.closest("[data-change-file]")) {
      s.checked = null; s.error = ""; render();
    }
    const other = event.target.closest("[data-open-document]");
    if (other) openDocument(app, other.dataset.openDocument);
  });
  save.addEventListener("click", async () => {
    s.busy = true; save.disabled = true;
    try {
      const result = await app.api.post("/api/documents", { token: s.checked.token, mode: "attach", entry_id: entry.id,
        link_existing: Boolean(s.checked.existing_document), op_id: op });
      dialog.close();
      await onDone(result, t("doc.attached"));
    } catch (err) {
      s.busy = false; s.error = err.message; render();
    }
  });
  render();
}

// ------------------------------------------------------------------ « Créer une dépense depuis une facture »

export function openInvoiceImport(app, { propertyId = null, supplierId = null } = {}) {
  const { i18n } = app;
  const { t } = i18n;
  const s = { checked: null, busy: false, error: "", dups: { certain: [], probable: [] }, values: null };
  const op = app.newOpId();
  const dialog = openDialog(app, {
    title: t("doc.importTitle"),
    subtitle: t("doc.importSub"),
    wide: true,
    body: "",
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.cancel")}</button><button type="button" class="btn primary" data-save disabled>${raw(icon("check"))}${t("doc.create")}</button>`,
  });
  const save = dialog.querySelector("[data-save]");
  let meta = app.state.entries.data;
  const ensureMeta = async () => {
    if (!meta?.categories) meta = await app.api.get("/api/entries", { view: "archived" });
    return meta;
  };

  const tag = (key) => (s.suggested?.has(key) ? html`<span class="pill amber tiny">${t("doc.toCheck")}</span>` : "");

  const form = () => {
    const v = s.values;
    const props = (app.viewModel().properties || []).filter((p) => !p.archived);
    const categories = meta.categories.filter((c) => c.kind === "expense" && !c.archived);
    const groups = [...new Set(categories.map((c) => c.treatment))];
    const suppliers = (meta.suppliers || []).filter((sp) => !sp.archived);
    return html`
      <form class="form-grid" novalidate data-form>
        <div class="field"><label for="rc-d-prop">${t("sjf.property")}</label>
          <select id="rc-d-prop" name="property_id">${props.map((p) => html`<option value="${p.id}" ${raw(p.id === v.property_id ? "selected" : "")}>${p.name}</option>`)}</select></div>
        <div class="field"><label for="rc-d-sup">${t("exf.supplier")} ${tag("supplier_id")}</label>
          <select id="rc-d-sup" name="supplier_id"><option value="">—</option>${suppliers.map((sp) => html`<option value="${sp.id}" ${raw(sp.id === v.supplier_id ? "selected" : "")}>${sp.name}</option>`)}</select></div>
        <div class="field"><label for="rc-d-cat">${t("exf.category")}</label>
          <select id="rc-d-cat" name="category_id">${groups.map((g) => html`<optgroup label="${categories.find((c) => c.treatment === g).treatment_label}">
            ${categories.filter((c) => c.treatment === g).map((c) => html`<option value="${c.id}" ${raw(c.id === v.category_id ? "selected" : "")}>${c.label}</option>`)}</optgroup>`)}</select></div>
        <div class="field"><label for="rc-d-inv">${t("exf.invoice")} ${tag("invoice_number")}</label>
          <input id="rc-d-inv" name="invoice_number" maxlength="80" autocomplete="off" value="${v.invoice_number}"></div>
        <div class="field wide"><label for="rc-d-label">${t("exf.label")}</label>
          <input id="rc-d-label" name="label" required maxlength="140" autocomplete="off" value="${v.label}"></div>
        <div class="field"><label for="rc-d-amount">${t("exf.amount")} ${tag("amount")}</label>
          <input id="rc-d-amount" name="amount" required inputmode="decimal" autocomplete="off" value="${v.amount}"></div>
        <div class="field"><label for="rc-d-date">${t("exf.date")} ${tag("invoice_date")}</label>
          <input id="rc-d-date" name="date" type="date" required value="${v.date}"></div>
        <fieldset class="wide amounts pay-choice">
          <legend>${t("exf.payment")}</legend>
          <div class="choice-row" role="radiogroup">
            ${["paid", "unpaid", "unknown"].map((k) => html`<label class="pay-option"><input type="radio" name="payment" value="${k}" ${raw(k === v.payment ? "checked" : "")}><span>${t(`exf.pay.out.${k}`)}</span></label>`)}
          </div>
          <div class="form-grid" data-paid-fields ${raw(v.payment === "paid" ? "" : "hidden")}>
            <div class="field"><label for="rc-d-paydate">${t("exf.paidDate")}</label><input id="rc-d-paydate" name="paid_date" type="date" value="${v.paid_date}"></div>
          </div>
        </fieldset>
      </form>
      <p class="reading">${raw(icon("info"))}<span>${t("doc.afterCreate")}</span></p>`;
  };

  const render = () => {
    const c = s.checked;
    const body = !c
      ? html`${dropzone(t, "")}${s.busy && !c ? html`<div class="loading small"><div class="spinner"></div><span>${t("doc.checking")}</span></div>` : ""}`
      : html`${fileCard(app, c)}
        ${s.suggested?.size ? html`<p class="reading">${raw(icon("eye"))}<span>${t("doc.suggested")}</span></p>` : ""}
        <div data-dups>${duplicatesBox(app, s.dups)}</div>
        ${form()}`;
    dialog.querySelector(".dbody").innerHTML = markup(html`${body}<div data-error aria-live="assertive">${s.error ? raw(errorBox(s.error)) : ""}</div>`);
    refreshSave();
  };

  const refreshSave = () => {
    const probableOk = !s.dups.probable.length || dialog.querySelector("[data-confirm-probable]")?.checked;
    save.disabled = !s.checked || s.busy || s.dups.certain.length > 0 || !probableOk;
  };

  const readForm = () => {
    const f = dialog.querySelector("[data-form]");
    if (!f) return;
    const data = Object.fromEntries(new FormData(f).entries());
    s.values = { ...s.values, ...data };
    f.querySelector("[data-paid-fields]").hidden = data.payment !== "paid";
  };

  let checkTimer = null;
  const recheck = () => {
    clearTimeout(checkTimer);
    checkTimer = setTimeout(async () => {
      const v = s.values;
      try {
        const result = await app.api.post("/api/documents/check", { token: s.checked.token, supplier_id: v.supplier_id,
          invoice_number: v.invoice_number, invoice_date: v.date, amount: cleanAmount(v.amount) });
        s.dups = result.duplicates;
        const box = dialog.querySelector("[data-dups]");
        if (box) box.innerHTML = markup(duplicatesBox(app, s.dups));
        refreshSave();
      } catch (_) { /* the confirmation checks again */ }
    }, 300);
  };

  const choose = async (file) => {
    if (!file) return;
    s.busy = true; s.error = ""; render();
    try {
      await ensureMeta();
      const checked = await sendPdf(app, file, {});
      const found = checked.suggestions || {};
      const supplier = (meta.suppliers || []).find((sp) => sp.id === (found.supplier_id || supplierId));
      const chosenProperty = propertyId || (app.state.propertyId !== "all" ? app.state.propertyId : null)
        || (app.viewModel().properties || []).find((p) => !p.archived)?.id;
      s.suggested = new Set(Object.keys(found));
      s.values = {
        property_id: chosenProperty, supplier_id: supplier?.id || "",
        category_id: supplier?.categories?.[0] || "other_expense",
        invoice_number: found.invoice_number || "",
        label: [t("doc.labelPrefix"), supplier?.name, found.invoice_number].filter(Boolean).join(" "),
        amount: amountValue(found.amount ?? null), date: found.invoice_date || "", payment: "unknown", paid_date: found.invoice_date || app.session.today,
      };
      s.checked = checked;
      s.dups = checked.duplicates;
    } catch (err) {
      s.error = err.message;
    }
    s.busy = false;
    render();
    dialog.querySelector("#rc-d-label")?.focus();
  };
  wireDrop(dialog, choose);
  dialog.addEventListener("input", (event) => {
    if (!event.target.closest("[data-form]")) return;
    readForm();
    if (["supplier_id", "invoice_number", "amount", "date"].includes(event.target.name)) recheck();
  });
  dialog.addEventListener("change", (event) => {
    if (event.target.matches("[data-confirm-probable]")) refreshSave();
    if (!event.target.closest("[data-form]")) return;
    readForm();
    if (event.target.name === "supplier_id") {
      const supplier = (meta.suppliers || []).find((sp) => sp.id === event.target.value);
      if (supplier?.categories?.[0]) dialog.querySelector("#rc-d-cat").value = supplier.categories[0];
      readForm();
      recheck();
    }
  });
  dialog.addEventListener("click", (event) => {
    if (event.target.closest("[data-change-file]")) {
      s.checked = null; s.values = null; s.error = ""; s.dups = { certain: [], probable: [] }; render();
    }
    const other = event.target.closest("[data-open-document]");
    if (other) openDocument(app, other.dataset.openDocument);
    if (event.target.closest('[data-action="entry-open"]')) dialog.close();
  });
  save.addEventListener("click", async () => {
    readForm();
    const v = s.values;
    const entry = { property_id: v.property_id, category_id: v.category_id, label: v.label.trim(), amount: cleanAmount(v.amount), date: v.date,
      supplier_id: v.supplier_id || "", invoice_number: v.invoice_number.trim() };
    if (v.payment === "paid") Object.assign(entry, { paid: true, paid_date: v.paid_date || v.date });
    else entry.payment_declared = v.payment;
    s.busy = true; save.disabled = true;
    try {
      const result = await app.api.post("/api/documents", { token: s.checked.token, mode: "create", entry,
        confirm_probable: Boolean(dialog.querySelector("[data-confirm-probable]")?.checked), op_id: op });
      dialog.close();
      app.toast(t("doc.created"));
      await app.afterEntryChange();
      await app.afterDocumentChange();
      openEntry(app, result.detail.id);
    } catch (err) {
      s.busy = false;
      dialog.querySelector("[data-error]").innerHTML = errorBox(err.message);
      refreshSave();
    }
  });
  render();
}

// ------------------------------------------------------------------ the documents of an expense (entry page)

export function documentsSection(app, e) {
  const { i18n } = app;
  const { t } = i18n;
  const canWrite = app.canWrite;
  if (!e.documents && !canWrite) return "";
  if (!e.documents_access) {
    return html`<section><h3 class="section-title">${t("doc.title")}</h3>
      <p class="reading">${raw(icon("lock"))}<span>${i18n.plural(e.documents, "doc.hiddenOne", "doc.hiddenMany")}</span></p></section>`;
  }
  return html`
    <section>
      <h3 class="section-title">${t("doc.title")} <span class="count">(${e.document_list.length})</span></h3>
      ${e.document_list.length ? html`<div class="rows">${e.document_list.map((d) => html`
        <div class="keyrow doc-row">
          <span class="tile">${raw(icon("file"))}</span>
          <span><button type="button" class="linkbtn doc-name" data-open-document="${d.id}">${d.filename}</button>
            <small class="num">${i18n.plural(d.pages, "doc.pageOne", "doc.pageMany")} · ${i18n.size(d.size)}${d.entries.length > 1 ? ` · ${t("doc.sharedWith", { n: d.entries.length - 1 })}` : ""}</small></span>
          <span class="doc-actions">
            <a class="btn ghost small" href="${app.api.fileUrl(d.id)}" target="_blank" rel="noopener">${raw(icon("eye"))}${t("doc.open")}</a>
            <a class="btn ghost small" href="${app.api.fileUrl(d.id, true)}" download="${d.filename}">${raw(icon("download"))}${t("doc.download")}</a>
            ${canWrite ? html`<button type="button" class="btn ghost small" data-detach="${d.id}" data-revision="${d.revision}">${raw(icon("close"))}${t("doc.detach")}</button>` : ""}
          </span>
        </div>`)}</div>` : html`<div class="empty">${raw(icon("file"))}<span>${t("doc.none")}</span></div>`}
      ${canWrite && !e.superseded ? html`<div class="actions"><button type="button" class="btn outline-accent" data-attach>${raw(icon("plus"))}${t("doc.attachTitle")}</button></div>` : ""}
    </section>`;
}

export function wireDocumentsSection(app, dialog, e, reopen) {
  const { t } = app.i18n;
  dialog.querySelector("[data-attach]")?.addEventListener("click", () => openAttach(app, e, async (result, message) => {
    await reopen(result, message);
    await app.afterDocumentChange();
  }));
  dialog.querySelectorAll("[data-open-document]").forEach((button) => button.addEventListener("click", () => openDocument(app, button.dataset.openDocument)));
  dialog.querySelectorAll("[data-detach]").forEach((button) => button.addEventListener("click", () => openConfirm(app, {
    title: t("doc.detachTitle"), text: t("doc.detachText"), confirm: t("doc.detach"), danger: false,
    run: async () => {
      await reopen(await app.api.post(`/api/documents/${button.dataset.detach}/detach`, { entry_id: e.id, revision: Number(button.dataset.revision) }), t("doc.detached"));
      await app.afterDocumentChange();
    },
  })));
}

// ------------------------------------------------------------------ the page of a document

export async function openDocument(app, documentId) {
  const { t } = app.i18n;
  const dialog = openDialog(app, {
    title: t("doc.pageTitle"),
    body: html`<div class="loading small"><div class="spinner"></div><span>${t("common.loading")}</span></div>`,
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.close")}</button>`,
    wide: true,
    labelledby: "rc-document-title",
  });
  dialog.addEventListener("click", (event) => {
    if (event.target.closest('[data-action="entry-open"]')) dialog.close();
  });
  try {
    fillDocument(app, dialog, await app.api.get(`/api/documents/${encodeURIComponent(documentId)}`));
  } catch (err) {
    dialog.querySelector(".dbody").innerHTML = errorBox(err.message);
  }
}

function missing(t, d) {
  const reasons = [];
  if (!d.entries.length) reasons.push(t("doc.missing.entry"));
  if (!d.supplier) reasons.push(t("doc.missing.supplier"));
  if (d.amount === null || d.amount === undefined) reasons.push(t("doc.missing.amount"));
  return reasons.join(", ");
}

export function documentPill(t, d) {
  return d.incomplete
    ? html`<span class="pill amber">${raw(icon("docAlert"))}${t("doc.incomplete")}</span>`
    : html`<span class="pill teal">${raw(icon("checkCircle"))}${t("doc.complete")}</span>`;
}

function fillDocument(app, dialog, d) {
  const { i18n } = app;
  const { t } = i18n;
  const canWrite = app.canWrite;
  dialog.querySelector(".dhead h2").textContent = d.filename;
  const head = dialog.querySelector(".dhead div");
  head.querySelector("p")?.remove();
  head.insertAdjacentHTML("beforeend", markup(html`<p>${d.property} · <span class="num">${i18n.plural(d.pages, "doc.pageOne", "doc.pageMany")} · ${i18n.size(d.size)}</span></p>`));
  dialog.querySelector(".dbody").innerHTML = markup(html`
    <div class="pill-row">${documentPill(t, d)}${d.text_found ? "" : html`<span class="pill grey">${raw(icon("eye"))}${t("doc.scan")}</span>`}</div>
    ${d.incomplete ? html`<div class="tip">${raw(icon("docAlert"))}<div><p>${t("doc.incompleteText", { what: missing(t, d) })}</p></div></div>` : ""}
    <section>
      <h3 class="section-title">${t("doc.says")}</h3>
      <dl class="facts-list">
        <div><dt>${t("exf.supplier")}</dt><dd>${d.supplier || "—"}</dd></div>
        <div><dt>${t("exf.invoice")}</dt><dd>${d.invoice_number || "—"}</dd></div>
        <div><dt>${t("exf.date")}</dt><dd class="num">${d.invoice_date ? i18n.dateLong(d.invoice_date) : "—"}</dd></div>
        <div><dt>${t("exd.amount")}</dt><dd class="num">${d.amount !== null && d.amount !== undefined ? i18n.money(d.amount) : "—"}</dd></div>
      </dl>
    </section>
    <section>
      <h3 class="section-title">${t("doc.justifies")}</h3>
      <p class="reading">${raw(icon("info"))}<span>${t("doc.justifiesHint")}</span></p>
      ${d.entries.length ? html`<div class="rows">${d.entries.map((e) => html`
        <div class="keyrow doc-row">
          <span class="tile">${raw(icon("receipt"))}</span>
          <span><button type="button" class="linkbtn doc-name" data-action="entry-open" data-value="${e.id}">${e.label}</button><small class="num">${i18n.dateShort(e.date)} · ${e.category} · ${i18n.money(e.amount)}${e.archived ? ` · ${t("ex.archived")}` : ""}</small></span>
          ${canWrite ? html`<span class="doc-actions"><button type="button" class="btn ghost small" data-detach="${e.id}">${raw(icon("close"))}${t("doc.detach")}</button></span>` : ""}
        </div>`)}</div>` : html`<div class="empty">${raw(icon("link"))}<span>${t("doc.noEntry")}</span></div>`}
      ${canWrite && d.link_candidates?.length ? html`
        <div class="link-row">
          <label class="sr-only" for="rc-doc-link">${t("doc.linkLabel")}</label>
          <select id="rc-doc-link" data-link-select>
            <option value="">${t("doc.linkPick")}</option>
            ${d.link_candidates.map((e) => html`<option value="${e.id}">${i18n.dateShort(e.date)} · ${e.label} · ${i18n.money(e.amount)}</option>`)}
          </select>
          <button type="button" class="btn outline-accent" data-link disabled>${raw(icon("link"))}${t("doc.link")}</button>
        </div>` : ""}
    </section>
    <section>
      <h3 class="section-title">${t("doc.file")}</h3>
      <div class="actions">
        <a class="btn outline-accent" href="${app.api.fileUrl(d.id)}" target="_blank" rel="noopener">${raw(icon("eye"))}${t("doc.open")}</a>
        <a class="btn ghost" href="${app.api.fileUrl(d.id, true)}" download="${d.filename}">${raw(icon("download"))}${t("doc.download")}</a>
      </div>
      <dl class="facts-list">
        <div><dt>${t("doc.fingerprint")}</dt><dd class="mono" title="${d.sha256}">${d.sha256.slice(0, 16)}…</dd></div>
        <div><dt>${t("sjd.trace")}</dt><dd>${t("sjd.created", { date: i18n.dateShort((d.created_at || "").slice(0, 10)) })}${d.history?.length ? ` · ${i18n.plural(d.history.length, "sjd.changedOnce", "sjd.changedMany")}` : ""}</dd></div>
      </dl>
      <p class="reading">${raw(icon("shieldCheck"))}<span>${t("doc.privateNote")}</span></p>
    </section>`);
  const foot = dialog.querySelector(".dfoot");
  foot.classList.toggle("stay-actions", canWrite);
  foot.innerHTML = markup(canWrite ? html`
    ${d.entries.length ? "" : html`<button type="button" class="btn ghost danger-text del" data-delete>${raw(icon("trash"))}${t("doc.delete")}</button>`}
    <button type="button" class="btn primary" data-edit>${raw(icon("pencil"))}${t("sjd.edit")}</button>`
    : html`<button type="button" class="btn ghost" data-close>${t("common.close")}</button>`);

  const reopen = async (result, message) => {
    if (message) app.toast(message);
    if (result?.document) fillDocument(app, dialog, result.document);
    await app.afterDocumentChange();
    await app.afterEntryChange();
  };
  const select = dialog.querySelector("[data-link-select]");
  const linkButton = dialog.querySelector("[data-link]");
  select?.addEventListener("change", () => { linkButton.disabled = !select.value; });
  linkButton?.addEventListener("click", async () => {
    linkButton.disabled = true;
    try {
      await reopen(await app.api.post(`/api/documents/${d.id}/link`, { entry_id: select.value }), t("doc.linked"));
    } catch (err) {
      app.toast(err.message, true);
      linkButton.disabled = false;
    }
  });
  dialog.querySelectorAll("[data-detach]").forEach((button) => button.addEventListener("click", () => openConfirm(app, {
    title: t("doc.detachTitle"), text: t("doc.detachText"), confirm: t("doc.detach"), danger: false,
    run: async () => reopen(await app.api.post(`/api/documents/${d.id}/detach`, { entry_id: button.dataset.detach, revision: d.revision }), t("doc.detached")),
  })));
  dialog.querySelector("[data-delete]")?.addEventListener("click", () => openConfirm(app, {
    title: t("doc.deleteTitle"), text: t("doc.deleteText"), confirm: t("doc.delete"),
    run: async () => {
      await app.api.request("DELETE", `/api/documents/${d.id}`, { body: { revision: d.revision, dataset: app.api.dataset, lang: i18n.lang, op_id: app.newOpId() } });
      dialog.close();
      app.toast(t("doc.deleted"));
      await app.afterDocumentChange();
    },
  }));
  dialog.querySelector("[data-edit]")?.addEventListener("click", () => openDocumentForm(app, d, (result) => reopen(result, t("doc.updated"))));
}

async function openDocumentForm(app, d, onSaved) {
  const { i18n } = app;
  const { t } = i18n;
  let meta = app.state.entries.data;
  if (!meta?.suppliers) {
    try { meta = await app.api.get("/api/entries", { view: "archived" }); } catch (err) { app.toast(err.message, true); return; }
  }
  const suppliers = (meta.suppliers || []).filter((sp) => !sp.archived || sp.id === d.supplier_id);
  const dialog = openDialog(app, {
    title: t("doc.editTitle"),
    subtitle: d.filename,
    body: html`
      <form class="form-grid" novalidate>
        <div class="field"><label for="rc-de-sup">${t("exf.supplier")}</label>
          <select id="rc-de-sup" name="supplier_id"><option value="">—</option>${suppliers.map((sp) => html`<option value="${sp.id}" ${raw(sp.id === d.supplier_id ? "selected" : "")}>${sp.name}</option>`)}</select></div>
        <div class="field"><label for="rc-de-inv">${t("exf.invoice")}</label><input id="rc-de-inv" name="invoice_number" maxlength="80" autocomplete="off" value="${d.invoice_number}"></div>
        <div class="field"><label for="rc-de-date">${t("exf.date")}</label><input id="rc-de-date" name="invoice_date" type="date" value="${d.invoice_date}"></div>
        <div class="field"><label for="rc-de-amount">${t("exf.amount")}</label><input id="rc-de-amount" name="amount" inputmode="decimal" autocomplete="off" value="${amountValue(d.amount)}"></div>
        <p class="reading wide">${raw(icon("info"))}<span>${t("doc.editHint")}</span></p>
        <div class="wide" data-error aria-live="assertive"></div>
      </form>`,
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.cancel")}</button><button type="button" class="btn primary" data-save>${raw(icon("check"))}${t("exf.save")}</button>`,
  });
  const save = dialog.querySelector("[data-save]");
  const op = app.newOpId();
  save.addEventListener("click", async () => {
    const data = Object.fromEntries(new FormData(dialog.querySelector("form")).entries());
    save.disabled = true;
    try {
      const result = await app.api.request("PATCH", `/api/documents/${d.id}`, { body: {
        supplier_id: data.supplier_id, invoice_number: data.invoice_number.trim(), invoice_date: data.invoice_date,
        amount: cleanAmount(data.amount), revision: d.revision, dataset: app.api.dataset, lang: i18n.lang, op_id: op } });
      dialog.close();
      await onSaved(result);
    } catch (err) {
      dialog.querySelector("[data-error]").innerHTML = errorBox(err.message);
      save.disabled = false;
    }
  });
}
