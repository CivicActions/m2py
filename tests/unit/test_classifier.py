"""Unit tests for FOR loop and GOTO classification.

Tests line_parser.py and goto_analysis.py functions for:
- FOR loop type classification (BOUNDED, OPEN_ENDED, STRING_LIST, etc.)
- FOR loop extraction and parsing
- GOTO classification (FORWARD_JUMP, BACKWARD_JUMP, LOOP_EXIT, etc.)
- Statement parsing (full-fidelity ASG via SemanticAnalyzer)
- Unreachable code detection

Note: Tests for parse_line_content and related functions are in
test_line_parser.py. These tests use the full-fidelity analyze_statement
helper function.
"""

from m2py.analysis import (
    extract_for_commands,
    classify_for_command,
    analyze_statement,
)
from m2py.asg.enums import ForLoopType, ForParamType

# Test helpers for command extraction
from tests.helpers.extraction_helpers import (
    get_for_info,
    get_goto_info,
    get_do_info,
)
from m2py.asg.statements import (
    MForStatement,
    MSetStatement,
    MWriteStatement,
    MQuitStatement,
    MIfStatement,
)


def _classify_for_content(for_content: str):
    """Helper to classify FOR content using production functions.

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


class TestClassifyForLoop:
    """Test FOR loop classification using production functions."""

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


class TestExtractForFromLine:
    """Test FOR command extraction via get_for_info helper."""

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


class TestParseForStatement:
    """Test parse_for_statement function - builds MForStatement ASG nodes.

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


class TestQuitDetection:
    """Test QUIT exit point detection in FOR loops.

    NOTE: The textX-based parser separates FOR parsing from QUIT detection.
    Use detect_quit_after_for() to check if QUIT follows FOR on a line.
    """

    def test_open_ended_for_with_quit(self):
        """Open-ended FOR with QUIT should be detected."""
        from m2py.analysis import detect_quit_after_for

        result = detect_quit_after_for("F I=1:1 W I Q:I>10")
        assert result is True

    def test_open_ended_for_with_full_quit(self):
        """QUIT spelled out should be detected."""
        from m2py.analysis import detect_quit_after_for

        result = detect_quit_after_for("F I=1:1 W I QUIT:I>10")
        assert result is True

    def test_bounded_for_no_quit(self):
        """Bounded FOR without QUIT should return False."""
        from m2py.analysis import detect_quit_after_for

        result = detect_quit_after_for("F I=1:1:10 W I")
        assert result is False

    def test_quit_inside_string_not_counted(self):
        """Q inside string should not count as QUIT."""
        from m2py.analysis import detect_quit_after_for

        result = detect_quit_after_for('F I=1:1:10 W "Q value"')
        assert result is False

    def test_argumentless_for_with_quit(self):
        """Argumentless FOR with QUIT should detect it."""
        from m2py.analysis import detect_quit_after_for

        result = detect_quit_after_for("F  W X Q:X>10")
        assert result is True

    def test_postconditioned_quit(self):
        """Postconditioned QUIT (Q:cond) should be detected."""
        from m2py.analysis import detect_quit_after_for

        result = detect_quit_after_for("F I=1:1 S X=I*2 Q:X>100")
        assert result is True

    def test_unconditional_quit(self):
        """Unconditional QUIT should be detected."""
        from m2py.analysis import detect_quit_after_for

        result = detect_quit_after_for("F I=1:1:10 W I Q")
        assert result is True

    def test_quit_with_return_value(self):
        """QUIT with return value should be detected."""
        from m2py.analysis import detect_quit_after_for

        result = detect_quit_after_for("F I=1:1 Q I*2")
        assert result is True

        # Also verify the FOR statement still parses correctly
        stmt = analyze_statement("F", "I=1:1")
        assert stmt.loop_type == ForLoopType.OPEN_ENDED


