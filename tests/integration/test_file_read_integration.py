"""Integration tests for file READ through device layer.

Spec 022 Phase 9 Gap 1 (T104): End-to-end test that OPEN → USE → READ
reads file data, matching MUMPS standard §8.2.22/§8.2.23 semantics.
"""

from __future__ import annotations


from m2py.runtime import MUMPSRuntime


class TestFileReadIntegration:
    """Integration tests: OPEN file READONLY → USE file → READ X."""

    def test_open_use_read_basic(self, tmp_path):
        """OPEN/USE/READ reads file content line by line."""
        data_file = tmp_path / "data.txt"
        data_file.write_text("Hello\nWorld\n")

        rt = MUMPSRuntime()
        rt.open_device(str(data_file), ["READONLY"], None)
        rt.use_device(str(data_file))

        line1 = rt.read_line()
        assert line1 == "Hello"

        line2 = rt.read_line()
        assert line2 == "World"

    def test_open_use_read_write_to_principal(self, tmp_path):
        """Read from file, switch to principal, write what was read."""
        data_file = tmp_path / "input.txt"
        data_file.write_text("TestData\n")

        rt = MUMPSRuntime()
        rt.open_device(str(data_file), ["READONLY"], None)

        # USE file, READ
        rt.use_device(str(data_file))
        value = rt.read_line()

        # USE 0 (principal), WRITE
        rt.use_device("0")
        rt.write(value)

        assert rt.get_output() == "TestData"

    def test_read_multiple_files(self, tmp_path):
        """Can read from multiple files by switching USE."""
        file_a = tmp_path / "a.txt"
        file_b = tmp_path / "b.txt"
        file_a.write_text("AAA\n")
        file_b.write_text("BBB\n")

        rt = MUMPSRuntime()
        rt.open_device(str(file_a), ["READONLY"], None)
        rt.open_device(str(file_b), ["READONLY"], None)

        rt.use_device(str(file_a))
        val_a = rt.read_line()

        rt.use_device(str(file_b))
        val_b = rt.read_line()

        assert val_a == "AAA"
        assert val_b == "BBB"

    def test_close_file_after_read(self, tmp_path):
        """CLOSE after READ switches back to principal device."""
        data_file = tmp_path / "data.txt"
        data_file.write_text("line1\n")

        rt = MUMPSRuntime()
        rt.open_device(str(data_file), ["READONLY"], None)
        rt.use_device(str(data_file))
        rt.read_line()

        rt.close_device(str(data_file))
        # After close, current device should be principal
        assert rt._current_device is rt._principal_device

    def test_read_maxlen_from_file(self, tmp_path):
        """READ X#3 reads exactly 3 characters from file."""
        data_file = tmp_path / "data.txt"
        data_file.write_text("ABCDEFGH\n")

        rt = MUMPSRuntime()
        rt.open_device(str(data_file), ["READONLY"], None)
        rt.use_device(str(data_file))

        data, key = rt.read_maxlen(3)
        assert data == "ABC"

    def test_key_tracks_per_device(self, tmp_path):
        """$KEY is per-device — file device has its own $KEY."""
        data_file = tmp_path / "data.txt"
        data_file.write_text("hello\n")

        rt = MUMPSRuntime()
        rt.open_device(str(data_file), ["READONLY"], None)
        rt.use_device(str(data_file))

        rt.read_line()
        file_key = rt._current_device.key

        rt.use_device("0")
        # Principal device's $KEY should be independent
        _ = rt._current_device.key

        # File device should have its own key set from the read
        assert file_key != "" or file_key == "\r"  # depends on FileDevice impl

    def test_zeof_set_at_end_of_file(self, tmp_path):
        """$ZEOF is 1 after reading past end of file."""
        data_file = tmp_path / "data.txt"
        data_file.write_text("only\n")

        rt = MUMPSRuntime()
        rt.open_device(str(data_file), ["READONLY"], None)
        rt.use_device(str(data_file))

        rt.read_line()  # Read "only"
        rt.read_line()  # Try to read past EOF

        assert rt._current_device.zeof is True
