/* Copyright © 2026 Vincent Fournet */
// Sign-in and creation of the first administrator account.
// There is no default account: the very first visit creates the administrator.

import { html, raw } from "../dom.js";
import { icon, WELCOME_ART } from "../icons.js";

export function langSwitch(v) {
  const { i18n } = v;
  return html`
    <div class="langs" role="group" aria-label="${i18n.t("lang.label")}">
      <button type="button" data-action="lang" data-value="fr" aria-pressed="${i18n.lang === "fr" ? "true" : "false"}" lang="fr">Français</button>
      <button type="button" data-action="lang" data-value="en" aria-pressed="${i18n.lang === "en" ? "true" : "false"}" lang="en">English</button>
    </div>`;
}

export function renderAuth(v) {
  const { i18n, session, auth } = v;
  const { t } = i18n;
  const setup = session.setup_required;
  const error = auth.error ? html`<div class="error-box" role="alert">${raw(icon("alert"))}<span>${auth.error}</span></div>` : "";
  const form = setup ? html`
      <form class="stack" data-form="setup" novalidate>
        <div><h1>${t("auth.setupTitle")}</h1><p class="reading">${t("auth.setupSub")}</p></div>
        <div class="field"><label for="rc-u">${t("auth.username")}</label><input id="rc-u" name="username" autocomplete="username" required minlength="3" maxlength="40" aria-describedby="rc-u-h"><span class="help" id="rc-u-h">${t("auth.usernameHelp")}</span></div>
        <div class="field"><label for="rc-d">${t("auth.displayName")}</label><input id="rc-d" name="display_name" autocomplete="name" maxlength="60"></div>
        <div class="field"><label for="rc-p">${t("auth.password")}</label><input id="rc-p" name="password" type="password" autocomplete="new-password" required minlength="10" aria-describedby="rc-p-h"><span class="help" id="rc-p-h">${t("auth.passwordHelp")}</span></div>
        <div class="field"><label for="rc-c">${t("auth.confirm")}</label><input id="rc-c" name="confirm" type="password" autocomplete="new-password" required minlength="10"></div>
        ${error}
        <button type="submit" class="btn primary" ${raw(auth.busy ? "disabled" : "")}>${raw(icon("check"))}${t("auth.createAdmin")}</button>
      </form>` : html`
      <form class="stack" data-form="login" novalidate>
        <div><h1>${t("auth.loginTitle")}</h1><p class="reading">${t("auth.loginSub")}</p></div>
        <div class="field"><label for="rc-u">${t("auth.username")}</label><input id="rc-u" name="username" autocomplete="username" required value="${auth.username || ""}"></div>
        <div class="field"><label for="rc-p">${t("auth.password")}</label><input id="rc-p" name="password" type="password" autocomplete="current-password" required></div>
        ${auth.mfa ? html`<div class="field"><label for="rc-o">${t("auth.code")}</label><input id="rc-o" name="code" inputmode="numeric" autocomplete="one-time-code" pattern="[0-9]{6}" maxlength="6" required></div>` : ""}
        ${error}
        <button type="submit" class="btn primary" ${raw(auth.busy ? "disabled" : "")}>${raw(icon("arrowRight"))}${t("auth.signin")}</button>
      </form>`;
  return html`
    <div class="auth">
      <section class="card hero-card">
        <div class="stack">
          <div class="brand"><span class="logo">${raw(icon("logo"))}</span><span><b>Rental Cockpit</b><small>${t("app.tagline")}</small></span></div>
          ${raw(WELCOME_ART)}
          <ul class="points">
            <li>${raw(icon("checkCircle"))}<span>${t("auth.p1")}</span></li>
            <li>${raw(icon("checkCircle"))}<span>${t("auth.p2")}</span></li>
            <li>${raw(icon("checkCircle"))}<span>${t("auth.p3")}</span></li>
          </ul>
          ${langSwitch(v)}
        </div>
        ${form}
      </section>
    </div>`;
}
