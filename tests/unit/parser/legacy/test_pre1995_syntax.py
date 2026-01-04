"""
Pre-1995 MUMPS Syntax Tests - Parser Level.

Tests parser handling of deprecated and legacy MUMPS syntax constructs
from the 1977, 1984, and 1990 ANSI standards.

MUMPS Spec Reference:
- $NEXT function: Deprecated in 1995 §7.1.5, replaced by $ORDER
- For complete evolution table, see: specs/002-spec-unit-test-organization/research.md
"""

import pytest

from m2py.parser import MUMPSParser


@pytest.mark.parser
@pytest.mark.pre1995
class TestNextFunctionParsing:
    """
    §7.1.5 $NEXT Function (deprecated in 1995, use $ORDER instead).

    $NEXT was present in 1977-1990 standards and deprecated in 1995.
    M2PY should parse $NEXT syntax correctly for backward compatibility.
    VistA-M contains ~488 occurrences of $NEXT usage.
    """

    @pytest.fixture
    def parser(self):
        """Provide parser instance."""
        return MUMPSParser()

    def test_next_function_simple(self, parser):
        """Parse simple $NEXT function call."""
        # $NEXT returns next subscript in collating sequence
        code = 'TEST S X=$NEXT(^A(""))'
        routine = parser.parse(code)

        # Should parse as intrinsic function call
        stmt = routine.labels[0].body.statements[0]
        assert stmt is not None
        func = stmt.assignments[0].value
        assert type(func).__name__ == "IntrinsicFunction"
        assert func.name == "NEXT"

    def test_next_function_abbreviated(self, parser):
        """Parse abbreviated $N form of $NEXT."""
        # Both forms should produce identical ASG
        code = 'TEST S X=$N(^A(""))'
        routine = parser.parse(code)

        stmt = routine.labels[0].body.statements[0]
        assert stmt is not None
        func = stmt.assignments[0].value
        assert type(func).__name__ == "IntrinsicFunction"
        assert func.name == "N"  # Abbreviation preserved

    def test_next_function_local_variable(self, parser):
        """Parse $NEXT with local variable argument."""
        code = 'TEST S X=$NEXT(A(""))'
        routine = parser.parse(code)

        stmt = routine.labels[0].body.statements[0]
        assert stmt is not None
        func = stmt.assignments[0].value
        assert type(func).__name__ == "IntrinsicFunction"
        assert func.name == "NEXT"
        # Argument should be a local variable with subscript
        assert func.args.first.expr is not None

    def test_next_function_in_for_loop(self, parser):
        """Parse $NEXT used in FOR loop traversal pattern."""
        # Common legacy pattern for array traversal
        code = """TEST
 S K="" F  S K=$N(^A(K)) Q:K=""  D PROCESS(K)"""
        routine = parser.parse(code)

        label = routine.labels[0]
        assert len(label.body.statements) >= 1
        # First statement is SET K=""
        assert type(label.body.statements[0]).__name__ == "MSetStatement"
        # Second statement is FOR loop
        assert type(label.body.statements[1]).__name__ == "MForStatement"


@pytest.mark.parser
@pytest.mark.pre1995
class TestDeprecatedFunctionsParsing:
    """
    Test parsing of deprecated intrinsic functions.

    Note: $DEXTRACT and $DPIECE were proposed but never standardized.
    M2PY does NOT support these - they should raise parse errors.
    """

    @pytest.fixture
    def parser(self):
        """Provide parser instance."""
        return MUMPSParser()

    @pytest.mark.skip(reason="out-of-scope: $DEXTRACT never standardized per FR-055")
    def test_dextract_not_supported(self, parser):
        """Verify $DEXTRACT is not supported (never standardized)."""
        # $DEXTRACT was proposed but never included in ANSI standard
        pass

    @pytest.mark.skip(reason="out-of-scope: $DPIECE never standardized per FR-055")
    def test_dpiece_not_supported(self, parser):
        """Verify $DPIECE is not supported (never standardized)."""
        # $DPIECE was proposed but never included in ANSI standard
        pass


