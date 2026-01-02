"""Tests for MUMPSParser class public API.

Reference: M2PY Parser architecture
Migrated from: tests/unit/test_parser.py

Tests:
- TestMUMPSParserInit
- TestMUMPSParserParse
- TestMUMPSParserParseFile
- TestMUMPSParserMUGJ
- TestMUMPSParserGrammarIntegration
"""

import pytest

from m2py.parser import MUMPSParser, MUMPSSyntaxError
from m2py.asg import MRoutine


@pytest.mark.parser
class TestMUMPSParserInit:
    """Test MUMPSParser initialization.

    Migrated from: tests/unit/test_parser.py::TestMUMPSParserInit
    """

    def test_parser_initializes(self):
        """Parser should initialize without errors."""
        parser = MUMPSParser()
        assert parser is not None

    def test_parser_has_metamodel(self):
        """Parser should have a textX metamodel loaded."""
        parser = MUMPSParser()
        assert parser._metamodel is not None

    def test_parser_tracks_current_file(self):
        """Parser should track current file for error reporting."""
        parser = MUMPSParser()
        assert parser._current_file is None


@pytest.mark.parser
class TestMUMPSParserParse:
    """Test MUMPSParser.parse() method.

    Migrated from: tests/unit/test_parser.py::TestMUMPSParserParse
    """

    def test_parse_empty_returns_routine(self):
        """Parsing empty source should return an MRoutine."""
        parser = MUMPSParser()
        routine = parser.parse("")
        assert isinstance(routine, MRoutine)

    def test_parse_comment_only(self):
        """Parsing a comment-only line should work."""
        parser = MUMPSParser()
        routine = parser.parse("; This is a comment\n")
        assert isinstance(routine, MRoutine)

    def test_parse_simple_label(self):
        """Parsing a simple label definition should create MLabel."""
        parser = MUMPSParser()
        routine = parser.parse("LABEL\n")
        assert isinstance(routine, MRoutine)
        assert len(routine.labels) == 1
        assert routine.labels[0].name == "LABEL"

    def test_parse_label_with_comment(self):
        """Parsing label with comment should work."""
        parser = MUMPSParser()
        routine = parser.parse("LABEL ; comment\n")
        assert len(routine.labels) == 1
        assert routine.labels[0].name == "LABEL"

    def test_parse_multiple_labels(self):
        """Parsing multiple labels should create multiple MLabels."""
        parser = MUMPSParser()
        source = """FIRST
SECOND
THIRD
"""
        routine = parser.parse(source)
        assert len(routine.labels) == 3
        assert routine.labels[0].name == "FIRST"
        assert routine.labels[1].name == "SECOND"
        assert routine.labels[2].name == "THIRD"

    def test_parse_sets_source_file(self):
        """Parser should set source file from filename arg."""
        parser = MUMPSParser()
        routine = parser.parse("LABEL\n", filename="test.m")
        assert routine.source_file == "test.m"

    def test_parse_tab_indented_line(self):
        """Tab-indented continuation line should parse correctly."""
        parser = MUMPSParser()
        routine = parser.parse("LABEL\n\tS X=1\n")
        assert len(routine.labels) == 1
        assert len(routine.labels[0].body.statements) == 1

    def test_parse_space_indented_line(self):
        """Space-indented continuation line should parse correctly."""
        parser = MUMPSParser()
        routine = parser.parse("LABEL\n S X=1\n")
        assert len(routine.labels) == 1
        assert len(routine.labels[0].body.statements) == 1

    def test_parse_label_with_empty_formal_list(self):
        """Label with empty parentheses () should have empty formal_list."""
        parser = MUMPSParser()
        routine = parser.parse("TEST() S X=1\n")
        assert len(routine.labels) == 1
        label = routine.labels[0]
        assert label.name == "TEST"
        assert label.formal_list == []
        assert not routine.parse_errors

    def test_parse_label_with_one_param(self):
        """Label with one parameter should capture it in formal_list."""
        parser = MUMPSParser()
        routine = parser.parse("CALC(X) S Y=X*2\n")
        assert len(routine.labels) == 1
        label = routine.labels[0]
        assert label.name == "CALC"
        assert label.formal_list == ["X"]
        assert not routine.parse_errors

    def test_parse_label_with_multiple_params(self):
        """Label with multiple parameters should capture all in formal_list."""
        parser = MUMPSParser()
        routine = parser.parse("ADD(A,B,C) Q A+B+C\n")
        assert len(routine.labels) == 1
        label = routine.labels[0]
        assert label.name == "ADD"
        assert label.formal_list == ["A", "B", "C"]
        assert not routine.parse_errors

    def test_parse_numeric_label_with_empty_params(self):
        """Numeric label with empty () should have empty formal_list."""
        parser = MUMPSParser()
        routine = parser.parse("00001() S A=1\n")
        assert len(routine.labels) == 1
        label = routine.labels[0]
        assert label.name == "00001"
        assert label.formal_list == []
        assert not routine.parse_errors

    def test_parse_label_empty_params_with_comment(self):
        """Label with empty () and only comment should parse correctly."""
        parser = MUMPSParser()
        routine = parser.parse("V4GETS1() ;This is a comment\n")
        assert len(routine.labels) == 1
        label = routine.labels[0]
        assert label.name == "V4GETS1"
        assert label.formal_list == []
        assert not routine.parse_errors

    def test_parse_dot_block_requires_leading_space(self):
        """Dot-indented block line must have leading space (dot is in content)."""
        parser = MUMPSParser()
        # This should work: space + dot + space + command
        routine = parser.parse("TEST\n D\n . S X=1\n")
        do_stmt = routine.labels[0].body.statements[0]
        assert len(do_stmt.body.statements) == 1

    def test_parse_dot_without_leading_space_fails(self):
        """Line starting with dot (no leading space) is not valid MUMPS."""
        parser = MUMPSParser()
        # A line starting with '.' at column 1 is invalid - would be treated as label
        # The grammar expects ContLine to start with tab or space
        with pytest.raises(MUMPSSyntaxError):
            parser.parse("TEST\n.\n")  # dot at column 1 is not a valid line type


