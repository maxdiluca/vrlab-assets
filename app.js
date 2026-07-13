import {
  INVENTORIES,
  clearConfig,
  loadConfig,
  saveConfig,
} from "./config.js";

const connection = document.querySelector("[data-connection]");
const connectionLabel = document.querySelector("[data-connection-label]");
const setupNotice = document.querySelector("[data-setup-notice]");
const setupView = document.querySelector("[data-setup-view]");
const setupForm = document.querySelector("[data-setup-form]");
const formMessage = document.querySelector("[data-form-message]");
const clearButton = document.querySelector("[data-clear-config]");
const tiles = new Map(
  [...document.querySelectorAll("[data-inventory]")].map((tile) => [tile.dataset.inventory, tile]),
);

function updateConnectionStatus() {
  const online = navigator.onLine;
  connection.classList.toggle("is-offline", !online);
  connectionLabel.textContent = online ? "Online" : "Offline";
}

function configureTiles(config) {
  let configuredCount = 0;

  for (const inventory of INVENTORIES) {
    const tile = tiles.get(inventory.id);
    const destination = config[inventory.id];
    if (!tile) continue;

    if (destination) {
      tile.href = destination;
      tile.removeAttribute("aria-disabled");
      tile.classList.remove("is-unconfigured");
      tile.setAttribute("aria-label", `Open ${inventory.label} in Assetbots`);
      tile.referrerPolicy = "no-referrer";
      configuredCount += 1;
    } else {
      tile.href = "#";
      tile.setAttribute("aria-disabled", "true");
      tile.classList.add("is-unconfigured");
      tile.setAttribute("aria-label", `${inventory.label} is not configured`);
    }
  }

  setupNotice.hidden = configuredCount === INVENTORIES.length;
}

function showSetup() {
  document.body.classList.add("is-setup");
  document.querySelector(".standard-view").hidden = true;
  setupView.hidden = false;

  const current = loadConfig(window.localStorage);
  for (const inventory of INVENTORIES) {
    const input = setupForm.elements.namedItem(inventory.id);
    if (input && current[inventory.id]) input.value = current[inventory.id];
  }
}

for (const tile of tiles.values()) {
  tile.addEventListener("click", (event) => {
    if (tile.getAttribute("aria-disabled") === "true") event.preventDefault();
  });
}

setupForm.addEventListener("submit", (event) => {
  event.preventDefault();
  formMessage.className = "form-message";
  formMessage.textContent = "";

  try {
    const values = Object.fromEntries(new FormData(setupForm));
    saveConfig(window.localStorage, values);
    formMessage.classList.add("is-success");
    formMessage.textContent = "Saved on this device. Opening the homepage…";
    window.setTimeout(() => window.location.replace("./"), 400);
  } catch (error) {
    formMessage.classList.add("is-error");
    formMessage.textContent = error instanceof Error ? error.message : "The links could not be saved.";
  }
});

clearButton.addEventListener("click", () => {
  if (!window.confirm("Clear all five Assetbots links saved in this browser?")) return;

  try {
    clearConfig(window.localStorage);
    setupForm.reset();
    formMessage.className = "form-message is-success";
    formMessage.textContent = "Saved links cleared from this browser.";
  } catch {
    formMessage.className = "form-message is-error";
    formMessage.textContent = "The saved links could not be cleared.";
  }
});

window.addEventListener("online", updateConnectionStatus);
window.addEventListener("offline", updateConnectionStatus);
updateConnectionStatus();

const parameters = new URLSearchParams(window.location.search);
if (parameters.get("setup") === "1") {
  showSetup();
} else {
  configureTiles(loadConfig(window.localStorage));
}
