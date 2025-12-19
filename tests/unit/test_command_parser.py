"""Tests for grammar-based command parsing."""

import pytest
from m2py.analysis.command_parser import (
    parse_command,
    parse_expression,
    parse_set_command,
    parse_write_command,
    parse_quit_command,
    parse_if_command,
    parse_for_command,
    parse_line_content,
    parse_commands_from_line,
    get_line_comment,
    extract_for_commands,
    classify_for_from_textx,
    parse_for_command_to_asg,
    detect_quit_after_for,
)
from m2py.asg.expressions import MGlobal
from m2py.asg.enums import ForLoopType, ForParamType


class TestParseLineContent:
    """Test line content parsing using textX grammar."""

    def test_single_command(self):
        """Parse line with single command."""
        model = parse_line_content("S X=1")
        assert model is not None
        assert len(model.commands) == 1
        assert model.commands[0].cmd.__class__.__name__ == "SetCommand"

    def test_multiple_commands(self):
        """Parse line with multiple commands."""
        model = parse_line_content("S X=1 W X")
        assert model is not None
        assert len(model.commands) == 2
        assert model.commands[0].cmd.__class__.__name__ == "SetCommand"
        assert model.commands[1].cmd.__class__.__name__ == "WriteCommand"

    def test_with_comment(self):
        """Parse line with trailing comment."""
        model = parse_line_content("S X=1 ;comment here")
        assert model is not None
        assert len(model.commands) == 1
        assert model.comment is not None
        assert model.comment.text == "comment here"

    def test_only_comment(self):
        """Parse line with only comment."""
        model = parse_line_content(";just a comment")
        assert model is not None
        assert len(model.commands) == 0
        assert model.comment is not None
        assert model.comment.text == "just a comment"

    def test_empty_line(self):
        """Parse empty line - returns empty LineContent or empty string."""
        model = parse_line_content("")
        # Empty input may return empty string or LineContent with no commands
        if model is not None and hasattr(model, 'commands'):
            assert len(model.commands) == 0
            assert model.comment is None
        else:
            # textX may return empty string for empty input
            assert model == "" or model is None

    def test_adjacent_format_controls(self):
        """Parse W !! (adjacent newlines without comma)."""
        model = parse_line_content("W !!")
        assert model is not None
        assert len(model.commands) == 1
        cmd = model.commands[0].cmd
        assert cmd.__class__.__name__ == "WriteCommand"
        assert len(cmd.args) == 2

    def test_complex_line(self):
        """Parse complex line with multiple commands and comment."""
        model = parse_line_content('S X=1 F I=1:1:10 W I,! Q  ;loop')
        assert model is not None
        assert len(model.commands) == 4
        assert model.comment is not None


class TestParseCommandsFromLine:
    """Test extracting commands from line content."""

    def test_get_commands(self):
        """Get list of command models."""
        cmds = parse_commands_from_line("S X=1 W X")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "SetCommand"
        assert cmds[1].__class__.__name__ == "WriteCommand"

    def test_empty_line(self):
        """Empty line returns empty list."""
        cmds = parse_commands_from_line("")
        assert cmds == []


class TestGetLineComment:
    """Test extracting comments from line content."""

    def test_has_comment(self):
        """Extract comment from line."""
        comment = get_line_comment("S X=1 ;my comment")
        assert comment == "my comment"

    def test_no_comment(self):
        """Line without comment returns None."""
        comment = get_line_comment("S X=1")
        assert comment is None


class TestParseCommand:
    """Test generic command parsing."""

    def test_parse_set_command(self):
        """S X=1 parses as SetCommand"""
        result = parse_command("S X=1")
        assert result is not None
        assert result.__class__.__name__ == "SetCommand"

    def test_parse_write_command(self):
        """W X parses as WriteCommand"""
        result = parse_command("W X")
        assert result is not None
        assert result.__class__.__name__ == "WriteCommand"

    def test_parse_invalid(self):
        """Invalid command returns None"""
        result = parse_command("$$$INVALID")
        assert result is None


