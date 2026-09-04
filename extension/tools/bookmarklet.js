/*
 * trackactor lookup bookmarklet
 * ------------------------------
 * Drop this on any page, select a handle / link / case id, click the
 * bookmarklet, and trackactor's reverse lookup opens in a new tab.
 *
 * Install:
 *   1. Edit BASE below to point at your trackactor instance.
 *   2. Make a new bookmark. Paste the one-liner from bookmarklet.min.txt
 *      (which is this file, minified, with the same edit) as the URL.
 *
 * The browser extension's right-click "Look up in trackactor" does the same
 * thing without the manual setup - use that if you have the extension loaded.
 */
(function () {
  var BASE = "http://localhost:8080"; // <-- your trackactor URL

  var sel = window.getSelection ? String(window.getSelection()).trim() : "";
  var q = sel || window.prompt("Look up in trackactor:");
  if (!q) return;

  var url = BASE.replace(/\/+$/, "") + "/lookup?q=" + encodeURIComponent(q);
  window.open(url, "_blank", "noopener");
})();
