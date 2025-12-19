"""Unit tests for MUMPS parser.

Tests parser initialization, basic parsing, and error handling.
"""

import pytest
from pathlib import Path

from m2py.parser import MUMPSParser, MUMPSSyntaxError, ForPatternResult
from m2py.asg import MRoutine, MLabel, MScope
from m2py.asg.enums import ForLoopType, ForParamType
from m2py.asg.statements import MForStatement


class TestMUMPSParserInit:
    """Test MUMPSParser initialization."""
    
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


class TestMUMPSParserParse:
    """Test MUMPSParser.parse() method."""
    
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


class TestMUMPSParserParseFile:
    """Test MUMPSParser.parse_file() method."""
    
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


class TestMUMPSParserMUGJ:
    """Test parsing MUGJ files."""
    
    def test_parse_v1fora_labels(self, v1fora_source):
        """V1FORA.m should parse and have expected labels."""
        parser = MUMPSParser()
        routine = parser.parse(v1fora_source, filename="V1FORA.m")
        
        assert isinstance(routine, MRoutine)
        # V1FORA should have at least the main label
        assert len(routine.labels) >= 1
        # First label should be V1FORA
        assert routine.labels[0].name == "V1FORA"


class TestMUMPSParserClassifyPatterns:
    """Test MUMPSParser.classify_patterns() method."""
    
    def test_classify_patterns_returns_list(self):
        """classify_patterns should return a list."""
        parser = MUMPSParser()
        result = parser.classify_patterns("LABEL\n")
        assert isinstance(result, list)
    
    def test_classify_patterns_finds_bounded_for(self):
        """Should find bounded FOR loop."""
        parser = MUMPSParser()
        source = "TEST\tF I=1:1:10 W I\n"
        result = parser.classify_patterns(source)
        
        assert len(result) == 1
        assert result[0].loop_type == ForLoopType.BOUNDED
        assert result[0].loop_var == "I"
        assert result[0].label_name == "TEST"
    
    def test_classify_patterns_finds_open_ended_for(self):
        """Should find open-ended FOR loop."""
        parser = MUMPSParser()
        source = "TEST\tF I=1:1 W I Q:I>10\n"
        result = parser.classify_patterns(source)
        
        assert len(result) == 1
        assert result[0].loop_type == ForLoopType.OPEN_ENDED
        assert result[0].loop_var == "I"
    
    def test_classify_patterns_finds_argumentless_for(self):
        """Should find argumentless FOR loop."""
        parser = MUMPSParser()
        source = 'TEST\tF  W "loop" Q:X\n'
        result = parser.classify_patterns(source)
        
        assert len(result) == 1
        assert result[0].loop_type == ForLoopType.ARGUMENTLESS
    
    def test_classify_patterns_multiple_for_loops(self):
        """Should find multiple FOR loops in different labels."""
        parser = MUMPSParser()
        source = """FIRST\tF I=1:1:5 W I
SECOND\tF J=1:1:10 W J
"""
        result = parser.classify_patterns(source)
        
        assert len(result) == 2
        assert result[0].label_name == "FIRST"
        assert result[0].loop_var == "I"
        assert result[1].label_name == "SECOND"
        assert result[1].loop_var == "J"
    
    def test_classify_patterns_no_for_loops(self):
        """Should return empty list when no FOR loops."""
        parser = MUMPSParser()
        source = "TEST\tW \"hello\"\n"
        result = parser.classify_patterns(source)
        
        assert len(result) == 0
    
    def test_classify_patterns_from_file(self, tmp_path):
        """classify_patterns_from_file should work on file paths."""
        test_file = tmp_path / "TEST.m"
        test_file.write_text("TEST\tF I=1:1:5 W I\n")
        
        parser = MUMPSParser()
        result = parser.classify_patterns_from_file(test_file)
        
        assert len(result) == 1
        assert result[0].loop_type == ForLoopType.BOUNDED
    
    def test_classify_patterns_from_file_not_found(self, tmp_path):
        """classify_patterns_from_file should raise for missing file."""
        parser = MUMPSParser()
        with pytest.raises(FileNotFoundError):
            parser.classify_patterns_from_file(tmp_path / "nonexistent.m")

    def test_classify_patterns_returns_mforstatement(self):
        """classify_patterns should include MForStatement ASG node in result."""
        parser = MUMPSParser()
        source = "TEST\tF I=1:1:10 W I\n"
        result = parser.classify_patterns(source)
        
        assert len(result) == 1
        assert result[0].statement is not None
        assert isinstance(result[0].statement, MForStatement)
        assert result[0].statement.loop_var == "I"
        assert result[0].statement.loop_type == ForLoopType.BOUNDED

    def test_classify_patterns_mforstatement_has_parameters(self):
        """MForStatement in result should have parsed parameters."""
        parser = MUMPSParser()
        source = "TEST\tF I=1:2:10 W I\n"
        result = parser.classify_patterns(source)
        
        assert len(result) == 1
        stmt = result[0].statement
        assert len(stmt.parameters) == 1
        
        param = stmt.parameters[0]
        assert param.param_type == ForParamType.RANGE
        assert param.start.value == 1
        assert param.step.value == 2
        assert param.end.value == 10

    def test_classify_patterns_mforstatement_multiple_params(self):
        """MForStatement should capture multiple forparameters."""
        parser = MUMPSParser()
        source = 'TEST\tF I="A",1:1:3 W I\n'
        result = parser.classify_patterns(source)
        
        assert len(result) == 1
        stmt = result[0].statement
        assert len(stmt.parameters) == 2
        
        assert stmt.parameters[0].param_type == ForParamType.VALUE
        assert stmt.parameters[0].value.value == "A"
        
        assert stmt.parameters[1].param_type == ForParamType.RANGE
        assert stmt.parameters[1].start.value == 1
        assert stmt.parameters[1].end.value == 3
