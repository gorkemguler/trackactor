// Service worker: a right-click "look up in trackactor" entry, and a helper
// the popup calls to read the current page's selection.

import { webAppUrl } from "./lib/api.js";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "trackactor-lookup",
    title: 'Look up "%s" in trackactor',
    contexts: ["selection"],
  });
});

chrome.contextMenus.onClicked.addListener(async (info) => {
  if (info.menuItemId !== "trackactor-lookup" || !info.selectionText) return;
  const url = await webAppUrl(`/lookup?q=${encodeURIComponent(info.selectionText.trim())}`);
  chrome.tabs.create({ url });
});
