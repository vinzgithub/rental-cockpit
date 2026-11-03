/* Copyright © 2026 Vincent Fournet */
// Dialogs of « Réglages »: password, two-factor sign-in (three steps), recovery
// codes and Home Assistant keys. Secrets shown here (recovery codes, a new key)
// are displayed once and never stored by the interface.

import { openDialog } from "./dialogs.js";
import { html, markup, raw } from "./dom.js";
import { icon } from "./icons.js";

function errorBox(message) {
  return markup(html`<div class="error-box" role="alert">${raw(icon("alert"))}<span>${message}</span></div>`);
}

/** Run ``action`` on submit, with a busy button and the server message on failure. */
function wire(dialog, action) {
  const form = dialog.querySelector("form");
  const button = dialog.querySelector("[data-submit]");
  const errors = dialog.querySelector("[data-error]");
  const run = async (event) => {
    event?.preventDefault();
    button.disabled = true;
    errors.innerHTML = "";
    try {
      await action(new FormData(form));
    } catch (err) {
      errors.innerHTML = errorBox(err.message);
      form.querySelector("input")?.focus();
    } finally {
      button.disabled = false;
    }
  };
  form.addEventListener("submit", run);
  button.addEventListener("click", run);
  form.querySelector("input")?.focus();
}

/**
 * Copy to the clipboard. The asynchronous clipboard only exists on HTTPS or
 * localhost; on plain HTTP (a local network address) the text is copied with
 * the older command, and if that fails too it is selected for Ctrl+C.
 * ``from`` is the button pressed; ``select`` the element to select as a last resort.
 */
/**
 * Where the browser may refuse to copy (a plain http:// address), say so before the person tries,
 * next to the secret: one tap selects it, then « Copier » from the browser (acceptance ERGO-005).
 */
export function manualCopyNote(t) {
  if (window.isSecureContext) return "";
  return html`<p class="copy-manual" role="note">${raw(icon("info"))}<span>${t("copy.manualHint")}</span></p>`;
}

function selectFor(element) {
  if (!element) return false;
  if (element.matches?.("input, textarea")) {
    element.focus();
    element.select();
    return true;
  }
  window.getSelection()?.selectAllChildren(element);
  return true;
}

export async function copyText(app, text, { from = null, select = null } = {}) {
  const { t } = app.i18n;
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      app.toast(t("mfa.copied"));
      return;
    } catch (_) { /* fall back below */ }
  }
  // Inside a modal dialog the rest of the page is inert: work inside the dialog.
  const host = from?.closest("dialog") || document.body;
  const area = document.createElement("textarea");
  area.className = "copy-buffer";
  area.value = text;
  area.setAttribute("readonly", "");
  area.setAttribute("aria-hidden", "true");
  area.tabIndex = -1;
  host.appendChild(area);
  area.select();
  let copied = false;
  try { copied = document.execCommand("copy"); } catch (_) { copied = false; }
  area.remove();
  from?.focus({ preventScroll: true });
  if (copied) {
    app.toast(t("mfa.copied"));
    return;
  }
  const target = select || from?.closest(".codebox")?.querySelector("code");
  const selected = selectFor(target);
  // Said in the window too, not only in a message that fades away.
  const place = from?.closest(".field, .actions, .inline-field")?.parentElement;
  if (place && !place.querySelector(".copy-manual.failed")) {
    place.insertAdjacentHTML("beforeend", markup(html`<p class="copy-manual failed" role="status">${raw(icon("alert"))}<span>${t(selected ? "mfa.copySelected" : "mfa.copyFallback")}</span></p>`));
  }
  app.toast(t(selected ? "mfa.copySelected" : "mfa.copyFallback"), true);
}

function download(name, text) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function stepper(t, current) {
  return html`<ol class="stepper" aria-label="${t("mfa.stepOf", { n: current })}">
    ${[1, 2, 3].map((n) => html`<li class="${n < current ? "done" : n === current ? "current" : ""}" ${raw(n === current ? 'aria-current="step"' : "")}><span class="n">${n < current ? raw(icon("check")) : n}</span><span>${t(`mfa.step${n}`)}</span></li>`)}
  </ol>`;
}

function codesBlock(app, codes) {
  const { t } = app.i18n;
  return html`
    <p class="reading">${t("mfa.codesHelp")}</p>
    <ul class="codes" aria-label="${t("mfa.step3")}">${codes.map((code) => html`<li><code>${code}</code></li>`)}</ul>
    <div class="actions">
      <button type="button" class="btn ghost small" data-copy-codes>${raw(icon("copy"))}${t("mfa.copy")}</button>
      <button type="button" class="btn ghost small" data-download-codes>${raw(icon("download"))}${t("mfa.download")}</button>
    </div>
    ${manualCopyNote(t)}
    <label class="check-line"><input type="checkbox" data-stored> <span>${t("mfa.stored")}</span></label>`;
}