class TestParseSetStatement:
    """Test analyze_statement for SET (T041).

    NOTE: The textX-based SemanticAnalyzer returns NumericLiteral/StringLiteral for values.
    """

    def test_parse_simple_set(self):
        """Parse SET X=1 into MSetStatement."""
        stmt = analyze_statement("S", "X=1")

        assert isinstance(stmt, MSetStatement)
        assert len(stmt.assignments) == 1
        assert stmt.assignments[0].target.name == "X"
        # Full-fidelity ASG returns NumericLiteral with .value
        assert stmt.assignments[0].value.value == 1

    def test_parse_set_string(self):
        """Parse SET X="Hello" into MSetStatement."""
        stmt = analyze_statement("S", 'X="Hello"')

        assert len(stmt.assignments) == 1
        assert stmt.assignments[0].target.name == "X"
        # Full-fidelity ASG returns StringLiteral with .value
        assert stmt.assignments[0].value.value == "Hello"

    def test_parse_set_multiple_assignments(self):
        """Parse SET A=1,B=2,C=3 into MSetStatement."""
        stmt = analyze_statement("S", "A=1,B=2,C=3")

        assert len(stmt.assignments) == 3
        assert stmt.assignments[0].target.name == "A"
        assert stmt.assignments[1].target.name == "B"
        assert stmt.assignments[2].target.name == "C"

    def test_parse_set_empty(self):
        """Empty SET content returns None (argumentless SET is not valid)."""
        stmt = analyze_statement("S", "")

        # Full-fidelity ASG returns None for invalid SET without assignments
        assert stmt is None

    def test_parse_set_with_expression(self):
        """Parse SET X=A+B into MSetStatement."""
        stmt = analyze_statement("S", "X=A+B")

        assert len(stmt.assignments) == 1
        assert stmt.assignments[0].target.name == "X"
        # Full-fidelity ASG returns MBinaryOp for expressions
        assert stmt.assignments[0].value is not None


class TestParseWriteStatement:
    """Test analyze_statement for WRITE (T042).

    NOTE: The full-fidelity SemanticAnalyzer returns proper ASG objects:
    - StringLiteral/NumericLiteral for expressions
    - MFormatControl with control_type=NEWLINE for !
    - MFormatControl with control_type=TAB for ?10
    """

    def test_parse_write_string(self):
        """Parse WRITE "Hello" into MWriteStatement."""
        from m2py.parser.textx_classes import StringLiteral

        stmt = analyze_statement("W", '"Hello"')

        assert isinstance(stmt, MWriteStatement)
        assert len(stmt.arguments) == 1
        # Full-fidelity ASG returns StringLiteral
        assert isinstance(stmt.arguments[0], StringLiteral)
        assert stmt.arguments[0].value == "Hello"

    def test_parse_write_newline(self):
        """Parse WRITE ! into MWriteStatement."""
        from m2py.asg.expressions import MFormatControl
        from m2py.asg.enums import FormatControlType

        stmt = analyze_statement("W", "!")

        assert len(stmt.arguments) == 1
        assert isinstance(stmt.arguments[0], MFormatControl)
        assert stmt.arguments[0].control_type == FormatControlType.NEWLINE

    def test_parse_write_tab(self):
        """Parse WRITE ?10 into MWriteStatement."""
        from m2py.asg.expressions import MFormatControl
        from m2py.asg.enums import FormatControlType

        stmt = analyze_statement("W", "?10")

        assert len(stmt.arguments) == 1
        assert isinstance(stmt.arguments[0], MFormatControl)
        assert stmt.arguments[0].control_type == FormatControlType.TAB
        assert stmt.arguments[0].expression.value == 10

    def test_parse_write_multiple(self):
        """Parse WRITE !,"Hello",! into MWriteStatement."""
        from m2py.asg.expressions import MFormatControl
        from m2py.asg.enums import FormatControlType
        from m2py.parser.textx_classes import StringLiteral

        stmt = analyze_statement("W", '!,"Hello",!')

        assert len(stmt.arguments) == 3
        assert isinstance(stmt.arguments[0], MFormatControl)
        assert stmt.arguments[0].control_type == FormatControlType.NEWLINE
        assert isinstance(stmt.arguments[1], StringLiteral)
        assert stmt.arguments[1].value == "Hello"
        assert isinstance(stmt.arguments[2], MFormatControl)
        assert stmt.arguments[2].control_type == FormatControlType.NEWLINE

    def test_parse_write_empty(self):
        """Empty WRITE content returns empty statement."""
        stmt = analyze_statement("W", "")

        assert isinstance(stmt, MWriteStatement)
        assert len(stmt.arguments) == 0


