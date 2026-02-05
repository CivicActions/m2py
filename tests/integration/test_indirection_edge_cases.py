"""Integration tests for Spec 012 Phase 11: Edge Cases & Error Handling.

T071-T072: Tests for indirection edge cases including:
- Undefined indirection source variables (T065)
- Invalid variable names from indirection (T066)
- FOR loop variable indirection (T068)
- KILL indirection (T069)
- NEW indirection (T070)
- XECUTE syntax error context (T067)
"""

import pytest

from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime


@pytest.fixture
def execute_mumps():
    """Fixture for parsing, generating, and executing MUMPS code."""

    def _execute(source: str, *, capture_output: bool = True):
        """Execute MUMPS source and return output string (including error message if any)."""
        python_code = generate_python(source)
        runtime = MUMPSRuntime()
        result = runtime.execute(python_code, capture_output=capture_output)
        # Include error message in output for error-checking tests
        if result.error:
            return f"ERROR: {result.error}"
        return result.output

    return _execute


# =============================================================================
# T068: FOR Loop Variable Indirection Tests
# =============================================================================


@pytest.mark.integration
class TestForLoopIndirection:
    """Tests for FOR loop variable indirection (F @A=1:1:3).

    T089: Migrated to use unified resolve_for_target() via IndirectionResolver.
    T090: Tests for @-expressions in FOR loop bounds.
    """

    def test_for_bounded_indirect_variable(self, execute_mumps):
        """F @A=1:1:3 where A="I" should iterate using variable I."""
        code = """TEST
 S A="I"
 F @A=1:1:3 W I
 Q
"""
        result = execute_mumps(code)
        assert result == "123"

    def test_for_indirect_variable_value_persists(self, execute_mumps):
        """After FOR loop, indirect variable should retain final value."""
        # The QUIT inside the loop exits on first iteration
        # We need to let the loop complete to see final value
        code = """TEST
 S A="I"
 F @A=1:1:3 S X=I
 W I
 Q
"""
        result = execute_mumps(code)
        assert result == "3"

    def test_for_string_list_indirect_variable(self, execute_mumps):
        """F @A="X","Y","Z" where A="V" should iterate using variable V."""
        code = """TEST
 S A="V"
 F @A="X","Y","Z" W V
 Q
"""
        result = execute_mumps(code)
        assert result == "XYZ"

    # T090: FOR with @-expressions in loop bounds
    def test_for_indirect_bounds_start_step_end(self, execute_mumps):
        """F B=@C:@D:@E where C,D,E contain values for start, step, end (I-490)."""
        code = """TEST
 S C="D1",D="D2",E="D3",D1=4,D2=1,D3=6
 F B=@C:@D:@E W B
 Q
"""
        result = execute_mumps(code)
        assert result == "456"

    def test_for_indirect_loop_var_and_bounds(self, execute_mumps):
        """F @A=@C:@D:@E where A is loop var and C,D,E are bounds (I-490)."""
        code = """TEST
 S A="B",C="D1",D="D2",E="D3",D1=7,D2=1,D3=10
 F @A=@C:@D:@E W B
 Q
"""
        result = execute_mumps(code)
        assert result == "78910"

    def test_for_double_level_indirection(self, execute_mumps):
        """F @@A where A="B" and B="C" should iterate using variable C (I-495)."""
        code = """TEST
 S A="B",B="C",C=""
 F @@A=1:1:5 W C
 Q
"""
        result = execute_mumps(code)
        assert result == "12345"

    def test_for_triple_level_indirection(self, execute_mumps):
        """F @@@A where A="B", B="C", C="D" should iterate using D (I-496)."""
        code = """TEST
 S A="B",B="C",C="D",D=9
 F @@@A=1:1:5 W D
 Q
"""
        result = execute_mumps(code)
        assert result == "12345"

    def test_for_indirect_subscripted_loop_var(self, execute_mumps):
        """F @A(@A(2))=... where indirection resolves subscripted variable (I-491).

        Setup: A(2)="A3", A3=4, A(4)="A(22)"
        @A(2) resolves to "A3"
        A(@A(2)) = A("A3") = A(A3) where A3=4 = A(4)
        @A(4) resolves to "A(22)"
        So F @A(@A(2))=4:1:7 iterates A(22) from 4 to 7
        """
        code = """TEST
 K A
 S A(2)="A3",A3=4,A(4)="A(22)"
 F @A(@A(2))=4:1:7 W A(22)
 Q
"""
        result = execute_mumps(code)
        # A(22) gets values 4,5,6,7
        assert result == "4567"

    def test_for_indirect_with_function_in_value(self, execute_mumps):
        """F @A=... where A contains nested @$E() (I-492)."""
        code = """TEST
 S A="@$E(""ABCDEF"",3)",B="@$E(""ABCDEF"",4)",D=4
 F @A=1:1:@B W C
 Q
"""
        result = execute_mumps(code)
        # @A resolves to @$E("ABCDEF",3) which is C
        # @B resolves to @$E("ABCDEF",4) which is D=4
        assert result == "1234"


