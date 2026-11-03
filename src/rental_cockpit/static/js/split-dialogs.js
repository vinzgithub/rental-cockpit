/* Copyright © 2026 Vincent Fournet */
// « Répartir entre les séjours » and « Rapprocher des saisies » for a supplier's invoice.
// Splitting is analytical only (the expense is still counted once); the
// server checks again every amount, line and stay before saving anything.

import { openDialog } from "./dialogs.js";
import { html, markup, raw } from "./dom.js";
import { icon } from "./icons.js";

function cleanAmount(value) {
  return String(value ?? "").replace(/[\s  €]/g, "");
}

function toCents(text) {
  const value = parseFloat(cleanAmount(text).replace(",", "."));
  return Number.isFinite(value) ? Math.round(value * 100) : null;
}

function amountValue(cents) {
  if (cents === null || cents === undefined) return "";
  return (cents / 100).toFixed(2).replace(".", ",").replace(",00", "");
}

function errorBox(message) {
  return markup(html`<div class="error-box" role="alert">${raw(icon("alert"))}<span>${message}</span></div>`);
}

/** The stay a service done on ``day`` most likely belongs to: departure that day, else the stay around it. */
function suggested(stays, day, fallback) {
  if (!day) return fallback || "";
  return stays.find((s) => s.end === day)?.id || stays.find((s) => s.start <= day && day < s.end)?.id || fallback || "";
}

// ------------------------------------------------------------------ split

export async function openSplit(app, entry, onDone) {
  const { i18n } = app;
  const { t } = i18n;
  let stays = [];
  try {
    // Cancelled stays are not offered, unless a share already went to one (it must not move silently).
    const used = new Set(entry.allocations.map((a) => a.stay_id));
    stays = (await app.api.get("/api/stays", { view: "all", property_id: entry.property_id })).stays.filter((s) => s.status !== "cancelled" || used.has(s.id));
  } catch (err) {
    app.toast(err.message, true);
    return;
  }
  const near = (day) => [...stays].sort((a, b) => Math.abs(Date.parse(a.end) - Date.parse(day)) - Math.abs(Date.parse(b.end) - Date.parse(day)));
  const label = (s) => `${s.guest_label || s.external_ref || i18n.t("sj.untitled", { date: i18n.dateShort(s.start) })} · ${i18n.range(s.start, s.end)}`;
  const stayOptions = (day, chosen) => html`<option value="">${t("spl.noStay")}</option>${near(day || entry.date).map((s) => html`<option value="${s.id}" ${raw(s.id === chosen ? "selected" : "")}>${label(s)}</option>`)}`;
  const allocationRow = (row, a = {}) => html`
    <div class="alloc" data-alloc>
      <select data-a="stay" aria-label="${t("spl.stay")}">${stayOptions(row.intervention_date, a.stay_id ?? suggested(stays, row.intervention_date, entry.stay_id))}</select>
      <input data-a="amount" inputmode="decimal" autocomplete="off" aria-label="${t("spl.amount")}" value="${amountValue(a.amount ?? null)}">
      <button type="button" class="iconbtn" data-alloc-remove aria-label="${t("spl.remove")}">${raw(icon("trash"))}</button>
    </div>`;

  const dialog = openDialog(app, {
    title: t("spl.dialogTitle"),
    subtitle: `${entry.label} · ${i18n.money(entry.amount)}`,
    wide: true,
    body: html`
      <p class="reading">${raw(icon("info"))}<span>${t("spl.dialogIntro")}</span></p>
      ${!stays.length ? html`<div class="tip">${raw(icon("alert"))}<div><p>${t("spl.noStays")}</p></div></div>` : ""}
      ${entry.split.map((row, index) => html`
        <fieldset class="split-block amounts" data-row="${index}" data-line="${row.line_id}">
          <legend>${row.kind_label || entry.label}${row.label && row.label !== row.kind_label ? ` · ${row.label}` : ""} · <span class="num">${i18n.money(row.amount)}</span></legend>
          ${row.intervention_date ? html`<p class="reading">${raw(icon("calendar"))}<span>${t("spl.done_on", { date: i18n.dateLong(row.intervention_date) })}</span></p>` : ""}
          <div data-allocs>${(row.allocations.length ? row.allocations : [{ amount: row.remaining }]).map((a) => allocationRow(row, a))}</div>
          <div class="split-foot"><button type="button" class="btn ghost small" data-alloc-add>${raw(icon("plus"))}${t("spl.add")}</button><small class="num" data-row-status></small></div>
        </fieldset>`)}
      <p class="split-total num" data-total aria-live="polite"></p>
      <div data-error aria-live="assertive"></div>`,
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.cancel")}</button><button type="button" class="btn primary" data-save>${raw(icon("check"))}${t("spl.save")}</button>`,
  });
  const save = dialog.querySelector("[data-save]");
  const op = app.newOpId();

  const refresh = () => {
    let total = 0;
    let ok = true;
    for (const block of dialog.querySelectorAll("[data-row]")) {
      const row = entry.split[Number(block.dataset.row)];
      const used = [...block.querySelectorAll("[data-a=amount]")].reduce((sum, input) => sum + (toCents(input.value) || 0), 0);
      total += used;
      const status = block.querySelector("[data-row-status]");
      const left = row.amount - used;
      status.textContent = left === 0 ? t("spl.rowDone") : left > 0 ? t("spl.rowLeft", { amount: i18n.money(left) }) : t("spl.rowOver", { amount: i18n.money(-left) });
      status.classList.toggle("bad", left < 0);
      ok = ok && left >= 0;
    }
    const whole = entry.split.reduce((sum, row) => sum + row.amount, 0);
    const totalEl = dialog.querySelector("[data-total]");
    totalEl.textContent = t("spl.total", { used: i18n.money(total), total: i18n.money(whole) });
    totalEl.classList.toggle("bad", !ok);
    save.disabled = !ok;
  };
  dialog.addEventListener("input", refresh);
  dialog.addEventListener("change", refresh);
  dialog.addEventListener("click", (event) => {
    const add = event.target.closest("[data-alloc-add]");
    if (add) {
      const block = add.closest("[data-row]");
      const row = entry.split[Number(block.dataset.row)];
      const used = [...block.querySelectorAll("[data-a=amount]")].reduce((sum, input) => sum + (toCents(input.value) || 0), 0);
      block.querySelector("[data-allocs]").insertAdjacentHTML("beforeend", markup(allocationRow(row, { amount: Math.max(row.amount - used, 0) || null, stay_id: "" })));
      block.querySelector("[data-alloc]:last-child select").focus();
      refresh();
    }
    const remove = event.target.closest("[data-alloc-remove]");
    if (remove) {
      remove.closest("[data-alloc]").remove();
      refresh();
    }
  });
  refresh();

  save.addEventListener("click", async () => {
    const allocations = [];
    for (const block of dialog.querySelectorAll("[data-row]")) {
      for (const alloc of block.querySelectorAll("[data-alloc]")) {
        const amount = cleanAmount(alloc.querySelector("[data-a=amount]").value);
        if (!amount || toCents(amount) === 0) continue;
        allocations.push({ line_id: block.dataset.line, stay_id: alloc.querySelector("[data-a=stay]").value, amount });
      }
    }
    save.disabled = true;
    try {
      const result = await app.api.post(`/api/entries/${entry.id}/allocations`, { allocations, revision: entry.revision, op_id: op });
      dialog.close();
      await onDone(result, t("spl.saved"));
    } catch (err) {
      dialog.querySelector("[data-error]").innerHTML = errorBox(err.message);
      save.disabled = false;
    }
  });
  dialog.querySelector("select, input")?.focus();
}

