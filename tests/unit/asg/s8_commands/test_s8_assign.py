"""ASSIGN command ASG analysis - not applicable.

ASSIGN is a parser limitation per LIM-013.
This command is not parsed, so no ASG is generated.

Parser tests: tests/unit/parser/s8_commands/test_s8_assign.py
Limitation: docs/limitations.md - LIM-013: ASSIGN Command
"""

# No tests - syntax is not parsed, no ASG to analyze.
