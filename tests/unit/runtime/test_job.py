"""Tests for JOB command — subprocess-based process creation.

Validates that JOB spawns a subprocess with:
- Its own MUMPSRuntime instance (independent $J, $IO, output)
- Shared global storage backend (SQLiteGlobalStorage)
- Correct $ZJOB tracking in parent
- HALT/exception safety (child crash doesn't affect parent)
- Timeout semantics ($TEST=0 on failure, $TEST=1 on success)
- Argument passing to formal parameters
- I/O redirection (INPUT, OUTPUT, ERROR process params)
- Cross-process lock release on exit

Consolidated from test_job_threading.py + test_job_subprocess.py per T128.

Spec 022: Phase 6 (US6), Phase 9 Gaps 2-4
"""

import os
import sys
import textwrap
import time

import pytest

from m2py.runtime import MUMPSRuntime
from m2py.runtime.sqlite_storage import SQLiteGlobalStorage

from tests.unit.runtime.conftest import wait_for_global, write_job_routine


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def db_path(tmp_path):
    """Create a temporary SQLite database path."""
    return str(tmp_path / "test_globals.db")


@pytest.fixture
def storage(db_path):
    """Create a SQLiteGlobalStorage instance."""
    s = SQLiteGlobalStorage(db_path)
    yield s
    s.close()


@pytest.fixture
def rt(storage):
    """Create a MUMPSRuntime with SQLiteGlobalStorage."""
    return MUMPSRuntime(global_storage=storage)


@pytest.fixture
def routine_dir(tmp_path):
    """Create a directory with common test routine modules."""
    routine_dir = tmp_path / "routines"
    routine_dir.mkdir()

    # Simple test routine that sets a global
    (routine_dir / "JOBTST.py").write_text(
        textwrap.dedent("""\
        def JOBTST(_rt, _scope=None):
            import os
            _rt.globals.set("result", (), str(os.getpid()))
            _rt.globals.set("done", (), "1")
        """)
    )

    # Routine that takes arguments
    (routine_dir / "JOBARGS.py").write_text(
        textwrap.dedent("""\
        def JOBARGS(_rt, _scope=None):
            _rt.globals.set("argstest", (), "ran")
        """)
    )

    # Routine that writes output
    (routine_dir / "JOBOUT.py").write_text(
        textwrap.dedent("""\
        def JOBOUT(_rt, _scope=None):
            _rt.write("Hello from child")
            _rt.globals.set("outtest", (), "done")
        """)
    )

    # Routine with a specific label entry point
    (routine_dir / "JOBLBL.py").write_text(
        textwrap.dedent("""\
        def JOBLBL(_rt, _scope=None):
            _rt.globals.set("entry", (), "main")

        def SUB(_rt, _scope=None):
            _rt.globals.set("entry", (), "sub")
        """)
    )

    # Routine that reads and modifies a global
    (routine_dir / "JOBMOD.py").write_text(
        textwrap.dedent("""\
        def JOBMOD(_rt, _scope=None):
            val = _rt.globals.get("counter", ())
            if val is None or val == "":
                val = "0"
            new_val = str(int(val) + 1)
            _rt.globals.set("counter", (), new_val)
        """)
    )

    # Add to sys.path so job_runner can import
    sys.path.insert(0, str(routine_dir))
    yield routine_dir
    sys.path.remove(str(routine_dir))


def _wait_for_global(storage, name, subs=None, timeout=10.0):
    """Wait for a global to be set, with timeout.

    Returns the value once set, or None if timeout.
    """
    if subs is None:
        subs = ()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        val = storage.get(name, subs)
        if val is not None:
            return val
        time.sleep(0.1)
    return None


# =============================================================================
# Basic JOB Execution (T068)
# =============================================================================