class TestParseQuitStatement:
    """Test analyze_statement for QUIT (T042).

    NOTE: Full-fidelity ASG returns proper expression trees for complex expressions.
    """

    def test_parse_quit_simple(self):
        """Parse QUIT with no arguments."""
        stmt = analyze_statement("Q", "")

        assert isinstance(stmt, MQuitStatement)
        assert stmt.return_value is None

    def test_parse_quit_with_value(self):
        """Parse QUIT X*2 into MQuitStatement."""
        stmt = analyze_statement("Q", "X*2")

        # Full-fidelity ASG returns MBinaryOp for X*2
        assert stmt.return_value is not None

    def test_parse_quit_with_postcondition(self):
        """Parse Q:X>10 into MQuitStatement."""
        from m2py.analysis import parse_commands_from_line, analyze_command

        # Postconditions are part of command syntax, not content
        commands = parse_commands_from_line("Q:X>10")
        stmt = analyze_command(commands[0])

        # Parser should capture the postcondition
        assert stmt.postcondition is not None
        assert stmt.return_value is None

    def test_parse_quit_postcondition_with_value(self):
        """Parse Q:X>10 Y into MQuitStatement."""
        from m2py.analysis import parse_commands_from_line, analyze_command

        # Postconditions are part of command syntax, not content
        commands = parse_commands_from_line("Q:X>10 Y")
        stmt = analyze_command(commands[0])

        assert stmt.postcondition is not None
        assert stmt.return_value is not None


class TestParseIfStatement:
    """Test analyze_statement for IF (T043).

    NOTE: Full-fidelity ASG parses IF conditions as expression trees.
    """

    def test_parse_if_simple(self):
        """Parse IF X=1 into MIfStatement."""
        stmt = analyze_statement("I", "X=1")

        assert isinstance(stmt, MIfStatement)
        # Single condition is in both condition and conditions
        assert stmt.condition is not None
        assert len(stmt.conditions) == 1

    def test_parse_if_argumentless(self):
        """Parse IF with no arguments (uses $TEST)."""
        stmt = analyze_statement("I", "")

        assert len(stmt.conditions) == 0

    def test_parse_if_complex_condition(self):
        """Parse IF with complex condition."""
        stmt = analyze_statement("I", "(X>0)&(Y<10)")

        # Full-fidelity ASG returns proper expression tree
        assert stmt.condition is not None
        assert len(stmt.conditions) == 1

    def test_parse_if_has_body_content(self):
        """IF statement should have a then_scope."""
        stmt = analyze_statement("I", "X=1")

        # SemanticAnalyzer creates a then_scope
        assert hasattr(stmt, "then_scope")
        assert stmt.then_scope is not None


# =============================================================================
# GOTO Statement Parsing Tests (T065-T067 - Phase 5)
# =============================================================================


