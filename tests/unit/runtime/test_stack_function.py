"""Unit tests for $STACK function (Phase 7: US4).

T042: Unit tests for stack_function() method
T043: Unit tests for $STACK snapshot behavior
"""

from m2py.runtime import MUMPSRuntime, StackFrame


class TestStackFunctionBasic:
    """T042: Unit tests for stack_function() basic operations."""

    def test_stack_no_args_returns_depth(self):
        """$STACK with no args returns current stack depth."""
        rt = MUMPSRuntime()
        # Initially stack is empty
        assert rt.stack_function(-1) == "0"
        # Push a frame
        rt.push_stack_frame("DO", routine="test", label="TEST", offset=0)
        assert rt.stack_function(-1) == "1"
        # Push another
        rt.push_stack_frame("DO", routine="test", label="SUB", offset=0)
        assert rt.stack_function(-1) == "2"

    def test_stack_level_returns_frame_type(self):
        """$STACK(n) returns frame type for level n."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", routine="test", label="TEST", offset=0)
        rt.push_stack_frame("$$", routine="test", label="FN", offset=0)
        # Level 1 is first frame (DO)
        assert rt.stack_function(1) == "DO"
        # Level 2 is second frame ($$)
        assert rt.stack_function(2) == "$$"

    def test_stack_level_exceeds_depth_returns_empty(self):
        """$STACK(n) returns "" if n > stack depth."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", routine="test", label="TEST", offset=0)
        assert rt.stack_function(2) == ""
        assert rt.stack_function(99) == ""

    def test_stack_level_0_returns_implementation_info(self):
        """$STACK(0) returns implementation-specific info."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", routine="test", label="TEST", offset=0)
        # Level 0 is implementation-specific - typically empty or version
        result = rt.stack_function(0)
        # Just check it doesn't error and returns a string
        assert isinstance(result, str)

    def test_stack_negative_1_returns_error_depth(self):
        """$STACK(-1) returns current depth (or error snapshot depth)."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", routine="test", label="TEST", offset=0)
        rt.push_stack_frame("DO", routine="test", label="SUB", offset=0)
        assert rt.stack_function(-1) == "2"


class TestStackFunctionInfoCodes:
    """T042: Unit tests for $STACK(n,info) info codes."""

    def test_stack_place_returns_label_offset_routine(self):
        """$STACK(n,"PLACE") returns "LABEL+offset^ROUTINE"."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", routine="myroutine", label="MAIN", offset=5)
        result = rt.stack_function(1, "PLACE")
        assert result == "MAIN+5^myroutine"

    def test_stack_place_with_zero_offset(self):
        """$STACK(n,"PLACE") with offset=0."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", routine="test", label="START", offset=0)
        result = rt.stack_function(1, "PLACE")
        assert result == "START+0^test"

    def test_stack_mcode_returns_source_line(self):
        """$STACK(n,"MCODE") returns MUMPS source line."""
        rt = MUMPSRuntime()
        rt.push_stack_frame(
            "DO", routine="test", label="TEST", offset=0, mcode="D SUB^TEST"
        )
        result = rt.stack_function(1, "MCODE")
        assert result == "D SUB^TEST"

    def test_stack_ecode_returns_error_codes(self):
        """$STACK(n,"ECODE") returns error codes at that level."""
        rt = MUMPSRuntime()
        # Create a frame with an error code
        frame = StackFrame(
            frame_type="DO",
            routine="test",
            label="ERR",
            offset=1,
            ecode=",M6,",
        )
        rt._stack_frames.append(frame)
        result = rt.stack_function(1, "ECODE")
        assert result == ",M6,"

    def test_stack_invalid_info_returns_empty(self):
        """$STACK(n,"INVALID") returns empty string."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", routine="test", label="TEST", offset=0)
        # Invalid info codes return empty
        result = rt.stack_function(1, "INVALID")
        assert result == ""


class TestStackSnapshotBehavior:
    """T043: Unit tests for $STACK snapshot behavior during errors."""

    def test_snapshot_taken_on_first_error(self):
        """Stack snapshot is frozen when $ECODE becomes non-empty."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", routine="test", label="OUTER", offset=0)
        rt.push_stack_frame("DO", routine="test", label="INNER", offset=0)
        # Simulate error - this should freeze snapshot
        rt._freeze_stack_snapshot()
        assert rt._stack_snapshot is not None
        assert len(rt._stack_snapshot) == 2

    def test_snapshot_not_updated_on_subsequent_errors(self):
        """Subsequent errors don't update the snapshot."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", routine="test", label="OUTER", offset=0)
        rt._freeze_stack_snapshot()
        # Now add more frames
        rt.push_stack_frame("DO", routine="test", label="INNER", offset=0)
        # Freeze again - should NOT update
        rt._freeze_stack_snapshot()
        # Snapshot should still have 1 frame
        assert len(rt._stack_snapshot) == 1

    def test_stack_returns_snapshot_during_error(self):
        """During error, $STACK returns data from frozen snapshot."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", routine="test", label="OUTER", offset=0)
        rt.push_stack_frame("DO", routine="test", label="INNER", offset=0)
        # Set $ECODE and freeze snapshot
        rt.set_ecode(",M6,")
        rt._freeze_stack_snapshot()
        # Pop a frame (simulating error unwinding)
        rt.pop_stack_frame()
        # $STACK auto-uses snapshot when $ECODE is non-empty
        assert rt.stack_function(-1) == "2"  # snapshot depth, not live (1)

    def test_snapshot_cleared_on_ecode_reset(self):
        """Snapshot is cleared when SET $ECODE=""."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", routine="test", label="TEST", offset=0)
        rt.set_ecode(",M6,")
        rt._freeze_stack_snapshot()
        assert rt._stack_snapshot is not None
        # Clear $ECODE
        rt.set_ecode("")
        # Snapshot should be cleared (reset to None)
        assert rt._stack_snapshot is None

    def test_stack_minus_1_returns_snapshot_depth_during_error(self):
        """$STACK(-1) returns snapshot depth when in error state."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", routine="test", label="OUTER", offset=0)
        rt.push_stack_frame("DO", routine="test", label="INNER", offset=0)
        rt.set_ecode(",M6,")
        rt._freeze_stack_snapshot()
        # Pop frames (simulating unwinding)
        rt.pop_stack_frame()
        rt.pop_stack_frame()
        # $STACK(-1) auto-uses snapshot when $ECODE is non-empty
        # Should return 2 (snapshot depth), not 0 (live stack)
        assert rt.stack_function(-1) == "2"


class TestStackFunctionEdgeCases:
    """Additional edge case tests for $STACK."""

    def test_empty_stack_returns_zero(self):
        """Empty stack returns 0 for depth."""
        rt = MUMPSRuntime()
        assert rt.stack_function(-1) == "0"

    def test_stack_with_xecute_frame(self):
        """$STACK with XECUTE frame type."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("XECUTE", mcode="S X=1 W X")
        assert rt.stack_function(1) == "XECUTE"
        assert rt.stack_function(1, "MCODE") == "S X=1 W X"

    def test_stack_with_extrinsic_frame(self):
        """$STACK with extrinsic ($$) frame type."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("$$", routine="test", label="FN", offset=0)
        assert rt.stack_function(1) == "$$"
        assert "FN" in rt.stack_function(1, "PLACE")

    def test_stack_case_insensitive_info(self):
        """$STACK info codes are case-insensitive."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", routine="test", label="TEST", offset=1)
        assert rt.stack_function(1, "place") == rt.stack_function(1, "PLACE")
        assert rt.stack_function(1, "mcode") == rt.stack_function(1, "MCODE")