/** Show recovery codes; the dialog can only be closed once the user says they stored them. */
function showCodes(app, dialog, codes, onDone) {
  const { t } = app.i18n;
  const text = `${t("mfa.fileHeader")}\n${new Date().toISOString().slice(0, 10)}\n\n${codes.join("\n")}\n`;
  dialog.querySelector(".dbody").innerHTML = markup(html`${dialog.dataset.stepper === "1" ? stepper(t, 3) : ""}${codesBlock(app, codes)}`);
  dialog.querySelector(".dfoot").innerHTML = markup(html`<button type="button" class="btn primary" data-finish disabled>${raw(icon("check"))}${t("mfa.finish")}</button>`);
  dialog.querySelector(".dhead [data-close]")?.remove();
  dialog.dataset.locked = "1"; // a click outside must not lose codes shown only once
  const finish = dialog.querySelector("[data-finish]");
  dialog.querySelector("[data-stored]").addEventListener("change", (event) => { finish.disabled = !event.target.checked; });
  dialog.querySelector("[data-copy-codes]").addEventListener("click", (event) => copyText(app, text, { from: event.currentTarget, select: dialog.querySelector("ul.codes") }));
  dialog.querySelector("[data-download-codes]").addEventListener("click", () => download("rental-cockpit-recovery-codes.txt", text));
  dialog.addEventListener("cancel", (event) => { if (finish.disabled) event.preventDefault(); });
  finish.addEventListener("click", () => { dialog.close(); onDone(); });
  finish.focus();
}

// ------------------------------------------------------------------ password

export function openPasswordDialog(app) {
  const { t } = app.i18n;
  const min = app.state.account?.min_password_length || 10;
  const dialog = openDialog(app, {
    title: t("pwd.title"), subtitle: t("pwd.sub"),
    body: html`<form class="form-grid" novalidate>
      <div class="field wide"><label for="rc-pc">${t("pwd.current")}</label><input id="rc-pc" name="current" type="password" autocomplete="current-password" required></div>
      <div class="field"><label for="rc-pn">${t("pwd.new")}</label><input id="rc-pn" name="new" type="password" autocomplete="new-password" minlength="${min}" required aria-describedby="rc-pn-h"><span class="help" id="rc-pn-h">${t("auth.passwordHelp")}</span></div>
      <div class="field"><label for="rc-pf">${t("pwd.confirm")}</label><input id="rc-pf" name="confirm" type="password" autocomplete="new-password" required></div>
      <div class="wide" data-error aria-live="assertive"></div></form>`,
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.cancel")}</button><button type="button" class="btn primary" data-submit>${raw(icon("check"))}${t("pwd.save")}</button>`,
  });
  wire(dialog, async (data) => {
    await app.api.request("POST", "/api/account/password", { body: Object.fromEntries(data.entries()) });
    dialog.close();
    app.toast(t("pwd.done"));
  });
}

// ------------------------------------------------------------------ two-factor sign-in

export function openMfaEnable(app) {
  const { t } = app.i18n;
  const dialog = openDialog(app, {
    title: t("mfa.title"),
    body: html`${stepper(t, 1)}<form class="stack" novalidate>
      <div class="field"><label for="rc-mp">${t("auth.password")}</label><input id="rc-mp" name="password" type="password" autocomplete="current-password" required></div>
      <div data-error aria-live="assertive"></div></form>`,
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.cancel")}</button><button type="button" class="btn primary" data-submit>${raw(icon("arrowRight"))}${t("mfa.continue")}</button>`,
  });
  dialog.dataset.stepper = "1";
  wire(dialog, async (data) => {
    const setup = await app.api.request("POST", "/api/account/mfa/start", { body: { password: data.get("password") } });
    // Step 2: QR code (generated by the server) and the first code.
    dialog.querySelector(".dbody").innerHTML = markup(html`${stepper(t, 2)}
      <div class="mfa-scan">
        <img class="qr" src="${setup.qr}" alt="${t("mfa.qrAlt")}" width="210" height="210">
        <div class="stack">
          <p class="reading">${t("mfa.scanHelp")}</p>
          <div class="field"><span class="help">${t("mfa.manual")}</span><div class="codebox"><code>${setup.secret}</code><button type="button" class="iconbtn" data-copy-secret aria-label="${t("mfa.copy")}">${raw(icon("copy"))}</button></div>${manualCopyNote(t)}</div>
          <form class="stack" novalidate>
            <div class="field"><label for="rc-mc">${t("mfa.firstCode")}</label><input id="rc-mc" name="code" inputmode="numeric" autocomplete="one-time-code" maxlength="6" pattern="[0-9]{6}" required></div>
            <div data-error aria-live="assertive"></div>
          </form>
        </div>
      </div>`);
    dialog.querySelector(".dfoot").innerHTML = markup(html`<button type="button" class="btn ghost" data-close>${t("common.cancel")}</button><button type="button" class="btn primary" data-submit>${raw(icon("shieldCheck"))}${t("mfa.activate")}</button>`);
    dialog.querySelector("[data-copy-secret]").addEventListener("click", (event) => copyText(app, setup.secret.replaceAll(" ", ""), { from: event.currentTarget }));
    wire(dialog, async (codeData) => {
      const result = await app.api.request("POST", "/api/account/mfa/enable", { body: { code: codeData.get("code") } });
      showCodes(app, dialog, result.recovery_codes, async () => {
        app.toast(t("mfa.enabled"));
        await app.loadAccount();
      });
    });
  });
}

