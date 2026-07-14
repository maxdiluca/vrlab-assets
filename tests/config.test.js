import assert from "node:assert/strict";
import test from "node:test";

import {
  INVENTORIES,
  STORAGE_KEY,
  clearConfig,
  loadConfig,
  normaliseAssetbotsUrl,
  saveConfig,
} from "../config.js";

function memoryStorage() {
  const data = new Map();
  return {
    getItem: (key) => data.get(key) ?? null,
    setItem: (key, value) => data.set(key, value),
    removeItem: (key) => data.delete(key),
  };
}

test("normalises secure Assetbots URLs", () => {
  assert.equal(
    normaliseAssetbotsUrl(" https://app.assetbots.com/kiosk/example#ignored "),
    "https://app.assetbots.com/kiosk/example",
  );
});

test("accepts secure Assetbots subdomains", () => {
  assert.equal(
    normaliseAssetbotsUrl("https://kiosk.assetbots.com/launch/abc"),
    "https://kiosk.assetbots.com/launch/abc",
  );
});

test("rejects insecure, unrelated and credential-bearing URLs", () => {
  assert.throws(() => normaliseAssetbotsUrl("http://app.assetbots.com/kiosk/example"));
  assert.throws(() => normaliseAssetbotsUrl("https://assetbots.example/kiosk/example"));
  assert.throws(() => normaliseAssetbotsUrl("https://user:secret@app.assetbots.com/example"));
});

test("saves, loads and clears a complete configuration", () => {
  const storage = memoryStorage();
  const values = Object.fromEntries(
    INVENTORIES.map(({ id }) => [id, `https://app.assetbots.com/kiosk/${id}`]),
  );

  const saved = saveConfig(storage, values);
  assert.deepEqual(loadConfig(storage), saved);
  assert.ok(storage.getItem(STORAGE_KEY));

  clearConfig(storage);
  assert.deepEqual(loadConfig(storage), {});
});

test("ignores malformed stored data", () => {
  const storage = memoryStorage();
  storage.setItem(STORAGE_KEY, "not json");
  assert.deepEqual(loadConfig(storage), {});
});
