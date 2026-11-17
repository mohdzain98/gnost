"""Download the pinned browser libraries into gnost/reporters/vendor and verify them.

Usage: vendor_js.py [--update]
Without --update the downloaded files must match the sha256 in vendor.json.
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List

VENDOR = Path(__file__).resolve().parent.parent / "gnost" / "reporters" / "vendor"

# One place for the pinned versions. Upgrading a library is a reviewed change here.
LIBS: List[Dict[str, str]] = [
    {
        "name": "mermaid",
        "version": "11.4.1",
        "license": "MIT",
        "file": "mermaid.min.js",
        "url": "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js",
    },
    {
        "name": "marked",
        "version": "12.0.2",
        "license": "MIT",
        "file": "marked.min.js",
        "url": "https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js",
    },
    {
        "name": "svg-pan-zoom",
        "version": "3.6.1",
        "license": "BSD-2-Clause",
        "file": "svg-pan-zoom.min.js",
        "url": "https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js",
    },
    {
        "name": "cytoscape",
        "version": "3.30.2",
        "license": "MIT",
        "file": "cytoscape.min.js",
        "url": "https://cdn.jsdelivr.net/npm/cytoscape@3.30.2/dist/cytoscape.min.js",
    },
    {
        "name": "layout-base",
        "version": "2.0.1",
        "license": "MIT",
        "file": "layout-base.js",
        "url": "https://cdn.jsdelivr.net/npm/layout-base@2.0.1/layout-base.js",
    },
    {
        "name": "cose-base",
        "version": "2.2.0",
        "license": "MIT",
        "file": "cose-base.js",
        "url": "https://cdn.jsdelivr.net/npm/cose-base@2.2.0/cose-base.js",
    },
    {
        "name": "cytoscape-fcose",
        "version": "2.2.0",
        "license": "MIT",
        "file": "cytoscape-fcose.js",
        "url": "https://cdn.jsdelivr.net/npm/cytoscape-fcose@2.2.0/cytoscape-fcose.js",
    },
]


def fetch(url: str) -> bytes:
    """Download a URL."""
    with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310
        return resp.read()


def fetch_license(lib: Dict[str, str]) -> str:
    """Fetch the package's license file, trying the usual names."""
    base = f"https://cdn.jsdelivr.net/npm/{lib['name']}@{lib['version']}/"
    for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "license", "LICENSE-MIT"):
        try:
            return fetch(base + name).decode()
        except urllib.error.HTTPError:
            continue
    raise SystemExit(f"no license file found for {lib['name']}")


def main(argv: List[str]) -> int:
    """Download, verify (or record) checksums and write the notices file."""
    update = "--update" in argv
    manifest_path = VENDOR / "vendor.json"
    old = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    manifest: Dict[str, Dict[str, str]] = {}
    notices = [
        "# Third-party notices\n",
        "These libraries are embedded in the HTML pages written by `gnost open`.\n",
    ]
    status = 0
    for lib in LIBS:
        data = fetch(lib["url"])
        digest = hashlib.sha256(data).hexdigest()
        want = old.get(lib["name"], {}).get("sha256")
        if not update and want != digest:
            print(f"CHECKSUM MISMATCH {lib['name']}: {digest} != {want}")
            status = 1
            continue
        (VENDOR / lib["file"]).write_bytes(data)
        manifest[lib["name"]] = {
            "version": lib["version"],
            "license": lib["license"],
            "file": lib["file"],
            "sha256": digest,
        }
        lic = fetch_license(lib)
        notices.append(
            f"\n## {lib['name']} {lib['version']} ({lib['license']})\n\n```\n{lic.strip()}\n```\n"
        )
    if status == 0:
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        (VENDOR / "THIRD_PARTY_NOTICES.md").write_text("".join(notices))
        print(f"vendored {len(manifest)} libraries")
    return status


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