class TestParseGotoStatement:
    """Test analyze_statement for GOTO (T065-T067)."""

    def test_parse_goto_local_label(self):
        """Parse G LABEL into MGotoStatement with local target (T065)."""
        from m2py.asg.statements import MGotoStatement

        stmt = analyze_statement("G", "LABEL")

        assert isinstance(stmt, MGotoStatement)
        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == "LABEL"
        assert stmt.targets[0].routine is None
        assert stmt.targets[0].offset is None

    def test_parse_goto_percent_label(self):
        """Parse G %LABEL into MGotoStatement (T065)."""
        stmt = analyze_statement("G", "%LABEL")

        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == "%LABEL"

    def test_parse_goto_label_offset(self):
        """Parse G LABEL+2 into MGotoStatement with offset (T066)."""
        stmt = analyze_statement("G", "LABEL+2")

        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == "LABEL"
        assert stmt.targets[0].offset is not None
        # Full-fidelity ASG returns NumericLiteral with .value
        assert stmt.targets[0].offset.value == 2

    def test_parse_goto_label_expression_offset(self):
        """Parse G LABEL+$D(A) into MGotoStatement with expression offset (T066)."""
        from m2py.asg.expressions import MIntrinsicFunction

        stmt = analyze_statement("G", "LABEL+$D(A)")

        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == "LABEL"
        assert stmt.targets[0].offset is not None
        # Full-fidelity ASG returns IntrinsicFunction for $D(A)
        assert isinstance(stmt.targets[0].offset, MIntrinsicFunction)
        assert stmt.targets[0].offset.name == "D"

    def test_parse_goto_external_routine(self):
        """Parse G LABEL^ROUTINE into MGotoStatement with external target (T067)."""
        stmt = analyze_statement("G", "LABEL^ROUTINE")

        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == "LABEL"
        assert stmt.targets[0].routine == "ROUTINE"

    def test_parse_goto_external_only_routine(self):
        """Parse G ^ROUTINE into MGotoStatement (entry point) (T067)."""
        stmt = analyze_statement("G", "^ROUTINE")

        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == ""
        assert stmt.targets[0].routine == "ROUTINE"

    def test_parse_goto_multiple_targets(self):
        """Parse G A,B,C into MGotoStatement with multiple targets."""
        stmt = analyze_statement("G", "A,B,C")

        assert len(stmt.targets) == 3
        assert stmt.targets[0].name == "A"
        assert stmt.targets[1].name == "B"
        assert stmt.targets[2].name == "C"

    def test_parse_goto_postconditioned(self):
        """Parse G:X>0 LABEL into MGotoStatement with postcondition."""
        from m2py.analysis import parse_commands_from_line, analyze_command

        # MUMPS uses command postcondition format: G:condition LABEL
        commands = parse_commands_from_line("G:X>0 LABEL")
        stmt = analyze_command(commands[0])

        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == "LABEL"
        # The postcondition is on the command level
        assert stmt.postcondition is not None


class TestExtractGotoFromLine:
    """Test GOTO command extraction via get_goto_info helper."""

    def test_extract_goto_abbreviated(self):
        """G abbreviation should be recognized."""
        result = get_goto_info("\tG LABEL")
        assert result is not None
        name, routine, offset = result
        assert name == "LABEL"
        assert routine is None

    def test_extract_goto_full(self):
        """GOTO full keyword should be recognized."""
        result = get_goto_info("\tGOTO LABEL")
        assert result is not None
        name, routine, offset = result
        assert name == "LABEL"

    def test_extract_no_goto(self):
        """Line without GOTO should return None."""
        result = get_goto_info("\tS X=1 W X")
        assert result is None


# =============================================================================
# GOTO Classification Tests (T080-T087 - Phase 5)
# =============================================================================


