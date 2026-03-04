#!/usr/bin/env python3
"""Download and extract VistA dependency archives for M-Unit integration tests.

Reads pinned versions from vista_versions.json and downloads ZIP archives
from GitHub into a local cache directory (.vista-deps/ by default).

Usage:
    uv run python tests/functional/munit/setup_deps.py

Environment variables:
    VISTA_DEPS_DIR  Override the default cache directory (.vista-deps/)
"""

from __future__ import annotations

import io
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

_HERE = Path(__file__).resolve().parent
_VERSIONS_FILE = _HERE / "vista_versions.json"
_REPO_ROOT = _HERE.parents[2]  # tests/functional/munit → repo root
_DEFAULT_DEPS_DIR = _REPO_ROOT / ".vista-deps"


def _deps_dir() -> Path:
    """Return the VistA dependencies directory (respects VISTA_DEPS_DIR env var)."""
    return Path(os.environ.get("VISTA_DEPS_DIR", str(_DEFAULT_DEPS_DIR)))


def _load_versions() -> dict:
    """Load pinned versions from vista_versions.json."""
    with open(_VERSIONS_FILE) as f:
        return json.load(f)


def _marker_path(dest_dir: Path, commit: str) -> Path:
    """Return the path of the marker file indicating a successful extraction."""
    return dest_dir / f".extracted-{commit[:12]}"


def _download_and_extract(name: str, url: str, commit: str, dest_dir: Path) -> None:
    """Download a ZIP archive and extract it.

    The archive is expected to contain a single top-level directory
    (e.g., VistA-6c18f1bf98a3...).  Its contents are moved to dest_dir.
    """
    marker = _marker_path(dest_dir, commit)
    if marker.exists():
        print(f"  {name}: already extracted ({dest_dir})")
        return

    # Clean previous extraction
    if dest_dir.exists():
        print(f"  {name}: removing stale extraction...")
        shutil.rmtree(dest_dir)

    print(f"  {name}: downloading {url} ...")
    try:
        with urlopen(url, timeout=600) as resp:  # noqa: S310
            data = resp.read()
    except URLError as e:
        print(f"  ERROR: Failed to download {name}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"  {name}: extracting ({len(data) / 1024 / 1024:.0f} MB) ...")
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        # Find the single top-level directory in the archive
        top_dirs = {n.split("/")[0] for n in zf.namelist() if "/" in n}
        if len(top_dirs) != 1:
            print(f"  ERROR: Expected 1 top-level dir, got {top_dirs}", file=sys.stderr)
            sys.exit(1)
        top_dir = top_dirs.pop()

        # Extract to a temp location, then rename
        extract_tmp = dest_dir.parent / f".tmp-{name}"
        if extract_tmp.exists():
            shutil.rmtree(extract_tmp)
        zf.extractall(extract_tmp)

        # Move the inner directory to the final location
        (extract_tmp / top_dir).rename(dest_dir)
        extract_tmp.rmdir()

    # Write marker file
    marker.write_text(commit + "\n")
    print(f"  {name}: done → {dest_dir}")


def setup() -> Path:
    """Download and extract all VistA dependencies.

    Returns the deps directory.
    """
    deps = _deps_dir()
    deps.mkdir(parents=True, exist_ok=True)

    versions = _load_versions()

    for name in ("VistA", "VistA-M"):
        info = versions[name]
        dest = deps / name
        _download_and_extract(name, info["url"], info["commit"], dest)

    return deps


def main() -> None:
    print("Setting up VistA dependencies for M-Unit tests...")
    deps = setup()
    print(f"\nAll dependencies ready in {deps}")


if __name__ == "__main__":
    main()
