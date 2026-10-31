/* Copyright © 2026 Vincent Fournet */
// Minimal templating: every interpolated value is escaped unless wrapped in
// raw(). Imported data (labels, file names) is always text, never HTML (SEC 06).

const RAW = Symbol("raw");

export function raw(markup) {
  return { [RAW]: true, markup: String(markup ?? "") };
}

export function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function part(value) {
  if (value === null || value === undefined || value === false) return "";
  if (Array.isArray(value)) return value.map(part).join("");
  if (typeof value === "object" && value[RAW]) return value.markup;
  return esc(value);
}

/** Tagged template returning a raw() fragment. */
export function html(strings, ...values) {
  let out = strings[0];
  values.forEach((value, index) => {
    out += part(value) + strings[index + 1];
  });
  return raw(out);
}

export function markup(fragment) {
  return part(fragment);
}

/** Fresh identifier for one user action, so a double click is applied once. */
export function opId() {
  const bytes = new Uint8Array(12);
  crypto.getRandomValues(bytes);
  return "op-" + Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}