# =============================================================================
# T069/T086: KILL Indirection Tests
# =============================================================================


@pytest.mark.integration
class TestKillIndirection:
    """Tests for KILL with indirection (K @A).

    T086: Migrated to use unified kill_indirected() via IndirectionResolver.
    """

    def test_kill_indirect_simple_variable(self, execute_mumps):
        """K @A where A="B" should kill variable B."""
        code = """TEST
 S A="B",B=123
 K @A
 W $G(B)
 Q
"""
        result = execute_mumps(code)
        assert result == ""

    def test_kill_indirect_leaves_source(self, execute_mumps):
        """K @A kills target but leaves source A intact."""
        code = """TEST
 S A="B",B=123
 K @A
 W A
 Q
"""
        result = execute_mumps(code)
        assert result == "B"

    def test_kill_multi_level_indirection(self, execute_mumps):
        """K @@A where A="B" and B="C" kills C."""
        code = """TEST
 S A="B",B="C",C=99
 K @@A
 W $G(C)
 Q
"""
        result = execute_mumps(code)
        assert result == ""

    def test_kill_with_subscripts(self, execute_mumps):
        """K @A@(1,2) kills subscripted variable via indirection.

        VV2VNIC pattern: K @B@(2) where B="VV(1)" kills VV(1,2).
        """
        code = """TEST
 S A="B",B(1,2)=99
 K @A@(1,2)
 W $G(B(1,2))
 Q
"""
        result = execute_mumps(code)
        assert result == ""

    def test_kill_global_via_indirection(self, execute_mumps):
        """K @A where A="^G" kills global variable."""
        code = """TEST
 S A="^G",^G=123
 K @A
 W $G(^G)
 Q
"""
        result = execute_mumps(code)
        assert result == ""

    def test_kill_subscripted_global_via_indirection(self, execute_mumps):
        """K @A where A="^G(1,2)" kills subscripted global."""
        code = """TEST
 S A="^G(1,2)",^G(1,2)=99
 K @A
 W $G(^G(1,2))
 Q
"""
        result = execute_mumps(code)
        assert result == ""


# =============================================================================
# T070: NEW Indirection Tests
# =============================================================================


@pytest.mark.integration
class TestNewIndirection:
    """Tests for NEW with indirection (N @A)."""

    def test_new_indirect_simple_variable(self, execute_mumps):
        """N @A where A="B" should NEW variable B."""
        code = """TEST
 S A="B",B=123
 D SUB
 W B,!
 Q
SUB
 N @A
 S B=456
 Q
"""
        result = execute_mumps(code)
        # After returning from SUB, B should be restored to 123
        assert result == "123\n"


# =============================================================================
# T065: Undefined Indirection Source Tests
# =============================================================================


@pytest.mark.integration
class TestUndefinedIndirectionSource:
    """Tests for error handling when indirection source is undefined."""

    def test_undefined_source_in_read(self, execute_mumps):
        """W @UNDEF should produce error with clear message."""
        code = """TEST
 W @UNDEF
 Q
"""
        result = execute_mumps(code)
        # Output should mention the undefined variable
        assert "UNDEF" in result or "undefined" in result.lower()

    def test_undefined_source_in_set(self, execute_mumps):
        """S @UNDEF=1 should produce error.

        Note: YDB produces LVUNDEF error, but m2py may produce VAREXPECTED
        when the undefined variable resolves to empty string and then
        fails variable name validation. Both are acceptable error behaviors.
        """
        code = """TEST
 S @UNDEF=1
 Q
"""
        result = execute_mumps(code)
        # Either UNDEF/undefined error (YDB) or VAREXPECTED (m2py) is acceptable
        assert (
            "UNDEF" in result
            or "undefined" in result.lower()
            or "VAREXPECTED" in result
        )


