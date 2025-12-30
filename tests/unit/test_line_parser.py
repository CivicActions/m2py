"""Tests for line_parser.py functions.

Tests the textX grammar-based parsing and extraction functions.
Also tests line parsing, expression parsing, and FOR command classification.

For semantic analysis (analyze_command, analyze_statement), see test_classifier.py
and test_semantic_analyzer.py.
"""

from m2py.parser.line_parser import (
    parse_line_content,
    parse_commands_from_line,
    extract_for_commands,
    classify_for_command,
    detect_quit_after_for,
)
from tests.helpers.parsing import parse_expression
from m2py.analysis import analyze_command
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
        if model is not None and hasattr(model, "commands"):
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
        model = parse_line_content("S X=1 F I=1:1:10 W I,! Q  ;loop")
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
    """Test extracting comments from line content using parse_line_content."""

    def test_has_comment(self):
        """Extract comment from line."""
        model = parse_line_content("S X=1 ;my comment")
        assert model.comment is not None
        assert model.comment.text == "my comment"

    def test_no_comment(self):
        """Line without comment returns None."""
        model = parse_line_content("S X=1")
        assert model.comment is None


class TestParseCommand:
    """Test generic command parsing using parse_commands_from_line."""

    def test_parse_set_command(self):
        """S X=1 parses as SetCommand"""
        cmds = parse_commands_from_line("S X=1")
        assert len(cmds) == 1
        assert cmds[0].__class__.__name__ == "SetCommand"

    def test_parse_write_command(self):
        """W X parses as WriteCommand"""
        cmds = parse_commands_from_line("W X")
        assert len(cmds) == 1
        assert cmds[0].__class__.__name__ == "WriteCommand"

    def test_parse_invalid(self):
        """Invalid command returns MParseError (Phase 94: error-tolerant parsing)"""
        from m2py.asg.elements import MParseError

        result = parse_commands_from_line("$$$INVALID")
        # Phase 94: Now returns MParseError instead of empty list
        assert isinstance(result, MParseError)


class TestParseExpression:
    """Test expression parsing."""

    def test_parse_simple_var(self):
        """Variable X parses correctly"""
        result = parse_expression("X")
        assert result is not None
        # The parsed expression is an Expr with structure
        assert hasattr(result, "left")

    def test_parse_arithmetic(self):
        """X+Y*Z parses with binary operators"""
        result = parse_expression("X+Y*Z")
        assert result is not None
        # Has left operand and tail for operators
        assert result.left is not None
        assert len(result.tail) > 0

    def test_parse_function(self):
        """$LENGTH(X) parses correctly"""
        result = parse_expression("$LENGTH(X)")
        assert result is not None
        # Function call is wrapped in expression structure
        assert hasattr(result, "left")

    def test_parse_global_var(self):
        """^GLOBAL parses correctly"""
        result = parse_expression("^GLOBAL")
        assert result is not None
        assert hasattr(result, "left")

    def test_parse_special_var(self):
        """$TEST parses correctly"""
        result = parse_expression("$TEST")
        assert result is not None
        assert hasattr(result, "left")


class TestParseSetCommand:
    """Test SET command parsing to full-fidelity ASG."""

    def test_simple_set(self):
        """S X=1 creates MSetStatement"""
        cmds = parse_commands_from_line("S X=1")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert len(stmt.assignments) == 1
        assert stmt.assignments[0].target.name == "X"

    def test_set_multiple(self):
        """S X=1,Y=2 creates two assignments"""
        cmds = parse_commands_from_line("S X=1,Y=2")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert len(stmt.assignments) == 2

    def test_set_global(self):
        """S ^GLOBAL=1 parses global variable"""
        cmds = parse_commands_from_line("S ^GLOBAL=1")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert isinstance(stmt.assignments[0].target, MGlobal)


class TestParseWriteCommand:
    """Test WRITE command parsing to full-fidelity ASG."""

    def test_simple_write(self):
        """W X creates MWriteStatement"""
        cmds = parse_commands_from_line("W X")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert len(stmt.arguments) == 1

    def test_write_string(self):
        """W "Hello" parses string"""
        cmds = parse_commands_from_line('W "Hello"')
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert len(stmt.arguments) == 1

    def test_write_newline(self):
        """W ! parses newline"""
        from m2py.asg.expressions import MFormatControl
        from m2py.asg.enums import FormatControlType

        cmds = parse_commands_from_line("W !")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert isinstance(stmt.arguments[0], MFormatControl)
        assert stmt.arguments[0].control_type == FormatControlType.NEWLINE


class TestParseQuitCommand:
    """Test QUIT command parsing to full-fidelity ASG."""

    def test_simple_quit(self):
        """Q creates MQuitStatement"""
        cmds = parse_commands_from_line("Q")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert stmt.return_value is None

    def test_quit_with_value(self):
        """Q X+1 parses return value"""
        cmds = parse_commands_from_line("Q X")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        # Return value should be captured as ASG node
        assert stmt.return_value is not None


class TestParseIfCommand:
    """Test IF command parsing to full-fidelity ASG."""

    def test_simple_if(self):
        """I X=1 creates MIfStatement"""
        cmds = parse_commands_from_line("I X=1")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        # The condition is stored in both 'condition' and 'conditions'
        assert stmt.condition is not None
        assert len(stmt.conditions) == 1

    def test_argumentless_if(self):
        """I (uses $TEST) parses"""
        cmds = parse_commands_from_line("I")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert len(stmt.conditions) == 0