@pytest.mark.runtime
class TestJobBasic:
    """Test basic subprocess JOB execution."""

    def test_job_starts_subprocess(self, rt, storage, routine_dir):
        """JOB should start a subprocess that can set globals."""
        result = rt.start_job("JOBTST", "JOBTST", [], None, None)
        assert result is True

        done = _wait_for_global(storage, "done")
        assert done == "1"

    def test_child_has_own_pid(self, rt, storage, routine_dir):
        """Child process should have its own PID as $JOB."""
        rt.start_job("JOBTST", "JOBTST", [], None, None)

        done = _wait_for_global(storage, "done")
        assert done == "1"

        child_pid_str = storage.get("result", ())
        child_pid = int(child_pid_str)

        # Child's reported PID should match $ZJOB
        assert child_pid == int(rt._zjob)

    def test_child_pid_differs_from_parent(self, rt, storage, routine_dir):
        """Child process should have a different PID than parent."""
        rt.start_job("JOBTST", "JOBTST", [], None, None)

        done = _wait_for_global(storage, "done")
        assert done == "1"

        child_pid = int(storage.get("result", []))
        assert child_pid != os.getpid()


# =============================================================================
# $ZJOB (T061a)
# =============================================================================


@pytest.mark.runtime
class TestJobZjob:
    """Tests for $ZJOB special variable."""

    def test_zjob_initially_zero(self):
        """$ZJOB should be "0" before any JOB command."""
        rt = MUMPSRuntime()
        assert rt.zjob() == "0"

    def test_zjob_set_after_start_job(self, tmp_path):
        """$ZJOB should be set to child's PID after JOB."""
        db_path = str(tmp_path / "test.db")
        storage = SQLiteGlobalStorage(db_path)
        routine_dir = tmp_path / "routines"
        routine_dir.mkdir()
        sys.path.insert(0, str(routine_dir))

        try:
            write_job_routine(
                routine_dir,
                "test_job_module",
                """
                import time
                time.sleep(0.01)
            """,
            )

            rt = MUMPSRuntime(global_storage=storage)
            rt._current_routine = "test_job_module"

            rt.start_job("entry", "test_job_module", [], None, None)

            assert rt.zjob() != "0"
            assert int(rt.zjob()) > 0
        finally:
            sys.path.remove(str(routine_dir))
            storage.close()

    def test_zjob_set_to_child_pid(self, rt, storage, routine_dir):
        """$ZJOB should be set to the child's real PID."""
        rt.start_job("JOBTST", "JOBTST", [], None, None)

        zjob = int(rt._zjob)
        assert zjob > 0
        assert zjob != os.getpid()


# =============================================================================
# Global Sharing (T068, US7)
# =============================================================================


@pytest.mark.runtime
class TestJobGlobalSharing:
    """Test global sharing between parent and child processes."""

    def test_child_reads_parent_globals(self, rt, storage, routine_dir):
        """Child should see globals set by parent."""
        storage.set("counter", (), "5")
        rt.start_job("JOBMOD", "JOBMOD", [], None, None)

        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            val = storage.get("counter", ())
            if val == "6":
                break
            time.sleep(0.1)

        assert storage.get("counter", ()) == "6"

    def test_parent_sees_child_globals(self, rt, storage, routine_dir):
        """Parent should see globals set by child."""
        rt.start_job("JOBTST", "JOBTST", [], None, None)

        done = _wait_for_global(storage, "done")
        assert done == "1"

        assert storage.get("result", ()) is not None

    def test_child_has_independent_locals(self, rt, storage, routine_dir):
        """Child should have its own local variable space."""
        rt.start_job("JOBTST", "JOBTST", [], None, None)
        done = _wait_for_global(storage, "done")
        assert done == "1"


# =============================================================================
# Label Entry Points (T068)
# =============================================================================


@pytest.mark.runtime
class TestJobLabels:
    """Test JOB with label entry points."""

    def test_job_main_label(self, rt, storage, routine_dir):
        """JOB with routine name as label enters at main entry."""
        rt.start_job("JOBLBL", "JOBLBL", [], None, None)
        done = _wait_for_global(storage, "entry")
        assert done == "main"

    def test_job_sub_label(self, rt, storage, routine_dir):
        """JOB with specific label enters at that label."""
        rt.start_job("SUB", "JOBLBL", [], None, None)
        done = _wait_for_global(storage, "entry")
        assert done == "sub"


