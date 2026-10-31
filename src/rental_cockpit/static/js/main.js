/* Copyright © 2026 Vincent Fournet */
// Entry point of the Rental Cockpit interface. Plain ES modules, no build
// step, nothing downloaded from elsewhere: every file is served by the app.

import { App } from "./app.js";

const app = new App(document.getElementById("app"));
app.start();
