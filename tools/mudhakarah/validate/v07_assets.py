"""V7 Missing assets. Every same-site file the page names (Open Graph image,
report.js) must exist in the repository (blocking). External addresses are never
fetched; an address on a host not named in the baseline pages is a warning.

`manassa-study.github.io/Tafseer/…` is served by the separate Tafseer repository
(the icons and the privacy page), so it is treated as an external location of the
baseline, not as a file of this repository."""
import re
from pathlib import Path
from urllib.parse import urlsplit

from ..errors import BLOCKING, WARNING, Finding

URL = re.compile(r"https?://[^\s\"'<>`)\\]+")
# Hosts (and the Tafseer project path) named by the baseline pilot page at de019d2.
BASELINE_LOCATIONS = (
    "bkqyroqdhkfofoevicjg.supabase.co",
    "cdn.jsdelivr.net",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "forms.gle",
    "manassa-study.github.io/Tafseer/",
    "www.w3.org",
)


def check(text, repo_root, site, where, own_output=None):
    """`own_output` is the page being built: it names its own address, which exists once written."""
    out = []
    base = urlsplit(site["base_url"])
    seen = set()
    for url in URL.findall(text):
        if url in seen:
            continue
        seen.add(url)
        parts = urlsplit(url)
        host_path = parts.netloc + parts.path
        if any(host_path.startswith(loc) if loc.endswith("/") else parts.netloc == loc
               for loc in BASELINE_LOCATIONS):
            continue
        if parts.netloc == base.netloc:
            rel = parts.path[len(base.path):] if parts.path.startswith(base.path) else parts.path.lstrip("/")
            if not rel or rel.endswith("/"):
                rel += "index.html"
            if rel != own_output and not (Path(repo_root) / rel).is_file():
                out.append(Finding("V7.missing-asset", BLOCKING,
                                   f"the page names {url}, but '{rel}' does not exist in the repository", where))
            continue
        out.append(Finding("V7.new-host", WARNING,
                           f"the page names a host that the baseline pages don't: {parts.netloc} ({url})", where))
    return out
