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
    normaliseAssetbotsUrl(" https://app.assetbots.com/assets#ignored "),
    "https://app.assetbots.com/assets",
  );
});

test("accepts secure Assetbots subdomains", () => {
  assert.equal(
    normaliseAssetbotsUrl("https://app.assetbots.com/databases/example"),
    "https://app.assetbots.com/databases/example",
  );
});

test("rejects insecure, unrelated and credential-bearing URLs", () => {
  assert.throws(() => normaliseAssetbotsUrl("http://app.assetbots.com/assets"));
  assert.throws(() => normaliseAssetbotsUrl("https://assetbots.example/assets"));
  assert.throws(() => normaliseAssetbotsUrl("https://user:secret@app.assetbots.com/example"));
});

test("rejects Assetbots kiosk links", () => {
  assert.throws(() => normaliseAssetbotsUrl("https://app.assetbots.com/kiosk/example"));
  assert.throws(() => normaliseAssetbotsUrl("https://kiosk.assetbots.com/launch/example"));
});

test("saves, loads and clears a complete configuration", () => {
  const storage = memoryStorage();
  const values = Object.fromEntries(
    INVENTORIES.map(({ id }) => [id, `https://app.assetbots.com/databases/${id}`]),
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
