/* Copyright © 2026 Vincent Fournet */
// Client of the Rental Cockpit JSON API. The server checks every right again:
// this file only decides what to ask. Changes carry the CSRF token of the
// session and a fresh operation id, so a double click is applied once.

import { opId } from "./dom.js";

export class ApiError extends Error {
  constructor(message, code, status) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

export class Api {
  constructor(lang) {
    this.lang = lang;
    this.dataset = "real";
    this.csrf = "";
    this.onLoginRequired = null;
  }

  async request(method, path, { query = {}, body = null } = {}) {
    const url = new URL(path, window.location.origin);
    for (const [key, value] of Object.entries({ lang: this.lang, ...query })) {
      if (value !== undefined && value !== null) url.searchParams.set(key, value);
    }
    const headers = { Accept: "application/json" };
    if (method !== "GET") {
      headers["Content-Type"] = "application/json";
      headers["X-CSRF-Token"] = this.csrf;
    }
    let response;
    try {
      response = await fetch(url, { method, headers, credentials: "same-origin", body: body ? JSON.stringify(body) : undefined });
    } catch (_) {
      throw new ApiError(this.lang === "fr" ? "Serveur injoignable : vérifiez la connexion puis réessayez. Rien n'a été enregistré." : "Server unreachable: check the connection and try again. Nothing was saved.", "network", 0);
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (response.status === 401 && this.onLoginRequired) this.onLoginRequired();
      throw new ApiError(data.message || response.statusText, data.code || "unknown", response.status);
    }
    if (data.csrf) this.csrf = data.csrf;
    return data;
  }

  get(path, query = {}) {
    return this.request("GET", path, { query: { dataset: this.dataset, ...query } });
  }

  /** A change on the current dataset, with a fresh op_id unless one is given. */
  post(path, body = {}) {
    return this.request("POST", path, { body: { dataset: this.dataset, lang: this.lang, op_id: opId(), ...body } });
  }
}
