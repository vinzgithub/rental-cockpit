/* Copyright © 2026 Vincent Fournet */
// Stay page, stay form, cancellation, restoration, deletion and payouts.
// Every change goes to the server, which checks the rights and the figures
// again; the dialogs only explain, collect and show what the server returns.

import { openConfirm, openDialog } from "./dialogs.js";
import { html, markup, raw } from "./dom.js";
import { icon } from "./icons.js";
import { payoutPill, statePill, stayTitle } from "./views/stays.js";

const AMOUNT_KEYS = ["gross", "commission", "payout", "taxes_collected", "deposit"];

/** "1 234,50 €" typed by a person → "1234,50" for the server (spaces are only grouping). */
function cleanAmount(value) {
  return String(value ?? "").replace(/[\s  €]/g, "");
}

function amountValue(cents) {
  if (cents === null || cents === undefined) return "";
  return (cents / 100).toFixed(2).replace(".", ",").replace(",00", "");
}

function errorBox(message) {
  return markup(html`<div class="error-box" role="alert">${raw(icon("alert"))}<span>${message}</span></div>`);
}

function nightsBetween(start, end) {
  if (!start || !end) return 0;
  return Math.round((Date.parse(`${end}T00:00:00Z`) - Date.parse(`${start}T00:00:00Z`)) / 86400000);
}

/** Nights of [start, end) month by month — what the Activity reading will spread. */
function nightsByMonth(i18n, start, end) {
  const nights = nightsBetween(start, end);
  if (nights <= 0) return "";
  const counts = new Map();
  for (let i = 0; i < nights; i += 1) {
    const day = new Date(Date.parse(`${start}T00:00:00Z`) + i * 86400000).toISOString().slice(0, 7);
    counts.set(day, (counts.get(day) || 0) + 1);
  }
  return [...counts.entries()].map(([month, n]) => `${i18n.plural(n, "stays.night", "stays.nights")} ${i18n.t("sjf.in")} ${i18n.monthLower(`${month}-01`)}`).join(" · ");
}

async function afterChange(app, message) {
  if (message) app.toast(message);
  await app.afterStayChange();
}

// ------------------------------------------------------------------ stay page

export async function openStay(app, stayId) {
  const { i18n } = app;
  const { t } = i18n;
  const dialog = openDialog(app, {
    title: t("sjd.title"),
    body: html`<div class="loading small"><div class="spinner"></div><span>${t("common.loading")}</span></div>`,
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.close")}</button>`,
    wide: true,
    labelledby: "rc-stay-title",
  });
  let detail;
  try {
    detail = await app.api.get(`/api/stays/${encodeURIComponent(stayId)}`);
  } catch (err) {
    dialog.querySelector(".dbody").innerHTML = errorBox(err.message);
    return;
  }
  fillStay(app, dialog, detail);
}

function money(i18n, cents, unknown) {
  return cents === null || cents === undefined ? html`<span class="muted">${unknown}</span>` : i18n.money(cents);
}

