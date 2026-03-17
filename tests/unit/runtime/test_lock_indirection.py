"""Unit tests for LOCK indirection runtime support.

Spec 021-correctness-features Phase 6 Task T036:
Tests for lock_indirected() runtime method.

LOCK indirection (@X) resolves the indirected name and acquires/releases
the lock instead of silently skipping. Tests cover:
- Basic name resolution for single-level indirection
- Multi-level indirection (@@A where A="B", B="^GLO")
- Timeout with $TEST update
- Incremental lock (+) and unlock (-) forms
- Subscript indirection (@A@(1,2))
"""

from m2py.runtime import MUMPSRuntime, MArray


class TestLockIndirectedErrorHandling:
    """Tests for graceful handling of malformed lock targets."""

    def test_malformed_subscripts_sets_test_true(self):
        """LOCK with unparseable indirected target sets $TEST=1 and returns.

        When ^DD metadata is incomplete, lock targets may resolve to
        malformed strings like '^GLO(1,2' (missing closing paren) that
        _parse_subscripted_name cannot parse.  In single-process mode
        all locks succeed, so the runtime should set $TEST=1 and return.
        """
        rt = MUMPSRuntime()
        rt._test = False
        scope = {"X": MArray("^GLO(1,2")}

        # Should not raise — catches the parse error internally
        rt.lock_indirected("X", scope, lockop="+", timeout=5)

        # $TEST should be set to True (lock success in single-process)
        assert rt._test is True

    def test_empty_subscripts_sets_test_true(self):
        """LOCK with empty subscripts in resolved name sets $TEST=1."""
        rt = MUMPSRuntime()
        rt._test = False
        scope = {"X": MArray("GLO()")}

        rt.lock_indirected("X", scope, lockop="+", timeout=5)

        assert rt._test is True

    def test_malformed_lock_does_not_acquire(self):
        """Malformed lock target should not add anything to lock table."""
        rt = MUMPSRuntime()
        scope = {"X": MArray("^GLO(1,2")}
        initial_locks = set(rt.globals._lock_table.keys())

        rt.lock_indirected("X", scope, lockop="+", timeout=5)

        # No new locks should be acquired
        assert set(rt.globals._lock_table.keys()) == initial_locks

    def test_valid_lock_after_malformed_still_works(self):
        """After a malformed lock, valid locks still work normally."""
        rt = MUMPSRuntime()
        scope = {
            "X": MArray("^GLO(1,2"),
            "Y": MArray("^GOODLOCK"),
        }

        # First: malformed lock (should not raise)
        rt.lock_indirected("X", scope, lockop="+", timeout=5)

        # Second: valid lock (should succeed)
        rt.lock_indirected("Y", scope, lockop="+")
        assert ("GOODLOCK", ()) in rt.globals._lock_table


class TestLockIndirectedBasic:
    """Tests for basic lock indirection resolution."""

    def test_single_level_local_lock(self):
        """L +@X where X="GLO" acquires lock on GLO."""
        rt = MUMPSRuntime()
        scope = {"X": MArray("GLO")}

        # Should resolve X to "GLO" and lock it
        rt.lock_indirected("X", scope, lockop="+")

        # Verify lock was acquired
        assert ("GLO", ()) in rt.globals._lock_table

    def test_single_level_global_lock(self):
        """L +@X where X="^PATIENT(1)" acquires lock on ^PATIENT(1)."""
        rt = MUMPSRuntime()
        scope = {"X": MArray("^PATIENT(1)")}

        rt.lock_indirected("X", scope, lockop="+")

        # Should parse "^PATIENT(1)" and lock PATIENT with subscript 1
        assert ("PATIENT", ("1",)) in rt.globals._lock_table

    def test_single_level_global_subscripted(self):
        """L +@X where X="^GLO(1,2)" acquires lock on ^GLO(1,2)."""
        rt = MUMPSRuntime()
        scope = {"X": MArray("^GLO(1,2)")}

        rt.lock_indirected("X", scope, lockop="+")

        assert ("GLO", ("1", "2")) in rt.globals._lock_table

    def test_unlock_single_level(self):
        """L -@X releases the lock."""
        rt = MUMPSRuntime()
        scope = {"X": MArray("^TEST")}

        # First acquire
        rt.lock_indirected("X", scope, lockop="+")
        assert ("TEST", ()) in rt.globals._lock_table

        # Then release
        rt.lock_indirected("X", scope, lockop="-")
        assert ("TEST", ()) not in rt.globals._lock_table

    def test_exclusive_lock_releases_first(self):
        """L @X (no + or -) releases all then acquires."""
        rt = MUMPSRuntime()
        scope = {"X": MArray("^NEW")}

        # Pre-acquire a different lock
        rt.globals.lock("OLD", (), lock_type="+")
        assert ("OLD", ()) in rt.globals._lock_table

        # Exclusive lock (no +/-) should release all first
        rt.lock_indirected("X", scope, lockop="")

        # OLD should be released, NEW should be acquired
        assert ("OLD", ()) not in rt.globals._lock_table
        assert ("NEW", ()) in rt.globals._lock_table