class TestParseExpression:
    """Test expression parsing."""

    def test_parse_simple_var(self):
        """Variable X parses"""
        result = parse_expression("X")
        assert result is not None

    def test_parse_arithmetic(self):
        """X+Y*Z parses"""
        result = parse_expression("X+Y*Z")
        assert result is not None

    def test_parse_function(self):
        """$LENGTH(X) parses"""
        result = parse_expression("$LENGTH(X)")
        assert result is not None


class TestParseSetCommand:
    """Test SET command parsing to ASG."""

    def test_simple_set(self):
        """S X=1 creates MSetStatement"""
        stmt = parse_set_command("S X=1")
        assert stmt is not None
        assert len(stmt.assignments) == 1
        assert stmt.assignments[0].target.name == "X"

    def test_set_multiple(self):
        """S X=1,Y=2 creates two assignments"""
        stmt = parse_set_command("S X=1,Y=2")
        assert stmt is not None
        assert len(stmt.assignments) == 2

    def test_set_global(self):
        """S ^GLOBAL=1 parses global variable"""
        stmt = parse_set_command("S ^GLOBAL=1")
        assert stmt is not None
        assert isinstance(stmt.assignments[0].target, MGlobal)


class TestParseWriteCommand:
    """Test WRITE command parsing to ASG."""

    def test_simple_write(self):
        """W X creates MWriteStatement"""
        stmt = parse_write_command("W X")
        assert stmt is not None
        assert len(stmt.arguments) == 1

    def test_write_string(self):
        """W "Hello" parses string"""
        stmt = parse_write_command('W "Hello"')
        assert stmt is not None
        assert len(stmt.arguments) == 1

    def test_write_newline(self):
        """W ! parses newline"""
        stmt = parse_write_command("W !")
        assert stmt is not None
        assert stmt.arguments[0]['type'] == 'newline'


class TestParseQuitCommand:
    """Test QUIT command parsing to ASG."""

    def test_simple_quit(self):
        """Q creates MQuitStatement"""
        stmt = parse_quit_command("Q")
        assert stmt is not None
        assert stmt.return_value is None

    def test_quit_with_value(self):
        """Q X+1 parses return value"""
        stmt = parse_quit_command("Q X")
        assert stmt is not None
        # Return value should be captured


class TestParseIfCommand:
    """Test IF command parsing to ASG."""

    def test_simple_if(self):
        """I X=1 creates MIfStatement"""
        stmt = parse_if_command("I X=1")
        assert stmt is not None
        # The condition is stored in 'condition' attribute
        assert stmt.condition is not None

    def test_argumentless_if(self):
        """I (uses $TEST) parses"""
        stmt = parse_if_command("I")
        assert stmt is not None


class TestParseForCommand:
    """Test FOR command parsing to ASG."""

    def test_bounded_for(self):
        """F I=1:1:10 parses as bounded"""
        stmt = parse_for_command("F I=1:1:10")
        assert stmt is not None
        assert stmt.loop_var == "I"
        assert stmt.loop_type == ForLoopType.BOUNDED
        assert len(stmt.parameters) == 1
        assert stmt.parameters[0].param_type == ForParamType.RANGE

    def test_open_ended_for(self):
        """F I=1:1 parses as open-ended"""
        stmt = parse_for_command("F I=1:1")
        assert stmt is not None
        assert stmt.loop_type == ForLoopType.OPEN_ENDED
        assert stmt.parameters[0].param_type == ForParamType.OPEN_RANGE

    def test_value_list_for(self):
        """F I=1,2,3 parses as string list"""
        stmt = parse_for_command("F I=1,2,3")
        assert stmt is not None
        assert stmt.loop_type == ForLoopType.STRING_LIST
        assert len(stmt.parameters) == 3

    def test_argumentless_for(self):
        """F (infinite loop) parses"""
        stmt = parse_for_command("F")
        assert stmt is not None
        assert stmt.loop_type == ForLoopType.ARGUMENTLESS


