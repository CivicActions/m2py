"""Integration tests for external calls (Spec 008).

Tests cross-routine coordination including:
- D ^ROUTINE (external DO routine call)
- D LABEL^ROUTINE (external DO label call)
- G ^ROUTINE (external GOTO)
- $$FUNC^ROUTINE (external extrinsic)
- Variable visibility across routines
- $TEXT with external routines

Uses fixtures from tests/fixtures/external/
"""

import sys
import tempfile
from pathlib import Path


from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime


class TestExternalDORoutineCall:
    """Test User Story 1: D ^ROUTINE calls entry label of external routine."""

    def test_d_routine_generates_import(self):
        """D ^ext2 should generate import statement."""
        source = """ext1
 D ^ext2
 Q
"""
        code = generate_python(source)
        assert "import ext2" in code
        assert "ext2.ext2()" in code

    def test_d_routine_entry_label(self, external_fixtures_path):
        """D ^ext2 should call ext2's entry label and return."""
        # Generate Python for ext2 (simple version without format controls)
        ext2_source = """ext2
 W "In ext2"
 Q
"""
        ext2_code = generate_python(ext2_source)

        # Generate Python for ext1 (the caller)
        ext1_source = """ext1
 D ^ext2
 Q
"""
        ext1_code = generate_python(ext1_source)

        # Create temp directory and write ext2.py
        with tempfile.TemporaryDirectory() as tmpdir:
            ext2_path = Path(tmpdir) / "ext2.py"
            ext2_path.write_text(ext2_code)

            # Add to sys.path
            sys.path.insert(0, tmpdir)
            try:
                # Clear any cached ext2 module
                if "ext2" in sys.modules:
                    del sys.modules["ext2"]

                # Execute ext1 which imports and calls ext2
                namespace = {}
                exec(ext1_code, namespace)

                # Call ext1 entry point
                namespace["ext1"]()

                # Import ext2 to check its output
                import ext2

                output = ext2._rt.get_output()
                assert "In ext2" in output

            finally:
                sys.path.remove(tmpdir)
                if "ext2" in sys.modules:
                    del sys.modules["ext2"]

    def test_d_routine_returns_to_caller(self, external_fixtures_path):
        """After D ^ext2 returns, caller continues execution."""
        # Generate Python for ext2 (simple version)
        ext2_source = """ext2
 W "In ext2"
 Q
"""
        ext2_code = generate_python(ext2_source)

        # Generate Python for ext1 with write after call
        ext1_source = """ext1
 D ^ext2
 W "Back in ext1"
 Q
"""
        ext1_code = generate_python(ext1_source)

        with tempfile.TemporaryDirectory() as tmpdir:
            ext2_path = Path(tmpdir) / "ext2.py"
            ext2_path.write_text(ext2_code)

            sys.path.insert(0, tmpdir)
            try:
                if "ext2" in sys.modules:
                    del sys.modules["ext2"]

                # Create runtime for ext1
                rt = MUMPSRuntime()
                namespace = {"_rt": rt}

                # Execute module code
                exec(ext1_code, namespace)

                # Overwrite module's _rt with our shared one
                namespace["_rt"] = rt

                # Call ext1
                namespace["ext1"]()

                # ext1's output should have "Back in ext1"
                output = rt.get_output()
                assert "Back in ext1" in output

            finally:
                sys.path.remove(tmpdir)
                if "ext2" in sys.modules:
                    del sys.modules["ext2"]


class TestExternalDOLabelCall:
    """Test User Story 2: D LABEL^ROUTINE calls specific label in external routine."""

    def test_d_label_routine_generates_call(self):
        """D HELPER^ext2 should generate call to ext2.HELPER()."""
        source = """ext1
 D HELPER^ext2
 Q
"""
        code = generate_python(source)
        assert "import ext2" in code
        assert "ext2.HELPER()" in code

    def test_d_label_routine_calls_label(self, external_fixtures_path):
        """D HELPER^ext2 should call the HELPER label (not entry label)."""
        # Generate Python for ext2 with two labels
        ext2_source = """ext2
 W "In ext2"
 Q
HELPER
 W "In HELPER"
 Q
"""
        ext2_code = generate_python(ext2_source)

        # Generate Python for ext1 calling HELPER
        ext1_source = """ext1
 D HELPER^ext2
 Q
"""
        ext1_code = generate_python(ext1_source)

        with tempfile.TemporaryDirectory() as tmpdir:
            ext2_path = Path(tmpdir) / "ext2.py"
            ext2_path.write_text(ext2_code)

            sys.path.insert(0, tmpdir)
            try:
                if "ext2" in sys.modules:
                    del sys.modules["ext2"]

                # Execute ext1
                namespace = {}
                exec(ext1_code, namespace)
                namespace["ext1"]()

                # Import ext2 to check output
                import ext2

                output = ext2._rt.get_output()
                # Should have HELPER output, not ext2 entry output
                assert "In HELPER" in output
                assert "In ext2" not in output

            finally:
                sys.path.remove(tmpdir)
                if "ext2" in sys.modules:
                    del sys.modules["ext2"]

    def test_d_label_missing_raises_error(self):
        """D NONEXISTENT^ext2 should raise LabelNotFoundError."""
        from m2py.runtime import LabelNotFoundError

        # ext2 without NONEXISTENT label
        ext2_source = """ext2
 W "In ext2"
 Q
"""
        ext2_code = generate_python(ext2_source)

        # ext1 calling nonexistent label
        ext1_source = """ext1
 D NONEXISTENT^ext2
 Q
"""
        ext1_code = generate_python(ext1_source)

        with tempfile.TemporaryDirectory() as tmpdir:
            ext2_path = Path(tmpdir) / "ext2.py"
            ext2_path.write_text(ext2_code)

            sys.path.insert(0, tmpdir)
            try:
                if "ext2" in sys.modules:
                    del sys.modules["ext2"]

                namespace = {}
                exec(ext1_code, namespace)

                # Should raise LabelNotFoundError when called
                import pytest

                with pytest.raises(LabelNotFoundError) as exc_info:
                    namespace["ext1"]()

                # Verify error details
                assert exc_info.value.label == "NONEXISTENT"
                assert exc_info.value.routine == "ext2"
                assert "ext2" in exc_info.value.available_labels

            finally:
                sys.path.remove(tmpdir)
                if "ext2" in sys.modules:
                    del sys.modules["ext2"]
