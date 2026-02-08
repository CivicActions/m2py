#!/usr/bin/env python
"""Analyze MUGJ transpilation failures."""

import re
import signal
from pathlib import Path
from m2py.codegen import generate_python

INREF_DIR = Path("YDBTest/mugj/inref")


def timeout_handler(signum, frame):
    raise TimeoutError("Parsing timeout")


# Parse driver
driver = Path("tests/functional/mugj/u_inref/mugj.csh").read_text()
driver_routines = []
for line in driver.splitlines():
    match = re.match(r'^W\s+!!,"([^"]+)"\s+D\s+\^(\w+)', line.strip())
    if match:
        label, routine = match.groups()
        driver_routines.append((label, routine))

print(f"Driver has {len(driver_routines)} routines")


def discover_deps(source):
    """Discover external routine dependencies from source code."""
    deps = set()
    # DO ^ROUTINE
    for match in re.finditer(
        r"\bD(?:O)?\s+\^(%\w*|[a-zA-Z]\w*)", source, re.IGNORECASE
    ):
        deps.add(match.group(1))
    # Comma-separated: ,^ROUTINE
    for match in re.finditer(r",\^(%\w*|[a-zA-Z]\w*)", source, re.IGNORECASE):
        deps.add(match.group(1))
    # GOTO ^ROUTINE
    for match in re.finditer(
        r"\bG(?:OTO)?\s+\^(%\w*|[a-zA-Z]\w*)", source, re.IGNORECASE
    ):
        deps.add(match.group(1))
    return {d for d in deps if (INREF_DIR / f"{d}.m").exists()}


# Find all dependencies
all_routines = set(r for _, r in driver_routines)
to_process = set(all_routines)
processed = set()

while to_process:
    routine = to_process.pop()
    if routine in processed:
        continue
    processed.add(routine)
    source_file = INREF_DIR / f"{routine}.m"
    if source_file.exists():
        source = source_file.read_text()
        deps = discover_deps(source)
        for d in deps:
            if d not in processed:
                to_process.add(d)

print(f"Total routines including deps: {len(processed)}")

# Try to transpile all
failed = []
for r in sorted(processed):
    source_file = INREF_DIR / f"{r}.m"
    if source_file.exists():
        # Set up timeout
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.setitimer(signal.ITIMER_REAL, 5.0)  # 5 second timeout
        try:
            code = generate_python(source_file.read_text())
        except TimeoutError:
            failed.append((r, "TIMEOUT - parsing took >5s"))
        except Exception as e:
            failed.append((r, str(e)[:80]))
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)

print(f"\nFailed to transpile ({len(failed)}):")
for r, err in failed:
    print(f"  {r}: {err}")