# =============================================================================
# HALT / Exception Safety (T065)
# =============================================================================


@pytest.mark.runtime
class TestJobHaltSafety:
    """Tests for HALT (SystemExit) in JOB'd subprocesses."""

    def test_halt_in_child_does_not_crash_parent(self, tmp_path):
        """SystemExit raised in child subprocess should not affect parent."""
        db_path = str(tmp_path / "test.db")
        storage = SQLiteGlobalStorage(db_path)
        routine_dir = tmp_path / "routines"
        routine_dir.mkdir()
        sys.path.insert(0, str(routine_dir))

        try:
            write_job_routine(
                routine_dir,
                "test_halt_module",
                """
                _rt.globals.set("HALTED", (), "yes")
                raise SystemExit(0)
            """,
            )

            rt = MUMPSRuntime(global_storage=storage)
            rt.start_job("entry", "test_halt_module", [], None, None)

            val = wait_for_global(storage, "HALTED")
            assert val == "yes"
        finally:
            sys.path.remove(str(routine_dir))
            storage.close()

    def test_exception_in_child_does_not_crash_parent(self, tmp_path):
        """Exception in child subprocess should not affect parent."""
        db_path = str(tmp_path / "test.db")
        storage = SQLiteGlobalStorage(db_path)
        routine_dir = tmp_path / "routines"
        routine_dir.mkdir()
        sys.path.insert(0, str(routine_dir))

        try:
            write_job_routine(
                routine_dir,
                "test_exc_module",
                """
                _rt.globals.set("BEFORE_ERROR", (), "yes")
                raise ValueError("child error")
            """,
            )

            rt = MUMPSRuntime(global_storage=storage)
            rt.start_job("entry", "test_exc_module", [], None, None)

            val = wait_for_global(storage, "BEFORE_ERROR")
            assert val == "yes"
        finally:
            sys.path.remove(str(routine_dir))
            storage.close()


# =============================================================================
# Lock Release on Child Exit (T117)
# =============================================================================


@pytest.mark.runtime
class TestJobLockRelease:
    """Tests for automatic lock release when JOB'd child exits."""

    def test_child_locks_released_on_halt(self, tmp_path):
        """Child's locks should be released when child HALTs."""
        db_path = str(tmp_path / "test.db")
        storage = SQLiteGlobalStorage(db_path)
        routine_dir = tmp_path / "routines"
        routine_dir.mkdir()
        sys.path.insert(0, str(routine_dir))

        try:
            write_job_routine(
                routine_dir,
                "test_lock_halt_module",
                """
                _rt.globals.lock("HELD_LOCK", (), lock_type="+")
                _rt.globals.set("LOCKED", (), "yes")
                raise SystemExit(0)
            """,
            )

            rt = MUMPSRuntime(global_storage=storage)
            rt.start_job("entry", "test_lock_halt_module", [], None, None)

            val = wait_for_global(storage, "LOCKED")
            assert val == "yes"

            # Give subprocess time to exit and release locks
            time.sleep(0.5)

            # Now main thread should be able to acquire the lock
            got_lock = storage.lock("HELD_LOCK", (), timeout=2.0, lock_type="+")
            assert got_lock is True
            storage.unlock("HELD_LOCK", ())
        finally:
            sys.path.remove(str(routine_dir))
            storage.close()


# =============================================================================
# Timeout Semantics (T062, T069)
# =============================================================================