class TestExtractForCommands:
    """Test extracting FOR commands from line content."""

    def test_single_for(self):
        """Extract FOR from line with one FOR."""
        fors = extract_for_commands("F I=1:1:10 W I")
        assert len(fors) == 1
        assert fors[0].__class__.__name__ == "ForCommand"
        assert fors[0].var == "I"

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
        loop_type, loop_var = classify_for_from_textx(fors[0])
        assert loop_type == ForLoopType.BOUNDED
        assert loop_var == "I"

    def test_open_ended_for(self):
        """Open-ended FOR I=1:1 classification."""
        fors = extract_for_commands("F I=1:1")
        assert len(fors) == 1
        loop_type, loop_var = classify_for_from_textx(fors[0])
        assert loop_type == ForLoopType.OPEN_ENDED
        assert loop_var == "I"

    def test_string_list_for(self):
        """String list FOR I=1,2,3 classification."""
        fors = extract_for_commands("F I=1,2,3")
        assert len(fors) == 1
        loop_type, loop_var = classify_for_from_textx(fors[0])
        assert loop_type == ForLoopType.STRING_LIST
        assert loop_var == "I"

    def test_argumentless_for(self):
        """Argumentless FOR classification."""
        fors = extract_for_commands("F")
        assert len(fors) == 1
        loop_type, loop_var = classify_for_from_textx(fors[0])
        assert loop_type == ForLoopType.ARGUMENTLESS
        assert loop_var == ""

    def test_mixed_for(self):
        """Mixed FOR I="A",1:1:3 classification."""
        fors = extract_for_commands('F I="A",1:1:3')
        assert len(fors) == 1
        loop_type, loop_var = classify_for_from_textx(fors[0])
        assert loop_type == ForLoopType.MIXED
        assert loop_var == "I"


class TestParseForCommandToAsg:
    """Test converting textX ForCommand to MForStatement ASG."""

    def test_bounded_for_asg(self):
        """Bounded FOR creates MForStatement with parameters."""
        fors = extract_for_commands("F I=1:2:10")
        assert len(fors) == 1
        stmt = parse_for_command_to_asg(fors[0])
        
        assert stmt.loop_var == "I"
        assert stmt.loop_type == ForLoopType.BOUNDED
        assert len(stmt.parameters) == 1
        
        param = stmt.parameters[0]
        assert param.param_type == ForParamType.RANGE
        assert param.start.value == 1
        assert param.step.value == 2
        assert param.end.value == 10

    def test_string_list_for_asg(self):
        """String list FOR creates MForStatement with VALUE params."""
        fors = extract_for_commands('F I="A","B","C"')
        assert len(fors) == 1
        stmt = parse_for_command_to_asg(fors[0])
        
        assert len(stmt.parameters) == 3
        for p in stmt.parameters:
            assert p.param_type == ForParamType.VALUE

    def test_open_ended_for_asg(self):
        """Open-ended FOR creates MForStatement with OPEN_RANGE param."""
        fors = extract_for_commands("F I=1:1")
        assert len(fors) == 1
        stmt = parse_for_command_to_asg(fors[0])
        
        assert stmt.loop_type == ForLoopType.OPEN_ENDED
        assert stmt.parameters[0].param_type == ForParamType.OPEN_RANGE


class TestDetectQuitAfterFor:
    """Test QUIT detection after FOR command."""

    def test_quit_after_for(self):
        """Detect QUIT after FOR on same line."""
        result = detect_quit_after_for("F I=1:1:10 W I Q")
        assert result is True

    def test_no_quit(self):
        """No QUIT returns False."""
        result = detect_quit_after_for("F I=1:1:10 W I")
        assert result is False

    def test_quit_without_for(self):
        """QUIT without FOR returns False."""
        result = detect_quit_after_for("S X=1 Q")
        assert result is False

    def test_quit_before_for(self):
        """QUIT before FOR doesn't count."""
        result = detect_quit_after_for("Q F I=1:1:10 W I")
        assert result is False

    def test_postconditioned_quit(self):
        """Postconditioned QUIT still detected."""
        result = detect_quit_after_for("F I=1:1:10 W I Q:I>5")
        assert result is True