function fillStay(app, dialog, s) {
  const { i18n } = app;
  const { t } = i18n;
  const v = app.viewModel();
  const canWrite = app.canWrite;
  const unknown = t("sjd.unknown");
  const a = s.amounts;
  const payoutComputed = a.payout === null && s.expected_payout !== null;
  const remaining = s.expected_payout === null ? null : Math.max(s.expected_payout - s.received, 0);
  const arrivalMonth = i18n.monthLower(`${s.start.slice(0, 7)}-01`);
  const cancelled = s.status === "cancelled";

  dialog.querySelector(".dhead h2").textContent = stayTitle(v, s);
  const head = dialog.querySelector(".dhead div");
  head.querySelector("p")?.remove();
  head.insertAdjacentHTML("beforeend", markup(html`<p>${s.property} · ${s.channel_label} · <span class="num">${i18n.dateLong(s.start)} → ${i18n.dateLong(s.end)}</span></p>`));

  const warnings = (s.warnings || []).map((w) => html`<div class="tip">${raw(icon("alert"))}<div><b>${t("sjf.warnings")}</b><p>${w.message}</p></div></div>`);
  const breakdown = html`
    <section>
      <h3 class="section-title">${t("sjd.counts")}</h3>
      <p class="reading">${raw(icon("info"))}<span>${cancelled ? t("sjd.cancelledNote", { month: arrivalMonth }) : t("sjd.countsIntro")}</span></p>
      ${a.gross === null && !cancelled ? html`<div class="tip">${raw(icon("alert"))}<div><p>${t("sjd.missingNote")}</p></div></div>` : html`
        <div class="lines-wrap compact-table">
          <table class="lines breakdown">
            <thead><tr><th>${t("sjd.month")}</th><th class="amt">${t("sjd.nights")}</th><th class="amt">${t("sjd.revenue")}</th><th class="amt">${t("sjd.fee")}</th><th class="amt">${t("sjd.net")}</th></tr></thead>
            <tbody>${s.breakdown.map((row) => html`<tr>
              <td class="c-item">${i18n.month(row.start)}</td>
              <td class="amt num" data-label="${t("sjd.nights")}">${cancelled ? "—" : row.nights}</td>
              <td class="amt num" data-label="${t("sjd.revenue")}">${money(i18n, row.revenue, unknown)}</td>
              <td class="amt num" data-label="${t("sjd.fee")}">${row.commission ? `− ${i18n.money(row.commission)}` : money(i18n, row.commission, unknown)}</td>
              <td class="amt num" data-label="${t("sjd.net")}"><b>${money(i18n, row.net, unknown)}</b></td>
            </tr>`)}</tbody>
          </table>
        </div>`}
      ${cancelled ? "" : html`<ul class="plain-list notes">
        <li>${t("sjd.invoiceNote", { month: arrivalMonth })}</li>
        <li>${t("sjd.cashNote")}</li>
      </ul>`}
    </section>`;

  const payments = html`
    <section>
      <h3 class="section-title">${t("sjd.payments")}</h3>
      <div class="rows">
        ${s.payments.length ? s.payments.map((p) => html`
          <div class="keyrow">
            <span class="tile">${raw(icon("coins"))}</span>
            <span><b class="num">${i18n.money(p.amount)}</b><small>${i18n.dateLong(p.date)}${p.method ? ` · ${p.method}` : ""}${p.note ? ` · ${p.note}` : ""}</small></span>
            ${canWrite ? html`<button type="button" class="btn ghost small" data-payment-delete="${p.id}" data-amount="${p.amount}" data-date="${p.date}">${raw(icon("trash"))}${t("sjd.deletePayment")}</button>` : ""}
          </div>`) : html`<div class="empty">${raw(icon("info"))}<span>${t("sjd.noPayment")}</span></div>`}
      </div>
      ${canWrite && s.payout_state !== "received" && s.payout_state !== "none" ? html`<div class="actions"><button type="button" class="btn outline-accent" data-payout>${raw(icon("plus"))}${t("sjd.recordPayout")}</button></div>` : ""}
    </section>`;

  const changes = s.history.length;
  dialog.querySelector(".dbody").innerHTML = markup(html`
    <div class="pill-row">${statePill(s)}${payoutPill(s)}</div>
    ${warnings}
    <section>
      <h3 class="section-title">${t("sjd.amounts")}</h3>
      <dl class="facts-list money-facts">
        <div><dt>${t("sjd.gross")}</dt><dd class="num">${money(i18n, a.gross, unknown)}</dd></div>
        <div><dt>${t("sjd.commission")}</dt><dd class="num">${money(i18n, a.commission, unknown)}</dd></div>
        <div><dt>${t("sjd.payout")}</dt><dd class="num">${money(i18n, s.expected_payout, unknown)}${s.expected_payout !== null ? html` <small>${payoutComputed ? t("sjd.payoutComputed") : t("sjd.payoutEntered")}</small>` : ""}</dd></div>
        ${s.adjustments_total ? html`<div><dt>${t("sjd.adjustments")}</dt><dd class="num">${i18n.money(s.adjustments_total)}</dd></div>` : ""}
        <div><dt>${t("sjd.received")}</dt><dd class="num">${i18n.money(s.received)}</dd></div>
        ${remaining !== null && remaining > 0 ? html`<div><dt>${t("sjd.remaining")}</dt><dd class="num"><b>${i18n.money(remaining)}</b></dd></div>` : ""}
        ${a.taxes_collected !== null ? html`<div><dt>${t("sjd.taxes")}</dt><dd class="num">${i18n.money(a.taxes_collected)} <small>${t("sjd.outside")}</small></dd></div>` : ""}
        ${a.deposit !== null ? html`<div><dt>${t("sjd.deposit")}</dt><dd class="num">${i18n.money(a.deposit)} <small>${t("sjd.outside")}</small></dd></div>` : ""}
        ${s.amounts_before_cancel ? html`<div><dt>${t("sjd.beforeCancel")}</dt><dd class="num">${money(i18n, s.amounts_before_cancel.gross, unknown)}</dd></div>` : ""}
      </dl>
    </section>
    ${breakdown}
    ${payments}
    <section>
      <h3 class="section-title">${t("sjd.about")}</h3>
      <dl class="facts-list">
        <div><dt>${t("stays.guests")}</dt><dd>${s.guests ? i18n.plural(s.guests, "props.guest", "props.guests") : "—"}</dd></div>
        <div><dt>${t("sjd.ref")}</dt><dd>${s.external_ref || "—"}</dd></div>
        ${s.note ? html`<div><dt>${t("sjd.note")}</dt><dd class="pre">${s.note}</dd></div>` : ""}
        <div><dt>${t("sjd.trace")}</dt><dd>${s.imported
          ? t("sjd.imported", { date: i18n.dateShort(s.imported.at.slice(0, 10)), file: s.imported.file_name || t(`imp.fileKind.${s.imported.kind}`) })
          : t("sjd.created", { date: i18n.dateShort((s.created_at || "").slice(0, 10)) })}${changes ? ` · ${i18n.plural(changes, "sjd.changedOnce", "sjd.changedMany")}` : ""}</dd></div>
      </dl>
    </section>`);

  const foot = dialog.querySelector(".dfoot");
  foot.classList.toggle("stay-actions", canWrite);
  foot.innerHTML = markup(canWrite ? html`
    ${s.deletable && !s.payments.length ? html`<button type="button" class="btn ghost danger-text del" data-stay-delete>${raw(icon("trash"))}${t("sjd.delete")}</button>` : ""}
    ${cancelled
      ? html`<button type="button" class="btn ghost" data-stay-restore>${raw(icon("repeat"))}${t("sjd.restore")}</button>`
      : html`<button type="button" class="btn ghost" data-stay-cancel>${raw(icon("ban"))}${t("sjd.cancel")}</button>`}
    ${cancelled ? "" : html`<button type="button" class="btn primary" data-stay-edit>${raw(icon("pencil"))}${t("sjd.edit")}</button>`}`
    : html`<button type="button" class="btn ghost" data-close>${t("common.close")}</button>`);

  const reopen = async (result, message) => {
    if (message) app.toast(message);
    if (result?.detail) fillStay(app, dialog, { ...result.detail, warnings: result.warnings || [] });
    await app.afterStayChange();
  };
  dialog.querySelector("[data-stay-edit]")?.addEventListener("click", () => openStayForm(app, { stay: s, onSaved: reopen }));
  dialog.querySelector("[data-stay-cancel]")?.addEventListener("click", () => openCancel(app, s, reopen));
  dialog.querySelector("[data-stay-restore]")?.addEventListener("click", () => openConfirm(app, {
    title: t("sjr.title"), text: t("sjr.text"), confirm: t("sjr.confirm"), danger: false,
    run: async () => reopen(await app.api.post(`/api/stays/${s.id}/restore`, { revision: s.revision }), t("sjr.done")),
  }));
  dialog.querySelector("[data-stay-delete]")?.addEventListener("click", () => openConfirm(app, {
    title: t("sjx.title"), text: t("sjx.text"), confirm: t("sjx.confirm"),
    run: async () => {
      await app.api.request("DELETE", `/api/stays/${s.id}`, { body: { dataset: app.api.dataset, lang: i18n.lang, op_id: app.newOpId() } });
      dialog.close();
      await afterChange(app, t("sjx.done"));
    },
  }));
  dialog.querySelector("[data-payout]")?.addEventListener("click", () => openPayout(app, s, remaining, reopen));
  dialog.querySelectorAll("[data-payment-delete]").forEach((button) => button.addEventListener("click", () => openConfirm(app, {
    title: t("sjp.deleteTitle"),
    text: t("sjp.deleteText", { amount: i18n.money(Number(button.dataset.amount)), date: i18n.dateLong(button.dataset.date) }),
    confirm: t("sjx.confirm"),
    run: async () => reopen(await app.api.request("DELETE", `/api/payments/${button.dataset.paymentDelete}`,
      { body: { dataset: app.api.dataset, lang: i18n.lang, op_id: app.newOpId() } }), t("sjp.deleted")),
  })));
}

