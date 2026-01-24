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

    def test_runtime_global_access(self, execute_mumps):
        """XECUTE can read and write global variables (§8.2.26, §7.3).

        Spec 014 Task E3 (T079): XECUTEd code has full access to globals.
        - Can read globals set before XECUTE
        - Can write new globals
        - Can modify existing globals
        """
        # Test reading a global in XECUTE
        result = execute_mumps('TEST S ^DATA=42 X "W ^DATA" Q')
        assert result.success is True
        assert result.output == "42"

        # Test writing a global in XECUTE
        result = execute_mumps('TEST X "S ^OUT=99" W ^OUT Q')
        assert result.success is True
        assert result.output == "99"

        # Test subscripted global access in XECUTE
        result = execute_mumps('TEST S ^ARR(1,2)=55 X "W ^ARR(1,2)" Q')
        assert result.success is True
        assert result.output == "55"

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
    The code stored in the global is fetched and executed at runtime.

    Implementation approach:
    - Constant keys: X ^%ZOSF("OS") fetches value from global and executes via runtime
    - Dynamic keys: X ^%ZOSF(VAR) generates runtime.execute_mumps() call

    Reference: VistA implementation patterns, §8.2.26
    """

    def test_zosf_constant_key_execution(self, execute_mumps):
        """XECUTE with constant ZOSF key executes stored code (§8.2.26).

        Spec 014 Task E3 (T080): X ^%ZOSF("key") fetches the code from
        the global and executes it. This works via the runtime for all keys.

        X ^%ZOSF("TEST") → _rt.execute_mumps(globals['^%ZOSF']["TEST"], _scope)
        """
        # Set up a ZOSF entry and execute it
        result = execute_mumps('TEST S ^ZOSF("CODE")="W 123,!" X ^ZOSF("CODE") Q')
        assert result.success is True
        assert "123" in result.output

        # Test with code that modifies scope
        result = execute_mumps('TEST S ^ZOSF("SETX")="S X=42" X ^ZOSF("SETX") W X Q')
        assert result.success is True
        assert result.output == "42"

    def test_zosf_dynamic_key_execution(self, execute_mumps):
        """XECUTE with dynamic ZOSF key uses runtime execution (§8.2.26).

        Spec 014 Task E3 (T080): X ^%ZOSF(VAR) generates a runtime call
        that resolves the key at execution time.

        X ^%ZOSF(KEY) → _rt.execute_mumps(_rt.globals.get('ZOSF', (KEY,)), _scope)
        """
        # Dynamic key resolution
        result = execute_mumps(
            'TEST S ^ZOSF("A")="W 1" S ^ZOSF("B")="W 2" S K="A" X ^ZOSF(K) Q'
        )
        assert result.success is True
        assert result.output == "1"

        # Change key and execute again
        result = execute_mumps(
            'TEST S ^ZOSF("A")="W 1" S ^ZOSF("B")="W 2" S K="B" X ^ZOSF(K) Q'
        )
        assert result.success is True
        assert result.output == "2"


@pytest.mark.codegen
class TestXecuteInlineControlFlow:
    """Tests for control flow inside inline XECUTE (T075m, T075n, T075o, T075s).

    When XECUTE contains constant strings that are inlined, control flow
    statements like QUIT, FOR, and GOTO need special handling.
    """

    def test_xecute_quit_exits_xecute_only(self, execute_mumps):
        """QUIT inside inline XECUTE exits just the XECUTE block (T075m).

        X "S X=1 Q S X=2" W X → outputs "1" (QUIT exits XECUTE, not routine)

        QUIT inside XECUTE should exit just that XECUTE argument,
        not return from the enclosing routine.
        """
        result = execute_mumps('TEST S X=0 X "S X=1 Q S X=2" W X,! Q')
        # QUIT exits XECUTE, but routine continues with W X
        assert result.output == "1\n"
        assert result.success is True

    def test_xecute_for_loop_body_works(self, execute_mumps):
        """FOR loop inside inline XECUTE correctly handles body (T075o).

        X "F I=1:1:3 W I" → outputs "123"

        FOR body must be properly structured even when inlined.
        """
        result = execute_mumps('TEST X "F I=1:1:3 W I" W ! Q')
        assert result.output == "123\n"
        assert result.success is True

    def test_xecute_for_with_quit(self, execute_mumps):
        """FOR with QUIT inside inline XECUTE works correctly (T075m, T075o).

        X "F I=1:1:10 W I Q:I>3" → outputs "1234"

        FOR loop with postconditioned QUIT should exit the FOR but
        continue after the XECUTE.
        """
        result = execute_mumps('TEST S R="" X "F I=1:1:10 S R=R_I Q:I>3" W R,! Q')
        # FOR iterates I=1,2,3,4 then QUIT exits the FOR loop
        assert result.output == "1234\n"
        assert result.success is True

    def test_xecute_multiple_args_quit_doesnt_skip(self, execute_mumps):
        """QUIT in one XECUTE arg doesn't skip subsequent args (T075s).

        X "S X=1 Q","S Y=1" → both X and Y are set

        Each XECUTE argument has its own control flow scope.
        QUIT in first argument should not skip second.
        """
        result = execute_mumps('TEST S X=0,Y=0 X "S X=1 Q","S Y=1" W X,Y,! Q')
        # First arg sets X=1 then QUITs, second arg still runs and sets Y=1
        assert result.output == "11\n"
        assert result.success is True

    def test_xecute_if_else_body_works(self, execute_mumps):
        """IF/ELSE inside inline XECUTE correctly handles body (T075o).

        X "I 1=1 W 1 E  W 0" → outputs "1"

        IF/ELSE body must be properly structured even when inlined.
        """
        result = execute_mumps('TEST X "I 1=1 W 1 E  W 0" W ! Q')
        assert result.output == "1\n"
        assert result.success is True

    def test_xecute_nested_for_if(self, execute_mumps):
        """Nested FOR and IF inside inline XECUTE works (T075o).

        X "F I=1:1:3 I I#2 W I" → outputs "13" (odd numbers only)
        """
        result = execute_mumps('TEST X "F I=1:1:5 I I#2 W I" W ! Q')
        # Writes odd numbers: 1, 3, 5
        assert result.output == "135\n"
        assert result.success is True