class TestClassifyGotos:
    """Test classify_gotos function (T080-T085)."""

    def _create_routine_with_goto(
        self,
        target_label_name: str,
        source_label_name: str = "MAIN",
        routine_name: str = None,
        enclosing_for: bool = False,
    ):
        """Create a routine with a GOTO for testing."""
        from m2py.asg.elements import MRoutine, MLabel, MScope, MCall
        from m2py.asg.statements import MGotoStatement, MForStatement

        routine = MRoutine(name="TEST")

        # Source label with GOTO
        source_label = MLabel(name=source_label_name)
        source_label.body = MScope()

        # Create GOTO statement
        goto_stmt = MGotoStatement()
        call = MCall(name=target_label_name, routine=routine_name)
        goto_stmt.targets.append(call)

        if enclosing_for:
            # Put GOTO inside a FOR loop
            for_stmt = MForStatement()
            for_stmt.body = MScope()
            for_stmt.body.add_statement(goto_stmt)
            source_label.body.add_statement(for_stmt)
        else:
            source_label.body.add_statement(goto_stmt)

        routine.add_label(source_label)

        # Target label
        target_label = MLabel(name="TARGET")
        target_label.body = MScope()
        routine.add_label(target_label)

        return routine

    def test_classify_external_goto(self):
        """GOTO ^ROUTINE should be classified as EXTERNAL (T085)."""
        from m2py.analysis import resolve_references, classify_gotos
        from m2py.asg.enums import GotoType

        routine = self._create_routine_with_goto("LABEL", routine_name="OTHER")
        resolve_references(routine)
        classify_gotos(routine)

        # Find the GOTO statement
        goto_stmt = list(routine.labels[0].body.walk_statements())[0]
        assert goto_stmt.goto_type == GotoType.EXTERNAL

    def test_classify_forward_jump(self):
        """GOTO to later label should be FORWARD_JUMP with is_cross_label=True (T080).

        Cross-label GOTOs are classified with their direction (FORWARD_JUMP or
        BACKWARD_JUMP) plus is_cross_label=True to indicate label boundary crossing.
        """
        from m2py.analysis import resolve_references, classify_gotos
        from m2py.asg.enums import GotoType

        routine = self._create_routine_with_goto("TARGET")
        resolve_references(routine)
        classify_gotos(routine)

        goto_stmt = list(routine.labels[0].body.walk_statements())[0]
        # TARGET is a different label, so FORWARD_JUMP with is_cross_label
        assert goto_stmt.goto_type == GotoType.FORWARD_JUMP
        assert goto_stmt.is_cross_label is True

    def test_classify_backward_jump(self):
        """GOTO to earlier label should be BACKWARD_JUMP (T081)."""
        from m2py.analysis import resolve_references, classify_gotos
        from m2py.asg.elements import MRoutine, MLabel, MScope, MCall
        from m2py.asg.statements import MGotoStatement
        from m2py.asg.enums import GotoType

        routine = MRoutine(name="TEST")

        # First label
        first = MLabel(name="FIRST")
        first.body = MScope()
        routine.add_label(first)

        # Second label with GOTO FIRST (backward)
        second = MLabel(name="SECOND")
        second.body = MScope()
        goto_stmt = MGotoStatement()
        call = MCall(name="FIRST")
        goto_stmt.targets.append(call)
        second.body.add_statement(goto_stmt)
        routine.add_label(second)

        resolve_references(routine)
        classify_gotos(routine)

        # Should be backward jump
        assert goto_stmt.goto_type == GotoType.BACKWARD_JUMP

    def test_classify_loop_exit(self):
        """GOTO inside single FOR should be LOOP_EXIT (T082)."""
        from m2py.analysis import resolve_references, classify_gotos
        from m2py.asg.enums import GotoType

        routine = self._create_routine_with_goto("TARGET", enclosing_for=True)
        resolve_references(routine)
        classify_gotos(routine)

        # Find the GOTO inside the FOR
        for_stmt = routine.labels[0].body.statements[0]
        goto_stmt = for_stmt.body.statements[0]

        assert goto_stmt.goto_type == GotoType.LOOP_EXIT
        assert len(goto_stmt.exits_loops) == 1

    def test_classify_multi_loop_exit(self):
        """GOTO inside nested FORs should be MULTI_LOOP_EXIT (T083)."""
        from m2py.analysis import resolve_references, classify_gotos
        from m2py.asg.elements import MRoutine, MLabel, MScope, MCall
        from m2py.asg.statements import MGotoStatement, MForStatement
        from m2py.asg.enums import GotoType

        routine = MRoutine(name="TEST")

        # Source label with nested FOR
        source = MLabel(name="MAIN")
        source.body = MScope()

        # Outer FOR
        outer_for = MForStatement()
        outer_for.body = MScope()

        # Inner FOR with GOTO
        inner_for = MForStatement()
        inner_for.body = MScope()

        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        goto_stmt.targets.append(call)
        inner_for.body.add_statement(goto_stmt)
        outer_for.body.add_statement(inner_for)

        source.body.add_statement(outer_for)
        routine.add_label(source)

        # Target label
        target = MLabel(name="TARGET")
        target.body = MScope()
        routine.add_label(target)

        resolve_references(routine)
        classify_gotos(routine)

        assert goto_stmt.goto_type == GotoType.MULTI_LOOP_EXIT
        assert len(goto_stmt.exits_loops) == 2

    def test_classify_unresolved(self):
        """GOTO to missing label should be UNRESOLVED (T080)."""
        from m2py.analysis import resolve_references, classify_gotos
        from m2py.asg.elements import MRoutine, MLabel, MScope, MCall
        from m2py.asg.statements import MGotoStatement
        from m2py.asg.enums import GotoType

        routine = MRoutine(name="TEST")
        label = MLabel(name="MAIN")
        label.body = MScope()

        goto_stmt = MGotoStatement()
        call = MCall(name="MISSING")
        goto_stmt.targets.append(call)
        label.body.add_statement(goto_stmt)

        routine.add_label(label)

        resolve_references(routine)
        classify_gotos(routine)

        assert goto_stmt.goto_type == GotoType.UNRESOLVED


