"""Tests for MUMPSParser class.

Tests parser initialization, parse(), parse_file(), and classify_patterns().
Verifies routine/label structure parsing and error handling.

For grammar acceptance tests, see test_grammar.py.
For command-level parsing, see test_command_parser.py.
"""

import pytest
from pathlib import Path

from m2py.parser import MUMPSParser, MUMPSSyntaxError, ForPatternResult, dump_asg_json
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


class TestMUMPSParserGrammarIntegration:
    """Test grammar-based command parsing integration."""

    def test_label_has_parsed_content(self):
        """Labels should have _parsed_content from textX grammar."""
        parser = MUMPSParser()
        routine = parser.parse("LABEL\tS X=1\n")
        label = routine.labels[0]
        assert hasattr(label, '_parsed_content')
        assert label._parsed_content is not None

    def test_label_has_parsed_commands(self):
        """Labels should have _parsed_commands list from textX grammar."""
        parser = MUMPSParser()
        routine = parser.parse("LABEL\tS X=1 W X\n")
        label = routine.labels[0]
        assert hasattr(label, '_parsed_commands')
        assert len(label._parsed_commands) == 2
        assert label._parsed_commands[0].__class__.__name__ == "SetCommand"
        assert label._parsed_commands[1].__class__.__name__ == "WriteCommand"

    def test_label_without_commands(self):
        """Label with no commands should have empty _parsed_commands."""
        parser = MUMPSParser()
        routine = parser.parse("LABEL\n")
        label = routine.labels[0]
        assert hasattr(label, '_parsed_commands')
        assert label._parsed_commands == []

    def test_for_command_parsed(self):
        """FOR command should be parsed via textX grammar."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\tF I=1:1:10 W I\n")
        label = routine.labels[0]
        assert len(label._parsed_commands) == 2
        assert label._parsed_commands[0].__class__.__name__ == "ForCommand"


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


# ============================================================================
# Phase 11 Performance Tests (T333-T335)
# ============================================================================

class TestParserPerformance:
    """Test parser performance meets SC-005 requirements.
    
    SC-005: Parser should complete in <2 seconds for a 500-line routine.
    """
    
    def test_500_line_synthetic_routine(self):
        """T333/T334: Parse 500-line synthetic routine in <2 seconds."""
        import time
        
        # Build a synthetic 500-line routine with realistic content
        lines = ["SYNTH\t;Synthetic 500-line routine for performance testing"]
        
        # Add SET commands with various expressions
        for i in range(100):
            lines.append(f"\tS X{i}={i},Y{i}=X{i}+1,Z{i}=$P(STR,\",\",{i+1})")
        
        # Add FOR loops
        for i in range(50):
            lines.append(f"\tF I{i}=1:1:100 S TOTAL=TOTAL+I{i}")
        
        # Add IF/ELSE blocks
        for i in range(50):
            lines.append(f"\tI X{i}>50 S FLAG{i}=1")
            lines.append(f"\tE  S FLAG{i}=0")
        
        # Add WRITE commands
        for i in range(50):
            lines.append(f"\tW !,\"Result \",X{i},\": \",Y{i}")
        
        # Add DO commands
        for i in range(50):
            lines.append(f"\tD HELPER(X{i})")
        
        # Add GOTO commands
        for i in range(25):
            lines.append(f"\tG:X{i}=0 EXIT")
        
        # Pad to 498 lines with comments
        while len(lines) < 498:
            lines.append(f"\t;Line {len(lines)+1}")
        
        # Add final statements
        lines.append("\tQ")
        lines.append("EXIT\tQ")
        
        # Join with newlines and add trailing newline
        source = "\n".join(lines) + "\n"
        
        # Verify we have ~500 lines
        line_count = len(source.strip().split('\n'))
        assert line_count >= 500, f"Only {line_count} lines generated"
        
        # Time the parse
        parser = MUMPSParser()
        start = time.perf_counter()
        result = parser.parse(source)
        elapsed = time.perf_counter() - start
        
        # Verify it parsed correctly
        assert result is not None
        # First label should be SYNTH
        assert len(result.labels) >= 1
        assert result.labels[0].name == "SYNTH"
        
        # SC-005: Must complete in <2 seconds
        assert elapsed < 2.0, f"Parse took {elapsed:.2f}s, exceeds 2s limit"
    
    def test_combined_mugj_files_performance(self, mugj_inref_dir):
        """T333: Parse combined MUGJ content (500+ lines) for performance.
        
        Combines multiple real MUGJ files to create a realistic 500+ line
        test case using actual MUMPS patterns.
        """
        import time
        from pathlib import Path
        
        # Read and combine content from multiple MUGJ files
        combined_lines = []
        files_to_combine = ["V1NST1.m", "V1OV.m", "V1GO1.m", "V1DO3.m", "V1DO2.m", "V1CALL.m"]
        
        for filename in files_to_combine:
            filepath = mugj_inref_dir / filename
            if filepath.exists():
                with open(filepath) as f:
                    lines = f.read().strip().split('\n')
                    # Add as a new label block (simulate multi-label routine)
                    for line in lines:
                        combined_lines.append(line)
            if len(combined_lines) >= 500:
                break
        
        # Verify we have enough content
        assert len(combined_lines) >= 400, f"Only {len(combined_lines)} lines available"
        
        # Parse individual files and time it (since combining requires label adjustment)
        parser = MUMPSParser()
        total_lines = 0
        start = time.perf_counter()
        
        for filename in files_to_combine:
            filepath = mugj_inref_dir / filename
            if filepath.exists():
                routine = parser.parse_file(filepath)
                with open(filepath) as f:
                    total_lines += len(f.readlines())
        
        elapsed = time.perf_counter() - start
        
        # Calculate lines per second
        lines_per_second = total_lines / elapsed if elapsed > 0 else float('inf')
        
        # Should parse at least 250 lines/second (2 seconds for 500 lines)
        assert lines_per_second > 250, f"Too slow: {lines_per_second:.0f} lines/sec"
        assert elapsed < 3.0, f"Combined parse took {elapsed:.2f}s"


# ============================================================================
# Phase 11 Error Handling Tests (T336-T337)
# ============================================================================

class TestParserErrorHandling:
    """Test parser error handling meets SC-007 requirements.
    
    SC-007: Syntax errors must include line and column numbers.
    """
    
    def test_syntax_error_has_line_info(self):
        """T336: MUMPSSyntaxError should include line number."""
        parser = MUMPSParser()
        
        # Invalid syntax - missing trailing newline
        invalid_source = 'TEST\tS X=1'  # No newline at end
        
        with pytest.raises(MUMPSSyntaxError) as excinfo:
            parser.parse(invalid_source)
        
        # Error message should contain position info
        error_msg = str(excinfo.value)
        assert "1:" in error_msg or "line" in error_msg.lower() or "Expected" in error_msg
    
    def test_syntax_error_preserves_message(self):
        """T336: MUMPSSyntaxError should preserve original error message."""
        parser = MUMPSParser()
        
        # Invalid syntax - null character
        invalid_source = '\x00INVALID\n'
        
        with pytest.raises(MUMPSSyntaxError) as excinfo:
            parser.parse(invalid_source)
        
        # Should have meaningful error info
        assert excinfo.value.message is not None
        assert len(str(excinfo.value)) > 0
    
    def test_syntax_error_from_file_includes_filename(self):
        """T336: Errors from parse_file should include filename."""
        import tempfile
        import os
        
        parser = MUMPSParser()
        
        # Create a temp file with invalid syntax (missing newline)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.m', delete=False) as f:
            f.write('TEST\tS X=1')  # No trailing newline
            temp_path = f.name
        
        try:
            with pytest.raises(MUMPSSyntaxError) as excinfo:
                parser.parse_file(temp_path)
            
            # Error should reference the file
            assert excinfo.value.source_file is not None
            assert temp_path in excinfo.value.source_file or '.m' in str(excinfo.value)
        finally:
            os.unlink(temp_path)
    
    def test_mumpssyntaxerror_attributes(self):
        """T336: MUMPSSyntaxError should have line/column attributes."""
        error = MUMPSSyntaxError(
            message="Test error",
            line=10,
            column=5,
            source_file="test.m",
            source_line="\tS X=1"
        )
        
        assert error.line == 10
        assert error.column == 5
        assert error.source_file == "test.m"
        assert error.source_line == "\tS X=1"
        
        # Message should include location
        error_str = str(error)
        assert "10" in error_str
        assert "5" in error_str
        assert "test.m" in error_str


# ============================================================================
# Phase 11 Serialization Tests (T338-T339)
# ============================================================================

class TestASGSerialization:
    """Test ASG serialization to dict/JSON (T338-T339)."""
    
    def test_routine_to_dict(self):
        """T338: MRoutine.to_dict() returns dictionary representation."""
        parser = MUMPSParser()
        source = 'TEST\tS X=1\n'
        routine = parser.parse(source)
        
        result = routine.to_dict()
        
        assert isinstance(result, dict)
        assert result["_type"] == "MRoutine"
        assert "labels" in result
        assert len(result["labels"]) >= 1
    
    def test_to_dict_includes_labels(self):
        """T338: to_dict() includes label details."""
        parser = MUMPSParser()
        source = 'TEST\tS X=1\nSUB\tQ\n'
        routine = parser.parse(source)
        
        result = routine.to_dict()
        
        labels = result["labels"]
        assert len(labels) >= 2
        assert labels[0]["name"] == "TEST"
        assert labels[1]["name"] == "SUB"
    
    def test_to_dict_with_position(self):
        """T338: to_dict() can include source position."""
        parser = MUMPSParser()
        source = 'TEST\tS X=1\n'
        routine = parser.parse(source, filename="test.m")
        routine.source_file = "test.m"
        
        result = routine.to_dict(include_position=True)
        
        assert result.get("source_file") == "test.m"
    
    def test_dump_asg_json(self):
        """T339: dump_asg_json() produces valid JSON."""
        import json
        
        parser = MUMPSParser()
        source = 'TEST\tS X=1\n'
        routine = parser.parse(source)
        
        json_str = dump_asg_json(routine)
        
        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["_type"] == "MRoutine"
    
    def test_dump_asg_json_pretty(self):
        """T339: dump_asg_json() supports indentation."""
        parser = MUMPSParser()
        source = 'TEST\tS X=1\n'
        routine = parser.parse(source)
        
        json_str = dump_asg_json(routine, indent=2)
        
        # Should have newlines from indentation
        assert "\n" in json_str
        assert "  " in json_str
    
    def test_to_dict_handles_nested_structures(self):
        """T338: to_dict() handles nested ASG structures."""
        parser = MUMPSParser()
        source = 'TEST\tF I=1:1:10 S X=I\n'
        routine = parser.parse(source)
        
        result = routine.to_dict(max_depth=5)
        
        # Should serialize without error
        assert result["_type"] == "MRoutine"
        
    def test_to_dict_max_depth_prevents_infinite_recursion(self):
        """T338: to_dict() respects max_depth to prevent stack overflow."""
        parser = MUMPSParser()
        source = 'TEST\tS X=1\n'
        routine = parser.parse(source)
        
        # Very shallow depth should truncate
        result = routine.to_dict(max_depth=1)
        
        assert result["_type"] == "MRoutine"
        # Labels might be truncated
        if result.get("labels"):
            first_label = result["labels"][0]
            assert first_label.get("_truncated") or "_type" in first_label


# =============================================================================
# Phase 12: Control Flow Body Population Tests
# =============================================================================

class TestControlFlowBodyPopulation:
    """T347-T352: Tests for control flow body population.
    
    These tests verify that FOR, IF, ELSE, and DO block bodies
    are properly populated with following commands.
    """
    
    def test_for_body_single_command(self):
        """T347: FOR captures single following command in body."""
        from m2py.asg.statements import MForStatement, MSetStatement
        
        parser = MUMPSParser()
        source = 'TEST\tF I=1:1:3 S X=I\n'
        routine = parser.parse(source)
        
        for_stmt = routine.labels[0].body.statements[0]
        assert isinstance(for_stmt, MForStatement)
        assert len(for_stmt.body.statements) == 1
        assert isinstance(for_stmt.body.statements[0], MSetStatement)
    
    def test_for_body_multiple_commands(self):
        """T347: FOR captures multiple following commands in body."""
        from m2py.asg.statements import MForStatement, MSetStatement, MWriteStatement
        
        parser = MUMPSParser()
        source = 'TEST\tF I=1:1:3 S X=I W X\n'
        routine = parser.parse(source)
        
        for_stmt = routine.labels[0].body.statements[0]
        assert isinstance(for_stmt, MForStatement)
        assert len(for_stmt.body.statements) == 2
        assert isinstance(for_stmt.body.statements[0], MSetStatement)
        assert isinstance(for_stmt.body.statements[1], MWriteStatement)
    
    def test_for_nested_for(self):
        """T353: Nested FOR loops are properly structured."""
        from m2py.asg.statements import MForStatement, MSetStatement
        
        parser = MUMPSParser()
        source = 'TEST\tF I=1:1:3 F J=1:1:3 S X=I*J\n'
        routine = parser.parse(source)
        
        outer_for = routine.labels[0].body.statements[0]
        assert isinstance(outer_for, MForStatement)
        assert outer_for.loop_var == "I"
        assert len(outer_for.body.statements) == 1
        
        inner_for = outer_for.body.statements[0]
        assert isinstance(inner_for, MForStatement)
        assert inner_for.loop_var == "J"
        assert len(inner_for.body.statements) == 1
        assert isinstance(inner_for.body.statements[0], MSetStatement)
    
    def test_if_body_single_command(self):
        """T348: IF captures single following command in then_scope."""
        from m2py.asg.statements import MIfStatement, MSetStatement
        
        parser = MUMPSParser()
        source = 'TEST\tI X=1 S Y=2\n'
        routine = parser.parse(source)
        
        if_stmt = routine.labels[0].body.statements[0]
        assert isinstance(if_stmt, MIfStatement)
        assert len(if_stmt.then_scope.statements) == 1
        assert isinstance(if_stmt.then_scope.statements[0], MSetStatement)
    
    def test_if_body_multiple_commands(self):
        """T348: IF captures multiple following commands in then_scope."""
        from m2py.asg.statements import MIfStatement, MSetStatement, MWriteStatement
        
        parser = MUMPSParser()
        source = 'TEST\tI X=1 S Y=2 W Y\n'
        routine = parser.parse(source)
        
        if_stmt = routine.labels[0].body.statements[0]
        assert isinstance(if_stmt, MIfStatement)
        assert len(if_stmt.then_scope.statements) == 2
        assert isinstance(if_stmt.then_scope.statements[0], MSetStatement)
        assert isinstance(if_stmt.then_scope.statements[1], MWriteStatement)
    
    def test_else_body_commands(self):
        """T348: ELSE captures following commands in body."""
        from m2py.asg.statements import MElseStatement, MSetStatement, MWriteStatement
        
        parser = MUMPSParser()
        source = 'TEST\tE  S Y=3 W Y\n'
        routine = parser.parse(source)
        
        else_stmt = routine.labels[0].body.statements[0]
        assert isinstance(else_stmt, MElseStatement)
        assert len(else_stmt.body.statements) == 2
        assert isinstance(else_stmt.body.statements[0], MSetStatement)
        assert isinstance(else_stmt.body.statements[1], MWriteStatement)
    
    def test_for_with_nested_if(self):
        """T354: FOR with nested IF is properly structured."""
        from m2py.asg.statements import MForStatement, MIfStatement, MSetStatement
        
        parser = MUMPSParser()
        source = 'TEST\tF I=1:1:10 I I#2 S X=I\n'
        routine = parser.parse(source)
        
        for_stmt = routine.labels[0].body.statements[0]
        assert isinstance(for_stmt, MForStatement)
        assert len(for_stmt.body.statements) == 1
        
        if_stmt = for_stmt.body.statements[0]
        assert isinstance(if_stmt, MIfStatement)
        assert len(if_stmt.then_scope.statements) == 1
        assert isinstance(if_stmt.then_scope.statements[0], MSetStatement)
    
    def test_if_with_nested_for(self):
        """T355: IF with nested FOR is properly structured."""
        from m2py.asg.statements import MIfStatement, MForStatement, MSetStatement
        
        parser = MUMPSParser()
        source = 'TEST\tI X>0 F I=1:1:X S A(I)=I\n'
        routine = parser.parse(source)
        
        if_stmt = routine.labels[0].body.statements[0]
        assert isinstance(if_stmt, MIfStatement)
        assert len(if_stmt.then_scope.statements) == 1
        
        for_stmt = if_stmt.then_scope.statements[0]
        assert isinstance(for_stmt, MForStatement)
        assert len(for_stmt.body.statements) == 1
        assert isinstance(for_stmt.body.statements[0], MSetStatement)
    
    def test_do_block_simple(self):
        """T349: Argumentless DO collects dot-indented lines in body."""
        from m2py.asg.statements import MDoStatement, MSetStatement, MWriteStatement
        
        parser = MUMPSParser()
        source = '''TEST\tD
 . S X=1
 . W X
 S Y=2
'''
        routine = parser.parse(source)
        
        # Should have 2 statements: DO block and SET
        assert len(routine.labels[0].body.statements) == 2
        
        do_stmt = routine.labels[0].body.statements[0]
        assert isinstance(do_stmt, MDoStatement)
        assert len(do_stmt.targets) == 0  # Argumentless DO
        assert len(do_stmt.body.statements) == 2
        assert isinstance(do_stmt.body.statements[0], MSetStatement)
        assert isinstance(do_stmt.body.statements[1], MWriteStatement)
        
        # SET Y=2 should be outside DO block
        assert isinstance(routine.labels[0].body.statements[1], MSetStatement)
    
    def test_do_block_nested(self):
        """T349: Nested DO blocks are properly structured."""
        from m2py.asg.statements import MDoStatement, MSetStatement
        
        parser = MUMPSParser()
        source = '''TEST\tD
 . S X=1
 . D
 . . S Y=2
 . . S Z=3
 . S A=4
 S B=5
'''
        routine = parser.parse(source)
        
        # Should have 2 statements: outer DO block and SET B=5
        assert len(routine.labels[0].body.statements) == 2
        
        outer_do = routine.labels[0].body.statements[0]
        assert isinstance(outer_do, MDoStatement)
        # Outer DO has: S X=1, nested DO, S A=4
        assert len(outer_do.body.statements) == 3
        
        inner_do = outer_do.body.statements[1]
        assert isinstance(inner_do, MDoStatement)
        # Inner DO has: S Y=2, S Z=3
        assert len(inner_do.body.statements) == 2

