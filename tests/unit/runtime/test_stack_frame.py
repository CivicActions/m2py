"""Tests for stack frame infrastructure and error code helpers.

Spec 021 Phase 2: Tests for StackFrame, _append_ecode(), _freeze_stack_snapshot(),
_format_zstatus(), push_stack_frame(), pop_stack_frame() and stack_level().

Reference: MUMPS 1995 ANSI Standard, Section 7.1.4.10 ($STACK).
YDB $ZSTATUS format: "errorcode,label+offset^routine,%YDB-E-ERRNAME, message"
"""

from m2py.runtime import MUMPSRuntime, StackFrame, TransactionLocalSnapshot


# =============================================================================
# StackFrame dataclass
# =============================================================================


class TestStackFrame:
    """Tests for the StackFrame dataclass."""

    def test_default_values(self):
        """StackFrame has sensible defaults for all optional fields."""
        frame = StackFrame(frame_type="DO")
        assert frame.frame_type == "DO"
        assert frame.routine == ""
        assert frame.label == ""
        assert frame.offset == 0
        assert frame.mcode == ""
        assert frame.ecode == ""

    def test_full_construction(self):
        """StackFrame can be constructed with all fields."""
        frame = StackFrame(
            frame_type="$$",
            routine="TEST",
            label="SUB",
            offset=3,
            mcode=' S X=$$SUB^TEST("arg")',
            ecode=",M6,",
        )
        assert frame.frame_type == "$$"
        assert frame.routine == "TEST"
        assert frame.label == "SUB"
        assert frame.offset == 3
        assert frame.mcode == ' S X=$$SUB^TEST("arg")'
        assert frame.ecode == ",M6,"

    def test_frame_types(self):
        """StackFrame supports DO, $$, XECUTE, ZINTR, TRIGGER frame types."""
        for ft in ("DO", "$$", "XECUTE", "ZINTR", "TRIGGER"):
            frame = StackFrame(frame_type=ft)
            assert frame.frame_type == ft

    def test_mutable_ecode(self):
        """StackFrame ecode can be modified after creation."""
        frame = StackFrame(frame_type="DO")
        assert frame.ecode == ""
        frame.ecode = ",M6,"
        assert frame.ecode == ",M6,"


# =============================================================================
# TransactionLocalSnapshot dataclass
# =============================================================================


class TestTransactionLocalSnapshot:
    """Tests for TransactionLocalSnapshot dataclass."""

    def test_default_values(self):
        """TransactionLocalSnapshot has expected defaults."""
        snap = TransactionLocalSnapshot()
        assert snap.restart_vars is None
        assert snap.restart_all is False
        assert snap.snapshot == {}
        assert snap.saved_test is None

    def test_full_construction(self):
        """TransactionLocalSnapshot can be constructed with all fields."""
        snap = TransactionLocalSnapshot(
            restart_vars=["X", "Y"],
            restart_all=True,
            snapshot={"X": "1", "Y": "2"},
            saved_test=True,
        )
        assert snap.restart_vars == ["X", "Y"]
        assert snap.restart_all is True
        assert snap.snapshot == {"X": "1", "Y": "2"}
        assert snap.saved_test is True


# =============================================================================
# push_stack_frame / pop_stack_frame / stack_level
# =============================================================================


