/* Copyright © 2026 Vincent Fournet */
// « Synthèse » — the overview screen.
// Three readings (Activité / Factures / Trésorerie), three key figures with
// their explanation, properties, things to check and upcoming stays.

import { html, raw } from "../dom.js";
import { icon, propertyIcon } from "../icons.js";

const MODES = ["activity", "invoice", "cash"];

export function filtersBar(v) {
  const { i18n, state, periodOptions, properties } = v;
  const { t } = i18n;
  return html`
    <div class="filters">
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
        <span class="sr-only">${t("filter.period")}</span>
        ${raw(icon("calendar", "lead"))}
        <select data-change="period">
          ${periodOptions.map((o) => html`<option value="${o.value}" ${raw(o.value === state.periodKey ? "selected" : "")}>${o.label}</option>`)}
        </select>
        ${raw(icon("chevronDown", "chev"))}
      </label>
    </div>`;
}

function modeSwitch(v) {
  const { t } = v.i18n;
  return html`
    <div class="segmented" role="group" aria-label="${t("mode.label")}">
      ${MODES.map((m) => html`<button type="button" data-action="mode" data-value="${m}" aria-pressed="${v.state.mode === m ? "true" : "false"}">${t(`mode.${m}`)}</button>`)}
    </div>`;
}

function delta(v, key, goodWhen) {
  const { i18n, overview } = v;
  if (overview.indicators[key]?.count === 0) {
    return html`<div class="delta flat"><span>${i18n.t("kpi.nodata")}</span></div>`;
  }
  const prev = overview.previous?.values?.[key];
  const cur = overview.indicators[key]?.value;
  const periodLabel = overview.previous ? periodName(v, overview.previous.period) : "";
  if (prev === null || prev === undefined || cur === null || cur === undefined || prev === 0) {
    return html`<div class="delta flat"><span>${i18n.t("kpi.nocompare")}</span></div>`;
  }
  const ratio = (cur - prev) / Math.abs(prev);
  const rounded = Math.round(ratio * 100);
  const cls = rounded === 0 ? "flat" : (ratio > 0) === (goodWhen === "up") ? "good" : "bad";
  return html`<div class="delta ${cls}"><b class="num">${i18n.percent(ratio)}</b><span>${i18n.t("kpi.vs", { period: periodLabel })}</span></div>`;
}

export function periodName(v, period) {
  const { i18n } = v;
  const start = period.start;
  const end = period.end;
  if (start.endsWith("-01-01") && end === `${Number(start.slice(0, 4)) + 1}-01-01`) return start.slice(0, 4);
  return i18n.monthLower(start);
}

function kpi(v, { id, labelKey, iconName, tone, goodWhen, hero = false }) {
  const { i18n, overview } = v;
  const item = overview.indicators[id];
  const label = id === "revenue" && v.state.mode === "cash" ? i18n.t("kpi.revenue.cash") : i18n.t(labelKey);
  const incomplete = item && item.complete === false && item.missing?.length
    ? html`<div class="incomplete">${raw(icon("alert"))}<span>${i18n.t("kpi.incomplete", { n: item.missing.length })}</span></div>` : "";
  return html`
    <article class="card kpi ${hero ? "hero" : ""}"><div class="kpi-body">
      <div class="bubble ${tone}">${raw(icon(iconName))}</div>
      <div>
        <div class="label">${label}</div>
        <div class="value num">${i18n.money(item?.value, { compact: true })}</div>
        ${delta(v, id, goodWhen)}
        ${incomplete}
      </div>
      <button type="button" class="howlink" data-action="explain" data-value="${id}">${raw(icon("help"))}<span>${i18n.t("kpi.how")}</span></button>
    </div></article>`;
}

function kpis(v) {
  // On phones the balance comes first and spans the width (hero), as on the boards.
  return html`
    <section class="kpis" aria-label="${v.i18n.t("nav.synthese")}">
      ${kpi(v, { id: "operating_balance", labelKey: "kpi.balance", iconName: "scale", tone: "teal", goodWhen: "up", hero: true })}
      ${kpi(v, { id: "revenue", labelKey: "kpi.revenue", iconName: "coins", tone: "teal", goodWhen: "up" })}
      ${kpi(v, { id: "operating_expenses", labelKey: "kpi.expenses", iconName: "wallet", tone: "rose", goodWhen: "down" })}
    </section>`;
}

