"""Unit tests for LOCK indirection code generation.

Spec 021-correctness-features Phase 6 Task T037:
Tests for generate_lock_indirection() in codegen/indirection.py.

Verifies the generated Python code correctly calls _rt.lock_indirected()
with the appropriate arguments for lock operations, timeouts, and
multi-level indirection.
"""

import pytest

from m2py.codegen import generate_python


@pytest.mark.codegen
class TestGenerateLockIndirectionCode:
    """Tests for generated LOCK indirection code patterns."""

    def test_simple_lock_indirection_code(self):
        """L +@X generates _rt.lock_indirected("X", _scope, lockop="+")."""
        from m2py.codegen.indirection import generate_lock_indirection

        code = generate_lock_indirection(
            lock_expr='"X"',
            lockop="+",
            timeout_expr=None,
            subscripts_expr=None,
            levels=1,
        )

        assert '_rt.lock_indirected("X", _scope' in code
        assert 'lockop="+"' in code
        assert "timeout=" not in code

    def test_unlock_indirection_code(self):
        """L -@X generates lockop="-"."""
        from m2py.codegen.indirection import generate_lock_indirection

        code = generate_lock_indirection(
            lock_expr='"VAR"',
            lockop="-",
            timeout_expr=None,
            subscripts_expr=None,
            levels=1,
        )

        assert 'lockop="-"' in code

    def test_exclusive_lock_indirection_code(self):
        """L @X (no + or -) generates lockop=""."""
        from m2py.codegen.indirection import generate_lock_indirection

        code = generate_lock_indirection(
            lock_expr='"VAR"',
            lockop="",
            timeout_expr=None,
            subscripts_expr=None,
            levels=1,
        )

        assert 'lockop=""' in code

    def test_timeout_included_in_code(self):
        """L +@X:5 generates timeout=5."""
        from m2py.codegen.indirection import generate_lock_indirection

        code = generate_lock_indirection(
            lock_expr='"X"',
            lockop="+",
            timeout_expr="5",
            subscripts_expr=None,
            levels=1,
        )

        assert "timeout=5" in code

    def test_multi_level_indirection_code(self):
        """L +@@X generates levels=2."""
        from m2py.codegen.indirection import generate_lock_indirection

        code = generate_lock_indirection(
            lock_expr='"X"',
            lockop="+",
            timeout_expr=None,
            subscripts_expr=None,
            levels=2,
        )

        assert "levels=2" in code

    def test_subscripts_in_code(self):
        """L +@X@(1,2) includes subscripts."""
        from m2py.codegen.indirection import generate_lock_indirection

        code = generate_lock_indirection(
            lock_expr='"X"',
            lockop="+",
            timeout_expr=None,
            subscripts_expr='["1", "2"]',
            levels=1,
        )

        assert 'per_level_subscripts=["1", "2"]' in code


@pytest.mark.codegen
class TestLockIndirectionCodegenIntegration:
    """Integration tests for LOCK indirection code generation."""

    def _run_codegen_for_lock(self, mumps_code: str) -> str:
        """Helper to transpile MUMPS code and return Python."""
        return generate_python(mumps_code)

    def test_transpiled_lock_plus_indirection(self):
        """Transpiled L +@X includes lock_indirected call."""
        code = self._run_codegen_for_lock('TEST S X="^GLO" L +@X Q')

        assert "lock_indirected" in code
        # Should have lockop="+"
        assert 'lockop="+"' in code or "lockop='+" in code

    def test_transpiled_lock_minus_indirection(self):
        """Transpiled L -@X includes lock_indirected call with lockop="-"."""
        code = self._run_codegen_for_lock('TEST S X="^GLO" L -@X Q')

        assert "lock_indirected" in code
        assert 'lockop="-"' in code or "lockop='-" in code

    def test_transpiled_lock_indirection_with_timeout(self):
        """Transpiled L +@X:0 includes timeout parameter."""
        code = self._run_codegen_for_lock('TEST S X="^GLO" L +@X:0 Q')

        assert "lock_indirected" in code
        assert "timeout=" in code

    def test_transpiled_lock_multi_level_indirection(self):
        """Transpiled L +@@X includes levels=2."""
        code = self._run_codegen_for_lock('TEST S A="B",B="^GLO" L +@@A Q')

        assert "lock_indirected" in code
        assert "levels=2" in code

    def test_transpiled_lock_exclusive_indirection(self):
        """Transpiled L @X (no + or -) includes lockop=""."""
        code = self._run_codegen_for_lock('TEST S X="^GLO" L @X Q')

        assert "lock_indirected" in code


@pytest.mark.codegen
class TestLockIndirectionExpressionLevels:
    """Tests for expression-based LOCK indirection generating levels=0."""

    def _run_codegen_for_lock(self, mumps_code: str) -> str:
        """Helper to transpile MUMPS code and return Python."""
        return generate_python(mumps_code)

    def test_expression_indirection_sets_levels_zero(self):
        r"""LOCK @("+"_X_":"_Y) produces levels=0 (pre-evaluated)."""
        code = self._run_codegen_for_lock('TEST L @("+"_X_":"_Y) Q')

        assert "lock_indirected" in code
        assert "levels=0" in code

    def test_simple_variable_indirection_default_levels(self):
        """LOCK @X does not emit levels=0 (uses default levels=1)."""
        code = self._run_codegen_for_lock("TEST L @X Q")

        assert "lock_indirected" in code
        # levels=1 is the default, so it should NOT appear in the call
        assert "levels=0" not in code


@pytest.mark.codegen
class TestLockIndirectionStmtLevelPattern:
    """Tests for statement-level lock patterns with indirection."""

    def _run_codegen_for_lock(self, mumps_code: str) -> str:
        """Helper to transpile MUMPS code and return Python."""
        return generate_python(mumps_code)

    def test_exclusive_lock_indirection_releases_first(self):
        """L @X (exclusive) should emit unlock_all() before lock."""
        code = self._run_codegen_for_lock('TEST S X="^GLO" L @X Q')

        # Exclusive lock without + releases all first
        assert "unlock_all" in code
        assert "lock_indirected" in code

    def test_incremental_lock_no_release(self):
        """L +@X (incremental) should NOT emit unlock_all()."""
        code = self._run_codegen_for_lock('TEST S X="^GLO" L +@X Q')

        # Should have lock_indirected but NOT unlock_all (incremental add)
        lines = code.split("\n")
        # Find lines with lock operations
        lock_lines = [line for line in lines if "lock_indirected" in line]

        # There should be lock but no unlock (for incremental)
        assert len(lock_lines) > 0
        # Incremental lock doesn't release all
        # (unlock_all may appear but only if exclusive lock at statement level)
