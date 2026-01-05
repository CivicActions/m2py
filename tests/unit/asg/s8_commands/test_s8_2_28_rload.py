"""RLOAD command ASG analysis (§8.2.28) - not applicable.

RLOAD is a parser limitation per LIM-009.
This command is not parsed, so no ASG is generated.

Parser tests: tests/unit/parser/s8_commands/test_s8_2_28_rload.py
Limitation: docs/limitations.md - LIM-009: RLOAD/RSAVE
"""

# No tests - syntax is not parsed, no ASG to analyze.
