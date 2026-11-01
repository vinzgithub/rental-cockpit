/* Copyright © 2026 Vincent Fournet */
// « Réglages » — account, two-factor sign-in, data shown (own data or demo),
// categories of expenses and income, the optional Home Assistant link and, for
// administrators, reader accounts with their rights and the backups.

import { html, raw } from "../dom.js";
import { icon } from "../icons.js";
import { langSwitch } from "./auth.js";
import { datasetSwitch } from "./dataset.js";

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

function dataCard(v) {
  const { t } = v.i18n;
  const canReset = v.canWrite && v.session.demo.exists;
  return html`
    <section class="card" aria-labelledby="rc-set-data">
      <div class="card-head"><span class="ico">${raw(icon("eye"))}</span><h2 id="rc-set-data">${t("settings.data")}</h2></div>
      <p class="reading">${t("settings.dataIntro")}</p>
      ${datasetSwitch(v)}
      ${canReset ? html`
        <p class="meta-line">${raw(icon("info"))}<span>${t("demo.resetHelp")}</span></p>
        <div class="actions">
          <button type="button" class="btn ghost" data-action="demo-reset">${raw(icon("repeat"))}${t("demo.resetTitle")}</button>
        </div>` : ""}
    </section>`;
}

function categoriesCard(v) {
  const { t } = v.i18n;
  const list = v.categories?.categories || [];
  const group = (kind) => list.filter((c) => c.kind === kind);
  const row = (c) => html`
    <div class="keyrow cat-row ${c.archived ? "archived" : ""}">
      <span class="tile">${raw(icon(c.kind === "income" ? "coins" : "tag"))}</span>
      <span><b>${c.label}</b><small>${c.treatment_label}${c.entries ? ` · ${v.i18n.plural(c.entries, "cat.entry", "cat.entries")}` : ""}${c.archived ? ` · ${t("cat.archived")}` : ""}${c.custom_label && c.builtin ? ` · ${t("cat.was", { label: c.default_label })}` : ""}</small></span>
      ${v.canWrite ? html`<span class="row-actions">
        <button type="button" class="iconbtn" data-action="category-edit" data-value="${c.id}" aria-label="${t("cat.rename", { label: c.label })}">${raw(icon("pencil"))}</button>
        <button type="button" class="iconbtn" data-action="category-toggle" data-value="${c.id}" aria-label="${t(c.archived ? "cat.restore" : "cat.archive", { label: c.label })}">${raw(icon(c.archived ? "repeat" : "archive"))}</button>
      </span>` : ""}
    </div>`;
  return html`
    <section class="card" aria-labelledby="rc-set-cat">
      <div class="card-head"><span class="ico">${raw(icon("tag"))}</span><h2 id="rc-set-cat">${t("cat.title")}</h2>
        ${v.canWrite ? html`<button type="button" class="btn primary small end" data-action="category-new">${raw(icon("plus"))}${t("cat.new")}</button>` : ""}</div>
      <p class="reading">${t("cat.intro")}</p>
      ${!v.categories ? html`<div class="loading small"><div class="spinner"></div></div>` : html`
        <h3 class="section-title">${t("ex.kind.expense")}</h3>
        <div class="rows">${group("expense").map(row)}</div>
        <h3 class="section-title">${t("ex.kind.income")}</h3>
        <div class="rows">${group("income").map(row)}</div>`}
    </section>`;
}

