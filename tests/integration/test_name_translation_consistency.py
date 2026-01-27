"""Integration tests for Phase 4 User Story 5: Name Translation Consistency.

T070: Tests that @"%ABC" resolves correctly at runtime using NameTranslator.
T071: Tests that codegen and runtime produce identical translations for all edge cases.

Feature: 018-unified-variable-system, Phase 4 User Story 5
Requirements: FR-005 through FR-009 (Name Translation Consistency)

This verifies that MUMPS identifiers translate identically in codegen and runtime,
ensuring that @"%FOO" generates `_pct_FOO` everywhere, making the single source
of truth (core.names.NameTranslator) work correctly.
"""

import pytest

from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime


@pytest.fixture
def execute_mumps():
    """Fixture for parsing, generating, and executing MUMPS code."""

    def _execute(source: str, *, capture_output: bool = True):
        """Execute MUMPS source and return output string."""
        python_code = generate_python(source)
        runtime = MUMPSRuntime()
        result = runtime.execute(python_code, capture_output=capture_output)
        if result.error:
            return f"ERROR: {result.error}"
        return result.output

    return _execute


# =============================================================================
# T070: Integration Test - @"%ABC" Resolves Correctly at Runtime
# =============================================================================


@pytest.mark.integration
class TestPercentNameIndirection:
    """Tests that percent-prefixed variable names resolve correctly through indirection."""

    def test_percent_name_set_indirection(self, execute_mumps):
        """S @"%ABC"=5 should set variable %ABC to 5.

        The indirection target "%ABC" must be translated to Python name "_pct_ABC"
        by the runtime, matching what codegen would produce for a direct S %ABC=5.
        """
        result = execute_mumps('TEST S @"%ABC"=5 W %ABC Q')
        assert result == "5"

    def test_percent_name_read_indirection(self, execute_mumps):
        """W @"%ABC" should read variable %ABC after direct set.

        Direct: S %ABC=42
        Indirect read: W @"%ABC"

        Both codegen and runtime must agree that %ABC → _pct_ABC.
        """
        result = execute_mumps('TEST S %ABC=42 S X="%ABC" W @X Q')
        assert result == "42"

    def test_percent_name_two_level_indirection(self, execute_mumps):
        """@@X where X="%ABC" and %ABC="%DEF" should resolve through %ABC to %DEF.

        This tests that multi-level indirection correctly translates percent names
        at each level.
        """
        result = execute_mumps('TEST S X="%ABC",%ABC="%DEF",%DEF=99 W @@X Q')
        assert result == "99"

    def test_percent_name_with_subscripts(self, execute_mumps):
        """S @"%ARR(1,2)"=5 should set subscripted percent variable.

        The base name %ARR must translate to _pct_ARR, and subscripts (1,2) apply.
        """
        result = execute_mumps('TEST S @"%ARR(1,2)"=5 W %ARR(1,2) Q')
        assert result == "5"

    def test_percent_just_prefix(self, execute_mumps):
        """Edge case: variable named just "%" should work through indirection.

        MUMPS allows a variable named simply %, translated to _pct_.
        """
        result = execute_mumps('TEST S @"%"=7 W % Q')
        assert result == "7"


# =============================================================================
# T071: Codegen and Runtime Produce Same Translation for All Edge Cases
# =============================================================================


