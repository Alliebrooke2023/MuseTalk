// Shared test harness: tiny assert lib + jsdom boot helper.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { JSDOM } from "jsdom";

const __dirname = dirname(fileURLToPath(import.meta.url));
const HTML_PATH = join(__dirname, "..", "index.html");

export const SITE_URL = "https://everythingsforsale.netlify.app/";

// Read the page source once; callers may pass a mutated source string instead.
export function readSource() {
  return readFileSync(HTML_PATH, "utf8");
}

// Boot a fresh jsdom instance and return its window (with window.EFS ready).
export function boot(source, url = SITE_URL) {
  const html = source ?? readSource();
  const dom = new JSDOM(html, {
    url,
    runScripts: "dangerously",
    pretendToBeVisual: true,
  });
  const { window } = dom;
  if (!window.EFS) throw new Error("boot failed: window.EFS is undefined");
  return window;
}

// Minimal test runner.
export function createSuite(name) {
  const results = [];
  function check(label, fn) {
    try {
      const r = fn();
      if (r === false) throw new Error("returned false");
      results.push({ label, ok: true });
    } catch (e) {
      results.push({ label, ok: false, err: e && e.message ? e.message : String(e) });
    }
  }
  function assert(cond, msg) {
    if (!cond) throw new Error(msg || "assertion failed");
  }
  function eq(a, b, msg) {
    if (a !== b) throw new Error((msg || "not equal") + ` (got ${JSON.stringify(a)}, want ${JSON.stringify(b)})`);
  }
  function report() {
    const passed = results.filter((r) => r.ok).length;
    const failed = results.length - passed;
    console.log(`\n=== ${name} — ${passed}/${results.length} passing ===`);
    for (const r of results) {
      if (!r.ok) console.log(`  ✗ ${r.label}\n      ${r.err}`);
    }
    if (failed === 0) console.log(`  ✓ all ${results.length} checks passed`);
    return { name, passed, failed, total: results.length };
  }
  return { check, assert, eq, report, results };
}
