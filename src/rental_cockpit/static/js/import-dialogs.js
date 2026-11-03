/* Copyright © 2026 Vincent Fournet */
// « Importer des séjours » : an Airbnb export or any CSV file, checked line by
// line before anything is written, then « Imports précédents » with the undo.
//
// The server reads the file and computes the preview; this dialog only
// collects the person's choices (columns, property of each listing, decision
// on each line) and asks for a new preview after each change. Nothing is
// written until « Importer » is pressed, and the server checks again that the
// preview it would write is the one that was shown.

import { openConfirm, openDialog } from "./dialogs.js";
import { html, markup, raw } from "./dom.js";
import { icon } from "./icons.js";

const MAX_BYTES = 5 * 1024 * 1024;
const MAX_SHOWN = 200;
const STATUS_TONE = { new: "teal", update: "blue", same: "grey", duplicate: "amber", unmapped: "amber", error: "rose" };
const STATUS_ICON = { new: "plus", update: "repeat", same: "check", duplicate: "copy", unmapped: "home", error: "alert" };
const FILTERS = ["all", "notes", "operations", "new", "update", "duplicate", "same", "unmapped", "error"];
const FAMILY_ICON = { compensation: "shield", credit: "coins", adjustment: "repeat", unknown: "alert" };
const CSV_FIELDS = ["start", "end", "nights", "gross", "commission", "payout", "taxes_collected", "external_ref", "guest_label", "guests", "property", "paid_on"];
const CHANNELS = ["airbnb", "abritel", "booking", "direct", "other"];
const AMOUNT_FIELDS = new Set(["gross", "commission", "payout", "taxes_collected"]);

function errorBox(message) {
  return html`<div class="error-box" role="alert">${raw(icon("alert"))}<span>${message}</span></div>`;
}

function stepper(t, current) {
  return html`<ol class="stepper" aria-label="${t("imp.stepOf", { n: current })}">
    ${[1, 2, 3].map((n) => html`<li class="${n < current ? "done" : n === current ? "current" : ""}" ${raw(n === current ? 'aria-current="step"' : "")}><span class="n">${n < current ? raw(icon("check")) : n}</span><span>${t(`imp.step${n}`)}</span></li>`)}
  </ol>`;
}

function readFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1] || "");
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

function countsText(t, counts) {
  const parts = ["created", "updated", "completed", "payouts", "entries"].filter((k) => counts?.[k]).map((k) => t(`imp.cnt.${k}`, { n: counts[k] }));
  return parts.join(" · ") || "—";
}

// ------------------------------------------------------------------ wizard

