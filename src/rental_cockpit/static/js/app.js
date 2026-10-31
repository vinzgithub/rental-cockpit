/* Copyright © 2026 Vincent Fournet */
// Rental Cockpit interface: shell, navigation, sign-in and state.
//
// The page is rendered from templates whose values are always escaped
// (see dom.js). Every figure comes from the server, which checks the rights
// of the signed-in account on each request.

import { Api } from "./api.js";
import { openAddMenu, openAlerts, openConfirm, openExplain, openPropertyDialog } from "./dialogs.js";
import { openStay, openStayForm } from "./stay-dialogs.js";
import { esc, html, markup, opId, raw } from "./dom.js";
import { makeI18n } from "./i18n.js";
import { icon } from "./icons.js";
import { langSwitch, renderAuth } from "./views/auth.js";
import { openCreateKey, openMfaCodes, openMfaDisable, openMfaEnable, openPasswordDialog, openRevokeKey, copyText } from "./settings-dialogs.js";
import { datasetSwitch } from "./views/dataset.js";
import { renderSettings } from "./views/settings.js";
import { renderStays, STAY_VIEWS } from "./views/stays.js";
import { renderSynthese } from "./views/synthese.js";
import { renderNoAccess, renderOnboarding, renderWelcome } from "./views/welcome.js";

// A screen enters the menu only once it works: no « coming soon » page.
// Dépenses, Prestataires and Documents join this list as they are delivered.
const SCREENS = [
  ["synthese", "chart"],
  ["sejours", "calendar"],
  ["reglages", "sliders"],
];
const READY = new Set(SCREENS.map(([key]) => key));
const STORE_KEY = "rental-cockpit.view";

// Per-browser conveniences only (screen, reading, language). Never data.
function readPrefs() {
  try { return JSON.parse(localStorage.getItem(STORE_KEY) || "{}") || {}; } catch (_) { return {}; }
}
function writePrefs(update) {
  try { localStorage.setItem(STORE_KEY, JSON.stringify({ ...readPrefs(), ...update })); } catch (_) { /* private browsing */ }
}

export class App {
  constructor(root) {
    this.root = root;
    this.state = { screen: "synthese", mode: "activity", propertyId: "all", periodKey: "", loading: true, error: "", overview: null, account: null,
      stays: { view: "active", q: "", data: null } };
    this.searchTimer = null;
    this.auth = { error: "", busy: false, mfa: false, username: "" };
    this.session = null;
  }

  get boot() { return this.session; }

  async start() {
    const prefs = readPrefs();
    const lang = prefs.lang || (navigator.language || "fr").slice(0, 2);
    this._setLang(lang);
    this.root.innerHTML = `<div class="page"></div><div class="dialogs"></div><div class="toast-host" role="status" aria-live="polite"></div>`;
    this.pageEl = this.root.querySelector(".page");
    this.dialogHost = this.root.querySelector(".dialogs");
    this.toastHost = this.root.querySelector(".toast-host");
    this.root.addEventListener("click", (event) => this._onClick(event));
    this.root.addEventListener("change", (event) => this._onChange(event));
    this.root.addEventListener("submit", (event) => this._onSubmit(event));
    this.root.addEventListener("input", (event) => this._onInput(event));
    this._render();
    await this.refreshSession();
  }

  _setLang(lang) {
    this.i18n = makeI18n(lang);
    document.documentElement.lang = this.i18n.lang;
    if (this.api) this.api.lang = this.i18n.lang;
    else {
      this.api = new Api(this.i18n.lang);
      this.api.onLoginRequired = () => this._sessionLost();
    }
  }

  async refreshSession() {
    try {
      this.session = await this.api.request("GET", "/api/session");
    } catch (err) {
      this.state.loading = false;
      this.state.error = err.message;
      this._render();
      return;
    }
    if (!readPrefs().lang && this.session.default_locale && !navigator.language) this._setLang(this.session.default_locale);
    if (!this.session.authenticated) {
      this.state.loading = false;
      this._render();
      this.root.querySelector("#rc-u")?.focus();
      return;
    }
    const prefs = readPrefs();
    let dataset = prefs.dataset || (this.session.real.first_choice === "demo" ? "demo" : "real");
    if (dataset === "demo" && !this.session.demo.exists) dataset = "real";
    this.api.dataset = dataset;
    this.state.mode = prefs.mode || "activity";
    this.state.screen = READY.has(prefs.screen) ? prefs.screen : "synthese";
    if (!this.state.periodKey) this.state.periodKey = this._defaultPeriodKey();
    await this.load();
    if (this.state.screen === "reglages") await this.loadAccount();
    if (this.state.screen === "sejours") await this.loadStays();
  }

