"""Event processing commands codegen - not applicable.

Event processing commands (ABLOCK, AUNBLOCK, ASTART, ASTOP, ESTART, ESTOP, ETRIGGER)
are parser limitations per LIM-001. They produce parse errors, so no code is generated.

Parser tests: tests/unit/parser/s8_commands/test_s8_event_processing.py
Limitation: docs/limitations.md - LIM-001: Event Processing Commands
"""

# No tests - syntax is not parsed, no code to generate.
