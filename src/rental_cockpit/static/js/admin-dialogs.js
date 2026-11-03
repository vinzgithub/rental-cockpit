/* Copyright © 2026 Vincent Fournet */
// Administration dialogs: reader accounts and their rights, backups and restore.
// The server checks everything again; a restore is checked in a staging copy
// and applied only after the person types the confirmation word.

import { openConfirm, openDialog } from "./dialogs.js";
import { html, markup, raw } from "./dom.js";
import { icon } from "./icons.js";
import { copyText, manualCopyNote } from "./settings-dialogs.js";

function errorBox(message) {
  return markup(html`<div class="error-box" role="alert">${raw(icon("alert"))}<span>${message}</span></div>`);
}

/** A temporary password the administrator passes on (the reader chooses their own at the first sign-in). */
function temporaryPassword() {
  const alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789";
  const values = new Uint32Array(14);
  crypto.getRandomValues(values);
  return Array.from(values, (n) => alphabet[n % alphabet.length]).join("").replace(/(.{4})(?!$)/g, "$1-");
}

function grantRows(t, properties, grants) {
  return html`
    <fieldset class="wide amounts grant-list">
      <legend>${t("usr.grants")}</legend>
      <p class="reading">${raw(icon("info"))}<span>${t("usr.grantsHelp")}</span></p>
      ${properties.length ? properties.map((p) => html`
        <div class="grant-row" data-property="${p.id}">
          <label class="check-line"><input type="checkbox" data-g="see" ${raw(p.id in grants ? "checked" : "")}><span>${p.name}${p.archived ? html` <small>(${t("usr.archivedProperty")})</small>` : ""}</span></label>
          <label class="check-line"><input type="checkbox" data-g="pdf" ${raw(grants[p.id] ? "checked" : "")} ${raw(p.id in grants ? "" : "disabled")}><span>${t("usr.pdf")}</span></label>
        </div>`) : html`<p class="meta-line">${t("usr.noProperties")}</p>`}
    </fieldset>`;
}

function readGrants(dialog) {
  return [...dialog.querySelectorAll("[data-property]")].filter((row) => row.querySelector("[data-g=see]").checked)
    .map((row) => ({ property_id: row.dataset.property, documents: row.querySelector("[data-g=pdf]").checked }));
}

function wireGrants(dialog) {
  dialog.addEventListener("change", (event) => {
    if (!event.target.matches("[data-g=see]")) return;
    const pdf = event.target.closest("[data-property]").querySelector("[data-g=pdf]");
    pdf.disabled = !event.target.checked;
    if (!event.target.checked) pdf.checked = false;
  });
}

function passwordField(t, id, value) {
  return html`
    <div class="field wide"><label for="${id}">${t("usr.tempPassword")}</label>
      <div class="inline-field"><input id="${id}" name="password" autocomplete="off" spellcheck="false" class="mono" value="${value}" minlength="10" required aria-describedby="${id}-h">
        <button type="button" class="btn ghost small" data-generate>${raw(icon("repeat"))}${t("usr.generate")}</button>
        <button type="button" class="btn ghost small" data-copy>${raw(icon("copy"))}${t("usr.copy")}</button></div>
      <span class="help" id="${id}-h">${t("usr.tempHelp")}</span>${manualCopyNote(t)}</div>`;
}

function wirePassword(app, dialog) {
  const input = dialog.querySelector("[name=password]");
  dialog.querySelector("[data-generate]").addEventListener("click", () => { input.value = temporaryPassword(); input.focus(); });
  // The same copy as the other secrets: older command on http://, then the field selected and said so.
  dialog.querySelector("[data-copy]").addEventListener("click", (event) => copyText(app, input.value, { from: event.currentTarget, select: input }));
}

// ------------------------------------------------------------------ reader accounts

export function openReaderForm(app, user = null) {
  const { t } = app.i18n;
  const properties = app.state.admin.users.properties;
  const dialog = openDialog(app, {
    title: t(user ? "usr.editTitle" : "usr.addTitle"),
    subtitle: user ? `@${user.username}` : t("usr.addSub"),
    wide: true,
    body: html`
      <form class="form-grid" novalidate>
        ${user ? "" : html`<div class="field"><label for="rc-us-name">${t("auth.username")}</label>
          <input id="rc-us-name" name="username" autocomplete="off" required minlength="3" maxlength="40" aria-describedby="rc-us-name-h"><span class="help" id="rc-us-name-h">${t("auth.usernameHelp")}</span></div>`}
        <div class="field"><label for="rc-us-display">${t("auth.displayName")}</label>
          <input id="rc-us-display" name="display_name" maxlength="60" autocomplete="off" value="${user?.display_name || ""}" placeholder="${t("usr.displayPh")}"></div>
        ${user ? "" : passwordField(t, "rc-us-pwd", temporaryPassword())}
        ${grantRows(t, properties, user?.grants || {})}
        <div class="wide" data-error aria-live="assertive"></div>
      </form>`,
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.cancel")}</button><button type="button" class="btn primary" data-save>${raw(icon("check"))}${t(user ? "exf.save" : "usr.create")}</button>`,
  });
  wireGrants(dialog);
  if (!user) wirePassword(app, dialog);
  const save = dialog.querySelector("[data-save]");
  save.addEventListener("click", async () => {
    const data = Object.fromEntries(new FormData(dialog.querySelector("form")).entries());
    const body = { display_name: data.display_name || "", grants: readGrants(dialog) };
    save.disabled = true;
    try {
      if (user) {
        app.state.admin.users = await app.api.request("PATCH", `/api/users/${user.id}`, { body });
      } else {
        app.state.admin.users = await app.api.request("POST", "/api/users", { body: { ...body, username: data.username.trim(), password: data.password } });
      }
      dialog.close();
      app.toast(t(user ? "usr.updated" : "usr.created", { name: user?.username || data.username.trim() }));
      app._render();
    } catch (err) {
      dialog.querySelector("[data-error]").innerHTML = errorBox(err.message);
      save.disabled = false;
    }
  });
  dialog.querySelector("input:not([type=checkbox])")?.focus();
}