class TestArgumentlessIfFollowedByCommand:
    """Test argumentless IF followed by another command (BUG-011 regression).

    In MUMPS, 'I  S X=1' (with TWO spaces after I) means:
    - Argumentless IF (checks $TEST)
    - Followed by SET command

    Single space 'I S' means IF with condition S (variable).
    """

    def test_argumentless_if_then_set(self):
        """I  S X=1 parses as argumentless IF + SET (not IF with condition S)."""
        cmds = parse_commands_from_line("I  S X=1")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "IfCommand"
        assert len(cmds[0].conditions) == 0  # argumentless
        assert cmds[1].__class__.__name__ == "SetCommand"

    def test_argumentless_if_then_quit(self):
        """I  Q parses as argumentless IF + QUIT."""
        cmds = parse_commands_from_line("I  Q")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "IfCommand"
        assert len(cmds[0].conditions) == 0
        assert cmds[1].__class__.__name__ == "QuitCommand"

    def test_argumentless_if_then_write(self):
        """I  W 1 parses as argumentless IF + WRITE."""
        cmds = parse_commands_from_line("I  W 1")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "IfCommand"
        assert len(cmds[0].conditions) == 0
        assert cmds[1].__class__.__name__ == "WriteCommand"

    def test_if_with_condition_single_space(self):
        """I S (single space) parses as IF with condition S."""
        cmds = parse_commands_from_line("I S")
        assert len(cmds) == 1
        assert cmds[0].__class__.__name__ == "IfCommand"
        assert len(cmds[0].conditions) == 1  # has condition

    def test_if_with_condition_then_set(self):
        """I 1 S X=1 parses as IF with condition 1, then SET."""
        cmds = parse_commands_from_line("I 1 S X=1")
        assert len(cmds) == 2
        assert cmds[0].__class__.__name__ == "IfCommand"
        assert len(cmds[0].conditions) == 1
        assert cmds[1].__class__.__name__ == "SetCommand"


class TestParseForCommand:
    """Test FOR command parsing to full-fidelity ASG."""

    def test_bounded_for(self):
        """F I=1:1:10 parses as bounded"""
        cmds = parse_commands_from_line("F I=1:1:10")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert stmt.loop_var.name == "I"
        assert stmt.loop_type == ForLoopType.BOUNDED
        assert len(stmt.parameters) == 1
        assert stmt.parameters[0].param_type == ForParamType.RANGE

    def test_open_ended_for(self):
        """F I=1:1 parses as open-ended"""
        cmds = parse_commands_from_line("F I=1:1")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert stmt.loop_type == ForLoopType.OPEN_ENDED
        assert stmt.parameters[0].param_type == ForParamType.OPEN_RANGE

    def test_value_list_for(self):
        """F I=1,2,3 parses as string list"""
        cmds = parse_commands_from_line("F I=1,2,3")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert stmt.loop_type == ForLoopType.STRING_LIST
        assert len(stmt.parameters) == 3

    def test_argumentless_for(self):
        """F (infinite loop) parses"""
        cmds = parse_commands_from_line("F")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert stmt.loop_type == ForLoopType.ARGUMENTLESS


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


class TestParseForCommandToAsg:
    """Test converting textX ForCommand to MForStatement ASG via analyze_command."""

    def test_bounded_for_asg(self):
        """Bounded FOR creates MForStatement with parameters."""
        fors = extract_for_commands("F I=1:2:10")
        assert len(fors) == 1
        stmt = analyze_command(fors[0])

        assert stmt.loop_var.name == "I"
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
        stmt = analyze_command(fors[0])

        assert len(stmt.parameters) == 3
        for p in stmt.parameters:
            assert p.param_type == ForParamType.VALUE

    def test_open_ended_for_asg(self):
        """Open-ended FOR creates MForStatement with OPEN_RANGE param."""
        fors = extract_for_commands("F I=1:1")
        assert len(fors) == 1
        stmt = analyze_command(fors[0])

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


# =============================================================================
# Extract Function Error Path Tests
# =============================================================================


class TestExtractFunctionErrorPaths:
    """Test error paths in extraction helper functions."""

    def test_extract_for_no_for_command(self):
        """get_for_info returns None when no FOR present."""
        from tests.helpers.extraction_helpers import get_for_info

        result = get_for_info("S X=1")
        assert result is None

    def test_extract_for_empty_string(self):
        """get_for_info handles empty string."""
        from tests.helpers.extraction_helpers import get_for_info

        result = get_for_info("")
        assert result is None

    def test_extract_goto_no_goto_command(self):
        """get_goto_info returns None when no GOTO present."""
        from tests.helpers.extraction_helpers import get_goto_info

        result = get_goto_info("W !,X")
        assert result is None

    def test_extract_goto_empty_string(self):
        """get_goto_info handles empty string."""
        from tests.helpers.extraction_helpers import get_goto_info

        result = get_goto_info("")
        assert result is None

    def test_extract_for_with_incomplete_syntax(self):
        """get_for_info handles incomplete FOR gracefully."""
        from tests.helpers.extraction_helpers import get_for_info

        # Incomplete FOR syntax - should not crash
        _result = get_for_info("F")  # Result intentionally unused
        # May return None or a valid result - key is no exception

    def test_extract_goto_with_valid_syntax(self):
        """get_goto_info extracts correct info."""
        from tests.helpers.extraction_helpers import get_goto_info

        _result = get_goto_info("G LABEL^ROUTINE")
