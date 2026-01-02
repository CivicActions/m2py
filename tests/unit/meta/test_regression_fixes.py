"""Tests for regression fixes and phase-specific bug fixes.

Reference: M2PY development phases
Migrated from: tests/unit/test_parser.py::TestPhase74Fixes

Tests for specific bug fixes and regressions that were discovered
during development phases.
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg.statements import MDoStatement


@pytest.mark.parser
class TestPhase74Fixes:
    """Tests for Phase 74 fixes: source_lines in parse(), transitive analysis.

    Migrated from: tests/unit/test_parser.py::TestPhase74Fixes
    """

    def test_parse_populates_source_lines(self):
        """parse() should populate source_lines for $TEXT function support."""
        parser = MUMPSParser()
        source = "LABEL\tS X=1\n\tW X\n\tQ\n"
        routine = parser.parse(source)

        # source_lines should be populated even without parse_file()
        assert routine.source_lines == ["LABEL\tS X=1", "\tW X", "\tQ"]

    def test_parse_get_text_line_works(self):
        """get_text_line should work with string-parsed routines."""
        parser = MUMPSParser()
        source = "LABEL\tS X=1\n\tW X\n\tQ\n"
        routine = parser.parse(source)

        # 1-indexed access should work
        assert routine.get_text_line(1) == "LABEL\tS X=1"
        assert routine.get_text_line(2) == "\tW X"
        assert routine.get_text_line(3) == "\tQ"

    def test_parse_get_text_at_label_works(self):
        """get_text_at_label should work with string-parsed routines."""
        parser = MUMPSParser()
        source = """MAIN\tS X=1
\tD SUB
\tQ
SUB\tW X
\tQ
"""
        routine = parser.parse(source)

        # Get text at label offset
        assert routine.get_text_at_label("MAIN", 0) == "MAIN\tS X=1"
        assert routine.get_text_at_label("MAIN", 1) == "\tD SUB"
        assert routine.get_text_at_label("SUB", 0) == "SUB\tW X"

    def test_compute_signatures_resolves_references_first(self):
        """compute_signatures=True should resolve references before transitive analysis."""
        parser = MUMPSParser()
        # MAIN calls SUB, which reads X - transitive analysis should propagate X to MAIN
        source = """MAIN\tD SUB
\tQ
SUB\tW X
\tQ
"""
        routine = parser.parse(source, compute_signatures=True)

        # After transitive analysis with resolved references,
        # MAIN should have X in its transitive inputs (from SUB)
        main_label = routine.get_label("MAIN")
        sub_label = routine.get_label("SUB")

        assert main_label is not None
        assert sub_label is not None

        # SUB reads X
        assert "X" in sub_label.input_variables

        # MAIN should have X in input_variables via transitive closure
        # because it calls SUB which reads X
        assert "X" in main_label.input_variables

    def test_analyze_variables_resolves_references_first(self):
        """analyze_variables=True should resolve references before transitive analysis."""
        parser = MUMPSParser()
        source = """OUTER\tD INNER
\tQ
INNER\tS Y=1
\tQ
"""
        routine = parser.parse(source, analyze_variables=True)

        # INNER writes Y (output)
        inner_label = routine.get_label("INNER")
        assert inner_label is not None
        assert "Y" in inner_label.output_variables

        # OUTER calls INNER - the DO target should be resolved
        outer_label = routine.get_label("OUTER")
        assert outer_label is not None

        # Check that DO statement has resolved target
        do_stmt = outer_label.body.statements[0]
        assert isinstance(do_stmt, MDoStatement)
        assert len(do_stmt.targets) == 1
        assert do_stmt.targets[0].is_resolved

    def test_transitive_chain_propagates(self):
        """Transitive inputs should propagate through call chain."""
        parser = MUMPSParser()
        # A -> B -> C, C reads Z
        source = """A\tD B
\tQ
B\tD C
\tQ
C\tW Z
\tQ
"""
        routine = parser.parse(source, compute_signatures=True)

        c_label = routine.get_label("C")
        b_label = routine.get_label("B")
        a_label = routine.get_label("A")

        # C reads Z
        assert "Z" in c_label.input_variables

        # B calls C, so B needs Z transitively
        assert "Z" in b_label.input_variables

        # A calls B, so A needs Z transitively
        assert "Z" in a_label.input_variables
