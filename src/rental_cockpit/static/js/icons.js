/* Copyright © 2026 Vincent Fournet */
// Line icons drawn for Rental Cockpit (24 × 24 grid, stroke = currentColor).
// Icons are decorative: the text next to them carries the meaning.

const PATHS = {
  logo: '<path d="M3.5 11.8 12 4.5l8.5 7.3"/><path d="M5.8 10v9.2a1.3 1.3 0 0 0 1.3 1.3h9.8a1.3 1.3 0 0 0 1.3-1.3V10"/><rect x="10" y="12.6" width="4" height="4" rx=".7"/>',
  home: '<path d="M3.5 11 12 4l8.5 7"/><path d="M5.5 9.6V20h13V9.6"/><path d="M10 20v-5.5h4V20"/>',
  building: '<rect x="5" y="3.5" width="14" height="17" rx="1.6"/><path d="M9 7.5h1.5M13.5 7.5H15M9 11h1.5M13.5 11H15M9 14.5h1.5M13.5 14.5H15M10.5 20.5V18h3v2.5"/>',
  chart: '<path d="M5 20v-6M10 20V9M15 20v-8M20 20V5"/>',
  calendar: '<rect x="3.5" y="5" width="17" height="15.5" rx="2.2"/><path d="M3.5 9.8h17M8 3v4M16 3v4"/>',
  wallet: '<rect x="3" y="5.5" width="18" height="13" rx="2.2"/><path d="M3 10h18M7 14.5h4"/>',
  users: '<circle cx="9" cy="8" r="3.2"/><path d="M3.3 19.2c.7-3.3 3-5.1 5.7-5.1s5 1.8 5.7 5.1"/><path d="M15.4 4.9a3.1 3.1 0 0 1 0 6.1M17.4 14.3c1.7.6 2.9 2.3 3.3 4.9"/>',
  file: '<path d="M13.8 3H7.2A2.2 2.2 0 0 0 5 5.2v13.6A2.2 2.2 0 0 0 7.2 21h9.6a2.2 2.2 0 0 0 2.2-2.2V8.2z"/><path d="M13.8 3v5.2H19M9 13h6M9 16.8h4"/>',
  sliders: '<path d="M4 6.5h9M17 6.5h3M4 12h3M11 12h9M4 17.5h11M19 17.5h1"/><circle cx="15" cy="6.5" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="17" cy="17.5" r="2"/>',
  coins: '<ellipse cx="12" cy="6.5" rx="7" ry="2.6"/><path d="M5 6.5v5c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6v-5"/><path d="M5 11.5v5c0 1.4 3.1 2.6 7 2.6s7-1.2 7-2.6v-5"/>',
  scale: '<path d="M12 4.5V20M8 20h8M5 7.5h14M10.3 5.5h3.4"/><path d="M2.6 14 5 8l2.4 6"/><path d="M2.6 14a2.4 1.8 0 0 0 4.8 0"/><path d="M16.6 14 19 8l2.4 6"/><path d="M16.6 14a2.4 1.8 0 0 0 4.8 0"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  upload: '<path d="M12 15V4.5M7.6 8.6 12 4.2l4.4 4.4"/><path d="M4 14.5v4A1.5 1.5 0 0 0 5.5 20h13a1.5 1.5 0 0 0 1.5-1.5v-4"/>',
  chevronRight: '<path d="m9.5 6 6 6-6 6"/>',
  chevronDown: '<path d="m6 9.5 6 6 6-6"/>',
  arrowRight: '<path d="M5 12h14M13.5 6.5 19 12l-5.5 5.5"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9.7 9.4a2.4 2.4 0 0 1 4.6 1c0 1.6-2.3 2.1-2.3 3.5"/><path d="M12 17.1h.01"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5.5M12 7.9h.01"/>',
  alert: '<path d="M10.4 4.6 2.9 17.8a1.8 1.8 0 0 0 1.6 2.7h15a1.8 1.8 0 0 0 1.6-2.7L13.6 4.6a1.8 1.8 0 0 0-3.2 0z"/><path d="M12 9.6v4.4M12 17h.01"/>',
  hourglass: '<path d="M6.5 3.5h11M6.5 20.5h11"/><path d="M8 3.5v2.3c0 2.1 4 4.2 4 6.2s-4 4.1-4 6.2v2.3M16 3.5v2.3c0 2.1-4 4.2-4 6.2s4 4.1 4 6.2v2.3"/>',
  docAlert: '<path d="M13.8 3H7.2A2.2 2.2 0 0 0 5 5.2v13.6A2.2 2.2 0 0 0 7.2 21h9.6a2.2 2.2 0 0 0 2.2-2.2V8.2z"/><path d="M13.8 3v5.2H19M12 11.5v3.2M12 17.4h.01"/>',
  split: '<path d="M4 12h6l4-5h6M14 17h6M10 12l4 5"/>',
  moon: '<path d="M19.5 14.6A7.8 7.8 0 1 1 9.4 4.5a6.3 6.3 0 0 0 10.1 10.1z"/>',
  bell: '<path d="M6 16.5v-5.3a6 6 0 0 1 12 0v5.3l1.6 2H4.4z"/><path d="M10 20.6a2 2 0 0 0 4 0"/>',
  close: '<path d="M6.5 6.5 17.5 17.5M17.5 6.5l-11 11"/>',
  check: '<path d="m5 12.6 4.4 4.4L19 7.4"/>',
  checkCircle: '<circle cx="12" cy="12" r="9"/><path d="m8.2 12.3 2.6 2.6 5-5.2"/>',
  eye: '<path d="M2.6 12S6 5.6 12 5.6 21.4 12 21.4 12 18 18.4 12 18.4 2.6 12 2.6 12z"/><circle cx="12" cy="12" r="3"/>',
  bulb: '<path d="M9.2 18h5.6M10.2 21h3.6"/><path d="M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z"/>',
  search: '<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/>',
  logout: '<path d="M14 4.5h3.5A1.5 1.5 0 0 1 19 6v12a1.5 1.5 0 0 1-1.5 1.5H14"/><path d="M10 16.5 5.5 12 10 7.5M5.5 12H15"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  key: '<circle cx="8" cy="15.5" r="4"/><path d="M10.9 12.6 19.5 4M15.8 7.7l2.6 2.6M13.6 9.9l1.9 1.9"/>',
  shield: '<path d="M12 3.2 4.8 6v5.4c0 4.5 3.1 8.1 7.2 9.4 4.1-1.3 7.2-4.9 7.2-9.4V6z"/>',
  shieldCheck: '<path d="M12 3.2 4.8 6v5.4c0 4.5 3.1 8.1 7.2 9.4 4.1-1.3 7.2-4.9 7.2-9.4V6z"/><path d="m8.9 12 2.2 2.2 4.1-4.4"/>',
  lock: '<rect x="5" y="10.5" width="14" height="10" rx="2.2"/><path d="M8.2 10.5V7.6a3.8 3.8 0 0 1 7.6 0v2.9M12 14.5v2.2"/>',
  copy: '<rect x="8.5" y="8.5" width="11.5" height="11.5" rx="2"/><path d="M15.5 8.5V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v7.5a2 2 0 0 0 2 2h2.5"/>',
  download: '<path d="M12 4v11M7.6 10.6 12 15l4.4-4.4"/><path d="M4 15.5v3A1.5 1.5 0 0 0 5.5 20h13a1.5 1.5 0 0 0 1.5-1.5v-3"/>',
  trash: '<path d="M4.5 7h15M9.5 7V4.5h5V7M6.5 7l1 13h9l1-13M10.2 11v5.5M13.8 11v5.5"/>',
  external: '<path d="M14 4h6v6M20 4l-8.5 8.5M18 13.5V19a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5.5"/>',
  user: '<circle cx="12" cy="8" r="3.6"/><path d="M5 20c.9-3.7 3.7-5.6 7-5.6s6.1 1.9 7 5.6"/>',
  link: '<path d="M10.2 13.8a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M13.8 10.2a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
  repeat: '<path d="M4 10.5V9a3 3 0 0 1 3-3h12"/><path d="m16 3 3 3-3 3"/><path d="M20 13.5V15a3 3 0 0 1-3 3H5"/><path d="m8 21-3-3 3-3"/>',
  pencil: '<path d="M4 20h4L18.6 9.4a2.1 2.1 0 0 0-3-3L5 17v3z"/><path d="m14.5 7.5 3 3"/>',
  ban: '<circle cx="12" cy="12" r="8.5"/><path d="m6 6 12 12"/>',
  receipt: '<path d="M6 3.5h12v17l-2.4-1.6-2.4 1.6-1.2-.8-1.2.8-2.4-1.6L6 20.5z"/><path d="M9 8h6M9 11.5h6M9 15h3.5"/>',
  archive: '<rect x="3.5" y="4.5" width="17" height="4.5" rx="1.2"/><path d="M5 9v9.3A1.7 1.7 0 0 0 6.7 20h10.6a1.7 1.7 0 0 0 1.7-1.7V9M10 13h4"/>',
  tag: '<path d="M3.5 12.2V4.8a1.3 1.3 0 0 1 1.3-1.3h7.4l8.3 8.3a1.3 1.3 0 0 1 0 1.8l-7.4 7.4a1.3 1.3 0 0 1-1.8 0z"/><circle cx="8" cy="8" r="1.4"/>',
  filter: '<path d="M4 5.5h16l-6 7.2v5.6l-4 1.7v-7.3z"/>',
};

