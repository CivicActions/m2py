"""Unit tests for TSTART restart variable snapshots (Spec 021 Phase 8).

Tests for:
- T048: snapshot_locals() — named vars, all vars (*), undefined var handling
- T049: discard_local_snapshot() — TCOMMIT and TROLLBACK both discard
- T050: Nested transaction snapshots — inner TROLLBACK discards inner only
"""

import pytest

from m2py.runtime import MArray, MUMPSRuntime


@pytest.mark.codegen
class TestSnapshotLocals:
    """T048: Tests for snapshot_locals() method."""

    def test_snapshot_named_vars(self):
        """Named variables are deep-copied into snapshot."""
        rt = MUMPSRuntime()
        scope = {
            "X": MArray(value="1"),
            "Y": MArray(value="2"),
            "Z": MArray(value="3"),
        }
        rt.snapshot_locals(scope, var_names=["X", "Y"])
        assert len(rt._transaction_snapshots) == 1
        snap = rt._transaction_snapshots[0]
        assert "X" in snap.snapshot
        assert "Y" in snap.snapshot
        assert "Z" not in snap.snapshot
        assert snap.snapshot["X"].value == "1"
        assert snap.snapshot["Y"].value == "2"

    def test_snapshot_all_vars(self):
        """TSTART * snapshots all local variables."""
        rt = MUMPSRuntime()
        scope = {
            "X": MArray(value="1"),
            "Y": MArray(value="2"),
        }
        rt.snapshot_locals(scope, all_vars=True)
        assert len(rt._transaction_snapshots) == 1
        snap = rt._transaction_snapshots[0]
        assert snap.restart_all is True
        assert "X" in snap.snapshot
        assert "Y" in snap.snapshot

    def test_snapshot_deep_copies(self):
        """Snapshot contains deep copies, not references."""
        rt = MUMPSRuntime()
        arr = MArray(value="original")
        scope = {"X": arr}
        rt.snapshot_locals(scope, var_names=["X"])
        # Mutate original
        arr.value = "modified"
        # Snapshot should have original value
        assert rt._transaction_snapshots[0].snapshot["X"].value == "original"

    def test_snapshot_undefined_var_not_recorded(self):
        """Undefined variable at TSTART time is not recorded in snapshot."""
        rt = MUMPSRuntime()
        scope = {"X": MArray(value="1")}
        rt.snapshot_locals(scope, var_names=["X", "UNDEF"])
        snap = rt._transaction_snapshots[0]
        assert "X" in snap.snapshot
        # UNDEF was not in scope, so not in snapshot
        assert "UNDEF" not in snap.snapshot

    def test_snapshot_saves_test_value(self):
        """$TEST value is saved in snapshot."""
        rt = MUMPSRuntime()
        rt._test = True
        scope = {"X": MArray(value="1")}
        rt.snapshot_locals(scope, var_names=["X"])
        assert rt._transaction_snapshots[0].saved_test is True

    def test_snapshot_no_restart_vars(self):
        """TSTART with no restart vars creates empty snapshot."""
        rt = MUMPSRuntime()
        scope = {"X": MArray(value="1")}
        rt.snapshot_locals(scope)
        assert len(rt._transaction_snapshots) == 1
        snap = rt._transaction_snapshots[0]
        assert snap.restart_vars is None
        assert snap.restart_all is False
        assert len(snap.snapshot) == 0

    def test_snapshot_subscripted_array(self):
        """Subscripted arrays are deep-copied into snapshot."""
        rt = MUMPSRuntime()
        arr = MArray(value="root")
        arr["1"] = "sub1"
        arr["2"] = "sub2"
        scope = {"X": arr}
        rt.snapshot_locals(scope, var_names=["X"])
        snap_arr = rt._transaction_snapshots[0].snapshot["X"]
        assert snap_arr.value == "root"
        assert snap_arr["1"].value == "sub1"
        # Verify deep copy — mutating original doesn't affect snapshot
        arr["1"]._value = "changed"
        assert snap_arr["1"].value == "sub1"


@pytest.mark.codegen
class TestDiscardLocalSnapshot:
    """T049: Tests for discard_local_snapshot()."""

    def test_discard_removes_latest(self):
        """discard_local_snapshot() removes the most recent snapshot."""
        rt = MUMPSRuntime()
        scope = {"X": MArray(value="1")}
        rt.snapshot_locals(scope, var_names=["X"])
        rt.snapshot_locals(scope, var_names=["X"])
        assert len(rt._transaction_snapshots) == 2
        rt.discard_local_snapshot()
        assert len(rt._transaction_snapshots) == 1

    def test_discard_on_empty_is_noop(self):
        """discard_local_snapshot() is a no-op when no snapshots exist."""
        rt = MUMPSRuntime()
        rt.discard_local_snapshot()  # Should not raise
        assert len(rt._transaction_snapshots) == 0

    def test_discard_all_snapshots(self):
        """discard_all_local_snapshots() clears all snapshots."""
        rt = MUMPSRuntime()
        scope = {"X": MArray(value="1")}
        rt.snapshot_locals(scope, var_names=["X"])
        rt.snapshot_locals(scope, var_names=["X"])
        rt.snapshot_locals(scope, var_names=["X"])
        assert len(rt._transaction_snapshots) == 3
        rt.discard_all_local_snapshots()
        assert len(rt._transaction_snapshots) == 0

    def test_tcommit_does_not_restore_locals(self):
        """TCOMMIT (discard) should NOT restore local variable values."""
        rt = MUMPSRuntime()
        scope = {"X": MArray(value="1")}
        rt.snapshot_locals(scope, var_names=["X"])
        # Modify local after TSTART
        scope["X"].value = "99"
        # TCOMMIT — discard snapshot
        rt.discard_local_snapshot()
        # Local should still have modified value
        assert scope["X"].value == "99"

    def test_trollback_does_not_restore_locals(self):
        """TROLLBACK (discard all) should NOT restore local variable values."""
        rt = MUMPSRuntime()
        scope = {"X": MArray(value="1")}
        rt.snapshot_locals(scope, var_names=["X"])
        scope["X"].value = "99"
        rt.discard_all_local_snapshots()
        assert scope["X"].value == "99"


