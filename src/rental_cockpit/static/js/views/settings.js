/* Copyright © 2026 Vincent Fournet */
// « Réglages » — account, two-factor sign-in and the optional Home Assistant link.
// Other settings (categories, readers, backup) arrive in later packages and are
// listed so nobody looks for them in vain.

import { html, raw } from "../dom.js";
import { icon } from "../icons.js";
import { langSwitch } from "./auth.js";

const DOC_BASE = "https://github.com/vinzgithub/rental-cockpit/blob/main/docs";

function accountCard(v) {
  const { i18n, account } = v;
  const { t } = i18n;
  const user = account.user;
  return html`
    <section class="card" aria-labelledby="rc-set-account">
      <div class="card-head"><span class="ico">${raw(icon("user"))}</span><h2 id="rc-set-account">${t("settings.account")}</h2></div>
      <dl class="facts-list">
        <div><dt>${t("settings.username")}</dt><dd>${user.username}</dd></div>
        <div><dt>${t("settings.role")}</dt><dd>${t(`auth.role.${user.role}`)}</dd></div>
        <div><dt>${t("settings.language")}</dt><dd>${langSwitch(v)}</dd></div>
      </dl>
      <div class="actions">
        <button type="button" class="btn ghost" data-action="pwd">${raw(icon("lock"))}${t("settings.changePassword")}</button>
        <button type="button" class="btn ghost" data-action="logout">${raw(icon("logout"))}${t("auth.signout")}</button>
      </div>
    </section>`;
}

function mfaCard(v) {
  const { i18n, account } = v;
  const { t } = i18n;
  const on = account.mfa.enabled;
  return html`
    <section class="card" aria-labelledby="rc-set-mfa">
      <div class="card-head">
        <span class="ico">${raw(icon(on ? "shieldCheck" : "shield"))}</span>
        <h2 id="rc-set-mfa">${t("settings.mfa")}</h2>
        <span class="end">${on
          ? html`<span class="pill teal">${raw(icon("check"))}${t("settings.mfaOn")}</span>`
          : html`<span class="pill grey">${raw(icon("info"))}${t("settings.mfaOff")}</span>`}</span>
      </div>
      <p class="reading">${t("settings.mfaIntro")}</p>
      ${on ? html`<p class="meta-line">${raw(icon("key"))}<span>${i18n.t("settings.mfaLeft", { n: account.mfa.recovery_left })}</span></p>` : ""}
      <div class="actions">
        ${on ? html`
          <button type="button" class="btn ghost" data-action="mfa-codes">${raw(icon("key"))}${t("settings.mfaCodes")}</button>
          <button type="button" class="btn ghost" data-action="mfa-disable">${raw(icon("shield"))}${t("settings.mfaDisable")}</button>`
        : html`<button type="button" class="btn primary" data-action="mfa-enable">${raw(icon("shieldCheck"))}${t("settings.mfaEnable")}</button>`}
      </div>
    </section>`;
}

function haCard(v) {
  const { i18n, account } = v;
  const { t } = i18n;
  const endpoint = `${window.location.origin}/api/v1/summary`;
  const doc = `${DOC_BASE}/${i18n.lang === "fr" ? "fr/home-assistant.md" : "en/home-assistant.md"}`;
  return html`
    <section class="card" aria-labelledby="rc-set-ha">
      <div class="card-head"><span class="ico">${raw(icon("link"))}</span><h2 id="rc-set-ha">${t("settings.ha")}</h2>
        <button type="button" class="btn primary small end" data-action="key-new">${raw(icon("plus"))}${t("settings.newKey")}</button></div>
      <p class="reading">${t("settings.haIntro")}</p>
      <div class="field">
        <span class="help">${t("settings.haEndpoint")}</span>
        <div class="codebox"><code>${endpoint}</code><button type="button" class="iconbtn" data-action="copy" data-copy="${endpoint}" aria-label="${t("mfa.copy")}">${raw(icon("copy"))}</button></div>
      </div>
      <h3 class="section-title">${t("settings.keys")}</h3>
      <div class="rows">
        ${account.keys.length ? account.keys.map((key) => html`
          <div class="keyrow">
            <span class="tile">${raw(icon("key"))}</span>
            <span><b>${key.name}</b><small>${t("settings.keyCreated", { date: i18n.dateShort(key.created_at.slice(0, 10)) })} · ${key.last_used_at ? t("settings.keyUsed", { date: i18n.dateShort(key.last_used_at.slice(0, 10)) }) : t("settings.keyNever")}</small></span>
            <button type="button" class="btn ghost small" data-action="key-revoke" data-value="${key.id}" data-name="${key.name}">${raw(icon("trash"))}${t("settings.revoke")}</button>
          </div>`) : html`<div class="empty">${raw(icon("info"))}<span>${t("settings.noKey")}</span></div>`}
      </div>
      <a class="linkbtn" href="${doc}" target="_blank" rel="noopener noreferrer">${raw(icon("external"))}${t("settings.haDoc")}</a>
    </section>`;
}

function soonCard(v) {
  const { t } = v.i18n;
  return html`
    <section class="card" aria-labelledby="rc-set-soon">
      <div class="card-head"><span class="ico">${raw(icon("hourglass"))}</span><h2 id="rc-set-soon">${t("settings.soon")}</h2></div>
      <ul class="plain-list">${t("settings.soonList").split("|").map((line) => html`<li>${line}</li>`)}</ul>
    </section>`;
}

export function renderSettings(v) {
  const { t } = v.i18n;
  const head = html`<header class="pagehead"><div><h1>${t("settings.title")}</h1><p class="sub">${t("settings.sub")}</p></div></header>`;
  if (!v.account) return html`${head}<div class="loading small"><div class="spinner"></div><span>${t("common.loading")}</span></div>`;
  return html`
    ${head}
    <div class="settings-grid">
      <div class="stack">${accountCard(v)}${mfaCard(v)}</div>
      <div class="stack">${haCard(v)}${soonCard(v)}</div>
    </div>`;
}