  _sessionLost() {
    if (this.session) this.session.authenticated = false;
    this.state.overview = null;
    this.auth = { error: this.i18n.t("auth.loginSub"), busy: false, mfa: false, username: "" };
    this.dialogHost.querySelectorAll("dialog").forEach((d) => d.close());
    this.refreshSession();
  }

  _defaultPeriodKey() {
    const focus = this.api.dataset === "demo" ? this.session.demo.focus : null;
    const day = focus ? focus.start : this.session.today;
    return `m:${day.slice(0, 7)}`;
  }

  get isDemo() { return this.api.dataset === "demo"; }
  get canWrite() { return Boolean(this.session?.user?.is_admin); }
  get showWelcome() { return this.session?.authenticated && !this.session.real.first_choice && !this.isDemo; }

  newOpId() { return opId(); }

  periodBounds(key = this.state.periodKey) {
    const [kind, value] = key.split(":");
    if (kind === "y") return { start: `${value}-01-01`, end: `${Number(value) + 1}-01-01` };
    const [y, m] = value.split("-").map(Number);
    const end = m === 12 ? `${y + 1}-01-01` : `${y}-${String(m + 1).padStart(2, "0")}-01`;
    return { start: `${value}-01`, end };
  }

  periodParams() {
    return { property_id: this.state.propertyId, mode: this.state.mode, ...this.periodBounds() };
  }

  periodOptions() {
    const today = this.session.today;
    const props = this.state.overview?.properties || [];
    const starts = props.map((p) => p.activity_start).filter(Boolean).sort();
    const first = starts[0] && starts[0] < today ? starts[0] : null;
    const anchor = this.isDemo && this.session.demo.focus ? this.session.demo.focus.start : today;
    const [ty, tm] = anchor.split("-").map(Number);
    let y = ty, m = tm + 3;
    if (m > 12) { y += 1; m -= 12; }
    const limit = first ? Number(first.slice(0, 4)) * 12 + Number(first.slice(5, 7)) - 1 : ty * 12 + tm - 1 - 24;
    const months = [];
    for (let index = y * 12 + m - 1; index >= limit && months.length < 60; index -= 1) {
      const yy = Math.floor(index / 12), mm = (index % 12) + 1;
      const iso = `${yy}-${String(mm).padStart(2, "0")}-01`;
      months.push({ value: `m:${iso.slice(0, 7)}`, label: this.i18n.month(iso) });
    }
    const years = [...new Set(months.map((o) => o.value.slice(2, 6)))].map((yy) => ({ value: `y:${yy}`, label: this.i18n.t("filter.year", { year: yy }) }));
    const options = [...months, ...years];
    if (!options.some((o) => o.value === this.state.periodKey)) {
      const key = this.state.periodKey;
      options.unshift({ value: key, label: key.startsWith("y:") ? this.i18n.t("filter.year", { year: key.slice(2) }) : this.i18n.month(`${key.slice(2)}-01`) });
    }
    return options;
  }

  // ---------------------------------------------------------------- data

  async load() {
    if (this.showWelcome) {
      this.state.loading = false;
      this._render();
      return;
    }
    this.state.loading = !this.state.overview;
    this.state.error = "";
    this._render();
    try {
      const overview = await this.api.get("/api/overview", this.periodParams());
      if (this.state.propertyId !== "all" && !overview.properties.some((p) => p.id === this.state.propertyId)) {
        this.state.propertyId = "all";
        return this.load();
      }
      this.state.overview = overview;
    } catch (err) {
      if (err.status === 401) return undefined;
      this.state.error = err.message;
    }
    this.state.loading = false;
    this._render();
    return undefined;
  }

  /** Account, two-factor status and API keys for « Réglages ». */
  async loadAccount() {
    try {
      this.state.account = await this.api.request("GET", "/api/account");
    } catch (err) {
      if (err.status !== 401) this.toast(err.message, true);
    }
    this._render();
  }