@pytest.mark.parser
class TestMUMPSParserParseFile:
    """Test MUMPSParser.parse_file() method.

    Migrated from: tests/unit/test_parser.py::TestMUMPSParserParseFile
    """

    def test_parse_file_not_found(self, tmp_path):
        """parse_file should raise FileNotFoundError for missing file."""
        parser = MUMPSParser()
        with pytest.raises(FileNotFoundError):
            parser.parse_file(tmp_path / "nonexistent.m")

    def test_parse_file_sets_routine_name(self, tmp_path):
        """parse_file should set routine name from filename."""
        test_file = tmp_path / "TESTRTN.m"
        test_file.write_text("LABEL\n")

        parser = MUMPSParser()
        routine = parser.parse_file(test_file)

        assert routine.name == "TESTRTN"
        assert routine.source_file == str(test_file)

    def test_parse_file_stores_source_lines(self, tmp_path):
        """parse_file should store source lines for $TEXT support."""
        test_file = tmp_path / "SRCLINES.m"
        source = "LABEL\tS X=1\n\tW X\n\tQ\n"
        test_file.write_text(source)

        parser = MUMPSParser()
        routine = parser.parse_file(test_file)

        assert routine.source_lines == ["LABEL\tS X=1", "\tW X", "\tQ"]

    def test_get_text_line_returns_source(self, tmp_path):
        """get_text_line should return 1-indexed source line."""
        test_file = tmp_path / "TEXTTEST.m"
        source = "LABEL\tS X=1\n\tW X\n\tQ\n"
        test_file.write_text(source)

        parser = MUMPSParser()
        routine = parser.parse_file(test_file)

        # 1-indexed access
        assert routine.get_text_line(1) == "LABEL\tS X=1"
        assert routine.get_text_line(2) == "\tW X"
        assert routine.get_text_line(3) == "\tQ"
        # Out of bounds returns empty
        assert routine.get_text_line(0) == ""
        assert routine.get_text_line(4) == ""
        assert routine.get_text_line(-1) == ""

    def test_get_text_at_label_returns_line(self, tmp_path):
        """get_text_at_label should return source at label+offset."""
        test_file = tmp_path / "LABELTEXT.m"
        source = "MAIN\tS X=1\n\tW X\n\tQ\nSUB\tS Y=2\n\tQ\n"
        test_file.write_text(source)

        parser = MUMPSParser()
        routine = parser.parse_file(test_file)

        # MAIN is at line 1
        assert routine.get_text_at_label("MAIN", 0) == "MAIN\tS X=1"
        assert routine.get_text_at_label("MAIN", 1) == "\tW X"
        assert routine.get_text_at_label("MAIN", 2) == "\tQ"
        # SUB is at line 4
        assert routine.get_text_at_label("SUB", 0) == "SUB\tS Y=2"
        assert routine.get_text_at_label("SUB", 1) == "\tQ"
        # Unknown label returns empty
        assert routine.get_text_at_label("UNKNOWN", 0) == ""

    def test_parse_file_utf8_encoding(self, tmp_path):
        """parse_file should handle UTF-8 encoded files correctly."""
        test_file = tmp_path / "UTF8TEST.m"
        # UTF-8 content with some special chars
        source = 'LABEL\tS X="Hello World"\n\tQ\n'
        test_file.write_text(source, encoding="utf-8")

        parser = MUMPSParser()
        routine = parser.parse_file(test_file)

        assert routine.name == "UTF8TEST"
        assert len(routine.labels) >= 1

    def test_parse_file_latin1_fallback(self, tmp_path):
        """parse_file should fall back to Latin-1 for non-UTF-8 files."""
        test_file = tmp_path / "LATIN1TEST.m"
        # Latin-1 content with characters that are invalid in UTF-8
        # 0xba = º (masculine ordinal), 0xf6 = ö (o with diaeresis)
        # These bytes appear in VistA files like TIULC.m
        source_bytes = b'LABEL\tS X="Test\xba\xf6"\n\tQ\n'
        test_file.write_bytes(source_bytes)

        parser = MUMPSParser()
        routine = parser.parse_file(test_file)

        assert routine.name == "LATIN1TEST"
        assert len(routine.labels) >= 1
        # Verify the content was read correctly as Latin-1
        assert "º" in routine.source_lines[0] or "ö" in routine.source_lines[0]

    def test_parse_file_latin1_preserves_content(self, tmp_path):
        """parse_file Latin-1 fallback should preserve source content."""
        test_file = tmp_path / "PRESERVE.m"
        # Latin-1 characters from VistA files: § (0xa7), ÷ (0xf7)
        source_bytes = b"MAIN\n\t; Comment with \xa7 and \xf7 chars\n\tQ\n"
        test_file.write_bytes(source_bytes)

        parser = MUMPSParser()
        routine = parser.parse_file(test_file)

        # Verify source_lines preserves the content correctly
        assert len(routine.source_lines) == 3
        assert "§" in routine.source_lines[1] or "÷" in routine.source_lines[1]


