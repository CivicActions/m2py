"""Tests for FOR loop pattern classification.

Reference: MUMPS 1995 ANSI Standard, Section 8.2.5
Migrated from: tests/unit/test_parser.py::TestMUMPSParserClassifyPatterns
Migrated from: tests/unit/test_classifier.py::TestClassifyForLoop
Migrated from: tests/unit/test_classifier.py::TestExtractForFromLine
Migrated from: tests/unit/test_classifier.py::TestParseForStatement
Migrated from: tests/unit/test_classifier.py::TestQuitDetection

Tests for:
- classify_for_patterns() and classify_for_patterns_from_file() methods of MUMPSParser
- FOR loop type classification (BOUNDED, OPEN_ENDED, STRING_LIST, etc.)
- FOR command extraction and parsing
- MForStatement ASG node parsing
- QUIT detection in FOR loops
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.analysis import (
    extract_for_commands,
    classify_for_command,
    analyze_statement,
    detect_quit_after_for,
)
from m2py.asg.enums import ForLoopType, ForParamType
from m2py.asg.statements import MForStatement
from tests.helpers.extraction_helpers import get_for_info


def _classify_for_content(for_content: str):
    """Helper to classify FOR content using production functions.

    Migrated from: tests/unit/test_classifier.py

    Args:
        for_content: Content after FOR command (e.g., "I=1:1:10 W I")

    Returns:
        Tuple of (ForLoopType, loop_var_name or None)
    """
    content = for_content.strip()

    # Empty or space-first = argumentless
    if not content or content[0] in (" ", "\t") or content.startswith(";"):
        return ForLoopType.ARGUMENTLESS, None

    # Use production functions
    cmds = extract_for_commands(f"F {content}")
    if cmds:
        loop_type, loop_var = classify_for_command(cmds[0])
        var_name = (
            loop_var if isinstance(loop_var, str) else getattr(loop_var, "name", None)
        )
        return loop_type, var_name or None

    return ForLoopType.ARGUMENTLESS, None


# =============================================================================
# FOR Loop Type Classification Tests
# =============================================================================


class TestClassifyForLoop:
    """Test FOR loop classification using production functions.

    Migrated from: tests/unit/test_classifier.py::TestClassifyForLoop
    """

    def test_bounded_for_simple(self):
        """FOR I=1:1:10 should be BOUNDED."""
        loop_type, var = _classify_for_content("I=1:1:10 W I")
        assert loop_type == ForLoopType.BOUNDED
        assert var == "I"

    def test_bounded_for_expressions(self):
        """FOR J=N:1:M should be BOUNDED."""
        loop_type, var = _classify_for_content("J=N:1:M D PROC")
        assert loop_type == ForLoopType.BOUNDED
        assert var == "J"

    def test_bounded_for_negative_step(self):
        """FOR K=10:-1:1 should be BOUNDED."""
        loop_type, var = _classify_for_content("K=10:-1:1 W K")
        assert loop_type == ForLoopType.BOUNDED
        assert var == "K"

    def test_bounded_for_zero_step(self):
        """FOR J=4:0:5 should be BOUNDED (semantically infinite)."""
        loop_type, var = _classify_for_content("J=4:0:5 S I=I+1")
        assert loop_type == ForLoopType.BOUNDED
        assert var == "J"

    def test_open_ended_for(self):
        """FOR I=1:1 should be OPEN_ENDED."""
        loop_type, var = _classify_for_content("I=1:1 W I")
        assert loop_type == ForLoopType.OPEN_ENDED
        assert var == "I"

    def test_string_list_single_value(self):
        """FOR I=7 should be STRING_LIST (single value)."""
        loop_type, var = _classify_for_content("I=7 S X=X_I")
        assert loop_type == ForLoopType.STRING_LIST
        assert var == "I"

    def test_string_list_multiple_values(self):
        """FOR I="A","B","C" should be STRING_LIST."""
        loop_type, var = _classify_for_content('I="A","B","C"')
        assert loop_type == ForLoopType.STRING_LIST
        assert var == "I"

    def test_argumentless_for_space(self):
        """FOR followed by space should be ARGUMENTLESS."""
        loop_type, var = _classify_for_content(' W "hello"')
        assert loop_type == ForLoopType.ARGUMENTLESS
        assert var is None

    def test_argumentless_for_empty(self):
        """Empty content after FOR should be ARGUMENTLESS."""
        loop_type, var = _classify_for_content("")
        assert loop_type == ForLoopType.ARGUMENTLESS
        assert var is None

    def test_percent_variable(self):
        """FOR %=1:1:10 should handle % variable."""
        loop_type, var = _classify_for_content("%=1:1:10 W %")
        assert loop_type == ForLoopType.BOUNDED
        assert var == "%"


# =============================================================================
# FOR Command Extraction Tests
# =============================================================================


class TestExtractForFromLine:
    """Test FOR command extraction via get_for_info helper.

    Migrated from: tests/unit/test_classifier.py::TestExtractForFromLine
    """

    def test_extract_for_abbreviated(self):
        """F abbreviation should be recognized."""
        result = get_for_info("\tF I=1:1:10 W I")
        assert result is not None
        loop_type, var = result
        assert loop_type == ForLoopType.BOUNDED
        assert var == "I"

    def test_extract_for_full(self):
        """FOR full keyword should be recognized."""
        result = get_for_info("\tFOR J=1:1:5 D ^PROC")
        assert result is not None
        loop_type, var = result
        assert loop_type == ForLoopType.BOUNDED
        assert var == "J"

    def test_extract_for_case_insensitive(self):
        """for should be recognized (case insensitive)."""
        result = get_for_info("\tfor K=1:1 W K")
        assert result is not None
        loop_type, var = result
        assert loop_type == ForLoopType.OPEN_ENDED
        assert var == "K"

    def test_extract_no_for(self):
        """Line without FOR should return None."""
        result = get_for_info("\tS X=1 W X")
        assert result is None

    def test_extract_argumentless(self):
        """F followed by double space should be ARGUMENTLESS."""
        result = get_for_info('\tF  W "loop"')
        assert result is not None
        loop_type, var = result
        assert loop_type == ForLoopType.ARGUMENTLESS
        assert var == ""


# =============================================================================
# MForStatement Parsing Tests
# =============================================================================


class TestParseForStatement:
    """Test parse_for_statement function - builds MForStatement ASG nodes.

    Migrated from: tests/unit/test_classifier.py::TestParseForStatement

    MForParameter fields (start, step, end, value) are NumericLiteral/StringLiteral objects.
    Use .value to access the parsed value.
    """

    def test_parse_bounded_for(self):
        """Parse FOR I=1:1:10 into MForStatement."""
        stmt = analyze_statement("F", "I=1:1:10")

        assert isinstance(stmt, MForStatement)
        assert stmt.loop_var.name == "I"
        assert stmt.loop_type == ForLoopType.BOUNDED
        assert len(stmt.parameters) == 1

        param = stmt.parameters[0]
        assert param.param_type == ForParamType.RANGE
        assert param.start.value == 1
        assert param.step.value == 1
        assert param.end.value == 10

    def test_parse_open_ended_for(self):
        """Parse FOR I=1:1 into MForStatement with OPEN_RANGE."""
        stmt = analyze_statement("F", "I=1:1")

        assert stmt.loop_var.name == "I"
        assert stmt.loop_type == ForLoopType.OPEN_ENDED
        assert len(stmt.parameters) == 1

        param = stmt.parameters[0]
        assert param.param_type == ForParamType.OPEN_RANGE
        assert param.start.value == 1
        assert param.step.value == 1
        assert param.end is None

    def test_parse_string_list_for(self):
        """Parse FOR I="A","B","C" into MForStatement with VALUE params."""
        stmt = analyze_statement("F", 'I="A","B","C"')

        assert stmt.loop_var.name == "I"
        assert stmt.loop_type == ForLoopType.STRING_LIST
        assert len(stmt.parameters) == 3

        assert stmt.parameters[0].param_type == ForParamType.VALUE
        # StringLiteral.value contains the parsed string value
        assert stmt.parameters[0].value.value == "A"
        assert stmt.parameters[1].value.value == "B"
        assert stmt.parameters[2].value.value == "C"

    def test_parse_mixed_for(self):
        """Parse FOR I="A",1:1:3 into MForStatement with MIXED type."""
        stmt = analyze_statement("F", 'I="A",1:1:3')

        assert stmt.loop_var.name == "I"
        assert stmt.loop_type == ForLoopType.MIXED
        assert len(stmt.parameters) == 2

        assert stmt.parameters[0].param_type == ForParamType.VALUE
        assert stmt.parameters[0].value.value == "A"

        assert stmt.parameters[1].param_type == ForParamType.RANGE
        assert stmt.parameters[1].start.value == 1
        assert stmt.parameters[1].end.value == 3

    def test_parse_argumentless_for(self):
        """Parse argumentless FOR into MForStatement."""
        stmt = analyze_statement("F", "")

        assert stmt.loop_var is None
        assert stmt.loop_type == ForLoopType.ARGUMENTLESS
        assert len(stmt.parameters) == 0

    def test_parse_for_has_body_scope(self):
        """MForStatement should have body MScope."""
        stmt = analyze_statement("F", "I=1:1:10")

        assert stmt.body is not None
        from m2py.asg.elements import MScope

        assert isinstance(stmt.body, MScope)

    def test_parse_for_decimal_step(self):
        """Parse FOR with decimal values."""
        stmt = analyze_statement("F", "I=0.1:0.1:1.0")

        assert stmt.loop_type == ForLoopType.BOUNDED
        param = stmt.parameters[0]
        # NumericLiteral.value contains parsed float
        assert param.start.value == 0.1
        assert param.step.value == 0.1
        assert param.end.value == 1.0

    def test_parse_for_negative_values(self):
        """Parse FOR with negative values."""
        from m2py.asg.expressions import MUnaryOp

        stmt = analyze_statement("F", "I=10:-1:0")

        assert stmt.loop_type == ForLoopType.BOUNDED
        param = stmt.parameters[0]
        assert param.start.value == 10
        # Full-fidelity ASG returns MUnaryOp for negative literals
        assert isinstance(param.step, MUnaryOp)
        assert param.step.operator == "-"
        assert param.step.operand.value == 1
        assert param.end.value == 0

    def test_parse_for_multiple_ranges(self):
        """Parse FOR with multiple range forparameters."""
        stmt = analyze_statement("F", "I=1:1:3,5:1:7")

        assert stmt.loop_type == ForLoopType.BOUNDED  # All RANGE = BOUNDED
        assert len(stmt.parameters) == 2

        assert stmt.parameters[0].start.value == 1
        assert stmt.parameters[0].end.value == 3
        assert stmt.parameters[1].start.value == 5
        assert stmt.parameters[1].end.value == 7


# =============================================================================
# QUIT Detection in FOR Loops Tests
# =============================================================================


class TestQuitDetection:
    """Test QUIT exit point detection in FOR loops.

    Migrated from: tests/unit/test_classifier.py::TestQuitDetection

    NOTE: The textX-based parser separates FOR parsing from QUIT detection.
    Use detect_quit_after_for() to check if QUIT follows FOR on a line.
    """

    def test_open_ended_for_with_quit(self):
        """Open-ended FOR with QUIT should be detected."""
        result = detect_quit_after_for("F I=1:1 W I Q:I>10")
        assert result is True

    def test_open_ended_for_with_full_quit(self):
        """QUIT spelled out should be detected."""
        result = detect_quit_after_for("F I=1:1 W I QUIT:I>10")
        assert result is True

    def test_bounded_for_no_quit(self):
        """Bounded FOR without QUIT should return False."""
        result = detect_quit_after_for("F I=1:1:10 W I")
        assert result is False

    def test_quit_inside_string_not_counted(self):
        """Q inside string should not count as QUIT."""
        result = detect_quit_after_for('F I=1:1:10 W "Q value"')
        assert result is False

    def test_argumentless_for_with_quit(self):
        """Argumentless FOR with QUIT should detect it."""
        result = detect_quit_after_for("F  W X Q:X>10")
        assert result is True

    def test_postconditioned_quit(self):
        """Postconditioned QUIT (Q:cond) should be detected."""
        result = detect_quit_after_for("F I=1:1 S X=I*2 Q:X>100")
        assert result is True

    def test_unconditional_quit(self):
        """Unconditional QUIT should be detected."""
        result = detect_quit_after_for("F I=1:1:10 W I Q")
        assert result is True

    def test_quit_with_return_value(self):
        """QUIT with return value should be detected."""
        result = detect_quit_after_for("F I=1:1 Q I*2")
        assert result is True

        # Also verify the FOR statement still parses correctly
        stmt = analyze_statement("F", "I=1:1")
        assert stmt.loop_type == ForLoopType.OPEN_ENDED


# =============================================================================
# MUMPSParser classify_for_patterns Tests
# =============================================================================


@pytest.mark.parser
class TestMUMPSParserClassifyPatterns:
    """Test MUMPSParser.classify_for_patterns() method.

    Migrated from: tests/unit/test_parser.py::TestMUMPSParserClassifyPatterns
    """

    def test_classify_for_patterns_returns_list(self):
        """classify_for_patterns should return a list."""
        parser = MUMPSParser()
        result = parser.classify_for_patterns("LABEL\n")
        assert isinstance(result, list)

    def test_classify_for_patterns_finds_bounded_for(self):
        """Should find bounded FOR loop."""
        parser = MUMPSParser()
        source = "TEST\tF I=1:1:10 W I\n"
        result = parser.classify_for_patterns(source)

        assert len(result) == 1
        assert result[0].loop_type == ForLoopType.BOUNDED
        assert result[0].loop_var == "I"
        assert result[0].label_name == "TEST"

    def test_classify_for_patterns_finds_open_ended_for(self):
        """Should find open-ended FOR loop."""
        parser = MUMPSParser()
        source = "TEST\tF I=1:1 W I Q:I>10\n"
        result = parser.classify_for_patterns(source)

        assert len(result) == 1
        assert result[0].loop_type == ForLoopType.OPEN_ENDED
        assert result[0].loop_var == "I"

    def test_classify_for_patterns_finds_argumentless_for(self):
        """Should find argumentless FOR loop."""
        parser = MUMPSParser()
        source = 'TEST\tF  W "loop" Q:X\n'
        result = parser.classify_for_patterns(source)

        assert len(result) == 1
        assert result[0].loop_type == ForLoopType.ARGUMENTLESS

    def test_classify_for_patterns_multiple_for_loops(self):
        """Should find multiple FOR loops in different labels."""
        parser = MUMPSParser()
        source = """FIRST\tF I=1:1:5 W I