class TestStackFrameManagement:
    """Tests for push_stack_frame(), pop_stack_frame(), and stack_level()."""

    def test_initial_stack_level(self):
        """Initial $STACK level is 0 (no frames)."""
        rt = MUMPSRuntime()
        assert rt.stack_level() == 0
        assert rt._stack_frames == []

    def test_push_increments_level(self):
        """push_stack_frame increases $STACK level."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO")
        assert rt.stack_level() == 1
        rt.push_stack_frame("DO")
        assert rt.stack_level() == 2

    def test_pop_decrements_level(self):
        """pop_stack_frame decreases $STACK level."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO")
        rt.push_stack_frame("DO")
        rt.pop_stack_frame()
        assert rt.stack_level() == 1
        rt.pop_stack_frame()
        assert rt.stack_level() == 0

    def test_pop_empty_stack_safe(self):
        """pop_stack_frame on empty stack is a no-op."""
        rt = MUMPSRuntime()
        rt.pop_stack_frame()  # Should not raise
        assert rt.stack_level() == 0

    def test_push_with_metadata(self):
        """push_stack_frame stores frame metadata."""
        rt = MUMPSRuntime()
        rt.push_stack_frame(
            "DO", routine="TEST", label="SUB", offset=3, mcode=" D SUB^TEST"
        )
        assert rt.stack_level() == 1
        frame = rt._stack_frames[0]
        assert frame.frame_type == "DO"
        assert frame.routine == "TEST"
        assert frame.label == "SUB"
        assert frame.offset == 3
        assert frame.mcode == " D SUB^TEST"

    def test_push_extrinsic_frame(self):
        """push_stack_frame with $$ frame type for extrinsic functions."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("$$", routine="MATH", label="ADD")
        assert rt.stack_level() == 1
        assert rt._stack_frames[0].frame_type == "$$"

    def test_push_xecute_frame(self):
        """push_stack_frame with XECUTE frame type."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("XECUTE")
        assert rt.stack_level() == 1
        assert rt._stack_frames[0].frame_type == "XECUTE"

    def test_nested_frames_correct_order(self):
        """Nested frames are stacked in LIFO order."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", label="A")
        rt.push_stack_frame("DO", label="B")
        rt.push_stack_frame("$$", label="C")
        assert rt.stack_level() == 3
        assert rt._stack_frames[0].label == "A"
        assert rt._stack_frames[1].label == "B"
        assert rt._stack_frames[2].label == "C"

        rt.pop_stack_frame()
        assert rt.stack_level() == 2
        assert rt._stack_frames[-1].label == "B"

    def test_legacy_push_pop_frame(self):
        """Legacy push_frame/pop_frame still work via list-based stack."""
        rt = MUMPSRuntime()
        rt.push_frame()
        assert rt.stack_level() == 1
        rt.push_frame()
        assert rt.stack_level() == 2
        rt.pop_frame()
        assert rt.stack_level() == 1
        rt.pop_frame()
        assert rt.stack_level() == 0


# =============================================================================
# _append_ecode
# =============================================================================


class TestAppendEcode:
    """Tests for _append_ecode() accumulator."""

    def test_first_error_code(self):
        """First error code wraps with surrounding commas."""
        rt = MUMPSRuntime()
        rt._append_ecode("M6")
        assert rt._ecode == ",M6,"

    def test_second_error_code(self):
        """Second error code appends after existing trailing comma."""
        rt = MUMPSRuntime()
        rt._append_ecode("M6")
        rt._append_ecode("M9")
        assert rt._ecode == ",M6,M9,"

    def test_three_error_codes(self):
        """Multiple codes accumulate correctly."""
        rt = MUMPSRuntime()
        rt._append_ecode("M6")
        rt._append_ecode("Z150373850")
        rt._append_ecode("M9")
        assert rt._ecode == ",M6,Z150373850,M9,"

    def test_ydb_format_match(self):
        """$ECODE format matches YDB behavior: ,M6,Z150373850,"""
        rt = MUMPSRuntime()
        rt._append_ecode("M6")
        rt._append_ecode("Z150373850")
        assert rt._ecode == ",M6,Z150373850,"

    def test_append_after_set_ecode_empty(self):
        """Appending after clearing $ECODE starts fresh."""
        rt = MUMPSRuntime()
        rt._append_ecode("M6")
        rt.set_ecode("")  # Clear
        assert rt._ecode == ""
        rt._append_ecode("M9")
        assert rt._ecode == ",M9,"

    def test_append_preserves_existing_manual_set(self):
        """Appending after manual SET $ECODE works correctly."""
        rt = MUMPSRuntime()
        rt.set_ecode(",M4,")
        rt._append_ecode("M6")
        assert rt._ecode == ",M4,M6,"


# =============================================================================
# _freeze_stack_snapshot
# =============================================================================


class TestFreezeStackSnapshot:
    """Tests for _freeze_stack_snapshot() deep copy mechanism."""

    def test_freeze_captures_current_stack(self):
        """Freeze captures a copy of the current stack frames."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", routine="TEST", label="A")
        rt.push_stack_frame("DO", routine="TEST", label="B")

        rt._freeze_stack_snapshot()

        assert rt._stack_snapshot is not None
        assert len(rt._stack_snapshot) == 2
        assert rt._stack_snapshot_depth == 2
        assert rt._stack_snapshot[0].label == "A"
        assert rt._stack_snapshot[1].label == "B"

    def test_freeze_is_deep_copy(self):
        """Snapshot is a deep copy — modifying live stack doesn't affect it."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", routine="R", label="X")
        rt._freeze_stack_snapshot()

        # Modify live stack
        rt.pop_stack_frame()
        assert rt.stack_level() == 0  # Live stack empty

        # Snapshot unchanged
        assert len(rt._stack_snapshot) == 1
        assert rt._stack_snapshot[0].label == "X"

    def test_freeze_idempotent(self):
        """Second freeze is a no-op — only first error freezes."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", label="FIRST")
        rt._freeze_stack_snapshot()

        # Push more frames and freeze again
        rt.push_stack_frame("DO", label="SECOND")
        rt._freeze_stack_snapshot()  # Should not update

        assert len(rt._stack_snapshot) == 1
        assert rt._stack_snapshot[0].label == "FIRST"

    def test_freeze_empty_stack(self):
        """Freeze on empty stack captures empty list."""
        rt = MUMPSRuntime()
        rt._freeze_stack_snapshot()

        assert rt._stack_snapshot is not None
        assert len(rt._stack_snapshot) == 0
        assert rt._stack_snapshot_depth == 0

    def test_snapshot_reset_allows_refreeze(self):
        """After resetting snapshot to None, freeze works again."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", label="A")
        rt._freeze_stack_snapshot()
        assert len(rt._stack_snapshot) == 1

        # Simulate SET $ECODE="" clearing the snapshot
        rt._stack_snapshot = None
        rt._stack_snapshot_depth = 0

        # Now push more and freeze again
        rt.push_stack_frame("DO", label="B")
        rt._freeze_stack_snapshot()
        assert len(rt._stack_snapshot) == 2  # Both A and B

    def test_deep_copy_isolation(self):
        """Modifying snapshot objects doesn't affect live frames."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", routine="R", label="A", mcode=" D A^R")
        rt._freeze_stack_snapshot()

        # Modify snapshot
        rt._stack_snapshot[0].label = "MODIFIED"
        rt._stack_snapshot[0].mcode = "CHANGED"

        # Live frame unchanged
        assert rt._stack_frames[0].label == "A"
        assert rt._stack_frames[0].mcode == " D A^R"

    def test_snapshot_uses_shallow_copy_not_deepcopy(self):
        """Snapshot uses dataclasses.replace (shallow), not copy.deepcopy.

        StackFrame fields are all immutable (str/int), so shallow copy
        is sufficient and avoids the O(n) deepcopy cost.
        Commit 14026e58.
        """
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", routine="R", label="A", offset=5, mcode=" D")
        rt.push_stack_frame("$$", routine="S", label="B", offset=0)
        rt._stack_frames[-1].ecode = ",M6,"
        rt._freeze_stack_snapshot()

        # Snapshot frames are distinct objects
        assert rt._stack_snapshot[0] is not rt._stack_frames[0]
        assert rt._stack_snapshot[1] is not rt._stack_frames[1]

        # But have identical content
        for snap, live in zip(rt._stack_snapshot, rt._stack_frames):
            assert snap.frame_type == live.frame_type
            assert snap.routine == live.routine
            assert snap.label == live.label
            assert snap.offset == live.offset
            assert snap.mcode == live.mcode
            assert snap.ecode == live.ecode

    def test_freeze_repeated_rapidly_only_first_takes(self):
        """Rapidly calling _freeze_stack_snapshot only captures first state.

        Simulates the $ETRAP cycling pattern in DMUDIC00 where $ECODE
        transitions from empty to non-empty thousands of times per second.
        """
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", label="A")
        rt._freeze_stack_snapshot()  # First freeze captures 1 frame

        # Push more frames and freeze many more times
        for i in range(100):
            rt.push_stack_frame("DO", label=f"L{i}")
            rt._freeze_stack_snapshot()  # All no-ops

        # Snapshot still has exactly 1 frame from first freeze
        assert len(rt._stack_snapshot) == 1
        assert rt._stack_snapshot[0].label == "A"