export function openReaderPassword(app, user) {
  const { t } = app.i18n;
  const dialog = openDialog(app, {
    title: t("usr.resetTitle"),
    subtitle: `@${user.username}`,
    body: html`
      <form class="form-grid" novalidate>
        ${passwordField(t, "rc-us-reset", temporaryPassword())}
        <p class="reading wide">${raw(icon("info"))}<span>${t("usr.resetHelp")}</span></p>
        <div class="wide" data-error aria-live="assertive"></div>
      </form>`,
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.cancel")}</button><button type="button" class="btn primary" data-save>${raw(icon("key"))}${t("usr.resetSave")}</button>`,
  });
  wirePassword(app, dialog);
  const save = dialog.querySelector("[data-save]");
  save.addEventListener("click", async () => {
    save.disabled = true;
    try {
      app.state.admin.users = await app.api.request("POST", `/api/users/${user.id}/password`, { body: { password: dialog.querySelector("[name=password]").value } });
      dialog.close();
      app.toast(t("usr.resetDone", { name: user.username }));
      app._render();
    } catch (err) {
      dialog.querySelector("[data-error]").innerHTML = errorBox(err.message);
      save.disabled = false;
    }
  });
}

export function confirmReaderDelete(app, user) {
  const { t } = app.i18n;
  openConfirm(app, {
    title: t("usr.deleteTitle", { name: user.username }), text: t("usr.deleteText"), confirm: t("usr.deleteConfirm"),
    run: async () => {
      app.state.admin.users = await app.api.request("DELETE", `/api/users/${user.id}`, { body: {} });
      app.toast(t("usr.deleted", { name: user.username }));
      app._render();
    },
  });
}

// ------------------------------------------------------------------ backups

export async function createBackup(app, button) {
  const { i18n } = app;
  const { t } = i18n;
  if (button) button.disabled = true;
  try {
    const result = await app.api.request("POST", "/api/backups", { body: {} });
    app.state.admin.backups = { ...app.state.admin.backups, backups: result.backups };
    app._render();
    const made = result.backup;
    // The file is offered at once; it also stays in the list below.
    const link = document.createElement("a");
    link.href = `/api/backups/${encodeURIComponent(made.name)}/file`;
    link.download = made.name;
    document.body.appendChild(link);
    link.click();
    link.remove();
    app.toast(made.missing_documents ? t("bak.madeMissing", { n: made.missing_documents }) : t("bak.made", { size: i18n.size(made.size) }), Boolean(made.missing_documents));
  } catch (err) {
    app.toast(err.message, true);
  } finally {
    if (button) button.disabled = false;
  }
}

export function confirmBackupDelete(app, name) {
  const { t } = app.i18n;
  openConfirm(app, {
    title: t("bak.deleteTitle"), text: t("bak.deleteText", { name }), confirm: t("bak.deleteConfirm"),
    run: async () => {
      const result = await app.api.request("DELETE", `/api/backups/${encodeURIComponent(name)}`, { body: {} });
      app.state.admin.backups = { ...app.state.admin.backups, backups: result.backups };
      app._render();
    },
  });
}

function figuresTable(app, backup, current) {
  const { i18n } = app;
  const { t } = i18n;
  const rows = [["properties", "count"], ["stays", "count"], ["entries", "count"], ["payments", "count"], ["suppliers", "count"], ["documents", "count"],
    ["expenses", "money"], ["income", "money"], ["payments", "moneyPaid"]];
  const value = (figures, [key, kind]) => (kind === "count" ? figures.counts[key] ?? 0 : i18n.money(figures.totals[kind === "moneyPaid" ? "payments" : key] ?? 0));
  return html`
    <div class="lines-wrap compact-table"><table class="lines">
      <thead><tr><th>${t("bak.what")}</th><th class="amt">${t("bak.inBackup")}</th><th class="amt">${t("bak.now")}</th></tr></thead>
      <tbody>${rows.map((r) => html`<tr><td>${t(`bak.row.${r[0]}${r[1] === "count" ? "" : "Amount"}`)}</td><td class="amt num"><b>${value(backup, r)}</b></td><td class="amt num">${value(current, r)}</td></tr>`)}</tbody>
    </table></div>`;
}

