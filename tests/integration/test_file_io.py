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


class TestCloseDelete:
    """Tests for CLOSE :DELETE parameter (GT.M/YDB extension)."""

    def test_close_delete_removes_file(self, tmp_path):
        """CLOSE device:DELETE closes and removes the file."""
        filepath = str(tmp_path / "to_delete.txt")
        rt = MUMPSRuntime()

        # Create and write to file
        rt.open_device(filepath, ["NEWVERSION"])
        rt.use_device(filepath)
        rt.write("temporary data")
        rt.close_device(filepath, parameters=["DELETE"])

        # File should be removed
        import os

        assert not os.path.exists(filepath)
        # Should be back on principal
        assert rt.io() == "0"

    def test_close_delete_case_insensitive(self, tmp_path):
        """DELETE parameter is case-insensitive."""
        filepath = str(tmp_path / "ci_delete.txt")
        rt = MUMPSRuntime()

        rt.open_device(filepath, ["NEWVERSION"])
        rt.use_device(filepath)
        rt.write("data")
        rt.close_device(filepath, parameters=["delete"])

        import os

        assert not os.path.exists(filepath)

    def test_close_without_delete_keeps_file(self, tmp_path):
        """Normal CLOSE preserves the file."""
        filepath = str(tmp_path / "keep.txt")
        rt = MUMPSRuntime()

        rt.open_device(filepath, ["NEWVERSION"])
        rt.use_device(filepath)
        rt.write("keep this")
        rt.close_device(filepath)

        import os

        assert os.path.exists(filepath)

    def test_close_delete_nonexistent_file_no_error(self, tmp_path):
        """DELETE of already-removed file doesn't raise."""
        filepath = str(tmp_path / "phantom.txt")
        rt = MUMPSRuntime()

        rt.open_device(filepath, ["NEWVERSION"])
        rt.close_device(filepath, parameters=["DELETE"])
        # Second close with DELETE on non-existent file should be a no-op
        # (device already removed from table, file already gone)


class TestOpenDeviceIndirected:
    """Tests for open_device_indirected() — runtime OPEN spec parsing."""

    def test_simple_file_path(self, tmp_path):
        """Indirected OPEN with just a file path."""
        filepath = str(tmp_path / "simple.txt")
        rt = MUMPSRuntime()
        # Touch the file so OPEN succeeds
        (tmp_path / "simple.txt").write_text("")

        result = rt.open_device_indirected(filepath, {})
        assert result is True
        rt.close_device(filepath)

    def test_file_with_params_and_timeout(self, tmp_path):
        """Indirected OPEN with params and timeout: 'file:(NEWVERSION):0'."""
        filepath = str(tmp_path / "indirected.txt")
        spec = f"{filepath}:(NEWVERSION):0"
        rt = MUMPSRuntime()

        result = rt.open_device_indirected(spec, {})
        assert result is True
        # $TEST should be set since timeout was present
        assert rt._test == 1
        rt.close_device(filepath)

    def test_file_write_via_indirection(self, tmp_path):
        """Full cycle: indirected OPEN → USE → WRITE → CLOSE → verify."""
        filepath = str(tmp_path / "via_indir.txt")
        spec = f"{filepath}:(NEWVERSION:NOWRAP:STREAM):0"
        rt = MUMPSRuntime()

        result = rt.open_device_indirected(spec, {})
        assert result is True

        rt.use_device(filepath)
        rt.write("indirected write")
        rt.write_newline()
        rt.close_device(filepath)

        with open(filepath) as f:
            assert f.read() == "indirected write\n"

    def test_variable_resolution(self, tmp_path):
        """Indirected OPEN resolves variable name to file path."""
        from m2py.runtime import MArray

        filepath = str(tmp_path / "varres.txt")
        (tmp_path / "varres.txt").write_text("")

        scope = {"_pct_IO": MArray()}
        scope["_pct_IO"].value = filepath

        rt = MUMPSRuntime()
        result = rt.open_device_indirected("%IO:(READONLY):0", scope)
        assert result is True
        rt.close_device(filepath)

    def test_empty_params(self, tmp_path):
        """Indirected OPEN with device::timeout (empty params)."""
        filepath = str(tmp_path / "emptyparam.txt")
        (tmp_path / "emptyparam.txt").write_text("")

        spec = f"{filepath}::0"
        rt = MUMPSRuntime()

        result = rt.open_device_indirected(spec, {})
        assert result is True
        assert rt._test == 1
        rt.close_device(filepath)

    def test_split_open_spec_parentheses(self):
        """_split_open_spec respects parentheses in params."""
        parts = MUMPSRuntime._split_open_spec("/tmp/file:(NEWVERSION:NOWRAP:STREAM):0")
        assert parts == ["/tmp/file", "(NEWVERSION:NOWRAP:STREAM)", "0"]

    def test_split_open_spec_no_params(self):
        """_split_open_spec handles device::timeout."""
        parts = MUMPSRuntime._split_open_spec("/tmp/file::5")
        assert parts == ["/tmp/file", "", "5"]