  /** « Séjours » list for the current view, property and search. */
  async loadStays() {
    const { view, q } = this.state.stays;
    try {
      const data = await this.api.get("/api/stays", { view, q, property_id: this.state.propertyId });
      if (view === this.state.stays.view && q === this.state.stays.q) this.state.stays.data = data;
    } catch (err) {
      if (err.status !== 401) this.toast(err.message, true);
    }
    this._render();
  }

  /** After any change to a stay: the list and the Overview are both refreshed from the server. */
  async afterStayChange() {
    await Promise.all([this.load(), this.state.screen === "sejours" ? this.loadStays() : Promise.resolve()]);
  }

  async afterPropertyCreated(propertyId) {
    this.session = await this.api.request("GET", "/api/session");
    this.state.propertyId = propertyId || "all";
    await this.load();
  }

  viewModel() {
    const overview = this.state.overview;
    return {
      i18n: this.i18n,
      state: this.state,
      boot: this.session,
      session: this.session,
      auth: this.auth,
      account: this.state.account,
      overview,
      properties: overview?.properties || this.state.stays.data?.properties || [],
      stays: this.state.stays,
      canWrite: this.canWrite,
      periodOptions: this.session?.authenticated ? this.periodOptions() : [],
      dataset: this.api.dataset,
      ready: READY,
    };
  }

  // ---------------------------------------------------------------- events

  async _onClick(event) {
    const target = event.target.closest("[data-action]");
    if (!target || target.getAttribute("aria-disabled") === "true") return;
    const { action, value } = target.dataset;
    switch (action) {
      case "nav":
      case "go":
        if (!READY.has(value)) break;
        this.state.screen = value;
        writePrefs({ screen: value });
        if (target.dataset.view && STAY_VIEWS.includes(target.dataset.view)) {
          this.state.stays = { ...this.state.stays, view: target.dataset.view, q: "", data: null };
        }
        this._render();
        this.root.querySelector(".main")?.scrollTo({ top: 0 });
        if (value === "reglages") await this.loadAccount();
        if (value === "sejours") await this.loadStays();
        break;
      case "stays-view":
        this.state.stays = { ...this.state.stays, view: value, data: this.state.stays.data };
        this._render();
        await this.loadStays();
        break;
      case "stay-open":
        openStay(this, value);
        break;
      case "stay-new":
        openStayForm(this);
        break;
      case "pwd":
        openPasswordDialog(this);
        break;
      case "mfa-enable":
        openMfaEnable(this);
        break;
      case "mfa-disable":
        openMfaDisable(this);
        break;
      case "mfa-codes":
        openMfaCodes(this);
        break;
      case "key-new":
        openCreateKey(this);
        break;
      case "key-revoke":
        openRevokeKey(this, { id: value, name: target.dataset.name || "" });
        break;
      case "copy":
        copyText(this, target.dataset.copy || "", { from: target });
        break;
      case "alerts":
        openAlerts(this);
        break;
      case "dataset":
        await this._chooseDataset(value);
        break;
      case "demo-reset":
        this._resetDemo();
        break;
      case "auth-back":
        this.auth = { error: "", busy: false, mfa: false, username: this.auth.username };
        this._render();
        this.root.querySelector("#rc-u")?.focus();
        break;
      case "open-settings":
        this.dialogHost.querySelectorAll("dialog").forEach((d) => d.close());
        this.state.screen = "reglages";
        writePrefs({ screen: "reglages" });
        this._render();
        await this.loadAccount();
        break;
      case "mode":
        this.state.mode = value;
        writePrefs({ mode: value });
        await this.load();
        break;
      case "explain":
        openExplain(this, value);
        break;
      case "focus-property":
        this.state.propertyId = value;
        await this.load();
        break;
      case "add-property":
        openPropertyDialog(this);
        break;
      case "add-menu":
        openAddMenu(this);
        break;
      case "start":
        await this._start(value);
        break;
      case "leave-demo":
        await this._switchDataset("real");
        break;
      case "retry":
        await this.load();
        break;
      case "lang":
        writePrefs({ lang: value });
        this._setLang(value);
        this.state.overview = null;
        if (this.session?.authenticated) await this.load();
        else this._render();
        break;
      case "account":
        this._openAccount();
        break;
      case "logout":
        await this._logout();
        break;
      default:
        break;
    }
  }

