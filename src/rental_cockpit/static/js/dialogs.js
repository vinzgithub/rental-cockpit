/* Copyright © 2026 Vincent Fournet */
// Dialogs: « Comment est calculé ce montant ? », the « Ajouter » menu and the
// property form. Native <dialog> gives focus trapping and Escape for free.

import { esc, html, markup, raw } from "./dom.js";
import { icon, propertyIcon } from "./icons.js";
import { openStayForm } from "./stay-dialogs.js";
import { checkItem, periodName } from "./views/synthese.js";

export function openDialog(app, { title, subtitle = "", body, footer, labelledby = "rc-dialog-title", wide = false }) {
  const dialog = document.createElement("dialog");
  dialog.className = "rc";
  if (wide) dialog.classList.add("dialog-wide");
  dialog.setAttribute("aria-labelledby", labelledby);
  dialog.innerHTML = markup(html`
    <div class="dhead">
      <div><h2 id="${labelledby}">${title}</h2>${subtitle ? html`<p>${subtitle}</p>` : ""}</div>
      <button type="button" class="iconbtn" data-close aria-label="${app.i18n.t("common.close")}">${raw(icon("close"))}</button>
    </div>
    <div class="dbody">${body}</div>
    ${footer ? html`<div class="dfoot">${footer}</div>` : ""}`);
  app.dialogHost.appendChild(dialog);
  dialog.addEventListener("click", (event) => {
    if ((event.target === dialog && !dialog.dataset.locked) || event.target.closest("[data-close]")) dialog.close();
  });
  dialog.addEventListener("close", () => dialog.remove());
  dialog.showModal();
  return dialog;
}

// ------------------------------------------------------------------ explain

