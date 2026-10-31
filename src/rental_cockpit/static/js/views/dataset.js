/* Copyright © 2026 Vincent Fournet */
// « Mes données / Démonstration » — always one click away (audit 0.1.0).
// The two datasets are separate registries on the server: switching only
// changes which one is shown, nothing is copied from one to the other.

import { html, raw } from "../dom.js";
import { icon } from "../icons.js";

export function datasetSwitch(v, { compact = false } = {}) {
  const { t } = v.i18n;
  const demoReady = v.session.demo.exists || v.canWrite;
  const pressed = (key) => (v.dataset === key ? "true" : "false");
  return html`
    <div class="dataset-switch ${compact ? "compact" : ""}" role="group" aria-label="${t("dataset.label")}">
      <button type="button" data-action="dataset" data-value="real" aria-pressed="${pressed("real")}">${raw(icon("home"))}<span>${t("dataset.real")}</span></button>
      <button type="button" class="demo" data-action="dataset" data-value="demo" aria-pressed="${pressed("demo")}" ${raw(demoReady ? "" : 'aria-disabled="true"')} title="${demoReady ? "" : t("dataset.demoMissing")}"><span class="dot" aria-hidden="true"></span><span>${t(compact ? "dataset.demoShort" : "dataset.demo")}</span></button>
    </div>`;
}