class TestLockIndirectedMultiLevel:
    """Tests for multi-level indirection (@@A)."""

    def test_two_level_indirection(self):
        """L +@@A where A="B", B="^GLO" locks ^GLO."""
        rt = MUMPSRuntime()
        scope = {
            "A": MArray("B"),
            "B": MArray("^GLO"),
        }

        rt.lock_indirected("A", scope, lockop="+", levels=2)

        assert ("GLO", ()) in rt.globals._lock_table

    def test_three_level_indirection(self):
        """L +@@@A where A="B", B="C", C="^DEEP" locks ^DEEP."""
        rt = MUMPSRuntime()
        scope = {
            "A": MArray("B"),
            "B": MArray("C"),
            "C": MArray("^DEEP"),
        }

        rt.lock_indirected("A", scope, lockop="+", levels=3)

        assert ("DEEP", ()) in rt.globals._lock_table


class TestLockIndirectedTimeout:
    """Tests for lock timeout with $TEST update."""

    def test_lock_timeout_success(self):
        """L +@X:0 sets $TEST=1 on immediate success."""
        rt = MUMPSRuntime()
        rt._test = False  # Reset $TEST
        scope = {"X": MArray("^AVAIL")}

        rt.lock_indirected("X", scope, lockop="+", timeout=0)

        # Lock acquired immediately, $TEST should be 1
        assert rt._test is True
        assert ("AVAIL", ()) in rt.globals._lock_table

    def test_unlock_with_timeout_sets_test(self):
        """L -@X:0 always sets $TEST=1 (unlock never fails)."""
        rt = MUMPSRuntime()
        rt._test = False
        scope = {"X": MArray("^TEST")}

        # Pre-acquire
        rt.globals.lock("TEST", (), lock_type="+")

        # Unlock with timeout
        rt.lock_indirected("X", scope, lockop="-", timeout=0)

        # Unlock always succeeds
        assert rt._test is True

    def test_lock_no_timeout_preserves_test(self):
        """L +@X (no timeout) does NOT modify $TEST."""
        rt = MUMPSRuntime()
        rt._test = False  # Set to False initially
        scope = {"X": MArray("^GLO")}

        rt.lock_indirected("X", scope, lockop="+")

        # $TEST should be unchanged (still False)
        assert rt._test is False


class TestLockIndirectedSubscripts:
    """Tests for subscript indirection @A@(subs)."""

    def test_subscript_indirection_single(self):
        """L +@A@(1) where A="^GLO" locks ^GLO(1)."""
        rt = MUMPSRuntime()
        scope = {"A": MArray("^GLO")}

        rt.lock_indirected("A", scope, lockop="+", per_level_subscripts=[["1"]])

        assert ("GLO", ("1",)) in rt.globals._lock_table

    def test_subscript_indirection_multiple(self):
        """L +@A@(1,2) where A="^GLO" locks ^GLO(1,2)."""
        rt = MUMPSRuntime()
        scope = {"A": MArray("^GLO")}

        rt.lock_indirected("A", scope, lockop="+", per_level_subscripts=[["1", "2"]])

        assert ("GLO", ("1", "2")) in rt.globals._lock_table

    def test_subscript_merges_with_resolved(self):
        """L +@A@(3) where A="^GLO(1,2)" locks ^GLO(1,2,3)."""
        rt = MUMPSRuntime()
        scope = {"A": MArray("^GLO(1,2)")}

        rt.lock_indirected("A", scope, lockop="+", per_level_subscripts=[["3"]])

        assert ("GLO", ("1", "2", "3")) in rt.globals._lock_table