SECOND\tF J=1:1:10 W J
"""
        result = parser.classify_for_patterns(source)

        assert len(result) == 2
        assert result[0].label_name == "FIRST"
        assert result[0].loop_var == "I"
        assert result[1].label_name == "SECOND"
        assert result[1].loop_var == "J"

    def test_classify_for_patterns_no_for_loops(self):
        """Should return empty list when no FOR loops."""
        parser = MUMPSParser()
        source = 'TEST\tW "hello"\n'
        result = parser.classify_for_patterns(source)

        assert len(result) == 0

    def test_classify_for_patterns_from_file(self, tmp_path):
        """classify_for_patterns_from_file should work on file paths."""
        test_file = tmp_path / "TEST.m"
        test_file.write_text("TEST\tF I=1:1:5 W I\n")

        parser = MUMPSParser()
        result = parser.classify_for_patterns_from_file(test_file)

        assert len(result) == 1
        assert result[0].loop_type == ForLoopType.BOUNDED

    def test_classify_for_patterns_from_file_not_found(self, tmp_path):
        """classify_for_patterns_from_file should raise for missing file."""
        parser = MUMPSParser()
        with pytest.raises(FileNotFoundError):
            parser.classify_for_patterns_from_file(tmp_path / "nonexistent.m")

    def test_classify_for_patterns_returns_mforstatement(self):
        """classify_for_patterns should include MForStatement ASG node in result."""
        parser = MUMPSParser()
        source = "TEST\tF I=1:1:10 W I\n"
        result = parser.classify_for_patterns(source)

        assert len(result) == 1
        assert result[0].statement is not None
        assert isinstance(result[0].statement, MForStatement)
        assert result[0].statement.loop_var.name == "I"
        assert result[0].statement.loop_type == ForLoopType.BOUNDED

    def test_classify_for_patterns_mforstatement_has_parameters(self):
        """MForStatement in result should have parsed parameters."""
        parser = MUMPSParser()
        source = "TEST\tF I=1:2:10 W I\n"
        result = parser.classify_for_patterns(source)

        assert len(result) == 1
        stmt = result[0].statement
        assert len(stmt.parameters) == 1

        param = stmt.parameters[0]
        assert param.param_type == ForParamType.RANGE
        assert param.start.value == 1
        assert param.step.value == 2
        assert param.end.value == 10

    def test_classify_for_patterns_mforstatement_multiple_params(self):
        """MForStatement should capture multiple forparameters."""
        parser = MUMPSParser()
        source = 'TEST\tF I="A",1:1:3 W I\n'
        result = parser.classify_for_patterns(source)

        assert len(result) == 1
        stmt = result[0].statement
        assert len(stmt.parameters) == 2

        assert stmt.parameters[0].param_type == ForParamType.VALUE
        assert stmt.parameters[0].value.value == "A"

        assert stmt.parameters[1].param_type == ForParamType.RANGE
        assert stmt.parameters[1].start.value == 1
        assert stmt.parameters[1].end.value == 3

    def test_classify_for_patterns_from_file_latin1_fallback(self, tmp_path):
        """classify_for_patterns_from_file should fall back to Latin-1 for non-UTF-8 files."""
        test_file = tmp_path / "LATIN1FOR.m"
        # Latin-1 content with FOR loop and characters that are invalid in UTF-8
        # 0xba = º (masculine ordinal) - appears in VistA files
        source_bytes = b'LABEL\tF I=1:1:10 W "Test\xba",I\n\tQ\n'
        test_file.write_bytes(source_bytes)

        parser = MUMPSParser()
        # Should not raise UnicodeDecodeError
        results = parser.classify_for_patterns_from_file(test_file)

        # Should find the bounded FOR loop
        assert len(results) == 1
        assert results[0].loop_type == ForLoopType.BOUNDED
        assert results[0].loop_var == "I"
        assert results[0].label_name == "LABEL"
