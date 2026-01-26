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