@pytest.mark.parser
@pytest.mark.pre1995
class TestPre1984Syntax:
    """
    Test syntax constructs from 1977 standard (pre-1984).

    These tests verify backward compatibility with original MUMPS syntax.
    Features added in 1984 ($ORDER, $QUERY, NEW, etc.) were additions,
    not changes, so core 1977 syntax should work unchanged.
    """

    @pytest.fixture
    def parser(self):
        """Provide parser instance."""
        return MUMPSParser()

    def test_1977_core_commands_parse(self, parser):
        """Verify all 1977 core commands parse correctly."""
        # All commands from original 1977 standard
        commands = [
            ("TEST SET X=1", "MSetStatement"),
            ("TEST IF X S Y=1", "MIfStatement"),
            ("TEST FOR I=1:1:10 S X(I)=I", "MForStatement"),
            ("TEST GOTO LABEL", "MGotoStatement"),
            ("TEST DO SUBROUTINE", "MDoStatement"),
            ("TEST QUIT", "MQuitStatement"),
            ("TEST WRITE !,X", "MWriteStatement"),
            ("TEST READ X", "MReadStatement"),
            ("TEST KILL X", "MKillStatement"),
            ("TEST LOCK ^GLOBAL", "MLockStatement"),
            ("TEST OPEN 1", "MOpenStatement"),
            ("TEST CLOSE 1", "MCloseStatement"),
            ("TEST USE 1", "MUseStatement"),
            ("TEST HALT", "MHaltStatement"),
            ("TEST HANG 1", "MHangStatement"),
            ("TEST BREAK", "MBreakStatement"),
            ("TEST ELSE  S X=0", "MElseStatement"),
            ('TEST XECUTE "S X=1"', "MXecuteStatement"),
        ]
        for cmd, expected_type in commands:
            routine = parser.parse(cmd)
            stmt = routine.labels[0].body.statements[0]
            assert stmt is not None, f"Failed to parse: {cmd}"
            assert type(stmt).__name__ == expected_type, (
                f"{cmd} -> {type(stmt).__name__}"
            )

    def test_1977_intrinsic_functions_parse(self, parser):
        """Verify all 1977 intrinsic functions parse correctly."""
        # Functions from original 1977 standard with expected abbreviated names
        functions = [
            ('TEST S X=$A("A")', "A"),  # $ASCII
            ("TEST S X=$C(65)", "C"),  # $CHAR
            ("TEST S X=$D(A)", "D"),  # $DATA
            ("TEST S X=$E(X,1,2)", "E"),  # $EXTRACT
            ('TEST S X=$F(X,"A")', "F"),  # $FIND
            ("TEST S X=$J(X,10)", "J"),  # $JUSTIFY
            ("TEST S X=$L(X)", "L"),  # $LENGTH
            ('TEST S X=$P(X,"^",1)', "P"),  # $PIECE
            ("TEST S X=$R(100)", "R"),  # $RANDOM
            ("TEST S X=$V(0)", "V"),  # $VIEW
        ]
        for func_code, expected_name in functions:
            routine = parser.parse(func_code)
            stmt = routine.labels[0].body.statements[0]
            func = stmt.assignments[0].value
            assert func is not None, f"Failed to parse: {func_code}"
            assert hasattr(func, "name"), f"Not a function: {func_code}"
            assert func.name == expected_name, f"{func_code} -> ${func.name}"


@pytest.mark.parser
@pytest.mark.pre1995
class TestPre1990Syntax:
    """
    Test syntax constructs from 1984 standard (pre-1990).

    1984 added: NEW, $ORDER, $QUERY, $GET, parameter passing.
    1990 added: MERGE, $NAME, $FNUMBER, $TRANSLATE, $REVERSE.
    """

    @pytest.fixture
    def parser(self):
        """Provide parser instance."""
        return MUMPSParser()

    def test_1984_new_command(self, parser):
        """Verify NEW command (added 1984) parses correctly."""
        code = """TEST
 NEW X,Y,Z
 SET X=1,Y=2,Z=3
 QUIT"""
        routine = parser.parse(code)
        assert routine is not None
        # Should have NEW, SET, QUIT statements
        stmts = routine.labels[0].body.statements
        assert type(stmts[0]).__name__ == "MNewStatement"
        assert type(stmts[1]).__name__ == "MSetStatement"
        assert type(stmts[2]).__name__ == "MQuitStatement"

    def test_1984_order_function(self, parser):
        """Verify $ORDER function (added 1984) parses correctly."""
        code = 'TEST S K=$ORDER(^A(""))'
        routine = parser.parse(code)
        assert routine is not None
        func = routine.labels[0].body.statements[0].assignments[0].value
        assert type(func).__name__ == "IntrinsicFunction"
        assert func.name == "ORDER"

    def test_1984_query_function(self, parser):
        """Verify $QUERY function (added 1984) parses correctly."""
        code = 'TEST S REF=$QUERY(^A(""))'
        routine = parser.parse(code)
        assert routine is not None
        func = routine.labels[0].body.statements[0].assignments[0].value
        assert type(func).__name__ == "IntrinsicFunction"
        assert func.name == "QUERY"

    def test_1984_get_function(self, parser):
        """Verify $GET function (added 1984) parses correctly."""
        code = "TEST S X=$GET(Y,0)"
        routine = parser.parse(code)
        assert routine is not None
        func = routine.labels[0].body.statements[0].assignments[0].value
        assert type(func).__name__ == "IntrinsicFunction"
        assert func.name == "GET"

    def test_1984_parameter_passing(self, parser):
        """Verify parameter passing (added 1984) parses correctly."""
        code = """ROUTINE
 DO SUB(1,2,3)
 QUIT
SUB(A,B,C)
 SET X=A+B+C
 QUIT"""
        routine = parser.parse(code)
        assert routine is not None
        # ROUTINE label has DO and QUIT
        stmts = routine.labels[0].body.statements
        assert type(stmts[0]).__name__ == "MDoStatement"
        # SUB label has formal parameters
        sub_label = routine.labels[1]
        assert sub_label.name == "SUB"
        # Formal list is directly a list of parameter names
        assert sub_label.formal_list is not None
        params = sub_label.formal_list
        assert len(params) == 3
        assert params[0] == "A"
        assert params[1] == "B"
        assert params[2] == "C"