export async function openExplain(app, indicatorId) {
  const { i18n } = app;
  const { t } = i18n;
  const v = app.viewModel();
  const dialog = openDialog(app, {
    title: t("explain.title"),
    subtitle: "",
    body: html`<div class="loading small"><div class="spinner"></div><span>${t("common.loading")}</span></div>`,
    footer: html`<button type="button" class="btn ghost" data-close>${t("explain.close")}</button>`,
    wide: true,
  });
  let detail;
  try {
    detail = await app.api.get("/api/indicator", { ...app.periodParams(), indicator: indicatorId });
  } catch (err) {
    dialog.querySelector(".dbody").innerHTML = markup(html`<div class="error-box">${raw(icon("alert"))}<span>${err.message}</span></div>`);
    return;
  }
  const ind = detail.indicator;
  const ov = app.state.overview;
  const scope = ov.properties.filter((p) => ov.property_ids.includes(p.id)).map((p) => p.name).join(", ") || "—";
  const lines = ind.lines || [];
  const equation = indicatorId === "operating_balance" ? html`
    <section class="card compact">
      <div class="card-head tight"><span class="bubble teal square">${raw(icon("chart"))}</span><h2>${t("explain.understand")}</h2></div>
      <div class="equation">
        <div class="term"><span>${ov.mode === "cash" ? t("kpi.revenue.cash") : t("kpi.revenue")}</span><div class="box num">${i18n.money(ov.indicators.revenue.value, { compact: true })}</div></div>
        <div class="op" aria-hidden="true">−</div>
        <div class="term"><span>${t("kpi.expenses")}</span><div class="box num">${i18n.money(ov.indicators.operating_expenses.value, { compact: true })}</div></div>
        <div class="op" aria-hidden="true">=</div>
        <div class="term"><span>${ind.label}</span><div class="box result num">${i18n.money(ind.value, { compact: true })}</div><small>${t("explain.before")}</small></div>
      </div>
    </section>` : "";
  const periodLabel = `${periodName(v, detail.period)} · ${i18n.dateShort(detail.period.start)} → ${i18n.dateShort(prevDay(detail.period.end))}`;
  const total = lines.reduce((sum, l) => sum + l.sign * l.share, 0);
  dialog.querySelector(".dhead h2").textContent = t("explain.title");
  dialog.querySelector(".dhead div").insertAdjacentHTML("beforeend", `<p>${esc(ind.label)} · <b class="num">${esc(i18n.money(ind.value))}</b></p>`);
  dialog.querySelector(".dbody").innerHTML = markup(html`
    ${equation}
    <dl class="facts-list">
      <div><dt>${t("explain.formula")}</dt><dd>${ind.formula}</dd></div>
      <div><dt>${t("explain.period")}</dt><dd>${periodLabel}</dd></div>
      <div><dt>${t("explain.reading")}</dt><dd>${detail.reading}</dd></div>
      <div><dt>${t("explain.scope")}</dt><dd>${scope}</dd></div>
      <div><dt>${t("explain.excludes")}</dt><dd>${ind.excludes}</dd></div>
    </dl>
    ${ind.missing?.length ? html`<div class="tip">${raw(icon("alert"))}<div><b>${t("explain.missing")}</b><ul>${ind.missing.map((m) => html`<li>${m.label}</li>`)}</ul></div></div>` : ""}
    <section>
      <h3 class="section-title">${t("explain.lines")} <span class="count">(${lines.length})</span></h3>
      ${lines.length ? html`
        <div class="lines-wrap">
          <table class="lines">
            <thead><tr><th>${t("explain.date")}</th><th>${t("explain.item")}</th><th>${t("explain.rule")}</th><th class="amt">${t("explain.total")}</th><th class="amt">${t("explain.share")}</th></tr></thead>
            <tbody>${lines.map((l) => html`<tr>
              <td class="num c-date">${i18n.dateShort(l.date)}</td>
              <td class="c-item">${l.label}<small>${l.property} · ${l.category}</small>${(l.ref_type === "stay" || l.ref_type === "stay_commission") && app.viewModel().ready.has("sejours") ? html`<button type="button" class="linkbtn small" data-action="stay-open" data-value="${l.ref_id}">${t("explain.openStay")}</button>` : ""}</td>
              <td class="c-rule">${l.rule}</td>
              <td class="amt num c-total" data-label="${t("explain.total")}${i18n.lang === "fr" ? " : " : ": "}">${i18n.money(l.total)}</td>
              <td class="amt num c-share">${l.sign < 0 ? "− " : ""}${i18n.money(l.share)}</td>
            </tr>`)}</tbody>
            <tfoot><tr><td colspan="4" class="c-item">${t("explain.sum")}</td><td class="amt num c-share">${i18n.money(total)}</td></tr></tfoot>
          </table>
        </div>` : html`<div class="empty">${raw(icon("info"))}<span>${t("explain.none")}</span></div>`}
    </section>
    ${ov.mode === "activity" ? html`<div class="tip">${raw(icon("bulb"))}<div><b>${t("explain.tip")}</b><p>${t("explain.tipText")}</p></div></div>` : ""}
  `);
}

function prevDay(iso) {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() - 1);
  return d.toISOString().slice(0, 10);
}

// ------------------------------------------------------------------ add menu

// Only what can really be recorded today is offered (no disabled « later » rows).
function addChoices(app) {
  const { t } = app.i18n;
  const choices = [];
  if ((app.viewModel().properties || []).some((p) => !p.archived)) {
    choices.push({ key: "stay", icon: "calendar", name: t("add.stay"), hint: t("add.stay.hint"), open: () => openStayForm(app) });
  }
  choices.push({ key: "property", icon: "home", name: t("add.property"), hint: t("add.property.hint"), open: () => openPropertyDialog(app) });
  return choices;
}

export function openAddMenu(app) {
  const { t } = app.i18n;
  const choices = addChoices(app);
  if (choices.length === 1) {
    choices[0].open();
    return;
  }
  const dialog = openDialog(app, {
    title: t("add.title"),
    subtitle: t("add.sub"),
    body: html`
      <div class="menu">${choices.map((c) => html`
        <button type="button" class="row" data-pick="${c.key}"><span class="tile">${raw(icon(c.icon))}</span><span><span class="name">${c.name}</span><span class="meta">${c.hint}</span></span></button>`)}
      </div>`,
  });
  for (const choice of choices) {
    dialog.querySelector(`[data-pick="${choice.key}"]`).addEventListener("click", () => {
      dialog.close();
      choice.open();
    });
  }
}

// ------------------------------------------------------------------ alerts (bell)

