"""Tests for XECUTE command code generation (§8.2.26).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.26
Spec 012 Phase 4: Constant string XECUTE with inline optimization.
"""

import pytest

from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime


@pytest.mark.codegen
class TestXecuteCommandCodegen:
    """Codegen-level tests for XECUTE command code generation (§8.2.26)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Phase 5: Dynamic XECUTE not yet implemented")
    def test_xecute_to_exec(self, generate_python):
        """XECUTE generates dynamic code execution (§8.2.26).

        Phase 5 (T032-T038): Dynamic XECUTE via runtime.execute_mumps().
        """
        pytest.fail("Stub - implement in Phase 5")

    def test_xecute_static_optimization(self, generate_python):
        """XECUTE literal string is statically inlined (§8.2.26).

        Spec 012 Phase 4 (T024): Constant strings are parsed at transpile
        time and inlined for efficiency.

        X "S X=1" → _scope.setdefault('X', MArray()).value = 1
        """
        code = generate_python('TEST X "S X=1" Q')
        # Should generate inline assignment, not runtime.execute call
        assert "_scope.setdefault('X', MArray()).value = 1" in code
        assert "execute" not in code.lower()

    def test_xecute_constant_write(self, generate_python):
        """XECUTE with WRITE command inside string literal.

        X "W 42" → _rt.write(42)
        """
        code = generate_python('TEST X "W 42" Q')
        assert "_rt.write(42)" in code

    def test_xecute_multiple_args_constant(self, generate_python):
        """XECUTE with multiple constant string arguments.

        Spec 012 Phase 4 (T026): Multiple constant strings are each
        parsed and inlined in order.

        X "S A=1","S B=2" → _scope.setdefault('A', MArray()).value = 1; ...
        """
        code = generate_python('TEST X "S A=1","S B=2" Q')
        assert "_scope.setdefault('A', MArray()).value = 1" in code
        assert "_scope.setdefault('B', MArray()).value = 2" in code
        # Verify order: A before B
        a_pos = code.index("_scope.setdefault('A', MArray()).value = 1")
        b_pos = code.index("_scope.setdefault('B', MArray()).value = 2")
        assert a_pos < b_pos

    def test_xecute_postcondition_true(self, generate_python):
        """XECUTE with postcondition generates conditional block.

        Spec 012 Phase 4 (T027): Postcondition wraps code in if block.

        X:cond "S X=1" → if m_truth(cond): _scope.setdefault('X', MArray()).value = 1
        """
        code = generate_python('TEST S P=1 X:P=1 "S X=5" Q')
        # Should have if statement with condition
        assert "if m_truth" in code
        # Should have inline assignment inside if block
        assert "_scope.setdefault('X', MArray()).value = 5" in code

    def test_xecute_postcondition_runtime(self):
        """XECUTE postcondition evaluated at runtime.

        When P=0, X:P=1 "code" should not execute.
        """
        code = generate_python('TEST S P=0 X:P=1 "S X=5" Q')

        _rt = MUMPSRuntime()
        _scope: dict = {}
        namespace = {
            "_rt": _rt,
            "_scope": _scope,
            "m_truth": __import__("m2py.codegen.helpers", fromlist=["m_truth"]).m_truth,
            "m_compare": __import__(
                "m2py.codegen.helpers", fromlist=["m_compare"]
            ).m_compare,
            "m_num": __import__("m2py.codegen.helpers", fromlist=["m_num"]).m_num,
        }
        exec(code, namespace)
        namespace["TEST"](_rt, _scope=_scope)

        # X should NOT be set since P=0 fails postcondition
        assert "X" not in _scope

    def test_xecute_empty_string(self, generate_python):
        """XECUTE with empty string is a no-op.

        X "" should not generate any statements.
        """
        code = generate_python('TEST X "" Q')
        # Empty string XECUTE should just produce a valid function
        # that returns immediately (besides the return statement)
        assert "def TEST" in code
        assert "return" in code


@pytest.mark.codegen
class TestMUMPSRuntimeCodegen:
    """Codegen tests for MUMPSRuntime infrastructure.

    The runtime handles dynamic code execution, variable scope, and
    global variable access for indirection and XECUTE.

    Reference: §8.2.26, §7.3
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: runtime execute method")
    def test_runtime_execute_method(self, generate_python):
        """Runtime provides execute() for dynamic MUMPS code.

        runtime.execute('S X=1') translates and runs at runtime.
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: runtime variable access")
    def test_runtime_variable_access(self, generate_python):
        """Runtime provides dynamic variable get/set.

        runtime.get_var(name), runtime.set_var(name, value)
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: runtime global access")
    def test_runtime_global_access(self, generate_python):
        """Runtime provides global variable access.

        runtime.get_global('^DATA', 1, 2), runtime.set_global(...)
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: runtime test tracking")
    def test_runtime_test_tracking(self, generate_python):
        """Runtime tracks $TEST across execute() calls.

        $TEST state visible to and from dynamically executed code.
        """
        pytest.fail("Stub - implement test")


@pytest.mark.codegen
class TestZosfPatternCodegen:
    """Codegen tests for ^%ZOSF pattern handling.

    VistA commonly uses X ^%ZOSF("code") for platform-specific operations.
    Known patterns can be translated to direct Python calls.

    Reference: VistA implementation patterns
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: zosf lookup table")
    def test_zosf_lookup_table(self, generate_python):
        """Known ^%ZOSF patterns use lookup table.

        X ^%ZOSF("TEST") generates: _zosf_test()
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: zosf fallback to runtime")
    def test_zosf_fallback_to_runtime(self, generate_python):
        """Unknown ^%ZOSF patterns fall back to runtime.

        X ^%ZOSF(DYNAMIC) generates: runtime.execute(globals['^%ZOSF'][DYNAMIC])
        """
        pytest.fail("Stub - implement test")
