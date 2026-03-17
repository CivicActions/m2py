"""Shared regex patterns for parsing MUMPS invocation strings.

Used by both adapter.py (to resolve entry functions) and parser.py
(to parse TestList files).
"""

from __future__ import annotations

import re

# D LABEL^%ut("ROUTINE"[,verb[,break]])  — M-Unit framework call.
# Groups: 1=label, 2=routine, 3=verbosity (optional), 4=break (optional).
UTCALL_RE = re.compile(
    r'D\s+(\w+)\^%ut\(\s*"([^"]+)"(?:\s*,\s*(\d+))?(?:\s*,\s*(\d+))?\s*\)'
)

# D TAG^ROUTINE or D ^ROUTINE  — direct DO call.
# Groups: 1=tag (optional, without caret), 2=routine.
DO_RE = re.compile(r"D\s+(\w+)?\^(\w+)")