# =============================================================================
# T066: Invalid Variable Name from Indirection
# =============================================================================


@pytest.mark.integration
class TestInvalidVariableNameIndirection:
    """Tests for invalid variable names produced by indirection."""

    def test_invalid_name_starting_with_number(self, execute_mumps):
        """@A where A="123INVALID" should produce error."""
        code = """TEST
 S A="123INVALID"
 W @A
 Q
"""
        result = execute_mumps(code)
        # Should indicate invalid variable name
        result_lower = result.lower()
        assert "invalid" in result_lower or "error" in result_lower

    def test_empty_variable_name(self, execute_mumps):
        """@A where A="" - m2py produces error for empty variable name.

        Note: YDB may produce empty output, but m2py validates variable names
        and raises an error for empty strings.
        """
        code = """TEST
 S A=""
 W @A
 Q
"""
        result = execute_mumps(code)
        # M2PY produces error for empty variable name (stricter than YDB)
        # Should indicate empty or invalid variable name
        result_lower = result.lower()
        assert (
            "empty" in result_lower
            or "invalid" in result_lower
            or "error" in result_lower
        )

    def test_t052_if_vs_write_empty_indirection(self, execute_mumps):
        """T052: Empty indirection behaves differently in IF vs WRITE.

        This test documents the context-sensitive T052 behavior:
        - IF @A where A="" → TRUE (YDB-specific: successful indirection is truthy)
        - W @A where A="" → error (m2py: empty is invalid variable name)

        This is intentionally different behavior based on command context.
        IF uses treat_empty_as_truthy=True, WRITE does not.
        """
        # IF with empty: should be TRUE
        if_code = """TEST
 S A=""
 I @A W "TRUE" E  W "FALSE"
 Q
"""
        if_result = execute_mumps(if_code)
        assert if_result == "TRUE", "IF @A where A='' should be TRUE (T052)"

        # WRITE with empty: should error
        write_code = """TEST
 S A=""
 W @A
 Q
"""
        write_result = execute_mumps(write_code)
        write_lower = write_result.lower()
        assert (
            "empty" in write_lower or "invalid" in write_lower or "error" in write_lower
        ), "WRITE @A where A='' should produce error"


# =============================================================================
# T091-T093: DO/GOTO Command Indirection Tests
# =============================================================================


@pytest.mark.integration
class TestDoGotoIndirection:
    """Tests for DO and GOTO command indirection (D @A, G @A).

    T091: DO command label indirection
    T092: GOTO command indirection
    T093: V1IDDO, V1IDGO test patterns
    """

    def test_do_simple_label_indirection(self, execute_mumps):
        """D @A where A="LABEL" calls LABEL (I-461 pattern)."""
        code = """TEST
 S A="SUB",R=""
 D @A
 W R
 Q
SUB S R="CALLED" Q
"""
        result = execute_mumps(code)
        assert result == "CALLED"

    def test_do_nested_indirection(self, execute_mumps):
        """D @A where A contains @B resolves nested indirection (I-462 pattern)."""
        code = """TEST
 S L="@L(1)",L(1)="SUB",R=""
 D @L
 W R
 Q
SUB S R="NESTED" Q
"""
        result = execute_mumps(code)
        assert result == "NESTED"

    def test_do_double_indirection(self, execute_mumps):
        """D @@A where A="B", B="LABEL" (I-465 pattern)."""
        code = """TEST
 S A="B",B="SUB",R=""
 D @@A
 W R
 Q
SUB S R="DOUBLE" Q
"""
        result = execute_mumps(code)
        assert result == "DOUBLE"

    def test_goto_simple_label_indirection(self, execute_mumps):
        """G @A where A="LABEL" transfers to LABEL."""
        code = """TEST
 S A="TARGET"
 G @A
 W "WRONG"
 Q
TARGET W "CORRECT" Q
"""
        result = execute_mumps(code)
        assert result == "CORRECT"

    def test_goto_nested_indirection(self, execute_mumps):
        """G @A where A contains nested @ resolves correctly."""
        code = """TEST
 S L="@L(1)",L(1)="TARGET"
 G @L
 W "WRONG"
 Q
TARGET W "NESTED_GOTO" Q
"""
        result = execute_mumps(code)
        assert result == "NESTED_GOTO"

    def test_do_multiple_targets_comma_separated(self, execute_mumps):
        """D @A where A="SUB1,SUB2" calls both subroutines (argument indirection)."""
        code = """TEST
 S A="SUB1,SUB2",R=""
 D @A
 W R
 Q
SUB1 S R=R_"1" Q
SUB2 S R=R_"2" Q
"""
        result = execute_mumps(code)
        assert result == "12"