function passwordAndCode(app, { title, subtitle, submitLabel, submitIcon, url, onSuccess }) {
  const { t } = app.i18n;
  const dialog = openDialog(app, {
    title, subtitle,
    body: html`<form class="form-grid" novalidate>
      <div class="field"><label for="rc-dp">${t("auth.password")}</label><input id="rc-dp" name="password" type="password" autocomplete="current-password" required></div>
      <div class="field"><label for="rc-dc">${t("auth.codeLabel")}</label><input id="rc-dc" name="code" autocomplete="one-time-code" required></div>
      <div class="wide" data-error aria-live="assertive"></div></form>`,
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.cancel")}</button><button type="button" class="btn primary" data-submit>${raw(icon(submitIcon))}${submitLabel}</button>`,
  });
  wire(dialog, async (data) => {
    const result = await app.api.request("POST", url, { body: Object.fromEntries(data.entries()) });
    await onSuccess(dialog, result);
  });
}

export function openMfaDisable(app) {
  const { t } = app.i18n;
  passwordAndCode(app, {
    title: t("mfa.disableTitle"), subtitle: t("mfa.disableSub"), submitLabel: t("settings.mfaDisable"), submitIcon: "shield",
    url: "/api/account/mfa/disable",
    onSuccess: async (dialog) => { dialog.close(); app.toast(t("mfa.disabled")); await app.loadAccount(); },
  });
}

export function openMfaCodes(app) {
  const { t } = app.i18n;
  passwordAndCode(app, {
    title: t("mfa.codesTitle"), subtitle: t("mfa.codesSub"), submitLabel: t("mfa.generate"), submitIcon: "key",
    url: "/api/account/mfa/recovery",
    onSuccess: async (dialog, result) => showCodes(app, dialog, result.recovery_codes, () => app.loadAccount()),
  });
}

// ------------------------------------------------------------------ Home Assistant keys

export function openCreateKey(app) {
  const { t } = app.i18n;
  const dialog = openDialog(app, {
    title: t("key.title"),
    body: html`<form class="stack" novalidate>
      <div class="field"><label for="rc-kn">${t("key.name")}</label><input id="rc-kn" name="name" maxlength="60" required value="${t("key.namePh")}"></div>
      <div data-error aria-live="assertive"></div></form>`,
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.cancel")}</button><button type="button" class="btn primary" data-submit>${raw(icon("key"))}${t("key.create")}</button>`,
  });
  wire(dialog, async (data) => {
    const created = await app.api.request("POST", "/api/account/keys", { body: { name: data.get("name") } });
    const line = `rental_cockpit_authorization: "Bearer ${created.token}"`;
    dialog.querySelector(".dbody").innerHTML = markup(html`
      <div class="tip">${raw(icon("alert"))}<div>${t("key.once")}</div></div>
      <div class="field"><span class="help">${t("key.secretLine")}</span><div class="codebox"><code>${line}</code><button type="button" class="iconbtn" data-copy-line aria-label="${t("mfa.copy")}">${raw(icon("copy"))}</button></div>${manualCopyNote(t)}</div>`);
    dialog.querySelector(".dfoot").innerHTML = markup(html`<button type="button" class="btn primary" data-close>${raw(icon("check"))}${t("common.done")}</button>`);
    dialog.querySelector("[data-copy-line]").addEventListener("click", (event) => copyText(app, line, { from: event.currentTarget }));
    dialog.addEventListener("close", () => app.loadAccount());
  });
}

export function openRevokeKey(app, key) {
  const { t } = app.i18n;
  const dialog = openDialog(app, {
    title: t("key.revokeTitle", { name: key.name }), subtitle: t("key.revokeSub"),
    body: html`<form novalidate><div data-error aria-live="assertive"></div></form>`,
    footer: html`<button type="button" class="btn ghost" data-close>${t("common.cancel")}</button><button type="button" class="btn danger" data-submit>${raw(icon("trash"))}${t("settings.revoke")}</button>`,
  });
  wire(dialog, async () => {
    await app.api.request("DELETE", `/api/account/keys/${encodeURIComponent(key.id)}`);
    dialog.close();
    app.toast(t("key.revoked"));
    await app.loadAccount();
  });
}
