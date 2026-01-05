"""Tests for Intrinsic Functions ASG analysis (§7.1.5).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.5
"""

import pytest

from m2py.analysis.semantic_analyzer import analyze_expression, analyze_statement
from m2py.asg.expressions import (
    MActualParameter,
    MBinaryOp,
    MDeviceControl,
    MExternalFunction,
    MGlobal,
    MIndirection,
    MIntrinsicFunction,
    MLiteral,
    MSelectArg,
    MUnaryOp,
    MVariable,
)
from m2py.asg.statements import MSetStatement
from m2py.parser.textx_classes import (
    GlobalVariable,
    LocalVariable,
    SelectFunction,
    TextFunction,
)
from tests.helpers.parsing import parse_expression


@pytest.mark.asg
class TestIntrinsicFunctionsAnalysis:
    """ASG-level tests for intrinsic functions analysis (§7.1.5)."""

    def test_function_ascii(self):
        """$ASCII function is correctly analyzed (§7.1.5.1).

        $ASCII returns the ASCII code of a character in a string.
        - $A(expr) returns code of first character
        - $A(expr,pos) returns code of character at position pos
        """
        # Basic form - single argument
        expr = parse_expression('$A("Hello")')
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "A"
        assert len(result.arguments) == 1
        assert isinstance(result.arguments[0], MLiteral)
        assert result.arguments[0].value == "Hello"

        # Two-argument form with position
        expr = parse_expression('$ASCII("Hello",3)')
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "ASCII"
        assert len(result.arguments) == 2
        assert result.arguments[1].value == 3

    def test_function_char(self):
        """$CHAR function is correctly analyzed (§7.1.5.2).

        $CHAR converts ASCII codes to characters.
        Can take multiple arguments: $C(65,66,67) returns "ABC"
        """
        # Single argument
        expr = parse_expression("$C(65)")
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "C"
        assert len(result.arguments) == 1
        assert isinstance(result.arguments[0], MLiteral)
        assert result.arguments[0].value == 65

        # Multiple arguments
        expr = parse_expression("$CHAR(65,66,67)")
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "CHAR"
        assert len(result.arguments) == 3

    def test_function_data(self):
        """$DATA function is correctly analyzed (§7.1.5.3).

        $DATA returns information about variable existence and descendants.
        Returns: 0=undefined, 1=defined no descendants, 10=undefined with descendants,
                 11=defined with descendants
        """
        # Local variable
        expr = parse_expression("$D(X)")
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "D"
        assert len(result.arguments) == 1
        assert isinstance(result.arguments[0], (MVariable, LocalVariable))
        assert result.arguments[0].name == "X"

        # Global variable with subscripts
        expr = parse_expression("$DATA(^GLOBAL(1,2))")
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "DATA"
        assert len(result.arguments) == 1
        arg = result.arguments[0]
        assert isinstance(arg, (MGlobal, GlobalVariable))
        assert arg.name == "GLOBAL"  # Global name without ^ prefix

    def test_function_data_naked_global(self):
        """$DATA(^(1)) uses naked reference as argument (§7.1.2.4).

        $DATA can take naked global references as arguments.
        """
        from m2py.asg.expressions import MNakedGlobal
        from m2py.parser.line_parser import parse_commands_from_line
        from m2py.analysis.semantic_analyzer import analyze_command

        cmds = parse_commands_from_line("S X=$D(^(1))")
        stmt = analyze_command(cmds[0])
        func = stmt.assignments[0].value

        assert isinstance(func, MIntrinsicFunction)
        assert func.name.upper() in ("D", "DATA")
        assert len(func.arguments) >= 1
        assert isinstance(func.arguments[0], MNakedGlobal)

    @pytest.mark.pre1995
    @pytest.mark.skip(reason="Deprecated: $DEXTRACT is pre-1995")
    def test_function_dextract(self):
        """$DEXTRACT function is deprecated (§7.1.5)."""
        pass

    @pytest.mark.pre1995
    @pytest.mark.skip(reason="Deprecated: $DPIECE is pre-1995")
    def test_function_dpiece(self):
        """$DPIECE function is deprecated (§7.1.5)."""
        pass

    def test_function_extract(self):
        """$EXTRACT function is correctly analyzed (§7.1.5.4).

        $EXTRACT returns substring(s) from a string.
        - $E(expr) returns first character
        - $E(expr,from) returns character at position from
        - $E(expr,from,to) returns substring from position from to to
        """
        # Single argument - first character
        expr = parse_expression('$E("Hello")')
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "E"
        assert len(result.arguments) == 1

        # Two arguments - character at position
        expr = parse_expression("$EXTRACT(X,3)")
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "EXTRACT"
        assert len(result.arguments) == 2

        # Three arguments - substring range
        expr = parse_expression('$E("Hello",2,4)')
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "E"
        assert len(result.arguments) == 3

    def test_function_find(self):
        """$FIND function is correctly analyzed (§7.1.5.5).

        $FIND searches for a substring and returns position after match.
        - $F(expr,substring) searches from beginning
        - $F(expr,substring,start) searches from start position
        """
        # Two arguments
        expr = parse_expression('$F("Hello","ll")')
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "F"
        assert len(result.arguments) == 2
        assert isinstance(result.arguments[1], MLiteral)
        assert result.arguments[1].value == "ll"

        # Three arguments with start position
        expr = parse_expression('$FIND("Hello World","o",5)')
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "FIND"
        assert len(result.arguments) == 3

    def test_function_fnumber(self):
        """$FNUMBER function is correctly analyzed (§7.1.5.6).

        $FNUMBER formats a number according to formatting codes.
        - $FN(numexpr,code) formats number
        - $FN(numexpr,code,decimal) formats with specified decimal places
        """
        # Two arguments
        expr = parse_expression('$FN(1234.5,",")')
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "FN"
        assert len(result.arguments) == 2

        # Three arguments with decimal places
        expr = parse_expression('$FNUMBER(1234.567,",",2)')
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "FNUMBER"
        assert len(result.arguments) == 3

    def test_function_get(self):
        """$GET function is correctly analyzed (§7.1.5.7).

        $GET returns a variable value or default if undefined.
        - $G(glvn) returns value or empty string
        - $G(glvn,default) returns value or default expression
        """
        # Single argument - no default
        expr = parse_expression("$G(X)")
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "G"
        assert len(result.arguments) == 1
        assert isinstance(result.arguments[0], MVariable)

        # Two arguments - with default
        expr = parse_expression('$GET(^DATA(1),"N/A")')
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "GET"
        assert len(result.arguments) == 2
        assert isinstance(result.arguments[1], MLiteral)
        assert result.arguments[1].value == "N/A"

    def test_function_justify(self):
        """$JUSTIFY function is correctly analyzed (§7.1.5.8).

        $JUSTIFY right-justifies a string in a field.
        - $J(expr,width) right-justifies in field of width
        - $J(numexpr,width,decimal) also formats decimal places
        """
        # Two arguments - string justification
        expr = parse_expression('$J("Hi",10)')
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "J"
        assert len(result.arguments) == 2

        # Three arguments - numeric formatting
        expr = parse_expression("$JUSTIFY(123.456,10,2)")
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "JUSTIFY"
        assert len(result.arguments) == 3

    def test_function_length(self):
        """$LENGTH function is correctly analyzed (§7.1.5.9).

        $LENGTH returns length of a string or count of delimited pieces.
        - $L(expr) returns character count
        - $L(expr,delim) returns piece count
        """
        # Single argument - character count
        expr = parse_expression('$L("Hello")')
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "L"
        assert len(result.arguments) == 1

        # Two arguments - piece count
        expr = parse_expression('$LENGTH("A:B:C",":")')
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "LENGTH"
        assert len(result.arguments) == 2
        assert isinstance(result.arguments[1], MLiteral)
        assert result.arguments[1].value == ":"

    def test_function_name(self):
        """$NAME function is correctly analyzed (§7.1.5.10).

        $NAME returns the name of a variable as a string.
        - $NA(glvn) returns full name
        - $NA(glvn,depth) returns name with subscripts up to depth
        """
        # Single argument
        expr = parse_expression("$NA(^X(1,2,3))")
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "NA"
        assert len(result.arguments) == 1
        assert isinstance(result.arguments[0], (MGlobal, GlobalVariable))
        assert result.arguments[0].name == "X"  # Global name without ^ prefix

        # Two arguments - with depth limit
        expr = parse_expression("$NAME(^X(1,2,3),2)")
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "NAME"
        assert len(result.arguments) == 2
        assert result.arguments[1].value == 2

    @pytest.mark.pre1995
    def test_function_next(self):
        """$NEXT function is correctly analyzed (§7.1.5 - deprecated).

        $NEXT returns the next subscript using -1 as sentinel.
        Deprecated since 1990, retained for backward compatibility.
        Used in ~58 VistA files, ~213 total usages.

        Key differences from $ORDER:
        - Uses -1 (not "") as starting/ending sentinel
        - Returns ambiguous results for arrays with negative numeric subscripts
        - $N(glvn) where last subscript is -1 returns first subscript

        From spec (1990__a107099): "$N[EXT]( glvn ) is included for backward
        compatibility. The use of $Order instead of $Next is strongly encouraged."
        """
        # Basic $NEXT call with -1 sentinel (start iteration)
        expr = parse_expression("$N(^A(-1))")
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "N"
        assert len(result.arguments) == 1

        # Full form $NEXT
        expr = parse_expression("$NEXT(^DATA(X))")
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "NEXT"

        # $NEXT with local variable
        expr = parse_expression("$N(A(K))")
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "N"
        # Argument should be subscripted local
        assert len(result.arguments) == 1

    def test_function_order(self):
        """$ORDER function is correctly analyzed (§7.1.5.11).

        $ORDER returns the next subscript in collation order.
        - $O(glvn) returns next subscript at same level
        - $O(glvn,direction) returns next/previous based on direction
        """
        # Single argument - forward order
        expr = parse_expression("$O(^X(1))")
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "O"
        assert len(result.arguments) == 1
        assert isinstance(result.arguments[0], (MGlobal, GlobalVariable))

        # Two arguments - with direction
        expr = parse_expression("$ORDER(^X(1),-1)")
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "ORDER"
        assert len(result.arguments) == 2
        # -1 is parsed as unary negation of 1
        direction_arg = result.arguments[1]
        assert isinstance(direction_arg, MUnaryOp)
        assert direction_arg.operator == "-"
        assert direction_arg.operand.value == 1

    def test_function_order_naked_global(self):
        """$ORDER(^(sub)) uses naked reference as argument (§7.1.2.4).

        $ORDER can navigate using naked global references.
        """
        from m2py.asg.expressions import MNakedGlobal
        from m2py.parser.line_parser import parse_commands_from_line
        from m2py.analysis.semantic_analyzer import analyze_command

        cmds = parse_commands_from_line('S X=$O(^(""))')
        stmt = analyze_command(cmds[0])
        func = stmt.assignments[0].value

        assert isinstance(func, MIntrinsicFunction)
        assert func.name.upper() in ("O", "ORDER")
        assert isinstance(func.arguments[0], MNakedGlobal)

    def test_function_piece(self):
        """$PIECE function is correctly analyzed (§7.1.5.12).

        $PIECE extracts delimited pieces from a string.
        - $P(str,delim) returns first piece
        - $P(str,delim,from) returns piece at position
        - $P(str,delim,from,to) returns pieces from-to concatenated
        """
        # Two arguments - first piece
        expr = parse_expression('$P(X,",")')
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "P"
        assert len(result.arguments) == 2

        # Three arguments - specific piece
        expr = parse_expression('$PIECE(X,":",3)')
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "PIECE"
        assert len(result.arguments) == 3

        # Four arguments - range of pieces
        expr = parse_expression('$P(X,",",2,5)')
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "P"
        assert len(result.arguments) == 4

    def test_function_qlength(self):
        """$QLENGTH function is correctly analyzed (§7.1.5.13).

        $QLENGTH returns the number of subscripts in a name value.
        """
        expr = parse_expression('$QL("^X(1,2,3)")')
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "QL"
        assert len(result.arguments) == 1
        assert isinstance(result.arguments[0], MLiteral)

        # Full name
        expr = parse_expression('$QLENGTH("^GLOBAL(A,B)")')
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "QLENGTH"
        assert len(result.arguments) == 1

    def test_function_qsubscript(self):
        """$QSUBSCRIPT function is correctly analyzed (§7.1.5.14).

        $QSUBSCRIPT returns a specific subscript from a name value.
        - $QS(namevalue,position) returns subscript at position
        - Position 0 returns the variable name, -1 returns environment
        """
        # Get subscript at position 2
        expr = parse_expression('$QS("^X(1,2,3)",2)')
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "QS"
        assert len(result.arguments) == 2
        assert result.arguments[1].value == 2

        # Full name with variable position
        expr = parse_expression("$QSUBSCRIPT(NAME,I)")
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "QSUBSCRIPT"
        assert len(result.arguments) == 2

    def test_function_query(self):
        """$QUERY function is correctly analyzed (§7.1.5.15).

        $QUERY returns the next subscripted variable in collation order.
        Returns a name value containing the full reference.
        """
        # Local variable
        expr = parse_expression("$Q(X(1))")
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "Q"
        assert len(result.arguments) == 1

        # Global variable
        expr = parse_expression("$QUERY(^DATA(A,B))")
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "QUERY"
        assert len(result.arguments) == 1

    def test_function_random(self):
        """$RANDOM function is correctly analyzed (§7.1.5.16).

        $RANDOM returns a random integer from 0 to range-1.
        """
        expr = parse_expression("$R(100)")
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "R"
        assert len(result.arguments) == 1
        assert isinstance(result.arguments[0], MLiteral)
        assert result.arguments[0].value == 100

        # Full name with variable
        expr = parse_expression("$RANDOM(N)")
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "RANDOM"
        assert len(result.arguments) == 1

    def test_function_reverse(self):
        """$REVERSE function is correctly analyzed (§7.1.5.17).

        $REVERSE returns a string with characters in reverse order.
        """
        expr = parse_expression('$RE("Hello")')
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "RE"
        assert len(result.arguments) == 1
        assert isinstance(result.arguments[0], MLiteral)
        assert result.arguments[0].value == "Hello"

        # Full name
        expr = parse_expression("$REVERSE(X)")
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "REVERSE"
        assert len(result.arguments) == 1

    def test_function_select(self):
        """$SELECT function is correctly analyzed (§7.1.5.18).

        $SELECT evaluates condition:value pairs and returns the value
        of the first true condition. Returns SelectFunction with MSelectArg.
        """

        # Two condition:value pairs
        expr = parse_expression('$S(A=1:"Yes",1:"No")')
        result = analyze_expression(expr)
        assert isinstance(result, SelectFunction)
        assert result.name == "S"
        assert len(result.arguments) == 2
        # Each argument is an MSelectArg with condition and value
        assert isinstance(result.arguments[0], MSelectArg)
        assert isinstance(result.arguments[1], MSelectArg)

        # Check first arg structure
        first_arg = result.arguments[0]
        assert isinstance(first_arg.condition, MBinaryOp)
        assert first_arg.condition.operator == "="
        assert isinstance(first_arg.value, MLiteral)
        assert first_arg.value.value == "Yes"

        # Full name
        expr = parse_expression("$SELECT(X>0:X,1:0)")
        result = analyze_expression(expr)
        assert isinstance(result, SelectFunction)
        assert result.name == "SELECT"

    def test_function_stack(self):
        """$STACK function is correctly analyzed (§7.1.5.19).

        $STACK returns information about the execution stack.
        - $ST(level) returns entry reference at level
        - $ST(level,code) returns specific stack info
        """
        # Single argument - stack level
        expr = parse_expression("$ST(0)")
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "ST"
        assert len(result.arguments) == 1
        assert result.arguments[0].value == 0

        # Two arguments - with info code
        expr = parse_expression('$STACK(-1,"ECODE")')
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "STACK"
        assert len(result.arguments) == 2
        assert result.arguments[1].value == "ECODE"

    def test_function_text(self):
        """$TEXT function is correctly analyzed (§7.1.5.20).

        $TEXT returns the source text of a routine line.
        Returns TextFunction with line_ref dictionary.
        """
        # Simple label reference
        expr = parse_expression("$T(LABEL)")
        result = analyze_expression(expr)
        assert isinstance(result, TextFunction)
        assert result.name == "T"
        assert hasattr(result, "line_ref")
        assert result.line_ref["label"] == "LABEL"

        # Label with offset
        expr = parse_expression("$TEXT(LABEL+5)")
        result = analyze_expression(expr)
        assert isinstance(result, TextFunction)
        assert result.name == "TEXT"
        assert result.line_ref["label"] == "LABEL"
        assert isinstance(result.line_ref["offset"], MLiteral)
        assert result.line_ref["offset"].value == 5

        # Label with routine
        expr = parse_expression("$T(LABEL^ROUTINE)")
        result = analyze_expression(expr)
        assert isinstance(result, TextFunction)
        assert result.line_ref["label"] == "LABEL"
        assert result.line_ref["routine"] == "ROUTINE"

    def test_function_translate(self):
        """$TRANSLATE function is correctly analyzed (§7.1.5.21).

        $TRANSLATE replaces or removes characters in a string.
        - $TR(str,from) removes characters in 'from'
        - $TR(str,from,to) replaces characters
        """
        # Two arguments - remove characters
        expr = parse_expression('$TR("Hello","aeiou")')
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "TR"
        assert len(result.arguments) == 2

        # Three arguments - replace characters
        expr = parse_expression('$TRANSLATE("Hello","aeiou","AEIOU")')
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "TRANSLATE"
        assert len(result.arguments) == 3
        assert result.arguments[1].value == "aeiou"
        assert result.arguments[2].value == "AEIOU"

    @pytest.mark.skip(reason="Implementation-defined: $VIEW function")
    def test_function_view(self):
        """$VIEW function is implementation-defined (§7.1.5)."""
        pass


