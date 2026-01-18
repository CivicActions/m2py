"""Tests for XECUTE command code generation (§8.2.26).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.26
Spec 012 Phase 4: Constant string XECUTE with inline optimization.
Spec 012 Phase 5: Dynamic XECUTE via runtime.execute_mumps().
"""

import pytest

from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime


@pytest.mark.codegen
class TestXecuteCommandCodegen:
    """Codegen-level tests for XECUTE command code generation (§8.2.26)."""

    def test_xecute_dynamic_generates_execute_mumps(self, generate_python):
        """XECUTE dynamic code generates runtime execute_mumps call (§8.2.26).

        Spec 012 Phase 5 (T032-T033): Dynamic XECUTE via runtime.execute_mumps().

        X CODE → _rt.execute_mumps(_scope.get('CODE', ''), _scope)
        """
        code = generate_python('TEST S CODE="S X=1" X CODE Q')
        # Should generate runtime execute_mumps call
        assert "execute_mumps" in code
        assert "_scope.get('CODE'" in code or '_scope.get("CODE"' in code
        assert "_scope)" in code  # Passes _scope to runtime

    def test_xecute_dynamic_multiple_args(self, generate_python):
        """XECUTE with multiple dynamic arguments generates multiple calls.

        Spec 012 Phase 5 (T032): Each dynamic expression gets its own call.

        X A,B → _rt.execute_mumps(A, _scope); _rt.execute_mumps(B, _scope)
        """
        code = generate_python('TEST S A="S X=1",B="S Y=2" X A,B Q')
        # Should have two execute_mumps calls
        assert code.count("execute_mumps") == 2

    def test_xecute_dynamic_with_postcondition(self, generate_python):
        """Dynamic XECUTE with postcondition wraps in if block.

        X:cond CODE → if m_truth(cond): _rt.execute_mumps(CODE, _scope)
        """
        code = generate_python('TEST S P=1,CODE="S X=5" X:P=1 CODE Q')
        assert "if m_truth" in code
        assert "execute_mumps" in code

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
class TestDynamicXecuteScopeAccess:
    """Tests for dynamic XECUTE scope sharing (T034, T036).

    Spec 012 Phase 5: XECUTEd code shares scope with caller.
    - Can read caller's variables
    - Can modify caller's variables
    - New variables set in XECUTE visible to caller
    """

    def test_xecute_reads_outer_scope(self):
        """XECUTEd code can read caller's variables (T034).

        S OUTER=10 X "S INNER=OUTER+1" → INNER=11
        """
        code = generate_python('TEST S OUTER=10 X "S INNER=OUTER+1" Q')

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

        # INNER should be 11 (OUTER+1 = 10+1) - stored as MArray
        assert _scope.get("INNER").value == 11

    def test_xecute_modifies_outer_scope(self):
        """XECUTEd code can modify caller's variables (T036).

        S OUTER=10 X "S OUTER=99" → OUTER=99
        """
        code = generate_python('TEST S OUTER=10 X "S OUTER=99" Q')

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

        # OUTER should be modified to 99 - stored as MArray
        assert _scope.get("OUTER").value == 99

    def test_xecute_with_concatenated_code(self):
        """XECUTE works with runtime-constructed code strings (T036).

        S CODE="S X=" S CODE=CODE_"5" X CODE → X=5
        """
        code = generate_python('TEST S CODE="S X=" S CODE=CODE_"5" X CODE Q')

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

        # X should be 5 (code was "S X=5") - stored as MArray
        assert _scope.get("X").value == 5


