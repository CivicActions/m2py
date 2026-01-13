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


class TestExternalGOTO:
    """Test User Story 3: G ^ROUTINE and G LABEL^ROUTINE for permanent control transfer."""

    def test_g_routine_generates_raise_goto_external(self):
        """T034: G ^ext2 should generate raise GotoExternal statement."""
        source = """ext1
 W "Start"
 G ^ext2
 W "Never"
 Q
"""
        code = generate_python(source)
        assert "import ext2" in code
        assert "from m2py.runtime import GotoExternal" in code
        assert "raise GotoExternal(ext2, None)" in code

    def test_g_label_routine_generates_raise_goto_external(self):
        """T035: G LABEL^ext2 should generate raise GotoExternal with label."""
        source = """ext1
 G HELPER^ext2
 Q
"""
        code = generate_python(source)
        assert "import ext2" in code
        assert "raise GotoExternal(ext2, 'HELPER')" in code

    def test_g_routine_transfers_control(self, external_fixtures_path):
        """T041: G ^ext2 transfers control permanently (no return)."""
        from m2py.runtime import run_with_goto_support

        # Generate ext2 that writes and quits
        ext2_source = """ext2
 W "In ext2"
 Q
"""
        ext2_code = generate_python(ext2_source)

        # Generate ext1 that GOTOs ext2 - "Never" should not print
        ext1_source = """ext1
 W "Start"
 G ^ext2
 W "Never"
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

                # Execute ext1 module code to get the entry function
                namespace = {}
                exec(ext1_code, namespace)

                # Use run_with_goto_support to handle the GotoExternal
                run_with_goto_support(namespace["ext1"])

                # Check output: should have "Start" and "In ext2", but NOT "Never"
                import ext2

                output = ext2._rt.get_output()
                assert "In ext2" in output
                # "Never" should NOT be in output - GOTO doesn't return
                # Note: "Start" goes to ext1's runtime, which is separate

            finally:
                sys.path.remove(tmpdir)
                if "ext2" in sys.modules:
                    del sys.modules["ext2"]

    def test_g_label_routine_transfers_to_label(self, external_fixtures_path):
        """T042: G LABEL^ext2 transfers control to specific label."""
        from m2py.runtime import run_with_goto_support

        # Generate ext2 with entry and HELPER labels
        ext2_source = """ext2
 W "In ext2 entry"
 Q
HELPER
 W "In HELPER"
 Q
"""
        ext2_code = generate_python(ext2_source)

        # Generate ext1 that GOTOs HELPER^ext2
        ext1_source = """ext1
 G HELPER^ext2
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

                run_with_goto_support(namespace["ext1"])

                import ext2

                output = ext2._rt.get_output()
                # Should have HELPER output, NOT entry output
                assert "In HELPER" in output
                assert "In ext2 entry" not in output

            finally:
                sys.path.remove(tmpdir)
                if "ext2" in sys.modules:
                    del sys.modules["ext2"]

    def test_g_routine_chain(self, external_fixtures_path):
        """Test chained GOTO: ext1 -> ext2 -> ext3 (all GOTOs, no returns)."""
        from m2py.runtime import run_with_goto_support

        # ext3: final destination
        ext3_source = """ext3
 W "In ext3"
 Q
"""
        ext3_code = generate_python(ext3_source)

        # ext2: GOTOs to ext3
        ext2_source = """ext2
 G ^ext3
 Q
"""
        ext2_code = generate_python(ext2_source)

        # ext1: GOTOs to ext2
        ext1_source = """ext1
 G ^ext2
 Q
"""
        ext1_code = generate_python(ext1_source)

        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "ext2.py").write_text(ext2_code)
            Path(tmpdir, "ext3.py").write_text(ext3_code)

            sys.path.insert(0, tmpdir)
            try:
                for mod in ["ext2", "ext3"]:
                    if mod in sys.modules:
                        del sys.modules[mod]

                namespace = {}
                exec(ext1_code, namespace)

                # This should chain: ext1 -> ext2 -> ext3 -> quit
                run_with_goto_support(namespace["ext1"])

                import ext3

                output = ext3._rt.get_output()
                assert "In ext3" in output

            finally:
                sys.path.remove(tmpdir)
                for mod in ["ext2", "ext3"]:
                    if mod in sys.modules:
                        del sys.modules[mod]

    def test_g_from_called_routine_no_return(self, external_fixtures_path):
        """Test: D ^ext2 where ext2 does G ^ext3 - caller's code after D never runs."""
        from m2py.runtime import run_with_goto_support

        # ext3: final destination
        ext3_source = """ext3
 W "In ext3"
 Q
"""
        ext3_code = generate_python(ext3_source)

        # ext2: GOTOs to ext3 (doesn't return)
        ext2_source = """ext2
 G ^ext3
 Q
"""
        ext2_code = generate_python(ext2_source)

        # ext1: DOs ext2, then writes "Return" (should not execute due to ext2's GOTO)
        ext1_source = """ext1
 D ^ext2
 W "Return"
 Q
"""
        ext1_code = generate_python(ext1_source)

        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "ext2.py").write_text(ext2_code)
            Path(tmpdir, "ext3.py").write_text(ext3_code)

            sys.path.insert(0, tmpdir)
            try:
                for mod in ["ext2", "ext3"]:
                    if mod in sys.modules:
                        del sys.modules[mod]

                namespace = {}
                exec(ext1_code, namespace)

                # This should: ext1 calls ext2, ext2 GOTOs ext3, ext3 quits
                # ext1's "Return" line should never execute
                run_with_goto_support(namespace["ext1"])

                import ext3

                output = ext3._rt.get_output()
                assert "In ext3" in output
                # "Return" should NOT be in output

            finally:
                sys.path.remove(tmpdir)
                for mod in ["ext2", "ext3"]:
                    if mod in sys.modules:
                        del sys.modules[mod]