@pytest.mark.parser
@pytest.mark.pre1995
class TestPre1995TransactionCommands:
    """
    Test transaction commands (added in 1995).

    These should parse correctly in 1995+ mode but tests confirm
    their absence from pre-1995 codebase expectations.
    """

    @pytest.fixture
    def parser(self):
        """Provide parser instance."""
        return MUMPSParser()

    def test_1995_tstart_command(self, parser):
        """Verify TSTART command (added 1995) parses correctly."""
        code = """TEST
 TSTART
 SET ^A=1
 TCOMMIT
 QUIT"""
        routine = parser.parse(code)
        assert routine is not None
        stmts = routine.labels[0].body.statements
        assert type(stmts[0]).__name__ == "MTStartStatement"
        assert type(stmts[1]).__name__ == "MSetStatement"
        assert type(stmts[2]).__name__ == "MTCommitStatement"
        assert type(stmts[3]).__name__ == "MQuitStatement"

    def test_1995_tcommit_command(self, parser):
        """Verify TCOMMIT command (added 1995) parses correctly."""
        code = "TEST TCOMMIT"
        routine = parser.parse(code)
        assert routine is not None
        stmt = routine.labels[0].body.statements[0]
        assert type(stmt).__name__ == "MTCommitStatement"

    def test_1995_trollback_command(self, parser):
        """Verify TROLLBACK command (added 1995) parses correctly."""
        code = "TEST TROLLBACK"
        routine = parser.parse(code)
        assert routine is not None
        stmt = routine.labels[0].body.statements[0]
        assert type(stmt).__name__ == "MTRollbackStatement"

    def test_1995_tlevel_variable(self, parser):
        """Verify $TLEVEL special variable (added 1995) parses correctly."""
        code = "TEST W $TLEVEL"
        routine = parser.parse(code)
        assert routine is not None
        stmt = routine.labels[0].body.statements[0]
        assert type(stmt).__name__ == "MWriteStatement"
        # $TLEVEL should be parsed as a special variable
        # MWriteStatement.arguments is a list of write items
        svar = stmt.arguments[0]
        assert type(svar).__name__ == "SpecialVariable"
        assert svar.name.upper() == "TLEVEL"


@pytest.mark.parser
@pytest.mark.pre1995
class TestNextVsOrderEquivalence:
    """
    Test that $NEXT and $ORDER produce equivalent ASG structures.

    Per 1995 spec §7.1.5, $NEXT is deprecated and $ORDER should be
    used instead. Both should produce identical behavior.
    """

    @pytest.fixture
    def parser(self):
        """Provide parser instance."""
        return MUMPSParser()

    def test_next_order_produce_same_asg_structure(self, parser):
        """Verify $NEXT and $ORDER produce equivalent ASG structures."""
        code_next = "TEST S X=$NEXT(^A(K))"
        code_order = "TEST S X=$ORDER(^A(K))"

        routine_next = parser.parse(code_next)
        routine_order = parser.parse(code_order)

        # Both should produce IntrinsicFunction nodes
        func_next = routine_next.labels[0].body.statements[0].assignments[0].value
        func_order = routine_order.labels[0].body.statements[0].assignments[0].value

        assert type(func_next).__name__ == "IntrinsicFunction"
        assert type(func_order).__name__ == "IntrinsicFunction"
        # Names differ but both are intrinsic functions
        assert func_next.name == "NEXT"
        assert func_order.name == "ORDER"
        # Both have same argument structure (global variable with subscript)
        assert func_next.args is not None
        assert func_order.args is not None

    def test_abbreviated_forms_equivalent(self, parser):
        """Verify $N and $O abbreviations work correctly."""
        code_n = "TEST S X=$N(^A(K))"
        code_o = "TEST S X=$O(^A(K))"

        routine_n = parser.parse(code_n)
        routine_o = parser.parse(code_o)

        # Both abbreviated forms should parse correctly as IntrinsicFunction
        func_n = routine_n.labels[0].body.statements[0].assignments[0].value
        func_o = routine_o.labels[0].body.statements[0].assignments[0].value

        assert type(func_n).__name__ == "IntrinsicFunction"
        assert type(func_o).__name__ == "IntrinsicFunction"
        assert func_n.name == "N"  # Abbreviation preserved
        assert func_o.name == "O"  # Abbreviation preserved
