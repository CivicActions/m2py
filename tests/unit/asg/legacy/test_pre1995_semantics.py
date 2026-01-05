"""
Pre-1995 MUMPS Semantics Tests - ASG Level.

Tests ASG analysis and semantic handling of deprecated and legacy MUMPS
constructs from the 1977, 1984, and 1990 ANSI standards.

MUMPS Spec Reference:
- $NEXT function: 1984 §3.2.8 - Returns next subscript value, -1 if none exists.
  Requires subscripted glvn. Uses -1 as starting condition (unlike $ORDER which
  uses ""). Deprecated in 1995, replaced by $ORDER.
- KILL command: 1977 §3.6.10 - "Killing the variable M sets $D(M) = 0 and causes
  the value of M to be undefined." Used for variable cleanup before NEW existed.
- NEW command: 1990 §2.6.13 - Introduced variable scoping via NAME-TABLE frames.
  Pre-1990 code used KILL for manual cleanup instead.
- For complete evolution table, see: specs/002-spec-unit-test-organization/research.md
"""

import pytest

from m2py.asg.enums import ForLoopType
from m2py.parser import MUMPSParser
from m2py.parser.textx_classes import GlobalVariable, IntrinsicFunction


@pytest.mark.asg
@pytest.mark.pre1995
class TestNextFunctionSemantics:
    """
    §7.1.5 $NEXT Function ASG semantics (deprecated in 1995).

    MUMPS Spec (1984 §3.2.8):
    - "$N[EXT]( glvn ) is included for backward compatibility."
    - "Only subscripted forms of lvn and gvn are permitted."
    - "If sn is -1, let A be the set of all subscripts."
    - "If no such t exists, -1 is returned."

    Tests verify that $NEXT produces correct ASG structure for analysis,
    even though the function is deprecated. $ORDER should be used instead.
    """

    @pytest.fixture
    def parser(self):
        """Provide parser instance."""
        return MUMPSParser()

    def test_next_function_asg_structure(self, parser):
        """Verify $NEXT produces correct ASG node type (IntrinsicFunction)."""
        code = 'TEST S X=$NEXT(^A(""))'
        routine = parser.parse(code)

        stmt = routine.labels[0].body.statements[0]
        # MSetStatement with assignment
        assert len(stmt.assignments) == 1

        # The $NEXT call produces IntrinsicFunction (textX parser class)
        func = stmt.assignments[0].value
        assert isinstance(func, IntrinsicFunction)
        assert func.name == "NEXT"

        # Verify the argument is a GlobalVariable
        assert len(func.arguments) == 1
        assert isinstance(func.arguments[0], GlobalVariable)
        assert func.arguments[0].name == "A"

    def test_next_function_variable_tracking(self, parser):
        """Verify variable analysis works with $NEXT."""
        code = """TEST
 S K="" F  S K=$N(^A(K)) Q:K=""  S X(K)=^A(K)"""
        routine = parser.parse(code)
        label_vars = parser.analyze_variables(routine)

        # Verify analysis returns results for TEST label
        assert "TEST" in label_vars

        # K is both read (in $N and subscripts) and written (SET K=...)
        test_vars = label_vars["TEST"]
        assert "K" in test_vars.writes
        assert "K" in test_vars.reads

        # X is written (SET X(K)=...)
        assert "X" in test_vars.writes

    def test_next_function_traversal_pattern(self, parser):
        """Verify FOR loop classification with $NEXT traversal pattern."""
        # Common legacy pattern: FOR loop with $NEXT for tree traversal
        code = """TEST
 S K="" F  S K=$N(^A(K)) Q:K=""  W K,!"""
        routine = parser.parse(code)
        parser.analyze_for_loops(routine)

        # Get the FOR statement
        for_stmt = routine.labels[0].body.statements[1]

        # Argumentless FOR is detected correctly
        assert for_stmt.loop_type == ForLoopType.ARGUMENTLESS

        # Body contains SET, QUIT, WRITE
        assert len(for_stmt.body.statements) == 3

        # First statement in body uses $N (abbreviated $NEXT)
        set_stmt = for_stmt.body.statements[0]
        func = set_stmt.assignments[0].value
        assert isinstance(func, IntrinsicFunction)
        assert func.name == "N"  # Abbreviated form


@pytest.mark.asg
@pytest.mark.pre1995
class TestPre1984Semantics:
    """
    Test ASG handling of pre-1984 constructs.

    MUMPS Evolution:
    - 1977: No NEW, $ORDER, $QUERY, $GET, parameter passing
    - 1984: Added $ORDER, $QUERY, $GET, parameter passing
    - 1990: Added NEW command (§2.6.13 - variable scoping via NAME-TABLE frames)

    Pre-NEW code relied on global variable scope, KILL for cleanup,
    and $NEXT for array traversal.
    """

    @pytest.fixture
    def parser(self):
        """Provide parser instance."""
        return MUMPSParser()

    def test_legacy_variable_scoping(self, parser):
        """Verify ASG handles code without NEW command correctly.

        Pre-1984/1990 code used manual KILL cleanup instead of NEW.
        MUMPS Spec (1977 §3.6.10): "Killing the variable M sets $D(M) = 0
        and causes the value of M to be undefined."

        Variable tracking sees KILL as a write operation (variable state changes).
        """
        code = """TEST
 S X=1,Y=2
 D SUBROUTINE
 K TMP
 Q
SUBROUTINE
 S TMP=X*Y
 Q"""
        routine = parser.parse(code)
        label_vars = parser.analyze_variables(routine)

        # Verify both labels analyzed
        assert "TEST" in label_vars
        assert "SUBROUTINE" in label_vars

        # TEST label: X, Y written; TMP killed (tracked as write)
        test_vars = label_vars["TEST"]
        assert "X" in test_vars.writes
        assert "Y" in test_vars.writes
        assert "TMP" in test_vars.writes  # KILL tracked as write

        # SUBROUTINE label: TMP written; X, Y read
        sub_vars = label_vars["SUBROUTINE"]
        assert "TMP" in sub_vars.writes
        assert "X" in sub_vars.reads
        assert "Y" in sub_vars.reads


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

    def test_legacy_array_copy_pattern(self, parser):
        """Verify ASG handles manual array copy pattern (pre-MERGE).

        Pre-1990 pattern for copying arrays used FOR + $ORDER loop.
        This pattern should be classified as an argumentless FOR loop.
        """
        code = """TEST
 S K="" F  S K=$O(^SRC(K)) Q:K=""  S ^DST(K)=^SRC(K)"""
        routine = parser.parse(code)
        parser.analyze_for_loops(routine)

        # Get the FOR statement
        for_stmt = routine.labels[0].body.statements[1]

        # Classified as argumentless FOR loop
        assert for_stmt.loop_type == ForLoopType.ARGUMENTLESS

        # Body contains SET (K=$O), QUIT, SET (^DST=^SRC)
        assert len(for_stmt.body.statements) == 3

        # Verify $ORDER is used (showing migration from $NEXT)
        set_stmt = for_stmt.body.statements[0]
        func = set_stmt.assignments[0].value
        assert isinstance(func, IntrinsicFunction)
        assert func.name == "O"  # Abbreviated $ORDER