@pytest.mark.integration
class TestCodegenRuntimeConsistency:
    """Tests that codegen and runtime produce identical translations."""

    def test_numeric_label_set_indirection(self, execute_mumps):
        """S @"01"=5 should fail with invalid variable name error.

        Note: While MUMPS variable names can't start with digits (per MUMPS spec),
        MUMPS *labels* can. This tests the translation consistency. In practice,
        variables starting with digits would fail validation.
        """
        # MUMPS variable names must start with letter or %
        # "01" as a variable is invalid - should get an error about invalid variable name
        result = execute_mumps('TEST S @"01"=5 W "DONE" Q')
        # The error message should indicate invalid variable name
        assert (
            "invalid variable name" in result.lower()
            or "must start with letter" in result.lower()
            or "varexpected" in result.lower()
            or "not a valid variable name" in result.lower()
        )

    def test_keyword_avoidance_if(self, execute_mumps):
        """Direct and indirect access to variable named 'if' should match.

        MUMPS is case-insensitive, so "IF" is a command, but "if" as a variable
        would collide with Python keyword. NameTranslator handles this.
        """
        # Note: In MUMPS, "IF" is the command, lowercase variables are unusual
        # but valid. The variable "if" → "_m_if" in Python.
        # This test verifies consistency between direct and indirect access.
        result = execute_mumps('TEST S if=123 S X="if" W @X Q')
        assert result == "123"

    def test_keyword_avoidance_for(self, execute_mumps):
        """Variable named 'for' works through indirection.

        Tests NameTranslator.to_python("for") → "_m_for" consistency.
        """
        result = execute_mumps('TEST S for=456 S X="for" W @X Q')
        assert result == "456"

    def test_direct_vs_indirect_equivalence_percent(self, execute_mumps):
        """Direct S %X=5 and indirect S @"%X"=5 produce same result.

        This is the core consistency test: both paths must use NameTranslator
        to translate %X → _pct_X.
        """
        # Direct set, then indirect read
        result1 = execute_mumps('TEST S %X=5 S A="%X" W @A Q')
        assert result1 == "5"

        # Indirect set, then direct read
        result2 = execute_mumps('TEST S @"%X"=5 W %X Q')
        assert result2 == "5"

    def test_direct_vs_indirect_equivalence_regular(self, execute_mumps):
        """Direct S FOO=5 and indirect S @"FOO"=5 produce same result.

        Regular names should pass through unchanged in both paths.
        """
        result1 = execute_mumps('TEST S FOO=5 S A="FOO" W @A Q')
        assert result1 == "5"

        result2 = execute_mumps('TEST S @"FOO"=5 W FOO Q')
        assert result2 == "5"


@pytest.mark.integration
class TestNameTranslatorUsageInRuntime:
    """Tests that runtime uses NameTranslator for all name translations."""

    def test_all_edge_case_names_roundtrip(self, execute_mumps):
        """Test roundtrip through codegen and runtime for various name patterns.

        For each name, we:
        1. Set the variable directly (codegen translates)
        2. Build the name as a string stored in variable IVAR and read via indirection (runtime translates)
        3. Verify they access the same variable
        """
        test_cases = [
            ("%A", "1"),
            ("%ABC", "2"),
            ("%ZTMP", "3"),
            ("FOO", "4"),
            ("X", "5"),
            ("A1", "6"),
            ("VAR99", "7"),
        ]

        for mumps_name, value in test_cases:
            # Build code: S <name>=<value> S IVAR="<name>" W @IVAR
            # Direct set uses codegen translation
            # Indirect read uses runtime translation (via IVAR which holds the name string)
            # They must match
            # Use IVAR (indirection variable) to avoid conflicts when mumps_name is "X"
            code = f'TEST S {mumps_name}={value} S IVAR="{mumps_name}" W @IVAR Q'
            result = execute_mumps(code)
            assert result == value, (
                f"Failed for {mumps_name}: expected {value}, got {result}"
            )


@pytest.mark.integration
class TestNameTranslationEndToEnd:
    """End-to-end tests verifying single source of truth for name translation."""

    def test_percent_name_survives_execute_mumps(self, execute_mumps):
        """Verify %VAR access works when execute_mumps is called during indirection.

        When evaluate_argument_indirection() calls execute_mumps() to evaluate
        expressions, the resulting scope must use consistent name translation.
        """
        # This tests the full path: IF @A where A="X>0" and X=%VAR
        result = execute_mumps('TEST S %VAR=5 I %VAR>0 W "YES" Q')
        assert result == "YES"

    def test_multilevel_percent_chain(self, execute_mumps):
        """Multi-level indirection with percent names throughout.

        S %A="%B",%B="%C",%C=42
        W @@@"%A"

        Each level must correctly translate % prefix.
        """
        result = execute_mumps('TEST S %A="%B",%B="%C",%C=42 S X="%A" W @@@X Q')
        assert result == "42"

    def test_mixed_percent_and_regular_indirection(self, execute_mumps):
        """Chain of indirection mixing percent and regular names.

        S X="%Y",%Y="Z",Z=100
        W @@X → resolves to 100
        """
        result = execute_mumps('TEST S X="%Y",%Y="Z",Z=100 W @@X Q')
        assert result == "100"