function propertyMeta(v, p) {
  const { i18n } = v;
  const bits = [];
  if (p.capacity) bits.push(i18n.plural(p.capacity, "props.guest", "props.guests"));
  if (p.bedrooms) bits.push(i18n.plural(p.bedrooms, "props.bedroom", "props.bedrooms"));
  if (p.archived) bits.push(i18n.t("props.archived"));
  return bits.join(" · ");
}

function propertiesCard(v) {
  const { i18n, overview, properties, canWrite } = v;
  const { t } = i18n;
  const rows = properties.filter((p) => !p.archived || overview.by_property[p.id]);
  return html`
    <section class="card" aria-labelledby="rc-props">
      <div class="card-head">
        <span class="ico">${raw(icon("home"))}</span>
        <h2 id="rc-props">${t("props.title")}</h2>
        ${canWrite ? html`<button type="button" class="btn primary small end" data-action="add-property">${raw(icon("plus"))}${t("props.add")}</button>` : ""}
      </div>
      <div class="rows">
        ${rows.length ? rows.map((p) => {
          const f = overview.by_property[p.id] || { revenue: 0, expenses: 0, balance: 0 };
          const inScope = overview.property_ids.includes(p.id);
          return html`
            <button type="button" class="row" data-action="focus-property" data-value="${p.id}" aria-label="${t("props.focus", { name: p.name })}">
              <span class="tile">${raw(propertyIcon(p.kind))}</span>
              <span><span class="name">${p.name}</span><span class="meta">${propertyMeta(v, p)}</span></span>
              <span class="figures num">
                <div><b>${inScope ? i18n.money(f.revenue, { compact: true }) : "—"}</b><span>${t("props.revenue")}</span></div>
                <div><b>${inScope ? i18n.money(f.expenses, { compact: true }) : "—"}</b><span>${t("props.expenses")}</span></div>
                <div class="bal"><b>${inScope ? i18n.money(f.balance, { compact: true }) : "—"}</b><span>${t("props.balance")}</span></div>
              </span>
              <span class="chev">${raw(icon("chevronRight"))}</span>
            </button>`;
        }) : html`<div class="empty">${raw(icon("info"))}<span>${t("props.empty")}</span></div>`}
      </div>
    </section>`;
}

const CHECK_ICONS = {
  documents_incomplete: ["docAlert", "amber"],
  payouts_to_confirm: ["hourglass", "amber"],
  payments_unknown: ["hourglass", "amber"],
  stays_without_amount: ["alert", "amber"],
  allocations_incomplete: ["split", "blue"],
};
// Where each « À vérifier » item leads, and which list it opens there.
const CHECK_TARGET = {
  documents_incomplete: ["justificatifs", "incomplete"],
  payouts_to_confirm: ["sejours", "attention"],
  payments_unknown: ["depenses", "to_confirm"],
  stays_without_amount: ["sejours", "attention"],
  allocations_incomplete: ["prestataires"],
};

/** One « À vérifier » item. It only leads somewhere when that screen exists. */
export function checkItem(v, item) {
  const [ic, tone] = CHECK_ICONS[item.kind] || ["info", "amber"];
  const [target, view] = CHECK_TARGET[item.kind] || [];
  const body = html`
    <span class="bubble ${tone}">${raw(icon(ic))}</span>
    <span><b>${item.title}</b><p>${item.hint}</p></span>`;
  if (target && v.ready.has(target)) {
    return html`<button type="button" class="check" data-action="go" data-value="${target}" data-view="${view || ""}">${body}<span class="chev">${raw(icon("chevronRight"))}</span></button>`;
  }
  return html`<div class="check static">${body}</div>`;
}

function checksCard(v) {
  const { i18n, overview } = v;
  const items = overview.to_check || [];
  return html`
    <section class="card" aria-labelledby="rc-check">
      <div class="card-head">
        <span class="ico warn">${raw(icon("alert"))}</span>
        <h2 id="rc-check">${i18n.t("check.title")}</h2>
      </div>
      <div class="rows">
        ${items.length ? items.map((item) => checkItem(v, item)) : html`<div class="empty">${raw(icon("checkCircle"))}<span>${i18n.t("check.empty")}</span></div>`}
      </div>
    </section>`;
}