@pytest.mark.asg
class TestIntrinsicFunctionASG:
    """Test MIntrinsicFunction ASG node structure."""

    def test_piece_function_args(self):
        """$PIECE(str,delim,pos) has 3 arguments."""
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        from m2py.asg.expressions import MIntrinsicFunction

        expr = parse_expression('$PIECE(X,":",2)')
        result = analyze_expression(expr)

        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "PIECE"
        assert len(result.arguments) == 3

    def test_length_function_args(self):
        """$LENGTH(str) has 1 argument."""
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        from m2py.asg.expressions import MIntrinsicFunction

        expr = parse_expression("$LENGTH(X)")
        result = analyze_expression(expr)

        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "LENGTH"
        assert len(result.arguments) == 1

    def test_nested_function_args(self):
        """Nested function $L($P(X,",",1)) has nested arguments."""
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        from m2py.asg.expressions import MIntrinsicFunction

        expr = parse_expression('$L($P(X,",",1))')
        result = analyze_expression(expr)

        assert isinstance(result, MIntrinsicFunction)
        assert result.name in ("L", "LENGTH")
        assert len(result.arguments) == 1

        inner = result.arguments[0]
        assert isinstance(inner, MIntrinsicFunction)
        assert inner.name in ("P", "PIECE")

    def test_binary_expression_in_function_arg(self):
        """$E(X,I+1) has a binary expression argument - regression test for T582.

        This tests that binary expressions inside function arguments are correctly
        preserved and not dropped during unwrapping. Previously, _unwrap_expr()
        checked for '.ops' attribute but the grammar uses '.tail' for BinaryOpTail.

        Note: We use $E (EXTRACT) instead of $T (TEXT) because $TEXT has special
        line reference syntax where TEX+I means "label TEX plus I lines", not
        a binary expression.
        """
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        from m2py.asg.expressions import (
            MIntrinsicFunction,
            MLiteral,
            MVariable,
            MBinaryOp,
        )

        expr = parse_expression("$E(X,I+1)")
        result = analyze_expression(expr)

        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "E"
        assert len(result.arguments) == 2

        # First argument is just X
        assert isinstance(result.arguments[0], MVariable)
        assert result.arguments[0].name == "X"

        # Second argument should be an MBinaryOp, not just LocalVariable
        arg = result.arguments[1]
        assert isinstance(arg, MBinaryOp), (
            f"Expected MBinaryOp, got {type(arg).__name__}"
        )
        assert arg.operator == "+"

        # Left should be I, right should be 1
        assert isinstance(arg.left, MVariable)
        assert arg.left.name == "I"
        assert isinstance(arg.right, MLiteral)
        assert arg.right.value == 1

    def test_text_function_line_reference(self):
        """$T(TEX+I) is parsed as a line reference, not a binary expression.

        In MUMPS, $TEXT takes a line reference argument where:
        - TEX is the label name
        - +I is the offset (number of lines from the label)

        This is distinct from a binary expression argument.
        """
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        from m2py.asg.expressions import MVariable
        from m2py.parser.textx_classes import TextFunction

        expr = parse_expression("$T(TEX+I)")
        result = analyze_expression(expr)

        assert isinstance(result, TextFunction)
        assert result.name == "T"
        # Arguments list is empty because line_ref is stored separately
        assert len(result.arguments) == 0

        # Check line_ref contains the label and offset
        assert hasattr(result, "line_ref")
        assert result.line_ref["label"] == "TEX"
        # Offset should be a variable reference to I
        assert isinstance(result.line_ref["offset"], MVariable)
        assert result.line_ref["offset"].name == "I"

    def test_complex_expression_in_function_arg(self):
        """$P(A," ;",2,99) preserves all arguments including string literals."""
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        from m2py.asg.expressions import MIntrinsicFunction, MLiteral, MVariable

        expr = parse_expression('$P(A," ;",2,99)')
        result = analyze_expression(expr)

        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "P"
        assert len(result.arguments) == 4

        # First arg is variable A
        assert isinstance(result.arguments[0], MVariable)
        assert result.arguments[0].name == "A"

        # Second arg is string literal " ;"
        assert isinstance(result.arguments[1], MLiteral)
        assert result.arguments[1].value == " ;"

        # Third and fourth args are numeric literals
        assert isinstance(result.arguments[2], MLiteral)
        assert result.arguments[2].value == 2
        assert isinstance(result.arguments[3], MLiteral)
        assert result.arguments[3].value == 99