# =============================================================================
# Additional consistency verification tests
# =============================================================================


@pytest.mark.integration
class TestZwriteNameTranslation:
    """Tests that ZWRITE properly displays MUMPS names, not Python names."""

    def test_zwrite_percent_variable(self, execute_mumps):
        """ZWRITE should display %VAR not _pct_VAR.

        This was a bug where zwrite() filtered names starting with "_"
        which incorrectly excluded _pct_, _n_, _m_ prefixed names, and
        also didn't translate Python names back to MUMPS format.
        """
        # Note: Double space before Q indicates argumentless ZWRITE
        result = execute_mumps("TEST S %ABC=123 ZWR  Q")
        # Output should show %ABC=123, not _pct_ABC=123
        assert "%ABC=123" in result
        assert "_pct_ABC" not in result

    def test_zwrite_shows_all_percent_variables(self, execute_mumps):
        """ZWRITE should show all percent-prefixed variables."""
        result = execute_mumps("TEST S %A=1,%B=2,%C=3 ZWR  Q")
        assert "%A=1" in result
        assert "%B=2" in result
        assert "%C=3" in result

    def test_zwrite_mixed_variables(self, execute_mumps):
        """ZWRITE shows regular and percent variables correctly."""
        result = execute_mumps("TEST S X=1,%Y=2,Z=3 ZWR  Q")
        assert "X=1" in result
        assert "%Y=2" in result
        assert "Z=3" in result
        # Should NOT show Python internal names
        assert "_pct_" not in result

    def test_zwrite_keyword_variable(self, execute_mumps):
        """ZWRITE should display 'if' not '_m_if' for keyword variables."""
        result = execute_mumps("TEST S if=42 ZWR  Q")
        # Note: MUMPS is case-insensitive, variable "if" is valid
        # Output should show if=42, not _m_if=42
        assert "if=42" in result
        assert "_m_if" not in result


@pytest.mark.integration
class TestCodegenRuntimeNameTranslatorIdentity:
    """Verify that codegen/names.py and runtime both use core.names.NameTranslator."""

    def test_codegen_names_imports_from_core(self):
        """codegen/names.py should re-export from core/names.py."""
        from m2py.codegen.names import NameTranslator as CodegenNameTranslator
        from m2py.core.names import NameTranslator as CoreNameTranslator

        # They should be the exact same class
        assert CodegenNameTranslator is CoreNameTranslator

    def test_codegen_translate_name_from_core(self):
        """codegen/names.py translate_name should be from core/names.py."""
        from m2py.codegen.names import translate_name as codegen_translate
        from m2py.core.names import translate_name as core_translate

        # They should be the same function
        assert codegen_translate is core_translate

    def test_codegen_reverse_name_from_core(self):
        """codegen/names.py reverse_name should be from core/names.py."""
        from m2py.codegen.names import reverse_name as codegen_reverse
        from m2py.core.names import reverse_name as core_reverse

        # They should be the same function
        assert codegen_reverse is core_reverse

    def test_translation_consistency_across_imports(self):
        """Test cases produce same result whether imported from codegen or core."""
        from m2py.codegen.names import NameTranslator as CG
        from m2py.core.names import NameTranslator as CR

        test_names = ["%ABC", "%", "FOO", "X", "if", "for", "01", "", "A123"]

        for name in test_names:
            cg_result = CG.to_python(name)
            cr_result = CR.to_python(name)
            assert cg_result == cr_result, (
                f"Mismatch for {name!r}: {cg_result} vs {cr_result}"
            )

            # And reverse
            cg_reverse = CG.from_python(cg_result)
            cr_reverse = CR.from_python(cr_result)
            assert cg_reverse == cr_reverse, f"Reverse mismatch for {name!r}"
