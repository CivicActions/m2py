"""Out-of-scope commands ASG analysis - not applicable.

These commands are parser limitations - they produce parse errors,
so no ASG is generated:
- Event processing: LIM-001
- THEN command: LIM-002
- ASSIGN command: LIM-013
- RLOAD/RSAVE: LIM-009

Parser tests verify parse error behavior in tests/unit/parser/s8_commands/.
See docs/limitations.md for full limitation details.
"""

# No tests - these syntaxes are not parsed, no ASG to analyze.
