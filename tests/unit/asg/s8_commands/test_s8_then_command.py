"""THEN command ASG analysis (§8.2.32) - not applicable.

THEN is a parser limitation per LIM-002.
This command is not parsed, so no ASG is generated.

Parser tests: tests/unit/parser/s8_commands/test_s8_then_command.py
Limitation: docs/limitations.md - LIM-002: THEN Command
"""

# No tests - syntax is not parsed, no ASG to analyze.