@pytest.mark.asg
class TestTextFunctionAnalysis:
    """Tests for $TEXT function semantic analysis."""

    def test_text_function_analysis_offset(self):
        """Test that $TEXT(label+offset^routine) analyzes the offset expression."""
        stmt = analyze_statement("S", "X=$TEXT(label+1^routine)")
        assert isinstance(stmt, MSetStatement)
        expr = stmt.assignments[0].value
        assert isinstance(expr, TextFunction)

        # Check line_ref
        line_ref = expr.line_ref
        assert line_ref["label"] == "label"
        assert line_ref["routine"] == "routine"

        # Check offset is analyzed (should be MLiteral, not textX object)
        offset = line_ref["offset"]
        assert isinstance(offset, MLiteral)
        assert offset.value == 1

    def test_text_function_analysis_complex_offset(self):
        """Test that $TEXT(label+1+2^routine) analyzes the complex offset expression."""
        stmt = analyze_statement("S", "X=$TEXT(label+1+2^routine)")
        expr = stmt.assignments[0].value

        offset = expr.line_ref["offset"]
        # Should be MBinaryOp, not textX Expr
        assert isinstance(offset, MBinaryOp)
        assert offset.operator == "+"
        assert isinstance(offset.left, MLiteral)
        assert offset.left.value == 1
        assert isinstance(offset.right, MLiteral)
        assert offset.right.value == 2

    def test_text_function_analysis_indirect_routine(self):
        """Test that $TEXT(label^@expr) analyzes the routine indirection."""
        # Use complex expression inside indirection to verify analysis recursion
        stmt = analyze_statement("S", 'X=$TEXT(label^@("rout"_"ine"))')
        expr = stmt.assignments[0].value

        line_ref = expr.line_ref
        assert "routine_indirect" in line_ref

        rout_ind = line_ref["routine_indirect"]
        assert isinstance(rout_ind, MIndirection)

        # The expression inside indirection should be analyzed (MBinaryOp)
        assert isinstance(rout_ind.expression, MBinaryOp)
        assert rout_ind.expression.operator == "_"
        assert rout_ind.expression.left.value == "rout"
        assert rout_ind.expression.right.value == "ine"


