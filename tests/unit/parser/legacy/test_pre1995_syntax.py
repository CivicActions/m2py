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

    @pytest.mark.xfail(reason="stub: $NEXT function parsing")
    @pytest.mark.stub
    def test_next_function_simple(self, parser):
        """Parse simple $NEXT function call."""
        # $NEXT returns next subscript in collating sequence
        code = 'TEST S X=$NEXT(^A(""))'
        routine = parser.parse_string(code)

        # Should parse as intrinsic function call
        stmt = routine.labels[0].body.statements[0]
        assert stmt is not None
        pytest.fail("Verify $NEXT parses as intrinsic function")

    @pytest.mark.xfail(reason="stub: $N abbreviation parsing")
    @pytest.mark.stub
    def test_next_function_abbreviated(self, parser):
        """Parse abbreviated $N form of $NEXT."""
        # Both forms should produce identical ASG
        code = 'TEST S X=$N(^A(""))'
        routine = parser.parse_string(code)

        stmt = routine.labels[0].body.statements[0]
        assert stmt is not None
        pytest.fail("Verify $N abbreviation parses correctly")

    @pytest.mark.xfail(reason="stub: $NEXT with local variable")
    @pytest.mark.stub
    def test_next_function_local_variable(self, parser):
        """Parse $NEXT with local variable argument."""
        code = 'TEST S X=$NEXT(A(""))'
        routine = parser.parse_string(code)

        stmt = routine.labels[0].body.statements[0]
        assert stmt is not None
        pytest.fail("Verify $NEXT works with local variables")

    @pytest.mark.xfail(reason="stub: $NEXT in loop construct")
    @pytest.mark.stub
    def test_next_function_in_for_loop(self, parser):
        """Parse $NEXT used in FOR loop traversal pattern."""
        # Common legacy pattern for array traversal
        code = """TEST
 S K="" F  S K=$N(^A(K)) Q:K=""  D PROCESS(K)"""
        routine = parser.parse_string(code)

        label = routine.labels[0]
        assert len(label.body.statements) >= 1
        pytest.fail("Verify $NEXT in FOR loop parses correctly")


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

    @pytest.mark.xfail(reason="stub: 1977 core commands")
    @pytest.mark.stub
    def test_1977_core_commands_parse(self, parser):
        """Verify all 1977 core commands parse correctly."""
        # All commands from original 1977 standard
        commands = [
            "TEST SET X=1",
            "TEST IF X S Y=1",
            "TEST FOR I=1:1:10 S X(I)=I",
            "TEST GOTO LABEL",
            "TEST DO SUBROUTINE",
            "TEST QUIT",
            "TEST WRITE !,X",
            "TEST READ X",
            "TEST KILL X",
            "TEST LOCK ^GLOBAL",
            "TEST OPEN 1",
            "TEST CLOSE 1",
            "TEST USE 1",
            "TEST HALT",
            "TEST HANG 1",
            "TEST BREAK",
            "TEST ELSE  S X=0",
            'TEST XECUTE "S X=1"',
        ]
        for cmd in commands:
            routine = parser.parse_string(cmd)
            assert routine is not None, f"Failed to parse: {cmd}"
        pytest.fail("Verify 1977 core command parsing produces correct ASG")

    @pytest.mark.xfail(reason="stub: 1977 intrinsic functions")
    @pytest.mark.stub
    def test_1977_intrinsic_functions_parse(self, parser):
        """Verify all 1977 intrinsic functions parse correctly."""
        # Functions from original 1977 standard
        functions = [
            'TEST S X=$A("A")',  # $ASCII
            "TEST S X=$C(65)",  # $CHAR
            "TEST S X=$D(A)",  # $DATA
            "TEST S X=$E(X,1,2)",  # $EXTRACT
            'TEST S X=$F(X,"A")',  # $FIND
            "TEST S X=$J(X,10)",  # $JUSTIFY
            "TEST S X=$L(X)",  # $LENGTH
            'TEST S X=$P(X,"^",1)',  # $PIECE
            "TEST S X=$R(100)",  # $RANDOM
            "TEST S X=$S(1:X,1:Y)",  # $SELECT
            "TEST S X=$T(+1)",  # $TEXT
            "TEST S X=$V(0)",  # $VIEW
        ]
        for func in functions:
            routine = parser.parse_string(func)
            assert routine is not None, f"Failed to parse: {func}"
        pytest.fail("Verify 1977 intrinsic function parsing produces correct ASG")


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

    @pytest.mark.xfail(reason="stub: 1984 NEW command")
    @pytest.mark.stub
    def test_1984_new_command(self, parser):
        """Verify NEW command (added 1984) parses correctly."""
        code = """TEST
 NEW X,Y,Z
 SET X=1,Y=2,Z=3
 QUIT"""
        routine = parser.parse_string(code)
        assert routine is not None
        pytest.fail("Verify NEW command parsing produces correct ASG")

    @pytest.mark.xfail(reason="stub: 1984 $ORDER function")
    @pytest.mark.stub
    def test_1984_order_function(self, parser):
        """Verify $ORDER function (added 1984) parses correctly."""
        code = 'TEST S K=$ORDER(^A(""))'
        routine = parser.parse_string(code)
        assert routine is not None
        pytest.fail("Verify $ORDER parsing produces correct ASG")

    @pytest.mark.xfail(reason="stub: 1984 $QUERY function")
    @pytest.mark.stub
    def test_1984_query_function(self, parser):
        """Verify $QUERY function (added 1984) parses correctly."""
        code = 'TEST S REF=$QUERY(^A(""))'
        routine = parser.parse_string(code)
        assert routine is not None
        pytest.fail("Verify $QUERY parsing produces correct ASG")

    @pytest.mark.xfail(reason="stub: 1984 $GET function")
    @pytest.mark.stub
    def test_1984_get_function(self, parser):
        """Verify $GET function (added 1984) parses correctly."""
        code = "TEST S X=$GET(Y,0)"
        routine = parser.parse_string(code)
        assert routine is not None
        pytest.fail("Verify $GET parsing produces correct ASG")

    @pytest.mark.xfail(reason="stub: 1984 parameter passing")
    @pytest.mark.stub
    def test_1984_parameter_passing(self, parser):
        """Verify parameter passing (added 1984) parses correctly."""
        code = """ROUTINE
 DO SUB(1,2,3)
 QUIT
SUB(A,B,C)
 SET X=A+B+C
 QUIT"""
        routine = parser.parse_string(code)
        assert routine is not None
        pytest.fail("Verify parameter passing parsing produces correct ASG")


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

    @pytest.mark.xfail(reason="stub: 1995 TSTART command")
    @pytest.mark.stub
    def test_1995_tstart_command(self, parser):
        """Verify TSTART command (added 1995) parses correctly."""
        code = """TEST
 TSTART
 SET ^A=1
 TCOMMIT
 QUIT"""
        routine = parser.parse_string(code)
        assert routine is not None
        pytest.fail("Verify TSTART parsing produces correct ASG")

    @pytest.mark.xfail(reason="stub: 1995 TCOMMIT command")
    @pytest.mark.stub
    def test_1995_tcommit_command(self, parser):
        """Verify TCOMMIT command (added 1995) parses correctly."""
        code = "TEST TCOMMIT"
        routine = parser.parse_string(code)
        assert routine is not None
        pytest.fail("Verify TCOMMIT parsing produces correct ASG")

    @pytest.mark.xfail(reason="stub: 1995 TROLLBACK command")
    @pytest.mark.stub
    def test_1995_trollback_command(self, parser):
        """Verify TROLLBACK command (added 1995) parses correctly."""
        code = "TEST TROLLBACK"
        routine = parser.parse_string(code)
        assert routine is not None
        pytest.fail("Verify TROLLBACK parsing produces correct ASG")

    @pytest.mark.xfail(reason="stub: 1995 $TLEVEL variable")
    @pytest.mark.stub
    def test_1995_tlevel_variable(self, parser):
        """Verify $TLEVEL special variable (added 1995) parses correctly."""
        code = "TEST W $TLEVEL"
        routine = parser.parse_string(code)
        assert routine is not None
        pytest.fail("Verify $TLEVEL parsing produces correct ASG")


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

    @pytest.mark.xfail(reason="stub: $NEXT/$ORDER ASG equivalence")
    @pytest.mark.stub
    def test_next_order_produce_same_asg_structure(self, parser):
        """Verify $NEXT and $ORDER produce equivalent ASG structures."""
        code_next = "TEST S X=$NEXT(^A(K))"
        code_order = "TEST S X=$ORDER(^A(K))"

        _routine_next = parser.parse_string(code_next)  # noqa: F841
        _routine_order = parser.parse_string(code_order)  # noqa: F841

        # Both should produce MIntrinsicFunctionCall nodes
        # with identical argument structures
        pytest.fail("Verify $NEXT and $ORDER ASG structure equivalence")

    @pytest.mark.xfail(reason="stub: $N/$O abbreviation equivalence")
    @pytest.mark.stub
    def test_abbreviated_forms_equivalent(self, parser):
        """Verify $N and $O abbreviations work correctly."""
        code_n = "TEST S X=$N(^A(K))"
        code_o = "TEST S X=$O(^A(K))"

        _routine_n = parser.parse_string(code_n)  # noqa: F841
        _routine_o = parser.parse_string(code_o)  # noqa: F841

        # Both abbreviated forms should parse correctly
        pytest.fail("Verify $N and $O abbreviation equivalence")