export function openRestore(app) {
  const { i18n } = app;
  const { t } = i18n;
  const s = { checked: null, busy: false, error: "", done: null };
  const dialog = openDialog(app, {
    title: t("bak.restoreTitle"),
    subtitle: t("bak.restoreSub"),
    wide: true,
    body: "",
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.cancel")}</button><button type="button" class="btn danger" data-save disabled>${raw(icon("repeat"))}${t("bak.replace")}</button>`,
  });
  dialog.dataset.locked = "1";  // a click outside never closes it in the middle of a restore
  const save = dialog.querySelector("[data-save]");
  const render = () => {
    const c = s.checked;
    let body;
    if (s.done) {
      body = html`
        <div class="tip ok">${raw(icon("checkCircle"))}<div><p><b>${t("bak.restored")}</b></p>
          <p>${t(s.done.same_totals ? "bak.sameTotals" : "bak.otherTotals")}</p>
          <p>${t("bak.safety", { name: s.done.safety_backup })}</p>
          ${s.done.grants.unknown.length ? html`<p>${t("bak.unknownReaders", { list: s.done.grants.unknown.join(", ") })}</p>` : ""}</div></div>`;
    } else if (!c) {
      body = html`
        <label class="dropzone" data-drop>
          <input type="file" class="sr-only" accept=".zip,application/zip" data-zip>
          <span class="tile">${raw(icon("upload"))}</span>
          <span><b>${t("bak.choose")}</b><small>${t("bak.chooseHint")}</small></span>
        </label>
        <p class="reading">${raw(icon("shieldCheck"))}<span>${t("bak.checkFirst")}</span></p>
        ${s.busy ? html`<div class="loading small"><div class="spinner"></div><span>${t("bak.checking")}</span></div>` : ""}`;
    } else {
      const b = c.backup;
      body = html`
        <div class="tip ok">${raw(icon("checkCircle"))}<div><p><b>${t("bak.checked")}</b></p>
          <p>${t("bak.checkedText", { date: b.created_at ? i18n.dateLong(b.created_at.slice(0, 10)) : "—", version: b.app_version || "—" })}</p>
          ${b.migrated ? html`<p>${t("bak.migrated", { from: b.schema, to: b.schema_now })}</p>` : ""}</div></div>
        ${figuresTable(app, b, c.current)}
        ${b.missing_documents.length ? html`<div class="tip warn">${raw(icon("alert"))}<div><p>${t("bak.missingDocs", { n: b.missing_documents.length })}</p></div></div>` : ""}
        <div class="error-box">${raw(icon("alert"))}<span>${t("bak.replaceWarning")}</span></div>
        <div class="field"><label for="rc-restore-word">${t("bak.typeWord")}</label>
          <input id="rc-restore-word" data-word autocomplete="off" spellcheck="false" placeholder="${t("bak.word")}"></div>`;
    }
    dialog.querySelector(".dbody").innerHTML = markup(html`${body}<div data-error aria-live="assertive">${s.error ? raw(errorBox(s.error)) : ""}</div>`);
    save.hidden = Boolean(s.done);
    save.disabled = true;
    dialog.querySelector(".dfoot [data-close]").textContent = t(s.done ? "common.close" : "common.cancel");
  };
  const choose = async (file) => {
    if (!file) return;
    s.busy = true; s.error = ""; render();
    try {
      s.checked = await app.api.request("POST", "/api/restore/check", { file, fileType: "application/zip" });
    } catch (err) {
      s.error = err.message;
    }
    s.busy = false;
    render();
    dialog.querySelector("[data-word]")?.focus();
  };
  dialog.addEventListener("change", (event) => { if (event.target.matches("[data-zip]")) choose(event.target.files?.[0]); });
  dialog.addEventListener("dragover", (event) => { if (dialog.querySelector("[data-drop]")) event.preventDefault(); });
  dialog.addEventListener("drop", (event) => {
    if (!dialog.querySelector("[data-drop]")) return;
    event.preventDefault();
    choose(event.dataTransfer?.files?.[0]);
  });
  dialog.addEventListener("input", (event) => {
    if (event.target.matches("[data-word]")) save.disabled = event.target.value.trim() !== t("bak.word");
  });
  save.addEventListener("click", async () => {
    save.disabled = true;
    try {
      s.done = await app.api.request("POST", "/api/restore/apply", { body: { token: s.checked.token, confirm: dialog.querySelector("[data-word]").value.trim() } });
      render();
      app.toast(t("bak.restored"));
      await app.afterRestore();
    } catch (err) {
      dialog.querySelector("[data-error]").innerHTML = errorBox(err.message);
      save.disabled = false;
    }
  });
  render();
}
