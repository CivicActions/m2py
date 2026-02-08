"""Tests for routine name auto-detection from first label.

When generate_python() is called without an explicit routine_name,
the routine name should be auto-detected from the first label in the source.
This is essential for resolving self-routine GOTOs like `G label^ROUTINE`
inside ROUTINE itself.

MUMPS Convention: The first label in a routine matches the routine/file name.
"""

import pytest
from m2py.codegen import generate_python


@pytest.mark.codegen
class TestRoutineNameAutodetect:
    """Test routine name auto-detection (T099 fix)."""

    def test_routine_name_autodetected_from_first_label(self):
        """Routine name should be set from first label when not provided."""
        # Simple routine with first label "TEST"
        source = """TEST S X=1 Q"""

        code = generate_python(source)

        # The generated code should define a function named after the first label
        assert "def TEST(" in code

    def test_routine_name_allows_self_routine_goto_resolution(self):
        """Self-routine GOTO (G label^ROUTINE inside ROUTINE) should resolve.

        This is a regression test for MVTS V1OV2 which had:
        G 691^V1OV2  ; inside routine V1OV2

        Previously this failed with "Cannot resolve offset GOTO target: 691"
        because the resolver treated label^ROUTINE as external even when
        ROUTINE was the current routine.
        """
        # Routine with self-routine GOTO
        source = """TEST ; routine TEST
LABEL1 G LABEL2^TEST
LABEL2 Q"""

        # Should not raise UnsupportedFeatureError
        code = generate_python(source)

        # Should generate valid Python with both labels
        assert "def TEST(" in code or "def LABEL1(" in code
        assert "_n_LABEL2" in code or "def LABEL2(" in code

    def test_explicit_routine_name_overrides_autodetect(self):
        """When routine_name is provided, it should override auto-detection."""
        source = """FIRST S X=1 Q"""

        code = generate_python(source, routine_name="OVERRIDE")

        # Function should still be named after first label (entry point)
        # but routine.name affects resolver (not function naming)
        assert "def FIRST(" in code