class TestLockIndirectedLocalNames:
    """Tests for local variable lock names (without ^)."""

    def test_local_name_lock(self):
        """L +@X where X="LOCALVAR" locks LOCALVAR."""
        rt = MUMPSRuntime()
        scope = {"X": MArray("LOCALVAR")}

        rt.lock_indirected("X", scope, lockop="+")

        assert ("LOCALVAR", ()) in rt.globals._lock_table

    def test_local_name_with_subscripts(self):
        """L +@X where X="A(1,2)" locks A(1,2)."""
        rt = MUMPSRuntime()
        scope = {"X": MArray("A(1,2)")}

        rt.lock_indirected("X", scope, lockop="+")

        assert ("A", ("1", "2")) in rt.globals._lock_table


class TestLockIndirectedGlobalFromExpression:
    """Tests using global reference in indirection source."""

    def test_global_source_variable(self):
        """L +@^CFG("LOCK") where ^CFG("LOCK")="^DATA" locks ^DATA."""
        rt = MUMPSRuntime()
        scope = {}

        # Set up global value
        rt.globals.set("CFG", ("LOCK",), "^DATA")

        rt.lock_indirected('^CFG("LOCK")', scope, lockop="+")

        assert ("DATA", ()) in rt.globals._lock_table


class TestLockIndirectedPreEvaluated:
    r"""Tests for levels=0 (pre-evaluated LOCK argument strings).

    When MUMPS has LOCK @(expr) where expr is a complex expression
    (e.g., ``"+"_REF_":n"``), the codegen evaluates the expression in
    Python and passes the result string to ``lock_indirected`` with
    ``levels=0``.  The function must parse +/- prefix and :timeout
    suffix directly from the string.
    """

    def test_pre_evaluated_global_simple(self):
        """levels=0 with simple global name acquires lock."""
        rt = MUMPSRuntime()
        scope: dict = {}

        rt.lock_indirected("^MYLOCK", scope, lockop="+", levels=0)

        assert ("MYLOCK", ()) in rt.globals._lock_table

    def test_pre_evaluated_with_subscripts(self):
        r"""levels=0 with subscripted global: ``^DD("IX",123)``."""
        rt = MUMPSRuntime()
        scope: dict = {}

        rt.lock_indirected('^DD("IX",123)', scope, lockop="+", levels=0)

        assert ("DD", ("IX", "123")) in rt.globals._lock_table

    def test_pre_evaluated_plus_prefix(self):
        """levels=0 parses + prefix from the string."""
        rt = MUMPSRuntime()
        scope: dict = {}

        rt.lock_indirected("+^GLOBAL(1)", scope, lockop="", levels=0)

        # + prefix overrides lockop=""
        assert ("GLOBAL", ("1",)) in rt.globals._lock_table

    def test_pre_evaluated_minus_prefix(self):
        """levels=0 parses - prefix and releases the lock."""
        rt = MUMPSRuntime()
        scope: dict = {}

        # Pre-acquire
        rt.globals.lock("GLO", (), lock_type="+")
        assert ("GLO", ()) in rt.globals._lock_table

        # Release via pre-evaluated string
        rt.lock_indirected("-^GLO", scope, lockop="+", levels=0)

        assert ("GLO", ()) not in rt.globals._lock_table

    def test_pre_evaluated_numeric_timeout(self):
        """levels=0 parses :5 numeric timeout and sets $TEST."""
        rt = MUMPSRuntime()
        rt._test = False
        scope: dict = {}

        rt.lock_indirected("+^DATA:5", scope, lockop="+", levels=0)

        # Timed lock sets $TEST
        assert rt._test is True
        assert ("DATA", ()) in rt.globals._lock_table

    def test_pre_evaluated_variable_timeout(self):
        r"""levels=0 parses :VARNAME timeout, looks up variable in scope.

        Simulates LOCK @("+"_REF_":DILOCKTM") where DILOCKTM=3.
        """
        rt = MUMPSRuntime()
        rt._test = False
        scope = {"DILOCKTM": MArray(3)}

        rt.lock_indirected('+^DD("IX",456):DILOCKTM', scope, lockop="+", levels=0)

        # Timeout resolved from DILOCKTM variable (value 3)
        assert rt._test is True
        assert ("DD", ("IX", "456")) in rt.globals._lock_table

    def test_pre_evaluated_colon_inside_subscripts_ignored(self):
        r"""Colons inside quoted subscripts are not treated as timeout.

        ``^DD("a:b",1)`` — the ``:`` in ``"a:b"`` is inside quotes.
        """
        rt = MUMPSRuntime()
        scope: dict = {}

        rt.lock_indirected('^DD("a:b",1)', scope, lockop="+", levels=0)

        assert ("DD", ("a:b", "1")) in rt.globals._lock_table

    def test_pre_evaluated_no_timeout_preserves_test(self):
        """levels=0 without :timeout does NOT modify $TEST."""
        rt = MUMPSRuntime()
        rt._test = False
        scope: dict = {}

        rt.lock_indirected("+^GLO", scope, lockop="+", levels=0)

        # No timeout, $TEST unchanged
        assert rt._test is False

    def test_pre_evaluated_undefined_timeout_var_defaults_zero(self):
        """levels=0 with undefined timeout variable defaults to 0."""
        rt = MUMPSRuntime()
        rt._test = False
        scope: dict = {}  # NOVAR not in scope

        rt.lock_indirected("+^GLO:NOVAR", scope, lockop="+", levels=0)

        # Timeout=0 → immediate success
        assert rt._test is True
        assert ("GLO", ()) in rt.globals._lock_table