// ------------------------------------------------------------------ stay form

export function openStayForm(app, { stay = null, propertyId = null, onSaved = null } = {}) {
  const { i18n } = app;
  const { t } = i18n;
  const props = (app.viewModel().properties || []).filter((p) => !p.archived || p.id === stay?.property_id);
  const channels = ["airbnb", "abritel", "booking", "direct", "other"];
  const chosen = stay?.property_id || propertyId || (app.state.propertyId !== "all" ? app.state.propertyId : props[0]?.id);
  const a = stay?.amounts || {};
  const field = (key, label, help, extra = "") => html`
    <div class="field"><label for="rc-s-${key}">${label}</label>
      <input id="rc-s-${key}" name="${key}" inputmode="decimal" autocomplete="off" value="${amountValue(a[key])}" ${raw(extra)} aria-describedby="rc-s-${key}-h">
      <span class="help" id="rc-s-${key}-h">${help}</span></div>`;
  const dialog = openDialog(app, {
    title: t(stay ? "sjf.titleEdit" : "sjf.titleNew"),
    subtitle: t("sjf.sub"),
    wide: true,
    body: html`
      <form class="form-grid" novalidate>
        <div class="field"><label for="rc-s-prop">${t("sjf.property")}</label>
          <select id="rc-s-prop" name="property_id" ${raw(stay ? "disabled" : "")}>${props.map((p) => html`<option value="${p.id}" ${raw(p.id === chosen ? "selected" : "")}>${p.name}</option>`)}</select></div>
        <div class="field"><label for="rc-s-channel">${t("sjf.channel")}</label>
          <select id="rc-s-channel" name="channel">${channels.map((c) => html`<option value="${c}" ${raw(c === (stay?.channel || "airbnb") ? "selected" : "")}>${t(`channel.${c}`)}</option>`)}</select></div>
        <div class="field"><label for="rc-s-start">${t("sjf.start")}</label><input id="rc-s-start" name="start" type="date" required value="${stay?.start || ""}"></div>
        <div class="field"><label for="rc-s-end">${t("sjf.end")}</label><input id="rc-s-end" name="end" type="date" required value="${stay?.end || ""}"></div>
        <p class="reading wide nights-preview" aria-live="polite">${raw(icon("moon"))}<span data-nights></span></p>
        <div class="field"><label for="rc-s-guests">${t("stays.guests")}</label><input id="rc-s-guests" name="guests" type="number" min="0" max="99" inputmode="numeric" value="${stay?.guests ?? ""}"></div>
        <div class="field"><label for="rc-s-status">${t("sjf.status")}</label>
          <select id="rc-s-status" name="status">${["confirmed", "provisional"].map((k) => html`<option value="${k}" ${raw((stay?.status === "provisional" ? "provisional" : "confirmed") === k ? "selected" : "")}>${t(`sjf.status.${k}`)}</option>`)}</select></div>
        <div class="field"><label for="rc-s-label">${t("sjf.label")}</label><input id="rc-s-label" name="guest_label" maxlength="80" autocomplete="off" placeholder="${t("sjf.labelPh")}" value="${stay?.guest_label || ""}" aria-describedby="rc-s-label-h"><span class="help" id="rc-s-label-h">${t("sjf.labelHelp")}</span></div>
        <div class="field"><label for="rc-s-ref">${t("sjf.ref")}</label><input id="rc-s-ref" name="external_ref" maxlength="80" autocomplete="off" value="${stay?.external_ref || ""}" aria-describedby="rc-s-ref-h"><span class="help" id="rc-s-ref-h">${t("sjf.refHelp")}</span></div>
        <fieldset class="wide amounts">
          <legend>${t("sjf.amounts")}</legend>
          <div class="form-grid">
            ${field("gross", t("sjf.gross"), t("sjf.grossHelp"))}
            ${field("commission", t("sjf.commission"), t("sjf.commissionHelp"))}
            ${field("payout", t("sjf.payout"), t("sjf.payoutHelp"))}
            ${field("taxes_collected", t("sjf.taxes"), t("sjf.taxesHelp"))}
            ${field("deposit", t("sjf.deposit"), t("sjf.depositHelp"))}
          </div>
        </fieldset>
        <div class="field wide"><label for="rc-s-note">${t("sjd.note")}</label><textarea id="rc-s-note" name="note" rows="2" maxlength="600">${stay?.note || ""}</textarea></div>
        <div class="wide" data-error aria-live="assertive"></div>
      </form>`,
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.cancel")}</button><button type="button" class="btn primary" data-save>${raw(icon("check"))}${t("sjf.save")}</button>`,
  });
  const form = dialog.querySelector("form");
  const save = dialog.querySelector("[data-save]");
  const errorBoxEl = dialog.querySelector("[data-error]");
  const nights = dialog.querySelector("[data-nights]");
  const payoutInput = dialog.querySelector("#rc-s-payout");
  const op = app.newOpId();

  const refresh = () => {
    const start = form.start.value;
    const end = form.end.value;
    const n = nightsBetween(start, end);
    nights.textContent = !start || !end ? t("sjf.datesFirst") : n <= 0 ? t("sjf.datesOrder") : nightsByMonth(i18n, start, end);
    nights.parentElement.classList.toggle("bad", Boolean(start && end && n <= 0));
    const gross = parseFloat(cleanAmount(form.gross.value).replace(",", "."));
    const fee = parseFloat(cleanAmount(form.commission.value).replace(",", ".")) || 0;
    payoutInput.placeholder = Number.isFinite(gross) ? t("sjf.payoutAuto", { amount: i18n.money(Math.round((gross - fee) * 100)) }) : "";
  };
  form.addEventListener("input", refresh);
  refresh();

  const submit = async () => {
    const data = Object.fromEntries(new FormData(form).entries());
    const body = {
      channel: data.channel, start: data.start, end: data.end, status: data.status,
      guest_label: data.guest_label.trim(), external_ref: data.external_ref.trim(), note: data.note,
      guests: data.guests === "" ? null : Number(data.guests),
      amounts: Object.fromEntries(AMOUNT_KEYS.map((key) => [key, cleanAmount(data[key])])),
    };
    if (!stay) body.property_id = data.property_id || form.property_id.value;
    if (stay) body.revision = stay.revision;
    save.disabled = true;
    errorBoxEl.innerHTML = "";
    try {
      const result = stay
        ? await app.api.request("PATCH", `/api/stays/${stay.id}`, { body: { ...body, dataset: app.api.dataset, lang: i18n.lang, op_id: op } })
        : await app.api.post("/api/stays", { ...body, op_id: op });
      dialog.close();
      for (const warning of result.warnings || []) app.toast(warning.message, true);
      if (onSaved) await onSaved(result, t(stay ? "sjf.updated" : "sjf.saved"));
      else {
        await afterChange(app, t("sjf.saved"));
        if (result.detail) openStay(app, result.detail.id);
      }
    } catch (err) {
      errorBoxEl.innerHTML = errorBox(err.message);
      save.disabled = false;
    }
  };
  save.addEventListener("click", submit);
  form.addEventListener("submit", (event) => { event.preventDefault(); submit(); });
  (props.length > 1 && !stay ? form.property_id : form.start).focus();
}