export function openImport(app) {
  const { i18n } = app;
  const { t } = i18n;
  const s = {
    step: 1, kind: "airbnb", fileName: "", size: 0, content: "",
    keepNames: false, payouts: true, remember: true,
    mapping: null, dateOrder: "auto", rate: "", channel: "other", csvLoaded: false,
    propertyMap: {}, propertyId: "", decisions: {},
    preview: null, filter: "all", busy: false, error: "", seq: 0, result: null, op: app.newOpId(),
  };
  const dialog = openDialog(app, { title: t("imp.title"), subtitle: t("imp.sub1"), body: "", footer: html`<span></span>`, wide: true, labelledby: "rc-imp-title" });
  dialog.classList.add("import-dialog");
  dialog.dataset.locked = "1"; // a click beside the window does not throw the choices away
  const body = dialog.querySelector(".dbody");
  const foot = dialog.querySelector(".dfoot");
  const sub = dialog.querySelector(".dhead p");

  // -------------------------------------------------------------- requests

  const payload = () => {
    const options = { keep_names: s.keepNames, create_payouts: s.payouts, property_map: s.propertyMap, property_id: s.propertyId, decisions: s.decisions };
    if (s.kind === "csv") {
      if (s.mapping) options.mapping = s.mapping;
      options.date_order = s.dateOrder;
      if (s.csvLoaded) Object.assign(options, { commission_rate: s.rate, channel: s.channel });
    }
    return { kind: s.kind, content: s.content, file_name: s.fileName, options };
  };

  const adopt = (data) => {
    s.preview = data;
    s.propertyMap = { ...data.property_map };
    s.propertyId = data.property_id || "";
    if (data.kind === "csv") {
      s.mapping = { ...data.mapping };
      s.rate = data.commission_rate || "";
      s.channel = data.channel || "other";
      s.dateOrder = data.date_order_setting || s.dateOrder;
      s.csvLoaded = true;
    }
    const keys = new Set(data.rows.map((r) => r.key));
    s.decisions = Object.fromEntries(Object.entries(s.decisions).filter(([key]) => keys.has(key)));
  };

  const refresh = async () => {
    const seq = ++s.seq;
    s.busy = true;
    render();
    try {
      const data = await app.api.post("/api/imports/preview", payload());
      if (seq !== s.seq) return;
      adopt(data);
      s.step = 2;
      s.error = "";
    } catch (err) {
      if (seq !== s.seq) return;
      s.error = err.message;
      if (!s.preview) s.step = 1;
    }
    s.busy = false;
    render();
  };

  const apply = async () => {
    const counts = s.preview.counts;
    s.busy = true;
    s.applying = true;
    render();
    try {
      const result = await app.api.post("/api/imports/apply", {
        ...payload(), remember: s.remember, expect: { to_write: counts.to_write, payouts: counts.payouts, entries: counts.entries || 0 }, op_id: s.op,
      });
      s.result = result.import;
      s.step = 3;
      s.error = "";
      s.busy = false;
      s.applying = false;
      render();
      dialog.querySelector("[data-k='see']")?.focus();
      await app.afterStayChange();
    } catch (err) {
      s.busy = false;
      s.applying = false;
      s.error = err.code === "preview_stale" ? t("imp.stale") : err.message;
      if (err.code === "preview_stale") await refresh();
      else render();
    }
  };

  const chooseFile = async (file) => {
    if (!file) return;
    s.error = "";
    if (file.size > MAX_BYTES) s.error = t("imp.tooLarge");
    else if (!file.size) s.error = t("imp.emptyFile");
    if (s.error) {
      render();
      return;
    }
    try {
      s.content = await readFile(file);
    } catch (_) {
      s.error = t("imp.readFailed");
      render();
      return;
    }
    s.fileName = file.name;
    s.size = file.size;
    s.preview = null;
    s.decisions = {};
    s.filter = "all";
    render();
    dialog.querySelector("[data-k='check']")?.focus();
  };

  const resetFile = () => {
    Object.assign(s, { step: 1, fileName: "", size: 0, content: "", preview: null, decisions: {}, filter: "all", error: "" });
    render();
  };

  // -------------------------------------------------------------- views

  const kindStep = () => html`
    ${stepper(t, 1)}
    <fieldset class="imp-kinds">
      <legend class="section-title">${t("imp.kind")}</legend>
      ${["airbnb", "csv"].map((k) => html`
        <label class="imp-kind">
          <input type="radio" name="imp-kind" value="${k}" data-k="kind-${k}" ${raw(s.kind === k ? "checked" : "")}>
          <span class="tile">${raw(icon(k === "airbnb" ? "calendar" : "file"))}</span>
          <span><b>${t(`imp.kind.${k}`)}</b><small>${t(`imp.kind.${k}.hint`)}</small></span>
        </label>`)}
    </fieldset>
    <label class="dropzone ${s.fileName ? "has-file" : ""}" data-drop>
      <input type="file" class="sr-only" accept=".csv,.txt,text/csv,text/plain" data-k="file">
      <span class="tile">${raw(icon(s.fileName ? "file" : "upload"))}</span>
      <span><b>${s.fileName || t("imp.choose")}</b><small>${s.fileName ? t("imp.size", { size: i18n.size(s.size) }) : t("imp.drop")}</small></span>
    </label>
    <div class="tip">${raw(icon("bulb"))}<div><b>${t(`imp.where.${s.kind}`)}</b><p>${t(`imp.whereText.${s.kind}`)}</p></div></div>
    <p class="reading">${raw(icon("shieldCheck"))}<span>${t("imp.safe")}</span></p>
    ${s.error ? errorBox(s.error) : ""}`;

  const fileInfo = (p) => {
    const parts = [t(`imp.fileKind.${p.kind}`), p.encoding === "cp1252" ? "Windows-1252" : "UTF-8", p.delimiter];
    if (p.date_order === "DMY" || p.date_order === "MDY") parts.push(t("imp.dates", { order: t(`imp.order.${p.date_order}`) }));
    return html`
      <div class="imp-file">
        <span class="tile">${raw(icon("file"))}</span>
        <span><b>${s.fileName}</b><small>${parts.join(" · ")}</small></span>
        <button type="button" class="btn ghost small" data-k="change-file">${raw(icon("repeat"))}${t("imp.changeFile")}</button>
      </div>`;
  };

  const columns = (p) => {
    const orderFound = p.date_order === "DMY" || p.date_order === "MDY" ? t(`imp.order.${p.date_order}`) : "";
    return html`
      <section class="imp-section">
        <h3 class="section-title">${t("imp.columns")}</h3>
        <p class="reading">${raw(icon("info"))}<span>${t("imp.columnsHelp")}</span></p>
        <div class="imp-map">
          ${CSV_FIELDS.map((field) => {
            const chosen = s.mapping?.[field] || "";
            const sample = chosen ? p.samples?.[chosen] : "";
            const required = field === "start";
            return html`
              <div class="field">
                <label for="rc-imp-f-${field}">${t(`imp.field.${field}`)}${required ? html` <small class="req">· ${t("imp.required")}</small>` : ""}</label>
                <select id="rc-imp-f-${field}" data-map="${field}" data-k="map-${field}">
                  <option value="">${t("imp.noColumn")}</option>
                  ${p.headers.map((h) => html`<option value="${h}" ${raw(h === chosen ? "selected" : "")}>${h}</option>`)}
                </select>
                ${sample ? html`<span class="help">${t("imp.sample", { value: sample })}</span>` : ""}
              </div>`;
          })}
        </div>
        <div class="imp-map">
          <div class="field">
            <label for="rc-imp-order">${t("imp.dateOrder")}</label>
            <select id="rc-imp-order" data-k="order">
              ${["auto", "DMY", "MDY"].map((o) => html`<option value="${o}" ${raw(s.dateOrder === o ? "selected" : "")}>${o === "auto" && orderFound ? t("imp.dateOrder.autoFound", { order: orderFound }) : t(`imp.dateOrder.${o}`)}</option>`)}
            </select>
          </div>
          <div class="field">
            <label for="rc-imp-channel">${t("imp.channel")}</label>
            <select id="rc-imp-channel" data-k="channel" aria-describedby="rc-imp-channel-h">
              ${CHANNELS.map((c) => html`<option value="${c}" ${raw(s.channel === c ? "selected" : "")}>${t(`channel.${c}`)}</option>`)}
            </select>
            <span class="help" id="rc-imp-channel-h">${t("imp.channelHelp")}</span>
          </div>
          <div class="field">
            <label for="rc-imp-rate">${t("imp.rate")}</label>
            <input id="rc-imp-rate" data-k="rate" inputmode="decimal" autocomplete="off" maxlength="6" placeholder="${t("imp.ratePh")}" value="${s.rate}" aria-describedby="rc-imp-rate-h">
            <span class="help" id="rc-imp-rate-h">${t("imp.rateHelp")}</span>
          </div>
        </div>
      </section>`;
  };

  const propertyOptions = (p, chosen) => html`
    <option value="">${t("imp.propertyPick")}</option>
    ${p.properties.map((prop) => html`<option value="${prop.id}" ${raw(prop.id === chosen ? "selected" : "")}>${prop.name}</option>`)}`;

  const properties = (p) => html`
    <section class="imp-section">
      <h3 class="section-title">${t("imp.properties")}</h3>
      ${!p.properties.length ? errorBox(t("imp.noProperty")) : p.listings.length ? html`
        <p class="reading">${raw(icon("info"))}<span>${t("imp.propertiesHelp")}</span></p>
        <div class="imp-listings">${p.listings.map((listing, index) => html`
          <div class="imp-listing">
            <label for="rc-imp-l-${index}">${listing}</label>
            <select id="rc-imp-l-${index}" data-listing="${index}" data-k="listing-${index}">${propertyOptions(p, s.propertyMap[listing] || "")}</select>
          </div>`)}
        </div>` : html`
        <div class="imp-listing">
          <label for="rc-imp-prop">${t("imp.propertyFor")}</label>
          <select id="rc-imp-prop" data-k="property">${propertyOptions(p, s.propertyId)}</select>
        </div>`}
    </section>`;

  const optionsBlock = () => html`
    <section class="imp-section imp-opts">
      <h3 class="section-title">${t("imp.options")}</h3>
      <label class="check-line"><input type="checkbox" data-k="keep-names" ${raw(s.keepNames ? "checked" : "")}><span>${t("imp.keepNames")}<small>${t("imp.keepNamesHelp")}</small></span></label>
      <label class="check-line"><input type="checkbox" data-k="payouts" ${raw(s.payouts ? "checked" : "")}><span>${t("imp.payouts")}<small>${t("imp.payoutsHelp")}</small></span></label>
      <label class="check-line"><input type="checkbox" data-k="remember" ${raw(s.remember ? "checked" : "")}><span>${t("imp.remember")}</span></label>
    </section>`;

  const valueText = (field, value) => {
    if (value === null || value === undefined || value === "") return "—";
    if (AMOUNT_FIELDS.has(field)) return i18n.money(value);
    if (field === "start" || field === "end") return i18n.dateShort(value);
    return String(value);
  };

  const amountsText = (a) => {
    if (!a) return "";
    const parts = [["gross", "imp.gross"], ["commission", "imp.commission"], ["payout", "imp.net"], ["taxes_collected", "imp.taxes"]]
      .filter(([key]) => a[key] !== null && a[key] !== undefined).map(([key, label]) => `${t(label)} ${i18n.money(a[key])}`);
    return parts.length ? parts.join(" · ") : t("imp.noAmount");
  };

  const decisionSelect = (r, prefix) => r.choices.length ? html`
    <label class="decision"><span>${t("imp.decision")}</span>
      <select data-decision="${r.key}" data-k="dec-${r.key}">${r.choices.map((c) => html`<option value="${c}" ${raw(c === r.decision ? "selected" : "")}>${t(`imp.dec.${prefix}.${c}`)}</option>`)}</select>
    </label>` : "";

  const operationCard = (r) => html`
    <article class="imp-row op ${r.status}">
      <header>
        <span class="pill ${r.status === "new" ? (r.family === "unknown" ? "amber" : "teal") : STATUS_TONE[r.status] || "grey"}">${raw(icon(r.status === "new" ? FAMILY_ICON[r.family] || "info" : STATUS_ICON[r.status] || "info"))}${r.status === "new" ? t(`imp.family.${r.family}`) : r.status_label}</span>
        <b>${r.type_label}</b>
        <small class="num">${t("imp.lineN", { n: r.lines[0] })}</small>
      </header>
      ${r.amount !== null && r.amount !== undefined ? html`<p class="num">${raw(icon("coins"))}<span><b>${r.direction === "out" ? "− " : "+ "}${i18n.money(r.amount)}</b> · ${r.date ? i18n.dateShort(r.date) : "—"}${r.category ? html` · ${r.category}` : ""}</span></p>` : ""}
      ${r.label ? html`<p>${raw(icon("receipt"))}<span>${t(r.direction === "out" ? "imp.opExpense" : "imp.opIncome", { label: r.label })}</span></p>` : ""}
      ${r.property ? html`<p>${raw(icon("home"))}<span>${r.property}</span></p>` : ""}
      ${(r.facts || []).map((f, i, all) => {
        const paid = r.payout && r.decision !== "skip" && i === all.length - 1;  // the payout comes last
        return html`<p class="${paid ? "ok" : ""}">${raw(icon(paid ? "check" : "info"))}<span>${f}</span></p>`;
      })}
      ${r.errors.map((e) => html`<p class="msg err">${raw(icon("alert"))}<span>${e}</span></p>`)}
      ${r.warnings.map((w) => html`<p class="msg warn">${raw(icon("info"))}<span>${w}</span></p>`)}
      ${decisionSelect(r, r.status === "same" ? "same" : "op")}
    </article>`;

  const rowCard = (r) => {
    if (r.kind === "operation") return operationCard(r);
    const title = r.external_ref || r.guest_label || t("imp.lineN", { n: r.lines[0] });
    const lines = r.lines.length > 1 ? t("imp.linesN", { list: r.lines.join(", ") }) : t("imp.lineN", { n: r.lines[0] });
    const facts = r.start ? [i18n.range(r.start, r.end), i18n.plural(r.nights, "stays.night", "stays.nights")] : [];
    if (r.guests) facts.push(i18n.plural(r.guests, "props.guest", "props.guests"));
    return html`
      <article class="imp-row ${r.status}">
        <header>
          <span class="pill ${STATUS_TONE[r.status] || "grey"}">${raw(icon(STATUS_ICON[r.status] || "info"))}${r.status_label}</span>
          <b>${title}</b>
          <small class="num">${lines}</small>
        </header>
        ${facts.length ? html`<p class="num">${raw(icon("calendar"))}<span>${facts.join(" · ")}</span></p>` : ""}
        ${r.property ? html`<p>${raw(icon("home"))}<span>${r.property}${r.listing ? html` <small>· ${t("imp.listing", { listing: r.listing })}</small>` : ""}</span></p>`
          : r.listing ? html`<p>${raw(icon("home"))}<span>${t("imp.listing", { listing: r.listing })}</span></p>` : ""}
        ${r.amounts ? html`<p class="num">${raw(icon("coins"))}<span>${amountsText(r.amounts)}</span></p>` : ""}
        ${r.payout && r.decision !== "skip" ? html`<p class="ok">${raw(icon("check"))}<span>${t(r.payout.bank_by ? "imp.payoutLineBank" : "imp.payoutLine", { amount: i18n.money(r.payout.amount), date: i18n.dateShort(r.payout.date), bank: r.payout.bank_by ? i18n.dateShort(r.payout.bank_by) : "" })}</span></p>` : ""}
        ${r.decision === "cancelled" ? html`<p class="ok">${raw(icon("ban"))}<span>${t("imp.cancelledLine")}</span></p>` : ""}
        ${r.status === "duplicate" && r.stay_id ? html`<p>${raw(icon("copy"))}<span>${t("imp.twin", { label: r.twin_label })}</span></p>` : ""}
        ${r.changes.length && r.decision !== "skip" && (r.status === "update" || r.decision === "complete") ? html`
          <div class="changes"><b>${t(r.status === "update" ? "imp.changes" : "imp.fills")}</b>
            <ul>${r.changes.map((c) => html`<li>${c.label} : ${r.status === "update" ? html`<span class="num">${valueText(c.field, c.before)}</span> → ` : ""}<b class="num">${valueText(c.field, c.after)}</b></li>`)}</ul>
          </div>` : ""}
        ${r.errors.map((e) => html`<p class="msg err">${raw(icon("alert"))}<span>${e}</span></p>`)}
        ${r.warnings.map((w) => html`<p class="msg warn">${raw(icon("info"))}<span>${w}</span></p>`)}
        ${decisionSelect(r, r.status)}
      </article>`;
  };

  // « Bilan des versements » : every payout of the file and what would stay unrecorded (ANO-001).
  const reconciliation = (p) => {
    const rec = p.reconciliation;
    if (!rec) return "";
    const k = rec.kinds;
    const parts = [["stay", "imp.rec.stays"], ["compensation", "imp.rec.compensation"], ["credit", "imp.rec.credit"], ["adjustment", "imp.rec.adjustment"], ["unknown", "imp.rec.unknown"]]
      .filter(([key]) => k[key]);
    const left = rec.states.left;
    return html`
      <section class="imp-section imp-rec" aria-labelledby="rc-imp-rec">
        <h3 class="section-title" id="rc-imp-rec">${t("imp.rec.title")}</h3>
        <dl class="facts-list money-facts">
          <div><dt><b>${t("imp.rec.total", { n: rec.count })}</b></dt><dd class="num"><b>${i18n.money(rec.total)}</b></dd></div>
          ${parts.map(([key, label]) => html`<div><dt>${t(label)}</dt><dd class="num">${i18n.money(k[key])}</dd></div>`)}
        </dl>
        ${left ? html`<div class="tip warn" role="status">${raw(icon("alert"))}<div><b>${t("imp.rec.leftTitle", { amount: i18n.money(left) })}</b>
            <p>${t("imp.rec.leftText")}</p>
            <ul>${rec.left.map((l) => html`<li><span class="num">${i18n.money(l.amount)}</span> · ${l.ref || t("imp.lineN", { n: l.line })} · ${t(`imp.rec.kind.${l.kind}`)} · ${i18n.dateShort(l.date)}</li>`)}</ul></div></div>`
          : html`<p class="reading ok">${raw(icon("checkCircle"))}<span>${t(rec.states.new ? "imp.rec.allNew" : "imp.rec.allKnown")}</span></p>`}
        ${rec.mismatched.length ? html`<div class="tip warn">${raw(icon("alert"))}<div><b>${t("imp.rec.mismatch")}</b>
            <ul>${rec.mismatched.map((m) => html`<li>${t("imp.lineN", { n: m.line })} · ${i18n.money(m.amount)} ≠ ${i18n.money(m.explained)}</li>`)}</ul></div></div>` : ""}
        <details class="imp-months">
          <summary>${t("imp.rec.byMonth")}</summary>
          <table class="table compact-table">
            <thead><tr><th scope="col">${t("imp.rec.month")}</th><th scope="col" class="amt">${t("imp.rec.sent")}</th><th scope="col" class="amt">${t("imp.rec.ofStays")}</th><th scope="col" class="amt">${t("imp.rec.ofOther")}</th><th scope="col" class="amt">${t("imp.rec.notRecorded")}</th></tr></thead>
            <tbody>${rec.months.map((m) => html`<tr><td>${i18n.month(m.month + "-01")}</td><td class="amt num">${i18n.money(m.total)}</td><td class="amt num">${i18n.money(m.stay)}</td><td class="amt num">${i18n.money(m.other)}</td><td class="amt num ${m.left ? "warn-text" : ""}">${m.left ? i18n.money(m.left) : "—"}</td></tr>`)}</tbody>
          </table>
        </details>
      </section>`;
  };

  const results = (p) => {
    const notable = (r) => r.errors.length || r.warnings.length;
    const counts = { ...p.counts, all: p.rows.length, notes: p.rows.filter(notable).length };
    const shown = p.rows.filter((r) => s.filter === "all" || (s.filter === "notes" ? notable(r)
      : s.filter === "operations" ? r.kind === "operation" : r.kind !== "operation" && r.status === s.filter));
    return html`
      <section class="imp-section">
        <h3 class="section-title">${t("imp.result")}</h3>
        <div class="chips" role="tablist" aria-label="${t("imp.filter")}">
          ${FILTERS.filter((f) => f === "all" || counts[f]).map((f) => html`
            <button type="button" role="tab" class="chip ${f === "error" || f === "duplicate" || f === "unmapped" ? "warn" : ""}" aria-selected="${s.filter === f ? "true" : "false"}" data-filter="${f}" data-k="filter-${f}">${t(`imp.filter.${f}`)}<span class="n num">${counts[f]}</span></button>`)}
        </div>
        <div class="imp-rows" aria-live="polite">
          ${shown.length ? shown.slice(0, MAX_SHOWN).map(rowCard) : html`<div class="empty">${raw(icon("info"))}<span>${t("imp.noRows")}</span></div>`}
        </div>
        ${shown.length > MAX_SHOWN ? html`<p class="reading">${raw(icon("info"))}<span>${t("imp.more", { n: shown.length - MAX_SHOWN })}</span></p>` : ""}
      </section>`;
  };

  const checkStep = () => {
    const p = s.preview;
    const blocked = p.errors.length > 0;
    return html`
      ${stepper(t, 2)}
      ${fileInfo(p)}
      ${s.error ? errorBox(s.error) : ""}
      ${blocked ? html`
        <div class="error-box" role="alert">${raw(icon("alert"))}<div><b>${t("imp.blocking")}</b><ul>${p.errors.map((e) => html`<li>${e}</li>`)}</ul>
          ${s.kind === "airbnb" ? html`<button type="button" class="btn ghost small" data-k="to-csv">${raw(icon("file"))}${t("imp.toCsv")}</button>` : ""}</div></div>` : ""}
      ${p.notices.length ? html`<div class="tip">${raw(icon("info"))}<div><b>${t("imp.notices")}</b><ul>${p.notices.map((n) => html`<li>${n}</li>`)}</ul></div></div>` : ""}
      ${p.kind === "csv" && p.headers.length ? columns(p) : ""}
      ${blocked && !p.rows.length ? "" : html`${properties(p)}${optionsBlock()}${reconciliation(p)}${results(p)}`}`;
  };

  const doneStep = () => {
    const r = s.result;
    return html`
      ${stepper(t, 3)}
      <div class="imp-done"><span class="bubble teal big">${raw(icon("checkCircle"))}</span><div><h3>${t("imp.doneTitle")}</h3><p>${t("imp.doneSub", { file: r.file_name || s.fileName })}</p></div></div>
      <dl class="facts-list money-facts">
        ${["created", "updated", "completed", "payouts", "entries"].filter((k) => k !== "entries" || r.counts.entries).map((k) => html`<div><dt>${t(k === "payouts" ? "imp.payoutsDone" : `imp.${k}`)}</dt><dd class="num">${r.counts[k]}</dd></div>`)}
      </dl>
      ${s.error ? errorBox(s.error) : ""}
      <p class="reading">${raw(icon("info"))}<span>${t("imp.undoHelp")}</span></p>`;
  };

  const footer = () => {
    if (s.step === 1) {
      return html`
        <button type="button" class="btn ghost back" data-k="history">${raw(icon("repeat"))}${t("imp.history")}</button>
        <button type="button" class="btn ghost" data-close>${t("common.cancel")}</button>
        <button type="button" class="btn primary" data-k="check" ${raw(!s.content || s.busy ? "disabled" : "")}>${raw(icon(s.busy ? "hourglass" : "eye"))}${t(s.busy ? "imp.checking" : "imp.check")}</button>`;
    }
    if (s.step === 2) {
      const c = s.preview.counts;
      const what = [c.to_write ? i18n.plural(c.to_write, "imp.nStay", "imp.nStays") : "", c.entries ? i18n.plural(c.entries, "imp.nEntry", "imp.nEntries") : "",
        c.payouts ? i18n.plural(c.payouts, "imp.nPayout", "imp.nPayouts") : ""].filter(Boolean)
        .reduce((text, part, index, all) => !index ? part : text + (index === all.length - 1 ? t("imp.and") : ", ") + part, "");
      const label = s.applying ? t("imp.applying") : s.busy ? t("imp.checking") : s.preview.can_apply ? t("imp.apply", { what }) : t("imp.nothing");
      return html`
        <button type="button" class="btn ghost back" data-k="back">${t("common.back")}</button>
        <button type="button" class="btn ghost" data-close>${t("common.cancel")}</button>
        <button type="button" class="btn primary" data-k="apply" ${raw(!s.preview.can_apply || s.busy ? "disabled" : "")}>${raw(icon(s.busy ? "hourglass" : "check"))}${label}</button>`;
    }
    return html`
      <button type="button" class="btn ghost danger-text back" data-k="undo">${raw(icon("repeat"))}${t("imp.undo")}</button>
      <button type="button" class="btn ghost" data-close>${t("common.close")}</button>
      <button type="button" class="btn primary" data-k="see">${raw(icon("calendar"))}${t("imp.seeStays")}</button>`;
  };

  function render() {
    const active = dialog.querySelector(":focus");
    const key = active?.dataset?.k;
    const scroll = body.scrollTop;
    sub.textContent = s.step === 1 ? t("imp.sub1") : s.step === 2 ? s.fileName : t("imp.sub3");
    body.innerHTML = markup(s.step === 1 ? kindStep() : s.step === 2 ? checkStep() : doneStep());
    foot.innerHTML = markup(footer());
    foot.classList.add("imp-foot");
    body.scrollTop = scroll;
    if (key) dialog.querySelector(`[data-k="${CSS.escape(key)}"]`)?.focus({ preventScroll: true });
  }

  // -------------------------------------------------------------- events

  dialog.addEventListener("change", (event) => {
    const el = event.target;
    const k = el.dataset.k || "";
    if (k.startsWith("kind-")) {
      s.kind = el.value;
      Object.assign(s, { preview: null, mapping: null, dateOrder: "auto", csvLoaded: false, decisions: {}, propertyMap: {}, propertyId: "", error: "" });
      render();
    } else if (k === "file") {
      chooseFile(el.files?.[0]);
    } else if (el.dataset.map) {
      s.mapping = { ...(s.mapping || {}) };
      if (el.value) s.mapping[el.dataset.map] = el.value;
      else delete s.mapping[el.dataset.map];
      refresh();
    } else if (el.dataset.listing !== undefined) {
      s.propertyMap = { ...s.propertyMap, [s.preview.listings[Number(el.dataset.listing)]]: el.value };
      refresh();
    } else if (el.dataset.decision) {
      s.decisions = { ...s.decisions, [el.dataset.decision]: el.value };
      refresh();
    } else if (k === "property") {
      s.propertyId = el.value;
      refresh();
    } else if (k === "order") {
      s.dateOrder = el.value;
      refresh();
    } else if (k === "channel") {
      s.channel = el.value;
      refresh();
    } else if (k === "rate") {
      s.rate = el.value.trim();
      refresh();
    } else if (k === "keep-names") {
      s.keepNames = el.checked;
      refresh();
    } else if (k === "payouts") {
      s.payouts = el.checked;
      refresh();
    } else if (k === "remember") {
      s.remember = el.checked;
    }
  });

  dialog.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && event.target.dataset.k === "rate") {
      event.preventDefault();
      event.target.blur();
    }
  });

  dialog.addEventListener("click", (event) => {
    const filter = event.target.closest("[data-filter]");
    if (filter) {
      s.filter = filter.dataset.filter;
      render();
      return;
    }
    const k = event.target.closest("[data-k]")?.dataset.k;
    if (k === "check") refresh();
    else if (k === "apply") apply();
    else if (k === "back" || k === "change-file") resetFile();
    else if (k === "history") openImportHistory(app);
    else if (k === "to-csv") {
      Object.assign(s, { kind: "csv", preview: null, mapping: null, csvLoaded: false, decisions: {}, propertyMap: {}, propertyId: "" });
      refresh();
    } else if (k === "see") {
      dialog.close();
      app.showStays("all");
    } else if (k === "undo") {
      openConfirm(app, {
        title: t("imp.undoTitle"), text: t("imp.undoText"), confirm: t("imp.undo"),
        run: async () => {
          await app.api.post(`/api/imports/${encodeURIComponent(s.result.id)}/undo`, {});
          dialog.close();
          app.toast(t("imp.undone"));
          await app.afterStayChange();
        },
      });
    }
  });

  const zone = () => dialog.querySelector("[data-drop]");
  dialog.addEventListener("dragover", (event) => {
    if (s.step !== 1) return;
    event.preventDefault();
    zone()?.classList.add("over");
  });
  dialog.addEventListener("dragleave", (event) => {
    if (!dialog.contains(event.relatedTarget)) zone()?.classList.remove("over");
  });
  dialog.addEventListener("drop", (event) => {
    if (s.step !== 1) return;
    event.preventDefault();
    zone()?.classList.remove("over");
    chooseFile(event.dataTransfer?.files?.[0]);
  });

  render();
  dialog.querySelector(`[data-k="kind-${s.kind}"]`)?.focus();
  return dialog;
}