@pytest.mark.asg
class TestComplexExpressionsAnalysis:
    """Tests for analysis of complex expression types."""

    def test_select_function_analysis(self):
        """Test that $SELECT arguments are correctly analyzed."""
        stmt = analyze_statement("S", "X=$S(A=1:10,1:20)")
        expr = stmt.assignments[0].value
        assert isinstance(expr, MIntrinsicFunction)
        assert expr.name == "S"

        args = expr.arguments
        assert len(args) == 2
        assert isinstance(args[0], MSelectArg)
        assert isinstance(args[1], MSelectArg)

        # Check first arg condition (A=1)
        cond = args[0].condition
        assert isinstance(cond, MBinaryOp)
        assert cond.operator == "="
        assert cond.left.name == "A"
        assert cond.right.value == 1

        # Check first arg value (10)
        val = args[0].value
        assert val.value == 10

    def test_device_control_analysis(self):
        """Test that DeviceControl parameters are correctly analyzed."""
        from m2py.asg.statements import MWriteStatement

        # Use WRITE command which supports DeviceControl
        stmt = analyze_statement("W", "/KEY(A+1)")

        assert isinstance(stmt, MWriteStatement)

        # stmt.arguments is list of Any (MExpr, MFormatControl, MDeviceControl)
        assert len(stmt.arguments) == 1
        dc = stmt.arguments[0]

        assert isinstance(dc, MDeviceControl)
        assert dc.keyword == "KEY"

        # Check param analysis
        assert len(dc.params) == 1
        p = dc.params[0]
        assert isinstance(p, MBinaryOp)
        assert p.operator == "+"
        assert p.left.name == "A"

    def test_external_function_analysis(self):
        """Test that $&func arguments are correctly analyzed."""
        stmt = analyze_statement("S", "X=$&lib.func(A+1)")
        expr = stmt.assignments[0].value

        assert isinstance(expr, MExternalFunction)
        assert expr.package == "lib"
        assert expr.name == "func"

        args = expr.arguments
        assert len(args) == 1
        arg = args[0]

        assert isinstance(arg, MActualParameter)
        assert isinstance(arg.expression, MBinaryOp)
        assert arg.expression.operator == "+"
        assert arg.expression.left.name == "A"