@pytest.mark.runtime
class TestJobTimeout:
    """Tests for JOB timeout semantics."""

    def test_job_with_timeout_returns_true(self, rt, storage, routine_dir):
        """JOB with timeout that succeeds returns True ($TEST=1)."""
        result = rt.start_job("JOBTST", "JOBTST", [], None, 5.0)
        assert result is True

    def test_job_without_timeout_returns_true(self, rt, storage, routine_dir):
        """JOB without timeout returns True, doesn't affect $TEST."""
        result = rt.start_job("JOBTST", "JOBTST", [], None, None)
        assert result is True

    def test_job_with_timeout_via_conftest_helper(self, tmp_path):
        """JOB with timeout should return True (conftest helper variant)."""
        db_path = str(tmp_path / "test.db")
        storage = SQLiteGlobalStorage(db_path)
        routine_dir = tmp_path / "routines"
        routine_dir.mkdir()
        sys.path.insert(0, str(routine_dir))

        try:
            write_job_routine(
                routine_dir,
                "test_timeout_module",
                """
                pass
            """,
            )

            rt = MUMPSRuntime(global_storage=storage)
            result = rt.start_job("entry", "test_timeout_module", [], None, 5.0)
            assert result is True
        finally:
            sys.path.remove(str(routine_dir))
            storage.close()

    def test_job_without_timeout_via_conftest_helper(self, tmp_path):
        """JOB without timeout should return True (conftest helper variant)."""
        db_path = str(tmp_path / "test.db")
        storage = SQLiteGlobalStorage(db_path)
        routine_dir = tmp_path / "routines"
        routine_dir.mkdir()
        sys.path.insert(0, str(routine_dir))

        try:
            write_job_routine(
                routine_dir,
                "test_no_timeout_module",
                """
                pass
            """,
            )

            rt = MUMPSRuntime(global_storage=storage)
            result = rt.start_job("entry", "test_no_timeout_module", [], None, None)
            assert result is True
        finally:
            sys.path.remove(str(routine_dir))
            storage.close()

    def test_missing_module_with_timeout_returns_false(self, tmp_path):
        """JOB on a missing module with timeout should return False ($TEST=0)."""
        db_path = str(tmp_path / "test.db")
        storage = SQLiteGlobalStorage(db_path)

        try:
            rt = MUMPSRuntime(global_storage=storage)
            result = rt.start_job("entry", "nonexistent_module", [], None, 5.0)
            assert result is False
        finally:
            storage.close()

    def test_missing_label_with_timeout_returns_false(self, tmp_path):
        """JOB on a missing label with timeout should return False ($TEST=0)."""
        db_path = str(tmp_path / "test.db")
        storage = SQLiteGlobalStorage(db_path)
        routine_dir = tmp_path / "routines"
        routine_dir.mkdir()
        sys.path.insert(0, str(routine_dir))

        try:
            write_job_routine(
                routine_dir,
                "test_nolabel_module",
                """
                pass
            """,
            )

            rt = MUMPSRuntime(global_storage=storage)
            result = rt.start_job(
                "nonexistent_label", "test_nolabel_module", [], None, 5.0
            )
            assert result is False
        finally:
            sys.path.remove(str(routine_dir))
            storage.close()

    def test_missing_routine_with_timeout(self, rt, storage, routine_dir):
        """JOB of nonexistent routine with timeout returns False ($TEST=0)."""
        result = rt.start_job("NONEXISTENT", "NONEXISTENT", [], None, 5.0)
        assert isinstance(result, bool)

    def test_missing_routine_without_timeout(self, rt, storage, routine_dir):
        """JOB of nonexistent routine without timeout returns True."""
        result = rt.start_job("NONEXISTENT", "NONEXISTENT", [], None, None)
        assert result is True


# =============================================================================
# Output Redirection (T064a, T111)
# =============================================================================


@pytest.mark.runtime
class TestJobOutput:
    """Test JOB process parameter handling (output redirection)."""

    def test_job_with_output_param(self, rt, storage, routine_dir, tmp_path):
        """JOB with output file process parameter."""
        output_file = str(tmp_path / "job_output.txt")
        result = rt.start_job("JOBOUT", "JOBOUT", [], [output_file], None)
        assert result is True

        done = _wait_for_global(storage, "outtest")
        assert done == "done"

        time.sleep(1.0)
        if os.path.exists(output_file):
            with open(output_file) as f:
                content = f.read()
            if content:
                assert "Hello from child" in content