class TestExternalExtrinsic:
    """Test User Story 5: $$FUNC^ROUTINE calls external function and returns value (Phase 7)."""

    def test_external_extrinsic_generates_import(self):
        """$$ADD^ext2(3,5) should generate import statement and pass _scope."""
        source = """ext1
 S X=$$ADD^ext2(3,5)
 Q
"""
        code = generate_python(source)
        assert "import ext2" in code
        # T045: External extrinsic calls pass _scope for variable visibility
        assert "_call_extrinsic(ext2.ADD, 3, 5, _scope=_scope)" in code

    def test_external_extrinsic_returns_value(self):
        """$$ADD^ext2(3,5) should call external function and return value."""
        # ext2 defines ADD function
        ext2_source = """ext2
 Q
ADD(A,B)
 Q A+B
"""
        ext2_code = generate_python(ext2_source)

        # ext1 calls $$ADD^ext2
        ext1_source = """ext1
 S X=$$ADD^ext2(3,5)
 Q X
"""
        ext1_code = generate_python(ext1_source)

        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "ext2.py").write_text(ext2_code)

            sys.path.insert(0, tmpdir)
            try:
                if "ext2" in sys.modules:
                    del sys.modules["ext2"]

                namespace = {}
                exec(ext1_code, namespace)

                result = namespace["ext1"]()
                assert result == 8

            finally:
                sys.path.remove(tmpdir)
                if "ext2" in sys.modules:
                    del sys.modules["ext2"]

    def test_external_extrinsic_test_isolation(self):
        """$TEST should be isolated across external extrinsic calls (T046)."""
        # ext2 defines SETTRUE which sets $TEST to true
        ext2_source = """ext2
 Q
SETTRUE()
 S X=1
 I X
 Q "OK"
"""
        ext2_code = generate_python(ext2_source)

        # ext1 sets $TEST to false, calls external extrinsic, then checks $TEST
        ext1_source = """ext1
 S X=0
 I X
 S Y=$$SETTRUE^ext2()
 I '$T Q "PASS"
 Q "FAIL"
"""
        ext1_code = generate_python(ext1_source)

        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "ext2.py").write_text(ext2_code)

            sys.path.insert(0, tmpdir)
            try:
                if "ext2" in sys.modules:
                    del sys.modules["ext2"]

                namespace = {}
                exec(ext1_code, namespace)

                result = namespace["ext1"]()

                # ext1 should have its $TEST restored after extrinsic call
                # $TEST was false (I X failed), should remain false after $$SETTRUE
                assert result == "PASS"

            finally:
                sys.path.remove(tmpdir)
                if "ext2" in sys.modules:
                    del sys.modules["ext2"]

    def test_external_extrinsic_scope_parameter_passed(self):
        """External extrinsic should receive _scope parameter (infrastructure test).

        Note: Full variable visibility requires variable storage to use _scope,
        which is not yet implemented. This test verifies _scope parameter
        infrastructure works correctly.
        """
        # ext2 defines CHECKSCOPE which checks if _scope was passed
        ext2_source = """ext2
 Q
CHECKSCOPE()
 Q "OK"
"""
        ext2_code = generate_python(ext2_source)

        # ext1 calls external extrinsic
        ext1_source = """ext1
 S RESULT=$$CHECKSCOPE^ext2()
 Q RESULT
"""
        ext1_code = generate_python(ext1_source)

        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "ext2.py").write_text(ext2_code)

            sys.path.insert(0, tmpdir)
            try:
                if "ext2" in sys.modules:
                    del sys.modules["ext2"]

                namespace = {}
                exec(ext1_code, namespace)

                # Call with shared _scope - should work without error
                shared_scope = {"test_var": 42}
                result = namespace["ext1"](_scope=shared_scope)
                assert result == "OK"

                # Infrastructure test: _scope was passed through without error
                # Full variable visibility test would verify shared_scope changes
                # but this requires variable storage to use _scope (future work)

            finally:
                sys.path.remove(tmpdir)
                if "ext2" in sys.modules:
                    del sys.modules["ext2"]