function usersCard(v) {
  const { i18n } = v;
  const { t } = i18n;
  const admin = v.admin;
  if (!admin?.users) return html`<section class="card"><div class="loading small"><div class="spinner"></div></div></section>`;
  const names = Object.fromEntries(admin.users.properties.map((p) => [p.id, p.name]));
  const row = (u) => {
    const ids = Object.keys(u.grants);
    const pdf = ids.filter((id) => u.grants[id]);
    const facts = u.role === "admin" ? t("auth.role.admin")
      : [t("auth.role.reader"), ids.length ? ids.map((id) => names[id] || "—").join(", ") : t("usr.noProperty"),
         pdf.length ? t("usr.pdfOn", { list: pdf.map((id) => names[id] || "—").join(", ") }) : t("usr.pdfOff")].join(" · ");
    return html`
      <div class="keyrow user-row">
        <span class="tile">${raw(icon(u.role === "admin" ? "shieldCheck" : "user"))}</span>
        <span><b>${u.display_name || u.username}</b><small>@${u.username} · ${facts}</small>
          ${u.must_change_password ? html`<span class="pill amber tiny">${t("usr.mustChange")}</span>` : ""}${u.mfa ? html`<span class="pill teal tiny">${t("usr.mfa")}</span>` : ""}</span>
        ${u.role === "reader" ? html`<span class="row-actions">
          <button type="button" class="iconbtn" data-action="user-edit" data-value="${u.id}" aria-label="${t("usr.edit", { name: u.username })}">${raw(icon("pencil"))}</button>
          <button type="button" class="iconbtn" data-action="user-password" data-value="${u.id}" aria-label="${t("usr.reset", { name: u.username })}">${raw(icon("key"))}</button>
          <button type="button" class="iconbtn" data-action="user-delete" data-value="${u.id}" aria-label="${t("usr.delete", { name: u.username })}">${raw(icon("trash"))}</button>
        </span>` : ""}
      </div>`;
  };
  return html`
    <section class="card" aria-labelledby="rc-set-users">
      <div class="card-head"><span class="ico">${raw(icon("users"))}</span><h2 id="rc-set-users">${t("usr.title")}</h2>
        <button type="button" class="btn primary small end" data-action="user-new">${raw(icon("plus"))}${t("usr.add")}</button></div>
      <p class="reading">${t("usr.intro")}</p>
      <div class="rows">${admin.users.users.map(row)}</div>
    </section>`;
}

function backupCard(v) {
  const { i18n } = v;
  const { t } = i18n;
  const list = v.admin?.backups?.backups;
  return html`
    <section class="card" aria-labelledby="rc-set-backup">
      <div class="card-head"><span class="ico">${raw(icon("archive"))}</span><h2 id="rc-set-backup">${t("bak.title")}</h2></div>
      <p class="reading">${t("bak.intro")}</p>
      <div class="tip">${raw(icon("lock"))}<div><p>${t("bak.private")}</p></div></div>
      <div class="actions">
        <button type="button" class="btn primary" data-action="backup-create">${raw(icon("download"))}${t("bak.create")}</button>
        <button type="button" class="btn ghost" data-action="backup-restore">${raw(icon("upload"))}${t("bak.restore")}</button>
      </div>
      ${!list ? html`<div class="loading small"><div class="spinner"></div></div>` : list.length ? html`
        <h3 class="section-title">${t("bak.onServer")}</h3>
        <div class="rows">${list.map((b) => html`
          <div class="keyrow backup-row">
            <span class="tile">${raw(icon("archive"))}</span>
            <span><b class="mono">${b.name}</b><small class="num">${i18n.dateTime(b.modified * 1000)} · ${i18n.size(b.size)}${b.kind === "before_restore" ? ` · ${t("bak.beforeRestore")}` : ""}</small></span>
            <span class="row-actions">
              <a class="iconbtn" href="/api/backups/${encodeURIComponent(b.name)}/file" download="${b.name}" aria-label="${t("bak.download", { name: b.name })}">${raw(icon("download"))}</a>
              <button type="button" class="iconbtn" data-action="backup-delete" data-value="${b.name}" aria-label="${t("bak.delete", { name: b.name })}">${raw(icon("trash"))}</button>
            </span>
          </div>`)}</div>` : html`<p class="meta-line">${raw(icon("info"))}<span>${t("bak.none")}</span></p>`}
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
      <div class="stack">${dataCard(v)}${haCard(v)}</div>
    </div>
    ${v.canAdmin ? html`<div class="settings-grid"><div class="stack">${usersCard(v)}</div><div class="stack">${backupCard(v)}</div></div>` : ""}
    ${categoriesCard(v)}`;
}