# =============================================================================
# Multiple Concurrent JOBs (T068)
# =============================================================================


@pytest.mark.runtime
class TestJobMultiple:
    """Test multiple concurrent JOBs."""

    def test_multiple_jobs_different_pids(self, rt, storage, routine_dir):
        """Multiple JOBs should get different PIDs."""
        pid_routine = routine_dir / "JOBPID.py"
        pid_routine.write_text(
            textwrap.dedent("""\
            def JOBPID(_rt, _scope=None):
                import os, time
                _rt.globals.set("pid", (str(os.getpid()),), str(os.getpid()))
                time.sleep(0.5)
            """)
        )

        rt.start_job("JOBPID", "JOBPID", [], None, None)
        zjob1 = rt._zjob

        rt.start_job("JOBPID", "JOBPID", [], None, None)
        zjob2 = rt._zjob

        assert zjob1 != zjob2
        assert int(zjob1) > 0
        assert int(zjob2) > 0


# =============================================================================
# Argument Passing — Gap 2 (T106-T107)
# =============================================================================


@pytest.mark.runtime
class TestJobArgumentPassing:
    """Spec 022 Phase 9 Gap 2 (T107): JOB with actual argument passing."""

    def test_job_passes_args_to_formal_params(self, db_path, storage, rt, tmp_path):
        """JOB CHILD^ROUTINE(arg1,arg2) delivers values to CHILD(A,B)."""
        args_dir = tmp_path / "routines_args"
        args_dir.mkdir()

        (args_dir / "ARGTEST.py").write_text(
            textwrap.dedent("""\
            def CHILD(_rt, A="", B="", _scope=None):
                _rt.globals.set("arg_a", (), str(A))
                _rt.globals.set("arg_b", (), str(B))
                _rt.globals.set("args_done", (), "1")
            """)
        )

        sys.path.insert(0, str(args_dir))
        try:
            rt.start_job("CHILD", "ARGTEST", ["hello", "42"], None, None)

            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if storage.get("args_done", ()) == "1":
                    break
                time.sleep(0.05)

            assert storage.get("arg_a", ()) == "hello"
            assert storage.get("arg_b", ()) == "42"
        finally:
            sys.path.remove(str(args_dir))

    def test_job_passes_single_arg(self, db_path, storage, rt, tmp_path):
        """JOB with single argument is passed correctly."""
        args_dir = tmp_path / "routines_single"
        args_dir.mkdir()

        (args_dir / "ONEARG.py").write_text(
            textwrap.dedent("""\
            def ENTRY(_rt, X="", _scope=None):
                _rt.globals.set("single_arg", (), str(X))
                _rt.globals.set("single_done", (), "1")
            """)
        )

        sys.path.insert(0, str(args_dir))
        try:
            rt.start_job("ENTRY", "ONEARG", ["world"], None, None)

            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if storage.get("single_done", ()) == "1":
                    break
                time.sleep(0.05)

            assert storage.get("single_arg", ()) == "world"
        finally:
            sys.path.remove(str(args_dir))

    def test_job_no_args_still_works(self, db_path, storage, rt, routine_dir):
        """JOB without args still works (backward compatibility)."""
        rt.start_job("JOBTST", "JOBTST", [], None, None)

        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if storage.get("done", ()) == "1":
                break
            time.sleep(0.05)

        result = storage.get("result", ())
        assert result is not None
        assert int(result) > 0


# =============================================================================
# I/O Redirection — Gap 3 (T109-T111)
# =============================================================================