@pytest.mark.parser
class TestMUMPSParserMUGJ:
    """Test parsing MUGJ files.

    Migrated from: tests/unit/test_parser.py::TestMUMPSParserMUGJ
    """

    def test_parse_v1fora_labels(self, v1fora_source):
        """V1FORA.m should parse and have expected labels."""
        parser = MUMPSParser()
        routine = parser.parse(v1fora_source, filename="V1FORA.m")

        assert isinstance(routine, MRoutine)
        # V1FORA should have at least the main label
        assert len(routine.labels) >= 1
        # First label should be V1FORA
        assert routine.labels[0].name == "V1FORA"


@pytest.mark.parser
class TestMUMPSParserGrammarIntegration:
    """Test grammar-based command parsing integration.

    Migrated from: tests/unit/test_parser.py::TestMUMPSParserGrammarIntegration
    """

    def test_label_has_parsed_content(self):
        """Labels should have _parsed_content from textX grammar."""
        parser = MUMPSParser()
        routine = parser.parse("LABEL\tS X=1\n")
        label = routine.labels[0]
        assert hasattr(label, "_parsed_content")
        assert label._parsed_content is not None

    def test_label_has_parsed_commands(self):
        """Labels should have _parsed_commands list from textX grammar."""
        parser = MUMPSParser()
        routine = parser.parse("LABEL\tS X=1 W X\n")
        label = routine.labels[0]
        assert hasattr(label, "_parsed_commands")
        assert len(label._parsed_commands) == 2
        assert label._parsed_commands[0].__class__.__name__ == "SetCommand"
        assert label._parsed_commands[1].__class__.__name__ == "WriteCommand"

    def test_label_without_commands(self):
        """Label with no commands should have empty _parsed_commands."""
        parser = MUMPSParser()
        routine = parser.parse("LABEL\n")
        label = routine.labels[0]
        assert hasattr(label, "_parsed_commands")
        assert label._parsed_commands == []

    def test_for_command_parsed(self):
        """FOR command should be parsed via textX grammar."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\tF I=1:1:10 W I\n")
        label = routine.labels[0]
        assert len(label._parsed_commands) == 2
        assert label._parsed_commands[0].__class__.__name__ == "ForCommand"
