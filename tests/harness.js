'use strict';
// Harness pro testy jádra kalkulačky (dod-2).
// Použití: node tests/harness.js <cesta k index.html> [klávesy...]
// Vyřízne obsah <script id="calc-core">, spustí ho ve vm kontextu bez
// document/window a na stdout vypíše JSON view po stisku zadaných kláves.
// Chyby harnessu (chybějící soubor, chybějící/duplicitní skript, chybějící
// CalcCore) končí exit 2, aby se lišily od selhání assertů (exit 1).
// Používá jen vestavěné moduly Node: fs, path, vm.

const fs = require('fs');
const path = require('path');
const vm = require('vm');

function fail(msg) {
  process.stderr.write('harness: ' + msg + '\n');
  process.exit(2);
}

const args = process.argv.slice(2);
if (args.length < 1) {
  fail('použití: node tests/harness.js <cesta k index.html> [klávesy...]');
}

const file = path.resolve(process.cwd(), args[0]);
const keys = args.slice(1);

let html;
try {
  html = fs.readFileSync(file, 'utf8');
} catch (e) {
  fail('nelze načíst soubor ' + file + ': ' + (e && e.message ? e.message : String(e)));
}

// Tolerantní k dalším atributům, pořadí atributů, dvojitým/jednoduchým
// uvozovkám i hodnotě bez uvozovek. `\s` před `id` brání shodě s např. data-id.
const SCRIPT_RE = /<script\b[^>]*\sid\s*=\s*(?:"calc-core"|'calc-core'|calc-core(?=[\s>\/]))[^>]*>([\s\S]*?)<\/script\s*>/gi;

const bodies = [];
let m;
while ((m = SCRIPT_RE.exec(html)) !== null) {
  bodies.push(m[1]);
}

if (bodies.length === 0) {
  fail('v souboru ' + file + ' chybí <script id="calc-core">');
}
if (bodies.length > 1) {
  fail('v souboru ' + file + ' je více <script id="calc-core"> (' + bodies.length + ')');
}

// Kontext bez document a window – jádro nesmí sahat na DOM.
const context = vm.createContext({});
try {
  vm.runInContext(bodies[0], context, { filename: 'calc-core.js' });
} catch (e) {
  fail('chyba při běhu calc-core: ' + (e && e.stack ? e.stack : String(e)));
}

const CalcCore = context.CalcCore;
if (!CalcCore || typeof CalcCore !== 'object' && typeof CalcCore !== 'function') {
  fail('calc-core nevystavil globalThis.CalcCore');
}
for (const name of ['initialState', 'press', 'view']) {
  if (typeof CalcCore[name] !== 'function') {
    fail('CalcCore.' + name + ' není funkce');
  }
}

let s;
try {
  s = CalcCore.initialState();
  for (const key of keys) {
    s = CalcCore.press(s, key);
  }
  const out = CalcCore.view(s);
  process.stdout.write(JSON.stringify(out) + '\n');
} catch (e) {
  fail('výjimka v CalcCore: ' + (e && e.stack ? e.stack : String(e)));
}
