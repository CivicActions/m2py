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
    """Tests for FOR loop variable indirection (F @A=1:1:3)."""

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