# =============================================================================
# _format_zstatus
# =============================================================================


class TestFormatZstatus:
    """Tests for _format_zstatus() YDB format string builder."""

    def test_full_format(self):
        """Full $ZSTATUS with all components."""
        rt = MUMPSRuntime()
        result = rt._format_zstatus(
            "150373850",
            "TEST",
            3,
            "test",
            "LVUNDEF",
            "Undefined local variable: X",
        )
        assert (
            result
            == "150373850,TEST+3^test,%YDB-E-LVUNDEF, Undefined local variable: X"
        )

    def test_divide_by_zero(self):
        """$ZSTATUS for divide-by-zero error."""
        rt = MUMPSRuntime()
        result = rt._format_zstatus(
            "150373210",
            "FOO",
            1,
            "bar",
            "DIVZERO",
            "Attempt to divide by zero",
        )
        assert result == "150373210,FOO+1^bar,%YDB-E-DIVZERO, Attempt to divide by zero"

    def test_empty_location(self):
        """$ZSTATUS with empty label and routine."""
        rt = MUMPSRuntime()
        result = rt._format_zstatus(
            "150373850",
            "",
            0,
            "",
            "LVUNDEF",
            "Undefined: X",
        )
        assert result == "150373850,+0^,%YDB-E-LVUNDEF, Undefined: X"

    def test_without_ydb_code(self):
        """$ZSTATUS without YDB error mnemonic."""
        rt = MUMPSRuntime()
        result = rt._format_zstatus("99", "A", 2, "B", "", "some error")
        assert result == "99,A+2^B, some error"

    def test_zero_offset(self):
        """$ZSTATUS with zero offset."""
        rt = MUMPSRuntime()
        result = rt._format_zstatus(
            "150373850",
            "MAIN",
            0,
            "routine",
            "LVUNDEF",
            "Undef",
        )
        assert result == "150373850,MAIN+0^routine,%YDB-E-LVUNDEF, Undef"

    def test_large_offset(self):
        """$ZSTATUS with large offset value."""
        rt = MUMPSRuntime()
        result = rt._format_zstatus(
            "150373850",
            "START",
            999,
            "bigfile",
            "LVUNDEF",
            "err",
        )
        assert result == "150373850,START+999^bigfile,%YDB-E-LVUNDEF, err"

    def test_m_select_error(self):
        """$ZSTATUS for $SELECT no true condition (M4)."""
        rt = MUMPSRuntime()
        result = rt._format_zstatus(
            "150372634",
            "FUNC",
            5,
            "util",
            "SELECTFALSE",
            "No TRUE condition in $SELECT",
        )
        assert (
            result
            == "150372634,FUNC+5^util,%YDB-E-SELECTFALSE, No TRUE condition in $SELECT"
        )