# =============================================================================
# T091d/T091e: DO Argument Indirection with Fall-Through and GotoExternal
# =============================================================================


@pytest.mark.integration
class TestDoIndirectionFallThrough:
    """Tests for DO argument indirection with fall-through chain (T091e).

    When D @P calls an internal label that doesn't explicitly QUIT but
    falls through to the next label, the fall-through chain must be followed.

    Pattern from V1SEQ test I-792:
    D @P where P="F" and F falls through to G which does external GOTO.
    """

    def test_do_indirect_label_with_fallthrough(self, execute_mumps):
        """D @P where P="F" and F falls through to G (T091e).

        When the called label doesn't QUIT, execution falls through to
        the next label. DO should follow this chain.
        """
        code = """TEST
 S P="F",R=""
 D @P
 W R
 Q
F
 S R=R_"F"
G
 S R=R_"G"
 Q
"""
        result = execute_mumps(code)
        # F falls through to G, so we get "FG"
        assert result == "FG"

    def test_do_indirect_multiple_fallthrough(self, execute_mumps):
        """D @P where P="A" and A→B→C fall-through chain (T091e).

        Multiple fall-throughs in sequence should all be followed.
        """
        code = """TEST
 S P="A",R=""
 D @P
 W R
 Q
A
 S R=R_"A"
B
 S R=R_"B"
C
 S R=R_"C"
 Q
"""
        result = execute_mumps(code)
        # A→B→C fall-through chain
        assert result == "ABC"

    def test_do_indirect_fallthrough_stops_at_quit(self, execute_mumps):
        """Fall-through stops when a label has explicit QUIT (T091e).

        If label B has QUIT, fall-through stops there even if C follows.
        """
        code = """TEST
 S P="A",R=""
 D @P
 W R
 Q
A
 S R=R_"A"
B
 S R=R_"B"
 Q
C
 S R=R_"C"
 Q
"""
        result = execute_mumps(code)
        # A→B, but B has QUIT so C is not reached
        assert result == "AB"

    def test_do_indirect_repeated_calls_with_fallthrough(self, execute_mumps):
        """D @P,@P calls P twice, each following fall-through (T091e).

        Pattern from V1SEQ: D @P,@P,@Q where each call follows fall-through.
        """
        code = """TEST
 S P="F",Q="H",R=""
 D @P,@P,@Q
 W R
 Q
F
 S R=R_"F"
G
 S R=R_"G"
 Q
H
 S R=R_"H"
 Q
"""
        result = execute_mumps(code)
        # D @P (F→G), @P (F→G again), @Q (H) = "FGFGH"
        assert result == "FGFGH"

    def test_do_indirect_with_offset_and_fallthrough(self, execute_mumps):
        """D @P+1 with offset applies offset when calling the label.

        In MUMPS, D @P+N where P="F" resolves to F and then adds offset.
        YDB verified: D @P+1 with P="F" outputs "01" (both lines run).
        """
        code = """TEST
 S P="F",R=""
 D @P+1
 W R
 Q
F
 S R=R_"0"
 S R=R_"1"
 Q
"""
        result = execute_mumps(code)
        # YDB verified output: 01
        assert result == "01"