class TestGetLoopExitingGotos:
    """Test get_loop_exiting_gotos function (T086)."""

    def test_returns_gotos_with_exits_loops(self):
        """Should return GOTOs that exit FOR loops."""
        from m2py.analysis import (
            resolve_references,
            classify_gotos,
            get_loop_exiting_gotos,
        )
        from m2py.asg.elements import MRoutine, MLabel, MScope, MCall
        from m2py.asg.statements import MGotoStatement, MForStatement

        routine = MRoutine(name="TEST")

        # Label with FOR containing GOTO
        label = MLabel(name="MAIN")
        label.body = MScope()

        for_stmt = MForStatement()
        for_stmt.body = MScope()

        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        goto_stmt.targets.append(call)
        for_stmt.body.add_statement(goto_stmt)

        label.body.add_statement(for_stmt)
        routine.add_label(label)

        target = MLabel(name="TARGET")
        target.body = MScope()
        routine.add_label(target)

        resolve_references(routine)
        classify_gotos(routine)

        result = get_loop_exiting_gotos(routine)
        assert len(result) == 1
        assert result[0] is goto_stmt


# =============================================================================
# NEW Statement Parsing Tests (T088-T089 - Phase 6)
# =============================================================================


class TestParseNewStatement:
    """Test analyze_statement for NEW (T088-T089)."""

    def test_parse_new_single_variable(self):
        """Parse N X into MNewStatement (T088)."""
        from m2py.asg.statements import MNewStatement

        stmt = analyze_statement("N", "X")

        assert isinstance(stmt, MNewStatement)
        assert stmt.variables == ["X"]
        assert not stmt.exclusive

    def test_parse_new_multiple_variables(self):
        """Parse N X,Y,Z into MNewStatement (T088)."""
        stmt = analyze_statement("N", "X,Y,Z")

        assert stmt.variables == ["X", "Y", "Z"]
        assert not stmt.exclusive

    def test_parse_new_exclusive_single(self):
        """Parse N (X) into exclusive MNewStatement (T089)."""
        stmt = analyze_statement("N", "(X)")

        assert stmt.exclusive
        assert stmt.except_list == ["X"]
        assert stmt.variables == []

    def test_parse_new_exclusive_multiple(self):
        """Parse N (X,Y) into exclusive MNewStatement (T089)."""
        stmt = analyze_statement("N", "(X,Y)")

        assert stmt.exclusive
        assert stmt.except_list == ["X", "Y"]

    def test_parse_new_argumentless(self):
        """Parse empty NEW command."""
        stmt = analyze_statement("N", "")

        assert stmt.variables == []
        assert not stmt.exclusive


# =============================================================================
# DO Statement Parsing Tests (T090 - Phase 6)
# =============================================================================


class TestParseDoStatement:
    """Test analyze_statement for DO (T090)."""

    def test_parse_do_local_label(self):
        """Parse D LABEL into MDoStatement (T090)."""
        from m2py.asg.statements import MDoStatement

        stmt = analyze_statement("D", "LABEL")

        assert isinstance(stmt, MDoStatement)
        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == "LABEL"

    def test_parse_do_external(self):
        """Parse D LABEL^ROUTINE into MDoStatement (T090)."""
        stmt = analyze_statement("D", "LABEL^ROUTINE")

        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == "LABEL"
        assert stmt.targets[0].routine == "ROUTINE"

    def test_parse_do_with_arguments(self):
        """Parse D SUB(X,Y) into MDoStatement (T090)."""
        stmt = analyze_statement("D", "SUB(X,Y)")

        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == "SUB"
        assert len(stmt.targets[0].arguments) == 2

    def test_parse_do_multiple_targets(self):
        """Parse D A,B,C into MDoStatement (T090)."""
        stmt = analyze_statement("D", "A,B,C")

        assert len(stmt.targets) == 3
        assert stmt.targets[0].name == "A"
        assert stmt.targets[1].name == "B"
        assert stmt.targets[2].name == "C"

    def test_parse_do_percent_label(self):
        """Parse D %LABEL into MDoStatement (T090)."""
        stmt = analyze_statement("D", "%LABEL")

        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == "%LABEL"

    def test_parse_do_argumentless(self):
        """Parse empty DO (block start)."""
        stmt = analyze_statement("D", "")

        assert len(stmt.targets) == 0


