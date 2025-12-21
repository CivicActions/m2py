#!/usr/bin/env python
"""Test SET after QUIT parsing issue."""

from m2py.analysis.command_parser import parse_commands_from_line, parse_line_content

tests = [
    'S X=1',
    'S X=1 Q',
    'Q',
    'Q S X=1',
    'S X=1 Q S Y=2',
    'S X=1 Q  S Y=2',  # two spaces
]

for test in tests:
    cmds = parse_commands_from_line(test)
    types = [type(c.cmd if hasattr(c, 'cmd') else c).__name__ for c in cmds]
    print(f"{len(cmds)} cmds: {test!r:30s} -> {types}")
