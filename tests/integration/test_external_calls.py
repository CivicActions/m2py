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
        """D ^ext2 should generate import statement and pass _scope."""
        source = """ext1
 D ^ext2
 Q
"""
        code = generate_python(source)
        assert "import ext2" in code
        # T029: External DO calls pass _scope for cross-routine variable visibility
        assert "ext2.ext2(_scope=_scope)" in code

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
        """D HELPER^ext2 should generate call to ext2.HELPER() with _scope."""
        source = """ext1
 D HELPER^ext2
 Q
"""
        code = generate_python(source)
        assert "import ext2" in code
        # T029: External DO calls pass _scope for cross-routine variable visibility
        assert "ext2.HELPER(_scope=_scope)" in code

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


class TestCrossRoutineVariableVisibility:
    """Test User Story 4: Variables visible across routine boundaries."""

    def test_scope_parameter_exists(self):
        """T030: Entry functions accept _scope parameter."""
        source = """ext1
 S X=1
 Q
"""
        code = generate_python(source)
        # Entry function should have _scope=None parameter
        assert "def ext1(_scope=None):" in code
        # Should initialize _scope if not provided
        assert "_scope = _scope if _scope is not None else {}" in code

    def test_scope_passed_to_external_call(self):
        """T029: External DO calls pass _scope parameter."""
        source = """ext1
 D ^ext2
 Q
"""
        code = generate_python(source)
        # External call should pass _scope as keyword argument
        assert "ext2.ext2(_scope=_scope)" in code

    def test_scope_infrastructure_works(self, external_fixtures_path):
        """T032: _scope passes through external calls (infrastructure test).

        Note: Full variable visibility requires variable storage to use _scope,
        which is not yet implemented. This test verifies the infrastructure
        (parameter passing) works correctly.
        """
        # Generate ext2 that accepts _scope
        ext2_source = """ext2
 W "In ext2"
 Q
"""
        ext2_code = generate_python(ext2_source)

        # Generate ext1 that calls ext2 with _scope
        ext1_source = """ext1
 D ^ext2
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

                # Call with shared _scope - should work without error
                shared_scope = {"test_var": 42}
                namespace["ext1"](_scope=shared_scope)

                # Infrastructure test: _scope was passed through without error
                # Full variable visibility test would verify shared_scope["X"]
                # changes made in ext2 are visible - but this requires variable
                # storage to use _scope (future work)

            finally:
                sys.path.remove(tmpdir)
                if "ext2" in sys.modules:
                    del sys.modules["ext2"]

    def test_new_semantics_deferred(self):
        """T031/T033: NEW semantics require Spec 005 (not yet implemented).

        When NEW is implemented, these tests should verify:
        - N X in callee hides caller's X
        - X restored to caller's value on return
        """
        import pytest

        pytest.skip("NEW command (Spec 005) not yet implemented")