export function openAlerts(app) {
  const { t } = app.i18n;
  const items = app.state.overview?.to_check || [];
  const v = app.viewModel();
  const dialog = openDialog(app, {
    title: t("check.title"),
    subtitle: t("check.sub"),
    body: html`<div class="rows">${items.length ? items.map((item) => checkItem(v, item))
      : html`<div class="empty">${raw(icon("checkCircle"))}<span>${t("check.empty")}</span></div>`}</div>`,
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.close")}</button>`,
  });
  dialog.addEventListener("click", (event) => {
    if (event.target.closest('[data-action="go"]')) dialog.close();
  });
}

// ------------------------------------------------------------------ confirmation

/** A yes/no question before an action that cannot be undone. */
export function openConfirm(app, { title, text, confirm, danger = true, run }) {
  const { t } = app.i18n;
  const dialog = openDialog(app, {
    title,
    body: html`<p>${text}</p><div data-error aria-live="assertive"></div>`,
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.cancel")}</button><button type="button" class="btn ${danger ? "danger" : "primary"}" data-confirm>${confirm}</button>`,
  });
  const button = dialog.querySelector("[data-confirm]");
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      await run();
      dialog.close();
    } catch (err) {
      dialog.querySelector("[data-error]").innerHTML = markup(html`<div class="error-box">${raw(icon("alert"))}<span>${err.message}</span></div>`);
      button.disabled = false;
    }
  });
  button.focus();
  return dialog;
}

// ------------------------------------------------------------------ property form

export function openPropertyDialog(app) {
  const { t } = app.i18n;
  const kinds = ["apartment", "house", "studio", "room", "other"];
  const dialog = openDialog(app, {
    title: t("property.title"),
    subtitle: t("property.sub"),
    body: html`
      <form class="form-grid" novalidate>
        <div class="field wide"><label for="rc-p-name">${t("property.name")}</label><input id="rc-p-name" name="name" required maxlength="80" autocomplete="off" placeholder="${t("property.namePh")}"></div>
        <div class="field"><label for="rc-p-kind">${t("property.kind")}</label><select id="rc-p-kind" name="kind">${kinds.map((k) => html`<option value="${k}">${t(`property.kind.${k}`)}</option>`)}</select></div>
        <div class="field"><label for="rc-p-start">${t("property.start")}</label><input id="rc-p-start" name="activity_start" type="date" aria-describedby="rc-p-start-help"><span class="help" id="rc-p-start-help">${t("property.startHelp")}</span></div>
        <div class="field"><label for="rc-p-cap">${t("property.capacity")}</label><input id="rc-p-cap" name="capacity" type="number" min="0" max="999" inputmode="numeric"></div>
        <div class="field"><label for="rc-p-bed">${t("property.bedrooms")}</label><input id="rc-p-bed" name="bedrooms" type="number" min="0" max="999" inputmode="numeric"></div>
        <p class="reading wide">${raw(icon("info"))}<span>${t("property.currency")}</span></p>
        <div class="wide" data-error aria-live="assertive"></div>
      </form>`,
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.cancel")}</button><button type="button" class="btn primary" data-save>${raw(icon("check"))}${t("property.save")}</button>`,
  });
  const form = dialog.querySelector("form");
  const save = dialog.querySelector("[data-save]");
  const errorBox = dialog.querySelector("[data-error]");
  const op = app.newOpId();
  const submit = async () => {
    const data = Object.fromEntries(new FormData(form).entries());
    for (const key of ["capacity", "bedrooms", "activity_start"]) if (data[key] === "") delete data[key];
    save.disabled = true;
    save.lastChild.textContent = t("common.saving");
    errorBox.innerHTML = "";
    try {
      const result = await app.api.post("/api/properties", { ...data, op_id: op });
      dialog.close();
      app.toast(t("property.saved", { name: result.property.name }));
      await app.afterPropertyCreated(result.property.id);
    } catch (err) {
      errorBox.innerHTML = markup(html`<div class="error-box">${raw(icon("alert"))}<span>${err.message}</span></div>`);
      save.disabled = false;
      save.lastChild.textContent = t("property.save");
      dialog.querySelector("#rc-p-name").focus();
    }
  };
  save.addEventListener("click", submit);
  form.addEventListener("submit", (event) => { event.preventDefault(); submit(); });
  dialog.querySelector("#rc-p-name").focus();
}

export { propertyIcon };