const FILLED = {
  dots: '<circle cx="5.5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="18.5" cy="12" r="1.6"/>',
  play: '<path d="M8 5.2v13.6a.8.8 0 0 0 1.2.7l10.6-6.8a.8.8 0 0 0 0-1.4L9.2 4.5A.8.8 0 0 0 8 5.2z"/>',
};

/** Inline SVG markup for an icon name. */
export function icon(name, cls = "") {
  if (FILLED[name]) return `<svg class="i filled ${cls}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${FILLED[name]}</svg>`;
  return `<svg class="i ${cls}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${PATHS[name] || PATHS.info}</svg>`;
}

/** Icon of a property according to its kind. */
export function propertyIcon(kind, cls = "") {
  return icon(kind === "studio" || kind === "room" ? "building" : "home", cls);
}

/** Welcome illustration: a small lit house, a dotted path and a checklist. */
export const WELCOME_ART = `
<svg class="art" viewBox="0 0 420 220" aria-hidden="true" focusable="false">
  <defs>
    <linearGradient id="rcwin" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#ffd27a"/><stop offset="1" stop-color="#f0a83c"/></linearGradient>
    <linearGradient id="rcroof" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#1d4258"/><stop offset="1" stop-color="#143247"/></linearGradient>
  </defs>
  <ellipse cx="128" cy="200" rx="118" ry="10" fill="#0f2a3a"/>
  <path d="M40 196c6-34 2-58 14-84 4 30 2 58-2 84z" fill="#123a42"/>
  <path d="M56 198c2-22 8-40 6-62 10 20 6 44-2 62z" fill="#164a50"/>
  <path d="M60 110 128 52l68 58v86H60z" fill="#122d40" stroke="#2c5a74" stroke-width="2"/>
  <path d="M48 116 128 46l80 70" fill="none" stroke="#3a6c87" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
  <rect x="104" y="128" width="32" height="32" rx="3" fill="url(#rcwin)"/>
  <path d="M120 128v32M104 144h32" stroke="#c98a2c" stroke-width="2"/>
  <rect x="160" y="138" width="22" height="58" rx="2" fill="#0e2433" stroke="#2c5a74" stroke-width="2"/>
  <rect x="72" y="150" width="18" height="18" rx="2" fill="url(#rcwin)" opacity=".85"/>
  <path d="M206 186c26 0 30-34 54-34s26-40 50-40" fill="none" stroke="#3fd8c6" stroke-width="3" stroke-dasharray="2 9" stroke-linecap="round"/>
  <circle cx="206" cy="186" r="6" fill="#3fd8c6"/><circle cx="258" cy="152" r="6" fill="#3fd8c6"/><circle cx="310" cy="112" r="6" fill="#3fd8c6"/>
  <rect x="300" y="18" width="104" height="120" rx="12" fill="#11283a" stroke="#2c5a74" stroke-width="2"/>
  <g stroke-linecap="round">
    <circle cx="322" cy="44" r="8" fill="#3fd8c6"/><path d="m318 44 3 3 5-6" stroke="#04211f" stroke-width="2.2" fill="none"/><path d="M340 44h48" stroke="#2f6680" stroke-width="5"/>
    <circle cx="322" cy="70" r="8" fill="#3fd8c6"/><path d="m318 70 3 3 5-6" stroke="#04211f" stroke-width="2.2" fill="none"/><path d="M340 70h40" stroke="#2f6680" stroke-width="5"/>
    <circle cx="322" cy="96" r="8" fill="#3fd8c6"/><path d="m318 96 3 3 5-6" stroke="#04211f" stroke-width="2.2" fill="none"/><path d="M340 96h44" stroke="#2f6680" stroke-width="5"/>
    <circle cx="322" cy="122" r="8" fill="none" stroke="#3fd8c6" stroke-width="2"/><path d="M340 122h34" stroke="#2f6680" stroke-width="5"/>
  </g>
</svg>`;