# =============================================================================
# ISV field initialization (Phase 1 T003)
# =============================================================================


class TestISVFieldInitialization:
    """Tests for new ISV field defaults in MUMPSRuntime.__init__."""

    def test_ztrap_default(self):
        """$ZTRAP starts empty."""
        rt = MUMPSRuntime()
        assert rt._ztrap == ""

    def test_zstatus_default(self):
        """$ZSTATUS starts empty."""
        rt = MUMPSRuntime()
        assert rt._zstatus == ""

    def test_zposition_default(self):
        """$ZPOSITION starts empty."""
        rt = MUMPSRuntime()
        assert rt._zposition == ""

    def test_in_error_handler_default(self):
        """Error handler flag starts False."""
        rt = MUMPSRuntime()
        assert rt._in_error_handler is False

    def test_etrap_set_level_default(self):
        """$ETRAP set level starts at 0."""
        rt = MUMPSRuntime()
        assert rt._etrap_set_level == 0

    def test_zsystem_exit_default(self):
        """$ZSYSTEM exit code starts at 0."""
        rt = MUMPSRuntime()
        assert rt._zsystem_exit == 0

    def test_zsearch_defaults(self):
        """$ZSEARCH state starts empty."""
        rt = MUMPSRuntime()
        assert rt._zsearch_results == []
        assert rt._zsearch_index == 0

    def test_transaction_snapshots_default(self):
        """Transaction snapshots start empty."""
        rt = MUMPSRuntime()
        assert rt._transaction_snapshots == []

    def test_stack_snapshot_default(self):
        """Stack snapshot starts as None."""
        rt = MUMPSRuntime()
        assert rt._stack_snapshot is None
        assert rt._stack_snapshot_depth == 0