// ------------------------------------------------------------------ cancellation

function openCancel(app, stay, onDone) {
  const { i18n } = app;
  const { t } = i18n;
  const dialog = openDialog(app, {
    title: t("sjc.title"),
    subtitle: stayTitle(app.viewModel(), stay),
    body: html`
      <p>${t("sjc.text")}</p>
      ${stay.received ? html`<div class="tip">${raw(icon("alert"))}<div><p>${t("sjc.received", { amount: i18n.money(stay.received) })}</p></div></div>` : ""}
      <form class="form-grid" novalidate>
        <div class="field"><label for="rc-c-ret">${t("sjc.retained")}</label><input id="rc-c-ret" name="retained" inputmode="decimal" autocomplete="off" placeholder="0" aria-describedby="rc-c-ret-h"><span class="help" id="rc-c-ret-h">${t("sjc.retainedHelp")}</span></div>
        <div class="field"><label for="rc-c-fee">${t("sjc.fee")}</label><input id="rc-c-fee" name="retained_commission" inputmode="decimal" autocomplete="off" placeholder="0"></div>
        <div class="wide" data-error aria-live="assertive"></div>
      </form>`,
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.back")}</button><button type="button" class="btn danger" data-save>${raw(icon("ban"))}${t("sjc.confirm")}</button>`,
  });
  const form = dialog.querySelector("form");
  const save = dialog.querySelector("[data-save]");
  const op = app.newOpId();
  const submit = async () => {
    save.disabled = true;
    try {
      const result = await app.api.post(`/api/stays/${stay.id}/cancel`, {
        retained: cleanAmount(form.retained.value), retained_commission: cleanAmount(form.retained_commission.value), revision: stay.revision, op_id: op,
      });
      dialog.close();
      await onDone(result, t("sjc.done"));
    } catch (err) {
      dialog.querySelector("[data-error]").innerHTML = errorBox(err.message);
      save.disabled = false;
    }
  };
  save.addEventListener("click", submit);
  form.addEventListener("submit", (event) => { event.preventDefault(); submit(); });
  form.retained.focus();
}

