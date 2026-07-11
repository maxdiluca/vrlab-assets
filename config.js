export const STORAGE_KEY = "vrlab.assetbots.kiosks.v1";

export const INVENTORIES = Object.freeze([
  Object.freeze({ id: "visitor-cards", label: "Visitor cards" }),
  Object.freeze({ id: "headsets", label: "Headsets" }),
  Object.freeze({ id: "it-equipment", label: "IT equipment" }),
  Object.freeze({ id: "various", label: "Various equipment" }),
  Object.freeze({ id: "storage-room", label: "Storage room" }),
]);

export function normaliseAssetbotsUrl(value) {
  const raw = String(value ?? "").trim();
  if (!raw) {
    throw new Error("Enter all five kiosk URLs.");
  }

  let url;
  try {
    url = new URL(raw);
  } catch {
    throw new Error("Enter a complete URL beginning with https://.");
  }

  const hostname = url.hostname.toLowerCase();
  const isAssetbots = hostname === "assetbots.com" || hostname.endsWith(".assetbots.com");

  if (url.protocol !== "https:" || !isAssetbots || url.username || url.password) {
    throw new Error("Use an HTTPS address on the assetbots.com domain.");
  }

  url.hash = "";
  return url.toString();
}

export function loadConfig(storage) {
  try {
    const raw = storage.getItem(STORAGE_KEY);
    if (!raw) return {};

    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};

    const config = {};
    for (const inventory of INVENTORIES) {
      if (typeof parsed[inventory.id] !== "string") continue;
      try {
        config[inventory.id] = normaliseAssetbotsUrl(parsed[inventory.id]);
      } catch {
        // Ignore corrupt or obsolete entries without exposing their values.
      }
    }
    return config;
  } catch {
    return {};
  }
}

export function saveConfig(storage, values) {
  const config = {};
  for (const inventory of INVENTORIES) {
    config[inventory.id] = normaliseAssetbotsUrl(values[inventory.id]);
  }
  storage.setItem(STORAGE_KEY, JSON.stringify(config));
  return config;
}

export function clearConfig(storage) {
  storage.removeItem(STORAGE_KEY);
}
