"""Canonicalise handles / links so a reply from "t.me/Acid_Burn" matches a
contact stored as "@Acid_Burn"."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

# hosts where the username is the first path segment
HANDLE_HOSTS = {
    "t.me",
    "telegram.me",
    "telegram.dog",
    "twitter.com",
    "x.com",
    "github.com",
    "keybase.io",
    "matrix.to",
}


def _strip_www(host: str) -> str:
    return host[4:] if host.startswith("www.") else host


def normalize_identifier(raw: str) -> str:
    """Lowercased, canonical form of a handle / link / address. Lossy but stable."""
    if not raw:
        return ""

    value = raw.strip().strip("​").strip()
    if not value:
        return ""

    lowered = value.lower()

    if lowered.startswith("mailto:"):
        return lowered[len("mailto:") :].split("?", 1)[0].strip()
    if lowered.startswith("xmpp:"):
        return lowered[len("xmpp:") :].split("?", 1)[0].strip()
    if lowered.startswith("tg://"):
        qs = parse_qs(urlparse(lowered).query)
        if qs.get("domain"):
            return qs["domain"][0].strip().lstrip("@")
        return lowered

    if lowered.startswith("@"):
        return lowered[1:].strip()

    if "://" in lowered or lowered.startswith("www."):
        parsed = urlparse(lowered if "://" in lowered else f"http://{lowered}")
        host = _strip_www(parsed.netloc.split("@")[-1])
        path = parsed.path.strip("/")
        if host in HANDLE_HOSTS and path:
            return path.split("/", 1)[0].lstrip("@").strip()
        return f"{host}/{path}".rstrip("/") if path else host

    # email / JID
    if "@" in lowered and "." in lowered.split("@", 1)[1]:
        return lowered

    return " ".join(lowered.split())


def normalize_name(raw: str) -> str:
    """Loose form for actor name / alias matching."""
    return " ".join(raw.strip().lower().split()) if raw else ""
