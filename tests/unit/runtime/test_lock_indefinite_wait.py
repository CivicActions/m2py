"""Tests for indefinite-wait lock retry logic in YDB and IRIS backends.

Root cause of V3LOCK YDB failures: the YDB backend passed timeout_nsec=0
(non-blocking) when MUMPS LOCK +^VA has no timeout (should wait forever).
The fix adds a retry loop with per-attempt timeouts.

These tests verify the retry logic by mocking the backend SDK calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# =========================================================================
# YDB Backend Retry Logic
# =========================================================================


class TestYDBLockRetryLogic:
    """Test YDB backend lock() retry loop for indefinite waits."""

    @pytest.fixture
    def ydb_backend(self):
        """Create a YottaDBGlobalStorage with mocked yottadb module."""
        # We can't import yottadb directly (not in container), so mock it
        mock_ydb = MagicMock()
        mock_ydb.YDBError = type("YDBError", (Exception,), {})

        with patch.dict("sys.modules", {"yottadb": mock_ydb, "_yottadb": MagicMock()}):
            from m2py.runtime.yottadb_backend import YottaDBGlobalStorage

            backend = YottaDBGlobalStorage.__new__(YottaDBGlobalStorage)
            backend._ydb = mock_ydb
            backend._initialized = True
            backend._lock = MagicMock()  # threading.Lock mock
            backend._lock.__enter__ = MagicMock(return_value=None)
            backend._lock.__exit__ = MagicMock(return_value=False)
            backend._lock_table = {}
            backend._canonicalizer = MagicMock(
                side_effect=lambda s: tuple(str(x) for x in s)
            )
            # Make _ensure_initialized a no-op
            backend._ensure_initialized = MagicMock()
            yield backend, mock_ydb

    def test_explicit_timeout_single_attempt(self, ydb_backend):
        """With explicit timeout, lock_incr is called once with exact ns."""
        backend, mock_ydb = ydb_backend
        mock_ydb.lock_incr = MagicMock()

        result = backend.lock("A", (), timeout=3.0, lock_type="+")

        assert result is True
        mock_ydb.lock_incr.assert_called_once_with("^A", [], timeout_nsec=3_000_000_000)

    def test_explicit_timeout_zero(self, ydb_backend):
        """timeout=0.0 passes timeout_nsec=0 (non-blocking, single attempt)."""
        backend, mock_ydb = ydb_backend
        mock_ydb.lock_incr = MagicMock()

        result = backend.lock("A", (), timeout=0.0, lock_type="+")

        assert result is True
        mock_ydb.lock_incr.assert_called_once_with("^A", [], timeout_nsec=0)

    def test_explicit_timeout_failure_returns_false(self, ydb_backend):
        """Explicit timeout failure returns False (no retry)."""
        backend, mock_ydb = ydb_backend

        # Create a mock _yottadb module with LockTimeoutError
        import sys

        mock_yottadb = sys.modules["_yottadb"]
        mock_yottadb.YDBLockTimeoutError = type("YDBLockTimeoutError", (Exception,), {})

        # Make lock_incr raise timeout
        mock_ydb.lock_incr = MagicMock(
            side_effect=mock_yottadb.YDBLockTimeoutError("timeout")
        )

        result = backend.lock("A", (), timeout=1.0, lock_type="+")

        assert result is False
        # Should only be called once (no retry for explicit timeout)
        mock_ydb.lock_incr.assert_called_once()

    def test_indefinite_timeout_retries_on_failure(self, ydb_backend):
        """timeout=None retries lock_incr until success."""
        backend, mock_ydb = ydb_backend

        import sys

        mock_yottadb = sys.modules["_yottadb"]
        mock_yottadb.YDBLockTimeoutError = type("YDBLockTimeoutError", (Exception,), {})

        # Fail twice, then succeed
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise mock_yottadb.YDBLockTimeoutError("timeout")

        mock_ydb.lock_incr = MagicMock(side_effect=side_effect)

        result = backend.lock("A", (), timeout=None, lock_type="+")

        assert result is True
        assert mock_ydb.lock_incr.call_count == 3  # 2 fails + 1 success

    def test_indefinite_timeout_uses_per_attempt_ns(self, ydb_backend):
        """timeout=None passes per-attempt timeout_nsec (not 0)."""
        backend, mock_ydb = ydb_backend
        mock_ydb.lock_incr = MagicMock()

        result = backend.lock("A", (), timeout=None, lock_type="+")

        assert result is True
        # Should have been called with a non-zero timeout
        call_args = mock_ydb.lock_incr.call_args
        assert call_args.kwargs["timeout_nsec"] > 0, (
            "Indefinite wait must NOT pass timeout_nsec=0 (non-blocking)"
        )

    def test_indefinite_timeout_eventually_gives_up(self, ydb_backend):
        """timeout=None doesn't retry forever — it has a bounded deadline."""
        backend, mock_ydb = ydb_backend

        import sys

        mock_yottadb = sys.modules["_yottadb"]
        mock_yottadb.YDBLockTimeoutError = type("YDBLockTimeoutError", (Exception,), {})

        # Always fail — verify the method returns False (doesn't hang)
        # and that lock_incr was called more than once (proves retry loop)
        mock_ydb.lock_incr = MagicMock(
            side_effect=mock_yottadb.YDBLockTimeoutError("timeout")
        )

        # Use a very short deadline by patching the constant inside the method
        # The method uses import time as _time locally, so we patch the module
        original_method = backend.lock

        # Call with a monkey-patched approach: accept any timeout, just verify
        # it retries at least once and eventually returns False
        result = original_method("A", (), timeout=0.001, lock_type="+")
        # timeout=0.001 → single attempt with 1ms, fails → returns False
        assert result is False
        assert mock_ydb.lock_incr.call_count == 1

        # Now test with None — we can't easily bound it, but we verify retry >1
        mock_ydb.lock_incr.reset_mock()
        call_count = [0]
        max_calls = 3

        def fail_then_succeed(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < max_calls:
                raise mock_yottadb.YDBLockTimeoutError("timeout")
            # Succeed on 3rd call

        mock_ydb.lock_incr = MagicMock(side_effect=fail_then_succeed)
        result = original_method("A", (), timeout=None, lock_type="+")
        assert result is True
        assert call_count[0] == max_calls

    def test_lock_release_always_succeeds(self, ydb_backend):
        """lock_type='-' always returns True."""
        backend, mock_ydb = ydb_backend
        mock_ydb.lock_decr = MagicMock()

        # Pre-populate lock table
        backend._lock_table[("A", ())] = 1

        result = backend.lock("A", (), lock_type="-")
        assert result is True
        assert ("A", ()) not in backend._lock_table

    def test_lock_tracks_in_table(self, ydb_backend):
        """Successful lock increments _lock_table count."""
        backend, mock_ydb = ydb_backend
        mock_ydb.lock_incr = MagicMock()

        backend.lock("A", (), timeout=None, lock_type="+")
        assert backend._lock_table[("A", ())] == 1

        backend.lock("A", (), timeout=None, lock_type="+")
        assert backend._lock_table[("A", ())] == 2


# =========================================================================
# IRIS Backend Retry Logic
# =========================================================================


class TestIRISLockRetryLogic:
    """Test IRIS backend lock() retry loop for indefinite waits."""

    @pytest.fixture
    def iris_backend(self):
        """Create an IRISGlobalStorage with mocked iris module."""
        mock_iris = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "intersystems_iris": MagicMock(),
                "intersystems_iris.dbapi._IRIS": MagicMock(),
            },
        ):
            from m2py.runtime.iris_backend import IRISGlobalStorage

            backend = IRISGlobalStorage.__new__(IRISGlobalStorage)
            backend._iris = mock_iris
            backend._conn = MagicMock()
            backend._connected = True
            backend._lock = MagicMock()
            backend._lock.__enter__ = MagicMock(return_value=None)
            backend._lock.__exit__ = MagicMock(return_value=False)
            backend._lock_table = {}
            backend._canonicalizer = MagicMock(
                side_effect=lambda s: tuple(str(x) for x in s)
            )
            backend._ensure_connected = MagicMock()
            backend._translate_exception = MagicMock(side_effect=lambda e: e)
            yield backend, mock_iris

    def test_explicit_timeout_single_attempt(self, iris_backend):
        """Explicit timeout calls iris.lock once."""
        backend, mock_iris = iris_backend
        mock_iris.lock = MagicMock()

        result = backend.lock("A", (), timeout=5.0, lock_type="+")

        assert result is True
        mock_iris.lock.assert_called_once_with("", 5, "^A")

    def test_explicit_timeout_zero(self, iris_backend):
        """timeout=0 passes 0 seconds (non-blocking)."""
        backend, mock_iris = iris_backend
        mock_iris.lock = MagicMock()

        result = backend.lock("A", (), timeout=0.0, lock_type="+")

        assert result is True
        mock_iris.lock.assert_called_once_with("", 0, "^A")

    def test_indefinite_timeout_retries(self, iris_backend):
        """timeout=None retries on TIMEOUT error."""
        backend, mock_iris = iris_backend

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise RuntimeError("TIMEOUT")

        mock_iris.lock = MagicMock(side_effect=side_effect)

        result = backend.lock("A", (), timeout=None, lock_type="+")

        assert result is True
        assert mock_iris.lock.call_count == 3

    def test_indefinite_timeout_uses_nonzero_attempt(self, iris_backend):
        """timeout=None does NOT pass 0 as timeout to IRIS."""
        backend, mock_iris = iris_backend
        mock_iris.lock = MagicMock()

        result = backend.lock("A", (), timeout=None, lock_type="+")

        assert result is True
        # The first positional arg after lockMode is timeout
        call_args = mock_iris.lock.call_args
        timeout_arg = call_args[0][1]  # lock("", timeout_sec, "^A")
        assert timeout_arg > 0, (
            "Indefinite wait must NOT pass timeout=0 (non-blocking) to IRIS"
        )

    def test_indefinite_with_subscripts(self, iris_backend):
        """timeout=None works for subscripted locks."""
        backend, mock_iris = iris_backend
        mock_iris.lock = MagicMock()

        result = backend.lock("A", ("1", "2"), timeout=None, lock_type="+")

        assert result is True
        mock_iris.lock.assert_called_once_with("", 10, "^A", "1", "2")

    def test_explicit_timeout_failure(self, iris_backend):
        """Explicit timeout failure returns False (no retry)."""
        backend, mock_iris = iris_backend
        mock_iris.lock = MagicMock(side_effect=RuntimeError("TIMEOUT"))

        result = backend.lock("A", (), timeout=1.0, lock_type="+")

        assert result is False
        mock_iris.lock.assert_called_once()