// ------------------------------------------------------------------ reconcile

export async function openReconcile(app, entry, onDone) {
  const { i18n } = app;
  const { t } = i18n;
  let candidates;
  try {
    candidates = (await app.api.get(`/api/entries/${encodeURIComponent(entry.id)}/candidates`)).candidates;
  } catch (err) {
    app.toast(err.message, true);
    return;
  }
  const already = entry.replaces.reduce((sum, r) => sum + r.amount, 0);
  const dialog = openDialog(app, {
    title: t("rec.dialogTitle"),
    subtitle: `${entry.label} · ${i18n.money(entry.amount)}`,
    wide: true,
    body: html`
      <p class="reading">${raw(icon("info"))}<span>${t("rec.dialogIntro")}</span></p>
      ${candidates.length ? html`<div class="rows">${candidates.map((c) => html`
        <label class="keyrow pick">
          <input type="checkbox" value="${c.id}" data-amount="${c.amount}">
          <span><b>${c.label}</b><small class="num">${i18n.dateShort(c.date)} · ${c.category}${c.paid ? ` · ${t("rec.alreadyPaid", { amount: i18n.money(c.paid) })}` : ""}</small></span>
          <b class="num">${i18n.money(c.amount)}</b>
        </label>`)}</div>` : html`<div class="empty">${raw(icon("checkCircle"))}<span>${t("rec.none")}</span></div>`}
      <p class="split-total num" data-total aria-live="polite"></p>
      <div data-error aria-live="assertive"></div>`,
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.cancel")}</button>${candidates.length ? html`<button type="button" class="btn primary" data-save disabled>${raw(icon("check"))}${t("rec.save")}</button>` : ""}`,
  });
  const save = dialog.querySelector("[data-save]");
  const op = app.newOpId();
  const refresh = () => {
    const picked = [...dialog.querySelectorAll("input:checked")];
    const sum = already + picked.reduce((acc, input) => acc + Number(input.dataset.amount), 0);
    const totalEl = dialog.querySelector("[data-total]");
    totalEl.textContent = t("rec.total", { matched: i18n.money(sum), total: i18n.money(entry.amount), left: i18n.money(Math.max(entry.amount - sum, 0)) });
    totalEl.classList.toggle("bad", sum > entry.amount);
    if (save) save.disabled = !picked.length || sum > entry.amount;
  };
  dialog.addEventListener("change", refresh);
  refresh();
  save?.addEventListener("click", async () => {
    const ids = [...dialog.querySelectorAll("input:checked")].map((input) => input.value);
    save.disabled = true;
    try {
      const result = await app.api.post(`/api/entries/${entry.id}/reconcile`, { entry_ids: ids, revision: entry.revision, op_id: op });
      dialog.close();
      await onDone(result, t("rec.saved", { n: ids.length }));
    } catch (err) {
      dialog.querySelector("[data-error]").innerHTML = errorBox(err.message);
      save.disabled = false;
    }
  });
}
