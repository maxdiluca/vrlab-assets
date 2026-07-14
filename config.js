export const STORAGE_KEY = "vrlab.assetbots.kiosks.v1";

export const INVENTORIES = Object.freeze([
  Object.freeze({ id: "visitor-cards", label: "Visitor cards" }),
  Object.freeze({ id: "headsets", label: "Headsets" }),
  Object.freeze({ id: "it-equipment", label: "IT equipment" }),
  Object.freeze({ id: "various", label: "Various equipment" }),
  Object.freeze({ id: "storage-room", label: "Storage room" }),
]);

// Public, limited-access kiosk launch URLs. Do not place API keys or
// administrator credentials in this client-side configuration.
export const DEFAULT_CONFIG = Object.freeze({
  "visitor-cards": "https://app.assetbots.com/kiosk/ko_cmrkjll92000h3b69doc4eh4j/launch",
  headsets: "https://app.assetbots.com/kiosk/ko_cmrkpw79y000m3b69rjyk94l3/launch",
  "it-equipment": "https://app.assetbots.com/kiosk/ko_cmrkpx814000h3b67d6xyghj3/launch",
  various: "https://app.assetbots.com/kiosk/ko_cmrkpy4y6000h3b69845u6hpm/launch",
  "storage-room": "https://app.assetbots.com/kiosk/ko_cmrkjkz0h000i3b69t1d860bf/launch",
});

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
    if (!raw) return { ...DEFAULT_CONFIG };

    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return { ...DEFAULT_CONFIG };
    }

    const config = { ...DEFAULT_CONFIG };
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
    return { ...DEFAULT_CONFIG };
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