function statusPill(v, stay) {
  const { t } = v.i18n;
  if (stay.status === "provisional") return html`<span class="pill amber">${raw(icon("hourglass"))}${t("status.provisional")}</span>`;
  if (stay.timing === "in_progress") return html`<span class="pill blue">${raw(icon("moon"))}${t("status.in_progress")}</span>`;
  return html`<span class="pill teal">${raw(icon("calendar"))}${t("status.upcoming")}</span>`;
}

function guests(v, n) {
  if (!n) return "—";
  return v.i18n.plural(n, "props.guest", "props.guests");
}

function staysCard(v) {
  const { i18n, overview } = v;
  const { t } = i18n;
  const stays = overview.upcoming_stays || [];
  const next = stays[0];
  const linked = v.ready.has("sejours");
  return html`
    <section class="card" aria-labelledby="rc-stays">
      <div class="card-head">
        <span class="ico">${raw(icon("calendar"))}</span>
        <h2 id="rc-stays"><span class="desktop-only">${t("stays.title")}</span><span class="mobile-only">${t("stays.next")}</span></h2>
        ${linked ? html`
          <button type="button" class="btn ghost small end desktop-only" data-action="go" data-value="sejours">${t("stays.all")}${raw(icon("chevronRight"))}</button>
          <button type="button" class="linkbtn end mobile-only" data-action="go" data-value="sejours">${t("stays.allShort")}</button>` : ""}
      </div>
      ${stays.length ? html`
        <table class="table stays-table">
          <thead><tr>
            <th scope="col">${t("stays.arrival")}</th><th scope="col">${t("stays.departure")}</th><th scope="col">${t("stays.property")}</th>
            <th scope="col">${t("stays.status")}</th><th scope="col">${t("stays.guests")}</th>${linked ? html`<th scope="col"><span class="sr-only">${t("stays.actions")}</span></th>` : ""}
          </tr></thead>
          <tbody>
            ${stays.map((s) => html`<tr class="${linked ? "clickable" : ""}" ${raw(linked ? `data-action="stay-open" data-value="${s.id}"` : "")}>
              <td class="num">${i18n.dateLong(s.start)}</td>
              <td class="num">${i18n.dateLong(s.end)}</td>
              <td><span class="propcell">${raw(propertyIcon(s.property_kind))}<span>${s.property}</span></span></td>
              <td>${statusPill(v, s)}</td>
              <td>${guests(v, s.guests)}</td>
              ${linked ? html`<td><button type="button" class="iconbtn" data-action="stay-open" data-value="${s.id}" aria-label="${t("stays.actionsFor", { date: i18n.dateLong(s.start) })}">${raw(icon("chevronRight"))}</button></td>` : ""}
            </tr>`)}
          </tbody>
        </table>
        <div class="stays-cards">
          ${linked ? html`<button type="button" class="stay-card clickable" data-action="stay-open" data-value="${next.id}" aria-label="${t("stays.actionsFor", { date: i18n.dateLong(next.start) })}">
            <span class="tile">${raw(propertyIcon(next.property_kind))}</span>
            <span class="body">
              <span class="stay-title"><b>${next.property}</b>${statusPill(v, next)}</span>
              <span class="when num">${i18n.dateShort(next.start)} → ${i18n.dateShort(next.end)}</span>
              <span class="facts"><span>${raw(icon("users"))}${guests(v, next.guests)}</span><span>${raw(icon("moon"))}${i18n.plural(next.nights, "stays.night", "stays.nights")}</span></span>
            </span>
            <span class="chev">${raw(icon("chevronRight"))}</span>
          </button>` : ""}
        </div>` : html`<div class="empty">${raw(icon("calendar"))}<span>${t("stays.empty")}</span></div>`}
    </section>`;
}

function metric(v, { id, labelKey, value, sub = "", strong = false, explain = true, go = null }) {
  const { i18n } = v;
  const label = i18n.t(labelKey);
  return html`
    <div class="metric ${strong ? "strong" : ""}">
      <span class="what"><b>${label}</b>${sub ? html`<small>${sub}</small>` : ""}</span>
      <span class="num value">${i18n.money(value)}</span>
      ${explain ? html`<button type="button" class="iconbtn" data-action="explain" data-value="${id}" aria-label="${i18n.t("kpi.howFor", { label })}">${raw(icon("help"))}</button>`
        : go && v.ready.has(go[0]) ? html`<button type="button" class="iconbtn" data-action="go" data-value="${go[0]}" data-view="${go[1] || ""}" aria-label="${i18n.t("kpi.see", { label })}">${raw(icon("chevronRight"))}</button>`
        : html`<span></span>`}
    </div>`;
}