// ------------------------------------------------------------------ history

export async function openImportHistory(app) {
  const { i18n } = app;
  const { t } = i18n;
  const dialog = openDialog(app, {
    title: t("imp.historyTitle"),
    subtitle: t("imp.historySub"),
    body: html`<div class="loading small"><div class="spinner"></div><span>${t("common.loading")}</span></div>`,
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.close")}</button>`,
  });
  const fill = async () => {
    let data;
    try {
      data = await app.api.get("/api/imports");
    } catch (err) {
      dialog.querySelector(".dbody").innerHTML = markup(errorBox(err.message));
      return;
    }
    const blocked = data.blockers.length > 0;
    dialog.querySelector(".dbody").innerHTML = markup(html`
      ${data.imports.length ? html`<div class="rows">${data.imports.map((item) => html`
        <div class="keyrow imp-hist">
          <span class="tile">${raw(icon(item.kind === "airbnb" ? "calendar" : "file"))}</span>
          <span><b>${item.file_name || t(`imp.fileKind.${item.kind}`)}</b>
            <small>${i18n.dateTime(item.at)} · ${t(`imp.fileKind.${item.kind}`)} · ${countsText(t, item.counts)}</small>
            ${item.undone_at ? html`<span class="pill grey">${raw(icon("ban"))}${t("imp.undoneOn", { date: i18n.dateTime(item.undone_at) })}</span>` : ""}</span>
          ${item.id === data.last_id && !item.undone_at && app.canWrite ? html`<button type="button" class="btn ghost small danger-text" data-undo="${item.id}" ${raw(blocked ? "disabled" : "")}>${raw(icon("repeat"))}${t("imp.undo")}</button>` : ""}
        </div>`)}</div>` : html`<div class="empty">${raw(icon("info"))}<span>${t("imp.historyEmpty")}</span></div>`}
      ${blocked ? html`<div class="tip">${raw(icon("alert"))}<div><p>${t("imp.blocked", { stays: data.blockers.join(", ") })}</p></div></div>` : ""}`);
    dialog.querySelector("[data-undo]")?.addEventListener("click", () => openConfirm(app, {
      title: t("imp.undoTitle"), text: t("imp.undoText"), confirm: t("imp.undo"),
      run: async () => {
        await app.api.post(`/api/imports/${encodeURIComponent(data.last_id)}/undo`, {});
        app.toast(t("imp.undone"));
        await app.afterStayChange();
        await fill();
      },
    }));
  };
  await fill();
}