@pytest.mark.codegen
class TestMUMPSRuntimeCodegen:
    """Codegen tests for MUMPSRuntime infrastructure.

    The runtime handles dynamic code execution, variable scope, and
    global variable access for indirection and XECUTE.

    Reference: §8.2.26, §7.3
    """

    def test_runtime_execute_mumps_basic(self):
        """Runtime execute_mumps() executes MUMPS code string.

        Spec 012 Phase 5: runtime.execute_mumps() transpiles and runs code.
        """
        _rt = MUMPSRuntime()
        _scope: dict = {}

        _rt.execute_mumps("S X=42", _scope)

        # Variables stored as MArray objects
        assert _scope.get("X").value == 42

    def test_runtime_execute_mumps_scope_read(self):
        """Runtime execute_mumps() can read from shared scope.

        XECUTEd code has access to caller's variables.
        """
        from m2py.runtime import MArray

        _rt = MUMPSRuntime()
        # Pre-populate scope with MArray (as codegen does)
        _scope: dict = {}
        _scope["Y"] = MArray()
        _scope["Y"].value = 10

        _rt.execute_mumps("S X=Y+5", _scope)

        # X should be 15 (Y+5 = 10+5)
        assert _scope.get("X").value == 15

    def test_runtime_execute_mumps_scope_write(self):
        """Runtime execute_mumps() can write to shared scope.

        XECUTEd code modifications persist after return.
        """
        from m2py.runtime import MArray

        _rt = MUMPSRuntime()
        # Pre-populate scope with MArray
        _scope: dict = {}
        _scope["Z"] = MArray()
        _scope["Z"].value = 1

        _rt.execute_mumps("S Z=99", _scope)

        # Z should be modified to 99
        assert _scope.get("Z").value == 99

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: runtime global access")
    def test_runtime_global_access(self, generate_python):
        """Runtime provides global variable access.

        runtime.get_global('^DATA', 1, 2), runtime.set_global(...)
        """
        pytest.fail("Stub - implement test")

    def test_runtime_execute_mumps_test_mutation(self):
        """Runtime execute_mumps() propagates $TEST mutations (T039).

        Spec 012 Phase 6 (T038): XECUTE does NOT stack $TEST.
        $TEST mutations in XECUTEd code are visible via _rt._test.
        """
        _rt = MUMPSRuntime()
        _scope: dict = {}

        # Execute IF that sets $TEST=False (0=1 is false)
        _rt.execute_mumps("I 0=1", _scope)

        # _rt._test should be False
        assert _rt._test is False

        # Execute IF that sets $TEST=True (1=1 is true)
        _rt.execute_mumps("I 1=1", _scope)

        # _rt._test should be True
        assert _rt._test is True

    def test_runtime_execute_mumps_test_in_scope(self):
        """Runtime execute_mumps() stores $TEST in _scope['_test'] (T039).

        The modified $TEST is stored in both _rt._test and _scope['_test'].
        """
        _rt = MUMPSRuntime()
        _scope: dict = {}

        _rt.execute_mumps("I 0=1", _scope)

        assert _scope.get("_test") is False


@pytest.mark.codegen
class TestXecuteTestSemantics:
    """Tests for XECUTE $TEST semantics (T038-T041).

    Spec 012 Phase 6: XECUTE does NOT stack $TEST.
    Unlike argumentless DO which saves/restores $TEST,
    XECUTE mutations to $TEST are visible to caller.
    """

    def test_xecute_dynamic_test_mutation_visible(self):
        """Dynamic XECUTE $TEST mutation visible to caller (T039).

        X CODE where CODE contains IF modifies caller's $TEST.
        """
        code = generate_python('TEST S CODE="I 0=1" I 1=1 X CODE Q')

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

        # After XECUTE "I 0=1", $TEST should be False
        # The module-level _test should be synced from _rt._test
        assert namespace["_test"] is False

    def test_xecute_dynamic_else_sees_modified_test(self):
        """ELSE after dynamic XECUTE sees modified $TEST (T040).

        I 1=1 X "I 0=1" E W "ELSE" → ELSE executes because inner IF set $TEST=0
        """
        code = generate_python('TEST S CODE="I 0=1" I 1=1 X CODE E  W "ELSE" Q')

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

        # ELSE should have executed, writing "ELSE"
        assert _rt._output == ["ELSE"]

    def test_xecute_constant_test_mutation_visible(self):
        """Constant XECUTE $TEST mutation visible to caller (T039).

        X "I 0=1" modifies caller's $TEST (already works via inline).
        """
        code = generate_python('TEST I 1=1 X "I 0=1" Q')

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

        # After inlined "I 0=1", $TEST should be False
        assert namespace["_test"] is False

    def test_xecute_constant_else_sees_modified_test(self):
        """ELSE after constant XECUTE sees modified $TEST (T040).

        I 1=1 X "I 0=1" E W "ELSE" → ELSE executes (already works via inline).
        """
        code = generate_python('TEST I 1=1 X "I 0=1" E  W "ELSE" Q')

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

        # ELSE should have executed, writing "ELSE"
        assert _rt._output == ["ELSE"]


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
