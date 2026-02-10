"""Integration test: runtime can be used without codegen layer.

Phase 4 (US2): Verifies that m2py.runtime and m2py.core.values can be
imported and used independently of the m2py.codegen layer. This is the
key deliverable of the runtime independence refactoring.

The test uses subprocess isolation to guarantee no codegen modules are
loaded as a side-effect of the test runner's own imports.
"""

import pathlib
import subprocess
import sys
import textwrap


class TestRuntimeIndependence:
    """Verify runtime imports work without codegen layer."""

    def _run_isolated(self, script: str) -> subprocess.CompletedProcess:
        """Run a Python script in a subprocess with codegen blocked."""
        # Add src to sys.path so m2py can be found without install
        src_path = str(pathlib.Path(__file__).resolve().parents[2] / "src")
        full_script = textwrap.dedent(f"""\
            import sys
            sys.path.insert(0, {src_path!r})

            class CodegenBlocker:
                def find_module(self, name, path=None):
                    if name.startswith('m2py.codegen'):
                        raise ImportError(f'Blocked: {{name}}')
                    return None

            sys.meta_path.insert(0, CodegenBlocker())

        """) + textwrap.dedent(script)
        return subprocess.run(
            [sys.executable, "-c", full_script],
            capture_output=True,
            text=True,
        )

    def test_import_mumps_runtime_without_codegen(self):
        """MUMPSRuntime can be imported without touching codegen."""
        result = self._run_isolated("""\
            from m2py.runtime import MUMPSRuntime
            rt = MUMPSRuntime()
            print('OK')
        """)
        assert result.returncode == 0, (
            f"Import failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "OK" in result.stdout

    def test_import_core_values_without_codegen(self):
        """core.values can be imported without touching codegen."""
        result = self._run_isolated("""\
            from m2py.core.values import m_num, m_str, m_truth, m_compare
            assert m_num('123') == 123
            assert m_str(42) == '42'
            assert m_truth(1) is True
            assert m_truth(0) is False
            print('OK')
        """)
        assert result.returncode == 0, (
            f"Import failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "OK" in result.stdout

    def test_runtime_basic_operations_without_codegen(self):
        """MUMPSRuntime basic operations work without codegen."""
        result = self._run_isolated("""\
            from m2py.runtime import MUMPSRuntime
            rt = MUMPSRuntime()
            rt.write('Hello')
            rt.write_newline()
            output = rt.get_output()
            assert 'Hello' in output, f'Expected Hello in {output!r}'
            print('OK')
        """)
        assert result.returncode == 0, (
            f"Operations failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert "OK" in result.stdout

    def test_codegen_callback_parameter(self):
        """MUMPSRuntime accepts codegen_callback parameter."""
        from m2py.runtime import MUMPSRuntime

        # Callback not provided — should default to None
        rt = MUMPSRuntime()
        assert rt._codegen_callback is None

        # Callback provided explicitly
        def fake_codegen(code, routine_name="XECUTE"):
            return "pass"

        rt2 = MUMPSRuntime(codegen_callback=fake_codegen)
        assert rt2._codegen_callback is fake_codegen

    def test_codegen_callback_propagates_to_child(self):
        """JOB'd child runtimes inherit the codegen_callback."""
        from m2py.runtime import MUMPSRuntime

        def fake_codegen(code, routine_name="XECUTE"):
            return "pass"

        rt = MUMPSRuntime(codegen_callback=fake_codegen)
        assert rt._codegen_callback is fake_codegen
