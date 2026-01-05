"""Event processing ASG analysis (§6.3.4) - not applicable.

Event processing is a parser limitation per LIM-001.
Commands produce parse errors, so no ASG is generated.

Parser tests: tests/unit/parser/s6_routine/test_s6_3_4_event_processing.py
Limitation: docs/limitations.md - LIM-001: Event Processing Commands
"""

# No tests - syntax is not parsed, no ASG to analyze.