class TestParseLockTargetString:
    """Unit tests for _parse_lock_target_string helper."""

    def test_no_prefix_no_timeout(self):
        """Simple global name: no prefix, no timeout."""
        from m2py.runtime import _parse_lock_target_string

        lockop, name, timeout = _parse_lock_target_string("^GLOBAL(1,2)")
        assert lockop is None
        assert name == "^GLOBAL(1,2)"
        assert timeout is None

    def test_plus_prefix(self):
        """+ prefix extracted."""
        from m2py.runtime import _parse_lock_target_string

        lockop, name, timeout = _parse_lock_target_string("+^DD(1)")
        assert lockop == "+"
        assert name == "^DD(1)"
        assert timeout is None

    def test_minus_prefix(self):
        """- prefix extracted."""
        from m2py.runtime import _parse_lock_target_string

        lockop, name, timeout = _parse_lock_target_string("-^GLO")
        assert lockop == "-"
        assert name == "^GLO"
        assert timeout is None

    def test_numeric_timeout(self):
        """Timeout is a number."""
        from m2py.runtime import _parse_lock_target_string

        lockop, name, timeout = _parse_lock_target_string("+^A:5")
        assert lockop == "+"
        assert name == "^A"
        assert timeout == "5"

    def test_variable_timeout(self):
        """Timeout is a variable name."""
        from m2py.runtime import _parse_lock_target_string

        lockop, name, timeout = _parse_lock_target_string('+^DD("IX",123):DILOCKTM')
        assert lockop == "+"
        assert name == '^DD("IX",123)'
        assert timeout == "DILOCKTM"

    def test_colon_inside_quotes_not_timeout(self):
        """Colon inside quoted subscripts is not a timeout separator."""
        from m2py.runtime import _parse_lock_target_string

        lockop, name, timeout = _parse_lock_target_string('^DD("a:b",1)')
        assert lockop is None
        assert name == '^DD("a:b",1)'
        assert timeout is None

    def test_colon_after_subscripts_is_timeout(self):
        """Colon after closing paren is timeout."""
        from m2py.runtime import _parse_lock_target_string

        lockop, name, timeout = _parse_lock_target_string('^DD("IX",1):n')
        assert lockop is None
        assert name == '^DD("IX",1)'
        assert timeout == "n"