// ------------------------------------------------------------------ payout

function openPayout(app, stay, remaining, onDone) {
  const { i18n } = app;
  const { t } = i18n;
  const today = app.session.today;
  const dialog = openDialog(app, {
    title: t("sjp.title"),
    subtitle: t("sjp.sub"),
    body: html`
      <form class="form-grid" novalidate>
        <div class="field"><label for="rc-p-date">${t("sjp.date")}</label><input id="rc-p-date" name="date" type="date" required value="${today}"></div>
        <div class="field"><label for="rc-p-amount">${t("sjp.amount")}</label><input id="rc-p-amount" name="amount" inputmode="decimal" autocomplete="off" value="${amountValue(remaining || null)}" aria-describedby="rc-p-amount-h">
          <span class="help" id="rc-p-amount-h">${remaining !== null ? t("sjp.amountHelp", { amount: i18n.money(remaining) }) : t("sjp.amountUnknown")}</span></div>
        <div class="field"><label for="rc-p-method">${t("sjp.method")}</label><input id="rc-p-method" name="method" maxlength="40" autocomplete="off" placeholder="${t("sjp.methodPh")}"></div>
        <div class="field"><label for="rc-p-note">${t("sjd.note")}</label><input id="rc-p-note" name="note" maxlength="300" autocomplete="off"></div>
        <p class="reading wide">${raw(icon("info"))}<span>${t("sjp.help")}</span></p>
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
      const result = await app.api.post(`/api/stays/${stay.id}/payouts`, {
        date: form.date.value, amount: cleanAmount(form.amount.value), method: form.method.value.trim(), note: form.note.value.trim(), op_id: op,
      });
      dialog.close();
      await onDone(result, t("sjp.done"));
    } catch (err) {
      dialog.querySelector("[data-error]").innerHTML = errorBox(err.message);
      save.disabled = false;
    }
  };
  save.addEventListener("click", submit);
  form.addEventListener("submit", (event) => { event.preventDefault(); submit(); });
  form.amount.focus();
}