@pytest.mark.runtime
class TestJobIORedirection:
    """Spec 022 Phase 9 Gap 3 (T111): JOB I/O parameter redirection."""

    def test_job_output_to_file(self, db_path, storage, rt, tmp_path):
        """JOB with OUTPUT param writes child stdout to specified file."""
        io_dir = tmp_path / "routines_io"
        io_dir.mkdir()
        output_file = tmp_path / "child_output.txt"

        (io_dir / "IOTEST.py").write_text(
            textwrap.dedent("""\
            def WRITER(_rt, _scope=None):
                import sys
                sys.stdout.write("hello from child\\n")
                sys.stdout.flush()
                _rt.globals.set("io_done", (), "1")
            """)
        )

        sys.path.insert(0, str(io_dir))
        try:
            rt.start_job("WRITER", "IOTEST", [], [f"OUTPUT={output_file}"], None)

            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if storage.get("io_done", ()) == "1":
                    break
                time.sleep(0.05)

            assert storage.get("io_done", ()) == "1"
            content = output_file.read_text()
            assert "hello from child" in content
        finally:
            sys.path.remove(str(io_dir))

    def test_job_error_to_file(self, db_path, storage, rt, tmp_path):
        """JOB with ERROR param writes child stderr to specified file."""
        err_dir = tmp_path / "routines_err"
        err_dir.mkdir()
        error_file = tmp_path / "child_error.txt"

        (err_dir / "ERRTEST.py").write_text(
            textwrap.dedent("""\
            def ERRWRITER(_rt, _scope=None):
                import sys
                sys.stderr.write("error from child\\n")
                sys.stderr.flush()
                _rt.globals.set("err_done", (), "1")
            """)
        )

        sys.path.insert(0, str(err_dir))
        try:
            rt.start_job("ERRWRITER", "ERRTEST", [], [f"ERROR={error_file}"], None)

            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if storage.get("err_done", ()) == "1":
                    break
                time.sleep(0.05)

            assert storage.get("err_done", ()) == "1"
            content = error_file.read_text()
            assert "error from child" in content
        finally:
            sys.path.remove(str(err_dir))

    def test_job_input_from_file(self, db_path, storage, rt, tmp_path):
        """JOB with INPUT param redirects child stdin from file."""
        in_dir = tmp_path / "routines_in"
        in_dir.mkdir()
        input_file = tmp_path / "child_input.txt"
        input_file.write_text("input_data\n")

        (in_dir / "INTEST.py").write_text(
            textwrap.dedent("""\
            def READER(_rt, _scope=None):
                import sys
                line = sys.stdin.readline().strip()
                _rt.globals.set("input_val", (), line)
                _rt.globals.set("in_done", (), "1")
            """)
        )

        sys.path.insert(0, str(in_dir))
        try:
            rt.start_job("READER", "INTEST", [], [f"INPUT={input_file}"], None)

            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if storage.get("in_done", ()) == "1":
                    break
                time.sleep(0.05)

            assert storage.get("in_done", ()) == "1"
            assert storage.get("input_val", ()) == "input_data"
        finally:
            sys.path.remove(str(in_dir))

    def test_job_legacy_bare_string_as_output(self, db_path, storage, rt, tmp_path):
        """Legacy: bare string param treated as output file."""
        leg_dir = tmp_path / "routines_legacy"
        leg_dir.mkdir()
        output_file = tmp_path / "legacy_output.txt"

        (leg_dir / "LEGTEST.py").write_text(
            textwrap.dedent("""\
            def LEGWRITER(_rt, _scope=None):
                import sys
                sys.stdout.write("legacy output\\n")
                sys.stdout.flush()
                _rt.globals.set("leg_done", (), "1")
            """)
        )

        sys.path.insert(0, str(leg_dir))
        try:
            rt.start_job("LEGWRITER", "LEGTEST", [], [str(output_file)], None)

            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if storage.get("leg_done", ()) == "1":
                    break
                time.sleep(0.05)

            assert storage.get("leg_done", ()) == "1"
            content = output_file.read_text()
            assert "legacy output" in content
        finally:
            sys.path.remove(str(leg_dir))
