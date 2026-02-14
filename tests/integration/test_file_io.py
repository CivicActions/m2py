"""Integration tests for file I/O via MUMPS transpilation.

Tests that MUMPS routines using OPEN/USE/CLOSE/READ/WRITE
transpile and produce correct output when run.

Spec 022: Phase 4 — US2 (File I/O Integration)
"""

from m2py.runtime import MUMPSRuntime


class TestFileIOIntegration:
    """Integration test: OPEN→USE→WRITE→CLOSE→OPEN→READ→CLOSE lifecycle."""

    def test_write_and_read_back(self, tmp_path):
        """Write lines to file, read them back, verify content."""
        filepath = str(tmp_path / "test.txt")
        rt = MUMPSRuntime()

        # Open for write (NEWVERSION)
        rt.open_device(filepath, ["NEWVERSION"])
        rt.use_device(filepath)

        # Write two lines
        rt.write("Hello")
        rt.write_newline()
        rt.write("World")
        rt.write_newline()

        # Close and switch back to principal
        rt.close_device(filepath)
        assert rt.io() == "0"

        # Reopen for read
        rt.open_device(filepath, ["READONLY"])
        rt.use_device(filepath)

        dev = rt._device_table[filepath]

        # Read line 1
        data1, key1 = dev.read()
        assert data1 == "Hello"
        assert key1 == chr(10)
        assert rt.zeof() == 0

        # Read line 2
        data2, key2 = dev.read()
        assert data2 == "World"
        assert key2 == chr(10)
        assert rt.zeof() == 0

        # Read EOF
        data3, key3 = dev.read()
        assert data3 == ""
        assert key3 == ""
        assert rt.zeof() == 1

        rt.close_device(filepath)
        assert rt.io() == "0"

    def test_principal_io_unaffected(self, tmp_path):
        """File I/O doesn't interfere with $PRINCIPAL output."""
        filepath = str(tmp_path / "test.txt")
        rt = MUMPSRuntime()

        # Write to principal
        rt.write("Before")

        # Write to file
        rt.open_device(filepath, ["NEWVERSION"])
        rt.use_device(filepath)
        rt.write("File Content")
        rt.use_device("0")

        # Write more to principal
        rt.write("After")

        rt.close_device(filepath)

        # Verify principal output
        assert rt.get_output() == "BeforeAfter"

        # Verify file content
        with open(filepath) as f:
            assert f.read() == "File Content"

    def test_xy_tracking_across_devices(self, tmp_path):
        """$X/$Y track independently across devices."""
        filepath = str(tmp_path / "test.txt")
        rt = MUMPSRuntime()

        # Principal: write 5 chars → $X=5
        rt.write("ABCDE")
        assert rt.x() == 5

        # File: fresh → $X=0
        rt.open_device(filepath, ["NEWVERSION"])
        rt.use_device(filepath)
        assert rt.x() == 0

        # File: write 3 chars → $X=3
        rt.write("XYZ")
        assert rt.x() == 3

        # Back to principal → $X=5 (preserved)
        rt.use_device("0")
        assert rt.x() == 5

        rt.close_device(filepath)

    def test_zeof_codegen_expression(self):
        """$ZEOF generates correct code via expressions.py."""
        from m2py.asg.expressions import MSpecialVariable

        from m2py.codegen.expressions import _generate_special_variable

        # Create a mock context — _generate_special_variable only uses var.name
        var = MSpecialVariable(name="ZEOF")

        class FakeCtx:
            pass

        result = _generate_special_variable(var, FakeCtx())
        assert result == "_rt.zeof()"
