"""Tests for FileDevice read behaviour on write-only files.

When a file is opened in write-only mode ("w" or "a"), attempting to read
should return EOF immediately rather than raising ``io.UnsupportedOperation``.
This matches GT.M/YDB behaviour where ``READ X`` on a write-only device
returns an empty string with ``$ZEOF=1``.

These tests cover the fix in devices.py that catches
``io.UnsupportedOperation`` in ``FileDevice.read()`` and
``FileDevice.read_char()``.
"""

from m2py.runtime.devices import FileDevice


class TestFileDeviceWriteOnlyRead:
    """Reading from a write-only FileDevice returns EOF immediately."""

    def test_read_line_from_write_only(self, tmp_path):
        """read() with no maxlen on write-only file → empty + EOF."""
        f = tmp_path / "test.txt"
        file_obj = open(f, "w")
        dev = FileDevice(str(f), file_obj, "w")

        data, key = dev.read()
        assert data == ""
        assert key == ""
        assert dev.zeof is True

        file_obj.close()

    def test_read_maxlen_from_write_only(self, tmp_path):
        """read(maxlen=10) on write-only file → empty + EOF."""
        f = tmp_path / "test.txt"
        file_obj = open(f, "w")
        dev = FileDevice(str(f), file_obj, "w")

        data, key = dev.read(maxlen=10)
        assert data == ""
        assert key == ""
        assert dev.zeof is True

        file_obj.close()

    def test_read_char_from_write_only(self, tmp_path):
        """read_char() on write-only file → empty string + EOF."""
        f = tmp_path / "test.txt"
        file_obj = open(f, "w")
        dev = FileDevice(str(f), file_obj, "w")

        ch = dev.read_char()
        assert ch == ""
        assert dev.zeof is True
        assert dev.key == ""

        file_obj.close()

    def test_read_line_from_append_only(self, tmp_path):
        """read() on append-only ("a") file → empty + EOF."""
        f = tmp_path / "test.txt"
        f.write_text("existing content\n")
        file_obj = open(f, "a")
        dev = FileDevice(str(f), file_obj, "a")

        data, key = dev.read()
        assert data == ""
        assert key == ""
        assert dev.zeof is True

        file_obj.close()

    def test_read_char_from_append_only(self, tmp_path):
        """read_char() on append-only ("a") file → empty + EOF."""
        f = tmp_path / "test.txt"
        f.write_text("existing content\n")
        file_obj = open(f, "a")
        dev = FileDevice(str(f), file_obj, "a")

        ch = dev.read_char()
        assert ch == ""
        assert dev.zeof is True

        file_obj.close()

    def test_multiple_reads_from_write_only(self, tmp_path):
        """Multiple reads from write-only all return EOF consistently."""
        f = tmp_path / "test.txt"
        file_obj = open(f, "w")
        dev = FileDevice(str(f), file_obj, "w")

        # First read
        data1, _ = dev.read()
        assert data1 == ""
        assert dev.zeof is True

        # Second read — still EOF
        data2, _ = dev.read()
        assert data2 == ""
        assert dev.zeof is True

        # read_char also EOF
        ch = dev.read_char()
        assert ch == ""
        assert dev.zeof is True

        file_obj.close()

    def test_write_then_read_from_write_only(self, tmp_path):
        """After writing, read on write-only still returns EOF."""
        f = tmp_path / "test.txt"
        file_obj = open(f, "w")
        dev = FileDevice(str(f), file_obj, "w")

        dev.write("Hello, world!")
        dev.write_newline()

        # Reading from the same write-only handle should be EOF
        data, key = dev.read()
        assert data == ""
        assert key == ""
        assert dev.zeof is True

        file_obj.close()

    def test_zeof_initially_false(self, tmp_path):
        """zeof starts False even for write-only device."""
        f = tmp_path / "test.txt"
        file_obj = open(f, "w")
        dev = FileDevice(str(f), file_obj, "w")

        assert dev.zeof is False

        file_obj.close()


class TestFileDeviceReadableStillWorks:
    """Verify that readable files still work correctly after the fix."""

    def test_read_line_from_readable(self, tmp_path):
        """Normal read from readable file returns line content."""
        f = tmp_path / "test.txt"
        f.write_text("line1\nline2\n")
        file_obj = open(f, "r")
        dev = FileDevice(str(f), file_obj, "r")

        data, key = dev.read()
        assert data == "line1"
        assert key == chr(10)
        assert dev.zeof is False

        file_obj.close()

    def test_read_maxlen_from_readable(self, tmp_path):
        """read(maxlen=3) from readable file returns partial data."""
        f = tmp_path / "test.txt"
        f.write_text("Hello\n")
        file_obj = open(f, "r")
        dev = FileDevice(str(f), file_obj, "r")

        data, key = dev.read(maxlen=3)
        assert data == "Hel"
        assert dev.zeof is False

        file_obj.close()

    def test_read_char_from_readable(self, tmp_path):
        """read_char() from readable file returns single character."""
        f = tmp_path / "test.txt"
        f.write_text("AB")
        file_obj = open(f, "r")
        dev = FileDevice(str(f), file_obj, "r")

        ch = dev.read_char()
        assert ch == "A"
        assert dev.zeof is False

        file_obj.close()

    def test_read_through_eof_from_readable(self, tmp_path):
        """Reading past end of readable file sets zeof."""
        f = tmp_path / "test.txt"
        f.write_text("only line\n")
        file_obj = open(f, "r")
        dev = FileDevice(str(f), file_obj, "r")

        data1, _ = dev.read()
        assert data1 == "only line"
        assert dev.zeof is False

        data2, key2 = dev.read()
        assert data2 == ""
        assert key2 == ""
        assert dev.zeof is True

        file_obj.close()

    def test_read_char_through_eof(self, tmp_path):
        """read_char() through all chars then EOF."""
        f = tmp_path / "test.txt"
        f.write_text("X")
        file_obj = open(f, "r")
        dev = FileDevice(str(f), file_obj, "r")

        ch1 = dev.read_char()
        assert ch1 == "X"
        assert dev.zeof is False

        ch2 = dev.read_char()
        assert ch2 == ""
        assert dev.zeof is True

        file_obj.close()

    def test_read_no_trailing_newline(self, tmp_path):
        """File without trailing newline: data returned, next read is EOF."""
        f = tmp_path / "test.txt"
        f.write_text("no newline")
        file_obj = open(f, "r")
        dev = FileDevice(str(f), file_obj, "r")

        data, key = dev.read()
        assert data == "no newline"
        # Still get $KEY=LF for lines even without trailing newline
        assert key == chr(10)
        assert dev.zeof is False

        # Next read → EOF
        data2, key2 = dev.read()
        assert data2 == ""
        assert key2 == ""
        assert dev.zeof is True

        file_obj.close()