class TestExtractDoFromLine:
    """Test DO command extraction via get_do_info helper."""

    def test_extract_do_abbreviated(self):
        """D abbreviation should be recognized."""
        result = get_do_info("\tD LABEL")
        assert result is not None
        content, _ = result
        assert "LABEL" in content

    def test_extract_do_full(self):
        """DO full keyword should be recognized."""
        result = get_do_info("\tDO SUB")
        assert result is not None

    def test_extract_do_not_intrinsic(self):
        """$D should not be recognized as DO."""
        result = get_do_info("\tS X=$D(A)")
        assert result is None


class TestDetectUnreachableCode:
    """Test detect_unreachable_code function (T106)."""

    def test_no_unreachable_code(self):
        """Normal code should have no unreachable lines."""
        from m2py.analysis import detect_unreachable_code

        lines = [
            "TEST\t; Start of routine",
            "\tS X=1",
            "\tW X",
            "\tQ",
        ]

        unreachable = detect_unreachable_code(lines)
        assert len(unreachable) == 0

    def test_unreachable_after_unconditional_quit(self):
        """Code after unconditional QUIT is unreachable."""
        from m2py.analysis import detect_unreachable_code

        lines = [
            "TEST\t; Start of routine",
            "\tS X=1",
            "\tQ",
            "\tW X",  # This line is unreachable
        ]

        unreachable = detect_unreachable_code(lines)
        assert len(unreachable) == 1
        assert unreachable[0][0] == 4  # Line 4 is unreachable

    def test_unreachable_after_unconditional_goto(self):
        """Code after unconditional GOTO is unreachable."""
        from m2py.analysis import detect_unreachable_code

        lines = [
            "TEST\t; Start",
            "\tS X=1",
            "\tG END",
            "\tW X",  # This line is unreachable
            "END\tQ",  # This line IS reachable (label)
        ]

        unreachable = detect_unreachable_code(lines)
        assert len(unreachable) == 1
        assert unreachable[0][0] == 4  # Line 4 is unreachable

    def test_label_resets_reachability(self):
        """Labels can be GOTO targets so they reset reachability."""
        from m2py.analysis import detect_unreachable_code

        lines = [
            "A\tG B",  # Unconditional GOTO
            "B\tS X=1",  # This is reachable via label
            "\tQ",
        ]

        unreachable = detect_unreachable_code(lines)
        assert len(unreachable) == 0  # B is reachable

    def test_conditional_quit_not_unreachable(self):
        """Code after conditional QUIT is still reachable."""
        from m2py.analysis import detect_unreachable_code

        lines = [
            "TEST\t; Start",
            "\tQ:X<0",  # Conditional QUIT
            "\tW X",  # Still reachable
            "\tQ",
        ]

        unreachable = detect_unreachable_code(lines)
        assert len(unreachable) == 0

    def test_conditional_goto_not_unreachable(self):
        """Code after conditional GOTO is still reachable."""
        from m2py.analysis import detect_unreachable_code

        lines = [
            "TEST\t; Start",
            "\tG:X<0 END",  # Conditional GOTO
            "\tW X",  # Still reachable
            "END\tQ",
        ]

        unreachable = detect_unreachable_code(lines)
        assert len(unreachable) == 0

    def test_quit_with_value_unconditional(self):
        """Q value without postcondition is still unconditional."""
        from m2py.analysis import detect_unreachable_code

        lines = [
            "FUNC(X)\t; Extrinsic function",
            "\tS Y=X*2",
            "\tQ Y",  # Unconditional quit with return value
            "\tW Y",  # Unreachable
        ]

        unreachable = detect_unreachable_code(lines)
        assert len(unreachable) == 1
        assert unreachable[0][0] == 4
