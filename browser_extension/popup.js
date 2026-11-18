const DEFAULTS = {
  snow: true, edgeSnow: true, santa: true, snowman: true, cursor: true,
  clickSound: false, typingSound: false, deleteSound: false,
  clickVolume: 0.22, typingVolume: 0.16, deleteVolume: 0.22
};

document.addEventListener("DOMContentLoaded", () => {
  const keys = Object.keys(DEFAULTS);
  chrome.storage.sync.get(DEFAULTS, (settings) => {
    for (const key of keys) {
      const el = document.getElementById(key);
      if (!el) continue;
      if (el.type === "checkbox") el.checked = Boolean(settings[key]);
      else el.value = String(settings[key]);
    }
  });

  for (const key of keys) {
    const el = document.getElementById(key);
    if (!el) continue;
    const eventName = el.type === "range" ? "input" : "change";
    el.addEventListener(eventName, () => {
      const value = el.type === "checkbox" ? el.checked : Number(el.value);
      chrome.storage.sync.set({ [key]: value });
    });
  }
});