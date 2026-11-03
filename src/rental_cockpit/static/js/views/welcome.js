/* Copyright © 2026 Vincent Fournet */
// First opening: two explicit choices (UX 02) and the five guided steps (UX 01).

import { html, raw } from "../dom.js";
import { icon, WELCOME_ART } from "../icons.js";

export function stepsList(v, done = {}) {
  const { t } = v.i18n;
  const steps = [
    ["s1", done.property], ["s2", done.property], ["s3", done.first_record], ["s4", done.dashboard], ["s5", done.backup],
  ];
  return html`
    <ol class="steps">
      ${steps.map(([key, isDone], index) => html`
        <li>
          <span class="n ${isDone ? "done" : ""}" aria-hidden="true">${isDone ? raw(icon("check")) : index + 1}</span>
          <span><b>${t(`welcome.${key}`)}</b><span>${t(`welcome.${key}h`)}</span></span>
        </li>`)}
    </ol>`;
}

export function renderWelcome(v) {
  const { t } = v.i18n;
  const admin = v.boot.user.is_admin;
  return html`
    <div class="welcome">
      <section class="card hero-card">
        <div class="stack">
          ${raw(WELCOME_ART)}
          <div>
            <h1>${t("welcome.title")}</h1>
            <p class="tagline">${t("welcome.tagline")}</p>
          </div>
          <p class="intro">${t("welcome.intro")}</p>
        </div>
        <div class="stack">
          ${stepsList(v)}
          <div class="choices">
            ${admin ? html`
              <button type="button" class="choice primary" data-action="start" data-value="own_data">
                ${raw(icon("play"))}<span><b>${t("welcome.own")}</b><span>${t("welcome.ownHint")}</span></span>
              </button>` : html`<div class="note">${raw(icon("info"))}<span>${t("welcome.readerNote")}</span></div>`}
            <button type="button" class="choice secondary" data-action="start" data-value="demo">
              ${raw(icon("eye"))}<span><b>${t("welcome.demo")}</b><span>${t("welcome.demoHint")}</span></span>
            </button>
          </div>
          <p class="reading">${raw(icon("info"))}<span>${t("welcome.later")}</span></p>
        </div>
      </section>
    </div>`;
}

export function renderOnboarding(v) {
  const { t } = v.i18n;
  return html`
    <section class="card stack">
      <div class="card-head flush">
        <span class="ico">${raw(icon("logo"))}</span>
        <div><h2>${t("onboard.title")}</h2><p class="reading">${t("onboard.sub")}</p></div>
      </div>
      ${stepsList(v, v.boot.real.onboarding || {})}
      ${v.canWrite ? html`<div><button type="button" class="btn primary" data-action="add-property">${raw(icon("plus"))}${t("onboard.cta")}</button></div>` : ""}
    </section>`;
}

export function renderNoAccess(v) {
  const { t } = v.i18n;
  return html`
    <section class="card placeholder">
      <h2>${t("noaccess.title")}</h2>
      <p class="reading">${t("noaccess.text")}</p>
      <button type="button" class="btn outline-accent" data-action="start" data-value="demo">${raw(icon("eye"))}${t("welcome.demo")}</button>
    </section>`;
}