  async _onChange(event) {
    const target = event.target.closest("[data-change]");
    if (!target) return;
    if (target.dataset.change === "property") this.state.propertyId = target.value;
    if (target.dataset.change === "period") this.state.periodKey = target.value;
    if (this.state.screen === "sejours") await Promise.all([this.loadStays(), this.load()]);
    else await this.load();
  }

  _onInput(event) {
    const target = event.target.closest("[data-input]");
    if (!target || target.dataset.input !== "stays-q") return;
    this.state.stays.q = target.value;
    clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => this.loadStays(), 250);
  }

  async _onSubmit(event) {
    const form = event.target.closest("form[data-form]");
    if (!form) return;
    event.preventDefault();
    const data = Object.fromEntries(new FormData(form).entries());
    const kind = form.dataset.form;
    this.auth = { ...this.auth, busy: true, error: "", username: data.username || "" };
    this._render();
    try {
      if (kind === "setup") {
        await this.api.request("POST", "/api/auth/setup", { body: data });
      } else if (kind === "mfa") {
        await this.api.request("POST", "/api/auth/mfa", { body: data });
      } else {
        const result = await this.api.request("POST", "/api/auth/login", { body: data });
        if (result.mfa_required) {
          this.auth = { ...this.auth, busy: false, mfa: true };
          this._render();
          this.root.querySelector("#rc-o")?.focus();
          return;
        }
      }
      this.auth = { error: "", busy: false, mfa: false, username: "" };
      this.state.periodKey = "";
      await this.refreshSession();
    } catch (err) {
      this.auth = { ...this.auth, busy: false, error: err.message };
      if (err.code === "mfa_expired") this.auth.mfa = false;
      this._render();
      this.root.querySelector(kind === "setup" ? "#rc-u" : kind === "mfa" && this.auth.mfa ? "#rc-o" : "#rc-p")?.focus();
    }
  }

  async _start(choice) {
    try {
      const result = await this.api.request("POST", "/api/start", { body: { choice, lang: this.i18n.lang } });
      this.session.real.first_choice = result.first_choice;
      this.session.demo = result.demo;
      if (choice === "demo" && !result.demo.exists) {
        this.toast(this.i18n.t("welcome.readerNote"), true);
        return;
      }
      await this._switchDataset(choice === "demo" ? "demo" : "real");
    } catch (err) {
      this.toast(err.message, true);
    }
  }

  async _switchDataset(dataset) {
    this.api.dataset = dataset;
    writePrefs({ dataset });
    this.state.overview = null;
    this.state.propertyId = "all";
    if (!READY.has(this.state.screen)) this.state.screen = "synthese";
    this.session = await this.api.request("GET", "/api/session");
    this.state.periodKey = this._defaultPeriodKey();
    await this.load();
  }

  /** « Mes données / Démonstration » from the menu, the account window or Réglages. */
  async _chooseDataset(dataset) {
    this.dialogHost.querySelectorAll("dialog").forEach((d) => d.close());
    if (dataset === this.api.dataset) return;
    try {
      if (dataset === "demo" && !this.session.demo.exists) {
        if (!this.canWrite) {
          this.toast(this.i18n.t("dataset.demoMissing"), true);
          return;
        }
        await this._start("demo");
      } else {
        await this._switchDataset(dataset);
      }
      this.toast(this.i18n.t(dataset === "demo" ? "dataset.nowDemo" : "dataset.nowReal"));
    } catch (err) {
      this.toast(err.message, true);
    }
  }

  _resetDemo() {
    const { t } = this.i18n;
    openConfirm(this, {
      title: t("demo.resetTitle"),
      text: t("demo.resetText"),
      confirm: t("demo.resetConfirm"),
      run: async () => {
        await this.api.request("POST", "/api/demo/reset", { body: { lang: this.i18n.lang } });
        this.toast(t("demo.resetDone"));
        if (this.isDemo) await this._switchDataset("demo");
        else this.session = await this.api.request("GET", "/api/session");
      },
    });
  }

  async _logout() {
    try { await this.api.request("POST", "/api/auth/logout"); } catch (_) { /* the session is cleared anyway */ }
    this.dialogHost.querySelectorAll("dialog").forEach((d) => d.close());
    this.state.overview = null;
    this.state.periodKey = "";
    await this.refreshSession();
  }

  _openAccount() {
    const { t } = this.i18n;
    const user = this.session.user;
    const dialog = document.createElement("dialog");
    dialog.className = "rc";
    dialog.setAttribute("aria-labelledby", "rc-account-title");
    dialog.innerHTML = markup(html`
      <div class="dhead"><div><h2 id="rc-account-title">${t("auth.account")}</h2></div>
        <button type="button" class="iconbtn" data-close aria-label="${t("common.close")}">${raw(icon("close"))}</button></div>
      <div class="dbody">
        <div class="userbox"><div class="who"><span class="avatar" aria-hidden="true">${initials(user.name)}</span><span><b>${user.name}</b><small>${t(`auth.role.${user.role}`)}</small></span></div></div>
        <div class="field"><span class="help">${t("dataset.label")}</span>${datasetSwitch(this.viewModel())}</div>
        <div class="field"><span class="help">${t("lang.label")}</span>${langSwitch(this.viewModel())}</div>
      </div>
      <div class="dfoot"><button type="button" class="btn ghost" data-action="open-settings">${raw(icon("sliders"))}${t("nav.reglages")}</button><button type="button" class="btn ghost" data-action="logout">${raw(icon("logout"))}${t("auth.signout")}</button></div>`);
    this.dialogHost.appendChild(dialog);
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog || event.target.closest("[data-close]")) dialog.close();
      if (event.target.closest('[data-action="lang"]')) dialog.close();
    });
    dialog.addEventListener("close", () => dialog.remove());
    dialog.showModal();
  }

  toast(message, isError = false) {
    const node = document.createElement("div");
    node.className = `toast ${isError ? "error" : ""}`;
    node.textContent = message;
    this.toastHost.appendChild(node);
    setTimeout(() => node.remove(), isError ? 9000 : 4500);
  }

  // ---------------------------------------------------------------- rendering

  _shell(content) {
    const { t } = this.i18n;
    const demo = this.isDemo;
    const user = this.session.user;
    const brand = html`<div class="brand"><span class="logo">${raw(icon("logo"))}</span><span><b>Rental Cockpit</b><small>${t("app.tagline")}</small></span></div>`;
    const alerts = (this.state.overview?.to_check || []).reduce((n, item) => n + (item.severity === "info" ? 0 : 1), 0);
    const hideNav = this.showWelcome;
    const current = (key) => raw(this.state.screen === key ? 'aria-current="page"' : "");
    const avatar = html`<span class="avatar" aria-hidden="true">${initials(user.name)}</span>`;
    return html`
      <div class="app">
        <nav class="sidebar" aria-label="${t("nav.main")}">
          ${brand}
          ${hideNav ? "" : html`<ul class="navlist">${SCREENS.map(([key, ic]) => html`<li><button type="button" class="navbtn" data-action="nav" data-value="${key}" ${current(key)}>${raw(icon(ic))}<span>${t(`nav.${key}`)}</span></button></li>`)}</ul>`}
          <div class="spacer"></div>
          <div class="stack-foot">
            ${hideNav ? "" : datasetSwitch(this.viewModel(), { compact: true })}
            <div class="userbox">
              <div class="who">${avatar}<span><b>${user.name}</b><small>${t(`auth.role.${user.role}`)}</small></span></div>
              <button type="button" class="linkbtn" data-action="logout">${raw(icon("logout"))}${t("auth.signout")}</button>
            </div>
          </div>
        </nav>
        <nav class="topnav" aria-label="${t("nav.main")}">
          ${brand}
          ${hideNav ? "" : html`<ul class="tabs">${SCREENS.map(([key, ic]) => html`<li><button type="button" class="tab" data-action="nav" data-value="${key}" ${current(key)}>${raw(icon(ic))}<span>${t(`nav.${key}`)}</span></button></li>`)}</ul>`}
          <span class="end"><button type="button" class="iconbtn" data-action="account" aria-label="${t("auth.account")} : ${user.name}">${avatar}</button></span>
        </nav>
        <header class="mobilebar">
          ${brand}
          ${demo ? html`<span class="demo-mini">${t("demo.short").split("\n")[0]}<br>${t("demo.short").split("\n")[1]}</span>` : html`<span class="push"></span>`}
          ${hideNav ? "" : html`<button type="button" class="iconbtn" data-action="alerts" aria-haspopup="dialog" aria-label="${t("common.alerts")}${alerts ? ` (${alerts})` : ""}">${raw(icon("bell"))}${alerts ? html`<span class="badge">${alerts}</span>` : ""}</button>`}
          <button type="button" class="iconbtn" data-action="account" aria-label="${t("auth.account")} : ${user.name}">${avatar}</button>
        </header>
        <main class="main" id="rc-main">${content}</main>
        ${hideNav ? html`<div></div>` : html`<nav class="bottomnav" aria-label="${t("nav.main")}">${SCREENS.map(([key, ic]) => html`<button type="button" class="navbtn" data-action="nav" data-value="${key}" ${current(key)}>${raw(icon(ic))}<span>${t(`nav.${key}`)}</span></button>`)}</nav>`}
      </div>`;
  }

  _content() {
    const { t } = this.i18n;
    if (this.showWelcome) return renderWelcome(this.viewModel());
    const banner = this.isDemo ? html`
      <div class="banner" role="note">${raw(icon("info"))}<span class="grow">${t("demo.banner")}</span>
        ${this.canWrite || this.session.real.properties ? html`<button type="button" class="linkbtn" data-action="leave-demo">${t("demo.leave")}${raw(icon("arrowRight"))}</button>` : ""}
      </div>` : "";
    let body;
    if (this.state.loading) {
      body = html`<div class="loading"><div class="spinner"></div><span>${t("common.loading")}</span></div>`;
    } else if (this.state.error) {
      body = html`<div class="error-box">${raw(icon("alert"))}<span>${t("error.load")} ${this.state.error}</span></div><div><button type="button" class="btn ghost" data-action="retry">${t("common.retry")}</button></div>`;
    } else if (this.state.screen === "reglages") {
      body = renderSettings(this.viewModel());
    } else if (this.state.screen === "sejours") {
      body = renderStays(this.viewModel());
    } else if (!this.state.overview.properties.length) {
      body = this.canWrite ? renderOnboarding(this.viewModel()) : renderNoAccess(this.viewModel());
    } else {
      body = renderSynthese(this.viewModel());
    }
    return html`<div class="content">${banner}${body}</div>`;
  }

  _render() {
    if (!this.pageEl) return;
    const { t } = this.i18n;
    let page;
    if (!this.session) {
      page = this.state.error
        ? html`<div class="content"><div class="error-box">${raw(icon("alert"))}<span>${t("error.load")} ${this.state.error}</span></div></div>`
        : html`<div class="loading"><div class="spinner"></div><span>${t("common.loading")}</span></div>`;
      this.pageEl.innerHTML = markup(html`<div class="root">${page}</div>`);
      return;
    }
    if (!this.session.authenticated) {
      this.pageEl.innerHTML = markup(html`<div class="root"><div class="main">${renderAuth(this.viewModel())}</div></div>`);
      return;
    }
    const active = document.activeElement;
    const focusKey = active && this.root.contains(active) ? `${active.dataset?.action || active.dataset?.change || active.dataset?.input || ""}|${active.dataset?.value || ""}` : null;
    const caret = active?.dataset?.input ? [active.selectionStart, active.selectionEnd] : null;
    const scroll = this.root.querySelector(".main")?.scrollTop || 0;
    this.pageEl.innerHTML = markup(html`<div class="root">${this._shell(this._content())}</div>`);
    const main = this.root.querySelector(".main");
    if (main) main.scrollTop = scroll;
    if (focusKey && focusKey !== "|") {
      const [a, v] = focusKey.split("|");
      const selector = `[data-action="${esc(a)}"]${v ? `[data-value="${esc(v)}"]` : ""}, [data-change="${esc(a)}"], [data-input="${esc(a)}"]`;
      const element = this.root.querySelector(selector);
      element?.focus({ preventScroll: true });
      if (caret && element?.setSelectionRange) element.setSelectionRange(caret[0], caret[1]);
    }
  }
}

function initials(name) {
  const parts = String(name || "?").trim().split(/[\s._-]+/).filter(Boolean);
  return ((parts[0]?.[0] || "?") + (parts[1]?.[0] || "")).toUpperCase();
}
