"""Tests for FOR loop classification patterns.

Tests the MUMPSParser.classify_for_patterns() and classify_for_patterns_from_file()
methods that analyze FOR loop structures.

MUMPS 1995 Reference: §8.2.5 FOR command
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg.enums import ForLoopType, ForParamType
from m2py.asg.statements import MForStatement
from m2py.parser.line_parser import (
    extract_for_commands,
    classify_for_command,
)


class TestMUMPSParserClassifyPatterns:
    """Test MUMPSParser.classify_for_patterns() method."""

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


class TestExtractForCommands:
    """Test extracting FOR commands from line content."""

    def test_single_for(self):
        """Extract FOR from line with one FOR."""
        fors = extract_for_commands("F I=1:1:10 W I")
        assert len(fors) == 1
        assert fors[0].__class__.__name__ == "ForCommand"
        # fors[0].var is now a LocalVariable object
        assert fors[0].var.name == "I"

    def test_no_for(self):
        """No FOR returns empty list."""
        fors = extract_for_commands("S X=1 W X")
        assert fors == []

    def test_multiple_for(self):
        """Multiple FORs (rare but possible in MUMPS)."""
        # Note: In MUMPS, multiple FORs on a line are sequential
        fors = extract_for_commands("F I=1:1:5 S X=I F J=1:1:3 W J")
        assert len(fors) == 2

    def test_for_in_string_not_extracted(self):
        """FOR in string literal shouldn't be extracted."""
        # The string "FOR" shouldn't match
        fors = extract_for_commands('W "FOR I=1:1:10"')
        assert fors == []


class TestClassifyForFromTextx:
    """Test FOR loop classification from textX models."""

    def test_bounded_for(self):
        """Bounded FOR I=1:1:10 classification."""
        fors = extract_for_commands("F I=1:1:10")
        assert len(fors) == 1
        loop_type, loop_var = classify_for_command(fors[0])
        assert loop_type == ForLoopType.BOUNDED
        assert loop_var == "I"

    def test_open_ended_for(self):
        """Open-ended FOR I=1:1 classification."""
        fors = extract_for_commands("F I=1:1")
        assert len(fors) == 1
        loop_type, loop_var = classify_for_command(fors[0])
        assert loop_type == ForLoopType.OPEN_ENDED
        assert loop_var == "I"

    def test_string_list_for(self):
        """String list FOR I=1,2,3 classification."""
        fors = extract_for_commands("F I=1,2,3")
        assert len(fors) == 1
        loop_type, loop_var = classify_for_command(fors[0])
        assert loop_type == ForLoopType.STRING_LIST
        assert loop_var == "I"

    def test_argumentless_for(self):
        """Argumentless FOR classification."""
        fors = extract_for_commands("F")
        assert len(fors) == 1
        loop_type, loop_var = classify_for_command(fors[0])
        assert loop_type == ForLoopType.ARGUMENTLESS
        assert loop_var == ""

    def test_mixed_for(self):
        """Mixed FOR I="A",1:1:3 classification."""
        fors = extract_for_commands('F I="A",1:1:3')
        assert len(fors) == 1
        loop_type, loop_var = classify_for_command(fors[0])
        assert loop_type == ForLoopType.MIXED
        assert loop_var == "I"
