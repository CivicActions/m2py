"""
Pre-1995 MUMPS Semantics Tests - ASG Level.

Tests ASG analysis and semantic handling of deprecated and legacy MUMPS
constructs from the 1977, 1984, and 1990 ANSI standards.

MUMPS Spec Reference:
- $NEXT function: Deprecated in 1995 §7.1.5, replaced by $ORDER
- For complete evolution table, see: specs/002-spec-unit-test-organization/research.md
"""

import pytest

from m2py.parser import MUMPSParser


@pytest.mark.asg
@pytest.mark.pre1995
class TestNextFunctionSemantics:
    """
    §7.1.5 $NEXT Function ASG semantics (deprecated in 1995).

    Tests verify that $NEXT produces correct ASG structure for analysis,
    even though the function is deprecated.
    """

    @pytest.fixture
    def parser(self):
        """Provide parser instance."""
        return MUMPSParser()

    @pytest.mark.xfail(reason="stub: $NEXT ASG analysis")
    @pytest.mark.stub
    def test_next_function_asg_structure(self, parser):
        """Verify $NEXT produces correct ASG node type."""
        code = 'TEST S X=$NEXT(^A(""))'
        routine = parser.parse_string(code)

        _stmt = routine.labels[0].body.statements[0]  # noqa: F841
        # Should produce MIntrinsicFunctionCall with name 'NEXT'
        pytest.fail("Verify $NEXT creates MIntrinsicFunctionCall ASG node")

    @pytest.mark.xfail(reason="stub: $NEXT variable tracking")
    @pytest.mark.stub
    def test_next_function_variable_tracking(self, parser):
        """Verify variable analysis works with $NEXT."""
        code = """TEST
 S K="" F  S K=$N(^A(K)) Q:K=""  S X(K)=^A(K)"""
        routine = parser.parse_string(code)
        parser.analyze_variables(routine)

        _label = routine.labels[0]  # noqa: F841
        # K should be tracked as both read and written
        pytest.fail("Verify variable analysis handles $NEXT arguments correctly")

    @pytest.mark.xfail(reason="stub: $NEXT in pattern detection")
    @pytest.mark.stub
    def test_next_function_traversal_pattern(self, parser):
        """Verify FOR loop classification with $NEXT traversal pattern."""
        # Common legacy pattern: FOR loop with $NEXT for tree traversal
        code = """TEST
 S K="" F  S K=$N(^A(K)) Q:K=""  W K,!"""
        routine = parser.parse_string(code)
        parser.analyze_for_loops(routine)

        # Should detect as traversal loop despite using deprecated $NEXT
        pytest.fail("Verify FOR loop classification handles $NEXT pattern")


@pytest.mark.asg
@pytest.mark.pre1995
class TestPre1984Semantics:
    """
    Test ASG handling of pre-1984 constructs.

    Before 1984, MUMPS did not have:
    - NEW command (variable scoping)
    - $ORDER function
    - $QUERY function
    - $GET function
    - Parameter passing

    Code from pre-1984 implementations relied on global variable scope
    and $NEXT for array traversal.
    """

    @pytest.fixture
    def parser(self):
        """Provide parser instance."""
        return MUMPSParser()

    @pytest.mark.xfail(reason="stub: pre-NEW scoping patterns")
    @pytest.mark.stub
    def test_legacy_variable_scoping(self, parser):
        """Verify ASG handles code without NEW command correctly."""
        # Pre-1984 code used manual variable cleanup instead of NEW
        code = """TEST
 S X=1,Y=2
 D SUBROUTINE
 K TMP  ; Manual cleanup instead of NEW
 Q
SUBROUTINE
 S TMP=X*Y
 Q"""
        routine = parser.parse_string(code)
        parser.analyze_variables(routine)

        # Should track TMP across both labels
        pytest.fail("Verify variable tracking works for pre-NEW scoping patterns")


@pytest.mark.asg
@pytest.mark.pre1995
class TestPre1990Semantics:
    """
    Test ASG handling of pre-1990 constructs.

    Before 1990, MUMPS did not have:
    - MERGE command
    - $NAME function
    - $FNUMBER function
    - $TRANSLATE function
    - $REVERSE function
    - $KEY, $REFERENCE special variables

    Code from pre-1990 implementations used manual loops for array copying
    instead of MERGE.
    """

    @pytest.fixture
    def parser(self):
        """Provide parser instance."""
        return MUMPSParser()

    @pytest.mark.xfail(reason="stub: pre-MERGE array copy pattern")
    @pytest.mark.stub
    def test_legacy_array_copy_pattern(self, parser):
        """Verify ASG handles manual array copy pattern (pre-MERGE)."""
        # Pre-1990 pattern for copying arrays (MERGE was added in 1990)
        code = """TEST
 ; Manual array copy without MERGE
 S K="" F  S K=$O(^SRC(K)) Q:K=""  S ^DST(K)=^SRC(K)"""
        routine = parser.parse_string(code)
        parser.analyze_for_loops(routine)

        # Should classify as traversal loop
        pytest.fail("Verify FOR loop analysis handles legacy array copy pattern")