@pytest.mark.codegen
class TestNestedTransactionSnapshots:
    """T050: Tests for nested transaction snapshots."""

    def test_nested_snapshots_independent(self):
        """Inner TCOMMIT only discards inner snapshot."""
        rt = MUMPSRuntime()
        scope = {"X": MArray(value="outer")}
        # Outer TSTART
        rt.snapshot_locals(scope, var_names=["X"])
        scope["X"].value = "inner"
        # Inner TSTART
        rt.snapshot_locals(scope, var_names=["X"])
        assert len(rt._transaction_snapshots) == 2

        # Inner TCOMMIT
        rt.discard_local_snapshot()
        assert len(rt._transaction_snapshots) == 1
        # Outer snapshot still has original value
        assert rt._transaction_snapshots[0].snapshot["X"].value == "outer"

    def test_trollback_discards_all_nesting_levels(self):
        """TROLLBACK discards all nested snapshots at once."""
        rt = MUMPSRuntime()
        scope = {"X": MArray(value="1")}
        rt.snapshot_locals(scope, var_names=["X"])
        rt.snapshot_locals(scope, var_names=["X"])
        rt.snapshot_locals(scope, var_names=["X"])
        assert len(rt._transaction_snapshots) == 3
        rt.discard_all_local_snapshots()
        assert len(rt._transaction_snapshots) == 0


@pytest.mark.codegen
class TestRestoreLocalsFromSnapshot:
    """Tests for restore_locals_from_snapshot() — TRESTART support."""

    def test_restore_named_vars(self):
        """Restore named variables from snapshot."""
        rt = MUMPSRuntime()
        scope = {"X": MArray(value="1"), "Y": MArray(value="2")}
        rt.snapshot_locals(scope, var_names=["X"])
        scope["X"].value = "99"
        scope["Y"].value = "99"
        rt.restore_locals_from_snapshot(scope)
        assert scope["X"].value == "1"
        assert scope["Y"].value == "99"  # Y was not in snapshot

    def test_restore_all_vars(self):
        """Restore all variables from snapshot (TSTART *)."""
        rt = MUMPSRuntime()
        scope = {"X": MArray(value="1"), "Y": MArray(value="2")}
        rt.snapshot_locals(scope, all_vars=True)
        scope["X"].value = "99"
        scope["Y"].value = "99"
        scope["Z"] = MArray(value="new")
        rt.restore_locals_from_snapshot(scope)
        assert scope["X"].value == "1"
        assert scope["Y"].value == "2"
        assert "Z" not in scope  # Z was added after TSTART

    def test_restore_kills_undefined_vars(self):
        """Variables undefined at TSTART time are KILLed on restore."""
        rt = MUMPSRuntime()
        scope = {"X": MArray(value="1")}
        rt.snapshot_locals(scope, var_names=["X", "Y"])
        # Y was undefined at TSTART — not in snapshot
        scope["Y"] = MArray(value="new")
        rt.restore_locals_from_snapshot(scope)
        assert scope["X"].value == "1"
        assert "Y" not in scope  # KILLed because undefined at TSTART

    def test_restore_preserves_snapshot(self):
        """TRESTART does not consume the snapshot (can be called again)."""
        rt = MUMPSRuntime()
        scope = {"X": MArray(value="1")}
        rt.snapshot_locals(scope, var_names=["X"])
        scope["X"].value = "modified"
        rt.restore_locals_from_snapshot(scope)
        assert scope["X"].value == "1"
        # Snapshot still exists
        assert len(rt._transaction_snapshots) == 1

    def test_restore_on_empty_is_noop(self):
        """restore_locals_from_snapshot with no snapshots is a no-op."""
        rt = MUMPSRuntime()
        scope = {"X": MArray(value="1")}
        rt.restore_locals_from_snapshot(scope)  # Should not raise
        assert scope["X"].value == "1"

    def test_restore_test_value(self):
        """$TEST is restored on TRESTART."""
        rt = MUMPSRuntime()
        rt._test = True
        scope = {"X": MArray(value="1")}
        rt.snapshot_locals(scope, var_names=["X"])
        rt._test = False
        rt.restore_locals_from_snapshot(scope)
        assert rt._test is True
