"""Tests for line dispatch utilities (Spec 007 Phase 2).

Tests the foundational infrastructure for computed offsets:
- Line map generation from MRoutine
- Offset call detection
- Line map code generation
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.codegen.line_dispatch import (
    generate_line_map,
    generate_line_map_code,
)
from m2py.codegen.emitter import CodeEmitter


@pytest.fixture
def parser():
    """Provide a parser instance."""
    return MUMPSParser()


@pytest.mark.codegen
class TestHasOffsetCalls:
    """Tests for has_offset_calls ASG field detection (T005).

    The has_offset_calls field is populated by classify_gotos() analysis pass.
    These tests verify the ASG field is correctly set.
    """

    def test_no_offset_calls(self, parser):
        """Routine with no offset calls returns False."""
        source = """TEST G NEXT Q
NEXT W "hello" Q"""
        routine = parser.parse(source)
        parser.classify_gotos(routine)
        assert routine.has_offset_calls is False

    def test_goto_with_literal_offset(self, parser):
        """GOTO with literal offset is detected."""
        source = """TEST G STAR+2 Q
STAR W "0"
 W "1"
 W "2"
 Q"""
        routine = parser.parse(source)
        parser.classify_gotos(routine)
        assert routine.has_offset_calls is True

    def test_goto_with_variable_offset(self, parser):
        """GOTO with variable offset is detected."""
        source = """TEST S N=2 G STAR+N Q
STAR W "done" Q"""
        routine = parser.parse(source)
        parser.classify_gotos(routine)
        assert routine.has_offset_calls is True

    def test_do_with_offset(self, parser):
        """DO with offset is detected."""
        source = """TEST D SUB+1 Q
SUB W "0" Q
 W "1" Q"""
        routine = parser.parse(source)
        parser.classify_gotos(routine)
        assert routine.has_offset_calls is True

    def test_mixed_calls(self, parser):
        """Routine with both regular and offset calls is detected."""
        source = """TEST D SUB G NEXT+1 Q
SUB W "sub" Q
NEXT W "0"
 W "1" Q"""
        routine = parser.parse(source)
        parser.classify_gotos(routine)
        assert routine.has_offset_calls is True


@pytest.mark.codegen
class TestGenerateLineMap:
    """Tests for generate_line_map (T006)."""

    def test_single_label_no_statements(self, parser):
        """Single label with inline command only.

        When commands are on the same line as the label, they have offset 0
        (same line as label).
        """
        source = """TEST W "hello" Q"""
        routine = parser.parse(source)
        line_map = generate_line_map(routine)

        # Line 1 = TEST label at offset 0 (inline commands also on line 1)
        assert line_map.get(1) == ("TEST", 0)

    def test_single_label_with_statements(self, parser):
        """Single label with multiple statements on separate lines."""
        source = """TEST
 W "line1"
 W "line2"
 Q"""
        routine = parser.parse(source)
        line_map = generate_line_map(routine)

        # Line 1 = TEST label (offset 0)
        # Line 2 = first statement (offset 1)
        # Line 3 = second statement (offset 2)
        # Line 4 = third statement (offset 3)
        assert line_map.get(1) == ("TEST", 0)
        assert line_map.get(2) == ("TEST", 1)
        assert line_map.get(3) == ("TEST", 2)
        assert line_map.get(4) == ("TEST", 3)

    def test_multiple_labels(self, parser):
        """Multiple labels with statements."""
        source = """TEST G NEXT Q
NEXT W "next" Q"""
        routine = parser.parse(source)
        line_map = generate_line_map(routine)

        # Line 1 = TEST label (offset 0)
        # Line 2 = NEXT label (offset 0)
        assert line_map.get(1) == ("TEST", 0)
        assert line_map.get(2) == ("NEXT", 0)

    def test_label_with_indented_statements(self, parser):
        """Label with indented continuation lines."""
        source = """STAR W "0"
 W "1"
 W "2"
 Q"""
        routine = parser.parse(source)
        line_map = generate_line_map(routine)

        assert line_map.get(1) == ("STAR", 0)
        assert line_map.get(2) == ("STAR", 1)
        assert line_map.get(3) == ("STAR", 2)
        assert line_map.get(4) == ("STAR", 3)

    def test_offset_from_label(self, parser):
        """Verify offset values match expected MUMPS semantics.

        G STAR+0 = label line itself (offset 0)
        G STAR+1 = first line after label (offset 1)
        G STAR+2 = second line after label (offset 2)
        """
        source = """STAR W "offset 0"
 W "offset 1"
 W "offset 2"
 Q"""
        routine = parser.parse(source)
        line_map = generate_line_map(routine)

        # Verify offset semantics
        assert line_map[1][1] == 0  # STAR+0 = label line
        assert line_map[2][1] == 1  # STAR+1 = first statement
        assert line_map[3][1] == 2  # STAR+2 = second statement


@pytest.mark.codegen
class TestGenerateLineMapCode:
    """Tests for generate_line_map_code (T007)."""

    def test_empty_line_map(self):
        """Empty line map generates empty dict."""
        emitter = CodeEmitter()
        generate_line_map_code({}, emitter)
        code = emitter.get_code()

        assert "_line_map: dict[int, tuple[str, int]] = {}" in code

    def test_single_entry(self):
        """Single entry generates proper dict."""
        emitter = CodeEmitter()
        line_map = {1: ("TEST", 0)}
        generate_line_map_code(line_map, emitter)
        code = emitter.get_code()

        assert "_line_map: dict[int, tuple[str, int]] = {" in code
        assert '1: ("TEST", 0),' in code
        assert "}" in code

    def test_multiple_entries_sorted(self):
        """Multiple entries are sorted by line number."""
        emitter = CodeEmitter()
        line_map = {3: ("NEXT", 0), 1: ("TEST", 0), 2: ("TEST", 1)}
        generate_line_map_code(line_map, emitter)
        code = emitter.get_code()

        lines = code.strip().split("\n")
        # Should be sorted: 1, 2, 3
        assert '1: ("TEST", 0),' in lines[1]
        assert '2: ("TEST", 1),' in lines[2]
        assert '3: ("NEXT", 0),' in lines[3]


@pytest.mark.codegen
class TestIntegration:
    """Integration tests for line dispatch utilities."""

    def test_full_workflow(self, parser):
        """Test complete workflow: parse → analyze → generate map → emit code."""
        source = """TEST G STAR+2 Q
STAR W "0"
 W "1"
 W "2"
 Q"""
        routine = parser.parse(source)
        parser.classify_gotos(routine)

        # Step 1: Check offset calls ASG field (set by classify_gotos)
        assert routine.has_offset_calls is True

        # Step 2: Generate line map
        line_map = generate_line_map(routine)
        assert 1 in line_map  # TEST label
        assert 2 in line_map  # STAR label
        assert 3 in line_map  # STAR+1
        assert 4 in line_map  # STAR+2
        assert 5 in line_map  # STAR+3

        # Step 3: Emit code
        emitter = CodeEmitter()
        generate_line_map_code(line_map, emitter)
        code = emitter.get_code()
        assert "_line_map" in code
