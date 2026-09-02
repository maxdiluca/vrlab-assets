import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const [html, app] = await Promise.all([
  readFile(new URL("../index.html", import.meta.url), "utf8"),
  readFile(new URL("../app.js", import.meta.url), "utf8"),
]);

test("provides a separate authenticated staff route without changing kiosk links", () => {
  assert.match(html, /href="\.\/\?staff=1"/);
  assert.match(html, /data-staff-view hidden/);
  assert.ok(
    html.includes(
      'href="https://app.assetbots.com/" target="_blank" rel="noopener noreferrer" referrerpolicy="no-referrer"',
    ),
  );
  assert.match(html, /Writer access is database-wide/);
  assert.match(html, /A new tab does not isolate an existing Safari session/);
});

test("routes setup before staff and moves skip-link focus", () => {
  const setupRoute = app.indexOf('parameters.get("setup") === "1"');
  const staffRoute = app.indexOf('parameters.get("staff") === "1"');

  assert.notEqual(setupRoute, -1);
  assert.notEqual(staffRoute, -1);
  assert.ok(setupRoute < staffRoute);
  assert.match(
    app,
    /function configureSkipTarget[\s\S]*event\.preventDefault\(\);[\s\S]*target\.focus\(\);/,
  );
  assert.ok(html.includes('id="staff-title" tabindex="-1"'));
  assert.ok(html.includes('id="setup-title" tabindex="-1"'));
});