/** Investment, taxes and loan repayments: shown apart, they never change the operating balance. */
function beyondCard(v) {
  const { i18n, overview } = v;
  const { t } = i18n;
  const ind = overview.indicators;
  if (!["investment", "taxes", "financing"].some((key) => ind[key]?.value)) return "";
  const split = ind.financing.split || {};
  const parts = [["principal", "kpi.principal"], ["interest", "kpi.interest"], ["insurance", "kpi.insurance"], ["unknown", "kpi.unsplit"]]
    .filter(([key]) => split[key]).map(([key, label]) => `${t(label)} ${i18n.money(split[key])}`).join(" · ");
  return html`
    <section class="card" aria-labelledby="rc-beyond">
      <div class="card-head"><span class="ico">${raw(icon("scale"))}</span><h2 id="rc-beyond">${t("kpi.beyond")}</h2></div>
      <p class="reading">${t("kpi.beyondIntro")}</p>
      <div class="metrics">
        ${ind.investment.value ? metric(v, { id: "investment", labelKey: "kpi.investment", value: ind.investment.value }) : ""}
        ${ind.taxes.value ? metric(v, { id: "taxes", labelKey: "kpi.taxes", value: ind.taxes.value }) : ""}
        ${ind.financing.value ? metric(v, { id: "financing", labelKey: "kpi.financing", value: ind.financing.value, sub: parts }) : ""}
        ${metric(v, { id: "balance_after_financing", labelKey: v.state.mode === "cash" ? "kpi.afterCash" : "kpi.after", value: ind.balance_after_financing.value, strong: true })}
      </div>
    </section>`;
}

/** What is still to pay and to receive at the end of the period, with the list behind it. */
function settleCard(v) {
  const { i18n, overview } = v;
  const { t } = i18n;
  const ind = overview.indicators;
  if (!ind.to_pay?.value && !ind.to_receive?.value) return "";
  const receive = ind.to_receive;
  const sub = receive.entries && receive.stays
    ? t("kpi.receiveSplit", { stays: i18n.money(receive.stays), entries: i18n.money(receive.entries) })
    : receive.entries ? t("kpi.receiveEntries") : t("kpi.receiveStays");
  return html`
    <section class="card" aria-labelledby="rc-settle">
      <div class="card-head"><span class="ico">${raw(icon("hourglass"))}</span><h2 id="rc-settle">${t("kpi.settle")}</h2></div>
      <p class="reading">${t("kpi.settleIntro", { date: i18n.dateLong(prevDayIso(overview.period.end)) })}</p>
      <div class="metrics">
        ${metric(v, { id: "to_pay", labelKey: "kpi.toPay", value: ind.to_pay.value, explain: false, go: ["depenses", "to_pay"],
                      sub: i18n.plural(ind.to_pay.count || 0, "kpi.expenseOne", "kpi.expenseMany") })}
        ${metric(v, { id: "to_receive", labelKey: "kpi.toReceive", value: receive.value, explain: false,
                      go: receive.entries && !receive.stays ? ["depenses", "to_receive"] : ["sejours", "attention"], sub })}
      </div>
    </section>`;
}

function prevDayIso(iso) {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() - 1);
  return d.toISOString().slice(0, 10);
}

export function renderSynthese(v) {
  const { i18n, overview } = v;
  const { t } = i18n;
  return html`
    <header class="pagehead">
      <div>
        <h1>${t("synthese.title")}</h1>
        <p class="sub">${t("synthese.sub")}</p>
      </div>
      ${filtersBar(v)}
    </header>
    <div class="modebar">
      ${modeSwitch(v)}
      <p class="reading">${raw(icon("info"))}<span>${overview.reading}</span></p>
    </div>
    ${kpis(v)}
    ${v.canWrite ? html`<div class="quick mobile-only">
      <button type="button" class="btn primary" data-action="add-menu">${raw(icon("plus"))}${t("quick.add")}</button>
    </div>` : ""}
    <div class="mobile-only">${staysCard(v)}</div>
    <div class="grid-2">
      ${propertiesCard(v)}
      ${checksCard(v)}
    </div>
    ${beyondCard(v) || settleCard(v) ? html`<div class="grid-2">${beyondCard(v)}${settleCard(v)}</div>` : ""}
    <div class="desktop-only">${staysCard(v)}</div>`;
}
