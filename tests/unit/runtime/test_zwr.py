"""Tests for ZWR (ZWRITE) format import/export.

Covers:
- parse_zwr_line: simple values, quoted strings, $C() escapes, numeric/string subscripts
- parse_zwr_stream: skipping headers, comments, blank lines; error propagation
- serialize_zwr_node: proper quoting, round-trip with parse_zwr_line
- import_zwr / export_zwr: round-trip with InMemoryGlobalStorage (MDict backend)
- import_zwr with real VistA ZWR snippets
- CLI integration: m2py globals import / export
"""

from __future__ import annotations

import io
import textwrap
from pathlib import Path

import pytest

from m2py.runtime.zwr import (
    _decode_zwr_value,
    _encode_zwr_value,
    _format_subscript,
    _is_canonical_number,
    _parse_subscripts,
    export_zwr,
    import_zwr,
    parse_zwr_line,
    parse_zwr_stream,
    serialize_zwr_node,
)


# =============================================================================
# parse_zwr_line
# =============================================================================


class TestParseZwrLine:
    """Tests for parse_zwr_line (T052)."""

    def test_simple_numeric_subscripts(self):
        """Parse ZWR line with numeric subscripts and simple value."""
        name, subs, val = parse_zwr_line('^DD(2,0)="PATIENT"')
        assert name == "^DD"
        assert subs == ["2", "0"]
        assert val == "PATIENT"

    def test_string_subscripts(self):
        """Parse ZWR line with quoted string subscripts."""
        name, subs, val = parse_zwr_line('^DIC(19.1,0,"GL")="^DIC(19.1,"')
        assert name == "^DIC"
        assert subs == ["19.1", "0", "GL"]
        assert val == "^DIC(19.1,"

    def test_mixed_subscripts(self):
        """Parse ZWR line with mixed numeric and string subscripts."""
        name, subs, val = parse_zwr_line('^DD(2,.01,0)="NAME^RF^^0;1^K:$L(X)>30 X"')
        assert name == "^DD"
        assert subs == ["2", ".01", "0"]
        assert val == "NAME^RF^^0;1^K:$L(X)>30 X"

    def test_embedded_quotes_in_value(self):
        """Parse ZWR line with doubled quotes in the value."""
        name, subs, val = parse_zwr_line(
            '^DIC(19.1,3,1,1,0)="This key locks out ""Global List"" and ""Programmer Mode"""'
        )
        assert name == "^DIC"
        assert val == 'This key locks out "Global List" and "Programmer Mode"'

    def test_empty_string_value(self):
        """Parse ZWR line with empty string value."""
        name, subs, val = parse_zwr_line('^G(1)=""')
        assert name == "^G"
        assert subs == ["1"]
        assert val == ""

    def test_dollar_c_in_value(self):
        """Parse ZWR line with $C() encoding for non-printable characters."""
        name, subs, val = parse_zwr_line('^G(1)="hello"_$C(10)_"world"')
        assert name == "^G"
        assert val == "hello\nworld"

    def test_dollar_c_multi_arg(self):
        """Parse ZWR line with $C(n1,n2) multi-argument form."""
        name, subs, val = parse_zwr_line("^G(1)=$C(65,66,67)")
        assert name == "^G"
        assert val == "ABC"

    def test_dollar_c_only_value(self):
        """Parse ZWR line whose value is purely $C()."""
        name, subs, val = parse_zwr_line("^G(1)=$C(0)")
        assert val == "\x00"

    def test_percent_global(self):
        """Parse ZWR line with %-prefixed global name."""
        name, subs, val = parse_zwr_line('^%ZOSF("OS")="GT.M (Linux)"')
        assert name == "^%ZOSF"
        assert subs == ["OS"]
        assert val == "GT.M (Linux)"

    def test_no_subscripts(self):
        """Parse ZWR line with no subscripts (root node)."""
        name, subs, val = parse_zwr_line('^ZTSK="12345"')
        assert name == "^ZTSK"
        assert subs == []
        assert val == "12345"

    def test_quoted_subscript_with_embedded_quotes(self):
        """Parse subscripts containing doubled quotes."""
        name, subs, val = parse_zwr_line('^G("say ""hi""")="ok"')
        assert subs == ['say "hi"']

    def test_deep_subscripts(self):
        """Parse deeply nested subscripts (5+ levels)."""
        name, subs, val = parse_zwr_line('^DD(2,.01,0,1,2,3)="deep"')
        assert subs == ["2", ".01", "0", "1", "2", "3"]

    def test_invalid_line_raises(self):
        """Malformed lines raise ValueError."""
        with pytest.raises(ValueError):
            parse_zwr_line("not a ZWR line")

    def test_invalid_no_equals(self):
        """Line missing equals sign raises ValueError."""
        with pytest.raises(ValueError):
            parse_zwr_line("^DD(1,2)")

    def test_negative_subscript(self):
        """Parse ZWR line with negative numeric subscript."""
        name, subs, val = parse_zwr_line('^G(-1)="neg"')
        assert subs == ["-1"]

    def test_decimal_subscript(self):
        """Parse ZWR line with decimal subscript."""
        name, subs, val = parse_zwr_line('^G(.01)="decimal"')
        assert subs == [".01"]


# =============================================================================
# parse_zwr_stream
# =============================================================================


class TestParseZwrStream:
    """Tests for parse_zwr_stream (T052)."""

    def test_basic_stream(self):
        """Parse a multi-line ZWR stream."""
        text = textwrap.dedent("""\
            ^DD(2,0)="PATIENT"
            ^DD(2,.01,0)="NAME"
        """)
        results = list(parse_zwr_stream(io.StringIO(text)))
        assert len(results) == 2
        assert results[0] == ("^DD", ["2", "0"], "PATIENT")
        assert results[1] == ("^DD", ["2", ".01", "0"], "NAME")

    def test_skips_headers(self):
        """ZWR header lines (non-^ lines) are skipped."""
        text = textwrap.dedent("""\
            OSEHRA ZGO Export: SECURITY KEY
            25-NOV-2019 15:23:25 ZWR
            ^DIC(19.1,0)="SECURITY KEY^19.1^634^586"
        """)
        results = list(parse_zwr_stream(io.StringIO(text)))
        assert len(results) == 1
        assert results[0][0] == "^DIC"

    def test_skips_comments(self):
        """Comment lines (starting with ;) are skipped."""
        text = '; This is a comment\n^G(1)="val"\n'
        results = list(parse_zwr_stream(io.StringIO(text)))
        assert len(results) == 1

    def test_skips_blank_lines(self):
        """Blank lines are skipped."""
        text = '\n\n^G(1)="val"\n\n^G(2)="val2"\n\n'
        results = list(parse_zwr_stream(io.StringIO(text)))
        assert len(results) == 2

    def test_error_includes_line_number(self):
        """Malformed data line reports line number."""
        text = '^G(1)="ok"\nBAD LINE\n'
        with pytest.raises(ValueError, match="Line 2"):
            list(parse_zwr_stream(io.StringIO(text)))

    def test_empty_stream(self):
        """Empty stream produces no results."""
        assert list(parse_zwr_stream(io.StringIO(""))) == []


# =============================================================================
# serialize_zwr_node
# =============================================================================


class TestSerializeZwrNode:
    """Tests for serialize_zwr_node (T053)."""

    def test_simple(self):
        """Serialize a simple node."""
        line = serialize_zwr_node("^DD", ["2", "0"], "PATIENT")
        assert line == '^DD(2,0)="PATIENT"'

    def test_string_subscripts_quoted(self):
        """String subscripts are quoted."""
        line = serialize_zwr_node("^DIC", ["19.1", "0", "GL"], "^DIC(19.1,")
        assert '"GL"' in line
        assert "19.1" in line  # numeric, unquoted

    def test_embedded_quotes(self):
        """Embedded quotes in value are doubled."""
        line = serialize_zwr_node("^G", ["1"], 'say "hi"')
        assert '""' in line

    def test_no_subscripts(self):
        """Serialize root node (no subscripts)."""
        line = serialize_zwr_node("^ZTSK", [], "12345")
        assert line == '^ZTSK="12345"'

    def test_empty_value(self):
        """Serialize empty string value."""
        line = serialize_zwr_node("^G", ["1"], "")
        assert line == '^G(1)=""'

    def test_non_printable_chars(self):
        """Non-printable characters produce $C() encoding."""
        line = serialize_zwr_node("^G", ["1"], "hello\nworld")
        assert "$C(10)" in line
        assert '"hello"' in line
        assert '"world"' in line


# =============================================================================
# Round-trip: serialize → parse
# =============================================================================


class TestRoundTrip:
    """Tests for serialize_zwr_node ↔ parse_zwr_line round-trip (T053)."""

    @pytest.mark.parametrize(
        "name, subs, value",
        [
            ("^DD", ["2", "0"], "PATIENT"),
            ("^DD", ["2", ".01", "0"], "NAME^RF^^0;1^K:$L(X)>30 X"),
            ("^G", ["1"], ""),
            ("^G", ["1"], 'say "hello"'),
            ("^%ZOSF", ["OS"], "GT.M (Linux)"),
            ("^G", [], "root value"),
            ("^G", ["-1", "0"], "negative"),
            ("^G", ["1"], "line1\nline2\ttab"),
        ],
        ids=[
            "simple",
            "complex_value",
            "empty_value",
            "embedded_quotes",
            "percent_global",
            "root_node",
            "negative_sub",
            "non_printable",
        ],
    )
    def test_round_trip(self, name: str, subs: list[str], value: str):
        """serialize → parse → equals original."""
        line = serialize_zwr_node(name, subs, value)
        parsed_name, parsed_subs, parsed_value = parse_zwr_line(line)
        assert parsed_name == name
        assert parsed_subs == subs
        assert parsed_value == value


# =============================================================================
# import_zwr / export_zwr round-trip
# =============================================================================


class TestImportExport:
    """Tests for import_zwr and export_zwr (T054)."""

    def _make_backend(self):
        """Create an InMemoryGlobalStorage backend."""
        from m2py.runtime.globals import InMemoryGlobalStorage

        return InMemoryGlobalStorage()

    def test_import_counts(self, tmp_path: Path):
        """import_zwr returns correct node count."""
        zwr_file = tmp_path / "test.zwr"
        zwr_file.write_text('^DD(2,0)="PATIENT"\n^DD(2,.01,0)="NAME"\n')
        backend = self._make_backend()
        count = import_zwr(backend, zwr_file)
        assert count == 2

    def test_import_sets_values(self, tmp_path: Path):
        """import_zwr correctly stores values in backend."""
        zwr_file = tmp_path / "test.zwr"
        zwr_file.write_text('^DD(2,0)="PATIENT"\n^DD(2,.01,0)="NAME"\n')
        backend = self._make_backend()
        import_zwr(backend, zwr_file)
        assert backend.get("DD", ("2", "0")) == "PATIENT"
        assert backend.get("DD", ("2", ".01", "0")) == "NAME"

    def test_import_from_stream(self):
        """import_zwr works with a TextIO stream."""
        stream = io.StringIO('^G(1)="hello"\n^G(2)="world"\n')
        backend = self._make_backend()
        count = import_zwr(backend, stream)
        assert count == 2
        assert backend.get("G", ("1",)) == "hello"
        assert backend.get("G", ("2",)) == "world"

    def test_import_skips_headers(self, tmp_path: Path):
        """import_zwr skips ZWR header lines."""
        zwr_file = tmp_path / "test.zwr"
        zwr_file.write_text(
            'OSEHRA ZGO Export: TEST\n25-NOV-2019 15:23:25 ZWR\n^G(1)="val"\n'
        )
        backend = self._make_backend()
        count = import_zwr(backend, zwr_file)
        assert count == 1

    def test_export_basic(self, tmp_path: Path):
        """export_zwr writes correct ZWR format."""
        backend = self._make_backend()
        backend.set("DD", ("2", "0"), "PATIENT")
        backend.set("DD", ("2", ".01", "0"), "NAME")

        out_file = tmp_path / "out.zwr"
        count = export_zwr(backend, ["^DD"], out_file)
        assert count == 2

        content = out_file.read_text()
        assert "^DD" in content
        assert "PATIENT" in content
        assert "NAME" in content

    def test_export_to_stream(self):
        """export_zwr writes to a TextIO stream."""
        backend = self._make_backend()
        backend.set("G", ("1",), "hello")
        stream = io.StringIO()
        count = export_zwr(backend, ["G"], stream)
        assert count == 1
        assert "hello" in stream.getvalue()

    def test_import_export_round_trip(self, tmp_path: Path):
        """import → export round-trip preserves data."""
        zwr_content = textwrap.dedent("""\
            ^DD(2,0)="PATIENT"
            ^DD(2,.01,0)="NAME^RF^^0;1^K:$L(X)>30 X"
            ^DD(2,.09,0)="SSN^RFJ9^^0;9"
        """)
        zwr_file = tmp_path / "input.zwr"
        zwr_file.write_text(zwr_content)

        backend = self._make_backend()
        import_count = import_zwr(backend, zwr_file)
        assert import_count == 3

        out_file = tmp_path / "output.zwr"
        export_count = export_zwr(backend, ["^DD"], out_file)
        assert export_count == 3

        # Re-import exported data and verify values match
        backend2 = self._make_backend()
        reimport_count = import_zwr(backend2, out_file)
        assert reimport_count == 3
        assert backend2.get("DD", ("2", "0")) == "PATIENT"
        assert backend2.get("DD", ("2", ".01", "0")) == "NAME^RF^^0;1^K:$L(X)>30 X"
        assert backend2.get("DD", ("2", ".09", "0")) == "SSN^RFJ9^^0;9"

    def test_export_multiple_globals(self, tmp_path: Path):
        """export_zwr handles multiple global names."""
        backend = self._make_backend()
        backend.set("DD", ("1",), "v1")
        backend.set("DIC", ("1",), "v2")

        out_file = tmp_path / "out.zwr"
        count = export_zwr(backend, ["^DD", "^DIC"], out_file)
        assert count == 2

        content = out_file.read_text()
        assert "^DD" in content
        assert "^DIC" in content

    def test_export_empty_global(self, tmp_path: Path):
        """export_zwr with non-existent global produces no output."""
        backend = self._make_backend()
        out_file = tmp_path / "out.zwr"
        count = export_zwr(backend, ["^NOSUCH"], out_file)
        assert count == 0
        assert out_file.read_text() == ""

    def test_import_embedded_quotes(self, tmp_path: Path):
        """import_zwr handles values with embedded quotes."""
        zwr_file = tmp_path / "quotes.zwr"
        zwr_file.write_text(
            '^G(1)="This key locks out ""Global List"" and ""Programmer Mode"""\n'
        )
        backend = self._make_backend()
        import_zwr(backend, zwr_file)
        assert (
            backend.get("G", ("1",))
            == 'This key locks out "Global List" and "Programmer Mode"'
        )

    def test_import_dollar_c_value(self, tmp_path: Path):
        """import_zwr handles $C() encoded values."""
        zwr_file = tmp_path / "dollar_c.zwr"
        zwr_file.write_text('^G(1)="hello"_$C(10)_"world"\n')
        backend = self._make_backend()
        import_zwr(backend, zwr_file)
        assert backend.get("G", ("1",)) == "hello\nworld"

    def test_import_non_utf8_bytes(self, tmp_path: Path):
        """import_zwr handles files with non-UTF-8 bytes (e.g., 0xa7).

        VistA DD.zwr contains legacy data with bytes that aren't valid
        UTF-8.  import_zwr should use ``errors='replace'`` so these
        don't crash the import — the replacement character (U+FFFD) is
        acceptable for non-standard byte values.
        """
        zwr_file = tmp_path / "non_utf8.zwr"
        # Write raw bytes: a valid ZWR line with a 0xa7 byte in the value
        zwr_file.write_bytes(b'^G(1)="hello\xa7world"\n')
        backend = self._make_backend()
        count = import_zwr(backend, zwr_file)
        assert count == 1
        val = backend.get("G", ("1",))
        assert "hello" in val
        assert "world" in val

    def test_import_non_utf8_multiple_lines(self, tmp_path: Path):
        """import_zwr handles multiple lines with non-UTF-8 bytes.

        Ensures errors='replace' doesn't stop after first bad byte — all
        lines are imported, with replacement characters where needed.
        """
        zwr_file = tmp_path / "multi_bad.zwr"
        zwr_file.write_bytes(
            b'^G(1)="line\x80one"\n^G(2)="normal"\n^G(3)="line\xff\xfethree"\n'
        )
        backend = self._make_backend()
        count = import_zwr(backend, zwr_file)
        assert count == 3
        assert "normal" == backend.get("G", ("2",))
        # Bad bytes replaced, but surrounding text preserved
        val1 = backend.get("G", ("1",))
        assert "line" in val1 and "one" in val1
        val3 = backend.get("G", ("3",))
        assert "line" in val3 and "three" in val3

    def test_import_non_utf8_in_subscript_area(self, tmp_path: Path):
        """import_zwr handles non-UTF-8 bytes in the subscript portion.

        The bad bytes might appear anywhere in the line, not just values.
        """
        zwr_file = tmp_path / "bad_sub.zwr"
        # 0xfe byte in a subscript value area
        zwr_file.write_bytes(b'^G("a\xfeb")="ok"\n')
        backend = self._make_backend()
        count = import_zwr(backend, zwr_file)
        assert count == 1

    def test_import_stream_not_affected_by_errors_replace(self):
        """import_zwr from stream (StringIO) still works normally.

        The errors='replace' is only applied to Path-based file opens.
        StringIO sources should work unchanged.
        """
        stream = io.StringIO('^G(1)="hello"\n^G(2)="world"\n')
        backend = self._make_backend()
        count = import_zwr(backend, stream)
        assert count == 2
        assert backend.get("G", ("1",)) == "hello"
        assert backend.get("G", ("2",)) == "world"


# =============================================================================
# Real VistA ZWR snippets (T055)
# =============================================================================


class TestVistaZwrSnippets:
    """Test import of real-world VistA ZWR data patterns."""

    def _make_backend(self):
        from m2py.runtime.globals import InMemoryGlobalStorage

        return InMemoryGlobalStorage()

    def test_security_key_excerpt(self):
        """Parse a real SECURITY KEY excerpt from VistA-M."""
        zwr_text = textwrap.dedent("""\
            OSEHRA ZGO Export: SECURITY KEY
            25-NOV-2019 15:23:25 ZWR
            ^DIC(19.1,0)="SECURITY KEY^19.1^634^586"
            ^DIC(19.1,0,"DD")="#"
            ^DIC(19.1,0,"DEL")="#"
            ^DIC(19.1,0,"GL")="^DIC(19.1,"
            ^DIC(19.1,1,0)="XUPROG"
        """)
        backend = self._make_backend()
        count = import_zwr(backend, io.StringIO(zwr_text))
        assert count == 5
        assert backend.get("DIC", ("19.1", "0")) == "SECURITY KEY^19.1^634^586"
        assert backend.get("DIC", ("19.1", "0", "GL")) == "^DIC(19.1,"
        assert backend.get("DIC", ("19.1", "1", "0")) == "XUPROG"

    def test_dd_field_definition(self):
        """Parse DD (Data Dictionary) field definition patterns."""
        zwr_text = textwrap.dedent("""\
            ^DD(2,.01,0)="NAME^RF^^0;1^K:$L(X)>30!(X?.N)!($L(X)<2) X"
            ^DD(2,.01,1,0)="^.1"
            ^DD(2,.01,3)="NAME MUST BE 2-30 CHARACTERS, NOT NUMERIC."
        """)
        backend = self._make_backend()
        count = import_zwr(backend, io.StringIO(zwr_text))
        assert count == 3
        val = backend.get("DD", ("2", ".01", "0"))
        assert val is not None
        assert "NAME^RF" in val

    def test_value_with_embedded_quotes(self):
        """Parse value with multiple levels of doubled quotes."""
        line = '^DIC(19.1,2,1,5,0)="1. It allows its holders to create ""Routine""-type Options in the"'
        name, subs, val = parse_zwr_line(line)
        assert '"Routine"' in val
        assert subs == ["19.1", "2", "1", "5", "0"]

    def test_percent_zosf_pattern(self):
        """Parse ^%ZOSF entries (common in Kernel)."""
        zwr_text = (
            '^%ZOSF("OS")="GT.M (Linux)"\n'
            '^%ZOSF("TRAP")="S $ZT=""G VSTERR^ZU"""\n'
            '^%ZOSF("LPC")="U IO:NOECHO"\n'
        )
        backend = self._make_backend()
        count = import_zwr(backend, io.StringIO(zwr_text))
        assert count == 3
        assert backend.get("%ZOSF", ("OS",)) == "GT.M (Linux)"
        assert backend.get("%ZOSF", ("LPC",)) == "U IO:NOECHO"

    def test_dialog_zwr_pattern(self):
        """Parse ^DI(.84) DIALOG entries used by M XML Parser."""
        zwr_text = textwrap.dedent("""\
            ^DI(.84,9500001,0)="9500001^1^^"
            ^DI(.84,9500001,1)="XML Parsing Error"
        """)
        backend = self._make_backend()
        count = import_zwr(backend, io.StringIO(zwr_text))
        assert count == 2
        assert backend.get("DI", (".84", "9500001", "0")) == "9500001^1^^"


# =============================================================================
# CLI integration tests (T056)
# =============================================================================


class TestGlobalsCli:
    """Tests for m2py globals import/export CLI."""

    def test_globals_import(self, tmp_path: Path):
        """m2py globals import reads a ZWR file."""
        from m2py.cli import main

        zwr_file = tmp_path / "test.zwr"
        zwr_file.write_text('^G(1)="hello"\n^G(2)="world"\n')

        exit_code = main(["globals", "import", str(zwr_file)])
        assert exit_code == 0

    def test_globals_import_missing_file(self, tmp_path: Path):
        """m2py globals import with nonexistent file returns error."""
        from m2py.cli import main

        exit_code = main(["globals", "import", str(tmp_path / "nope.zwr")])
        assert exit_code == 2  # click.Path(exists=True) gives UsageError (code 2)

    def test_globals_export(self, tmp_path: Path):
        """m2py globals export writes a ZWR file (empty, no data loaded)."""
        from m2py.cli import main

        out_file = tmp_path / "out.zwr"
        exit_code = main(["globals", "export", str(out_file), "--globals", "^DD"])
        assert exit_code == 0

    def test_globals_no_subcommand(self, capsys):
        """m2py globals with no subcommand shows help."""
        from click.testing import CliRunner

        from m2py.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["globals"])
        assert result.exit_code == 0
        assert "import" in result.output or "export" in result.output

    def test_cli_transpile_subcommand(self, tmp_path: Path):
        """m2py transpile <PATH> works as a subcommand."""
        from m2py.cli import main

        m_file = tmp_path / "HELLO.m"
        m_file.write_text("HELLO\n Q\n")
        exit_code = main(["transpile", str(m_file)])
        assert exit_code == 0


# =============================================================================
# Internal helpers
# =============================================================================


class TestInternalHelpers:
    """Tests for internal helper functions."""

    def test_is_canonical_number(self):
        """Verify canonical number detection."""
        assert _is_canonical_number("0")
        assert _is_canonical_number("1")
        assert _is_canonical_number("-1")
        assert _is_canonical_number("123")
        assert _is_canonical_number(".5")
        assert _is_canonical_number("-.5")
        assert _is_canonical_number("1.5")
        assert not _is_canonical_number("01")
        assert not _is_canonical_number("1.0")
        assert not _is_canonical_number("+1")
        assert not _is_canonical_number("1.50")
        assert not _is_canonical_number("")
        assert not _is_canonical_number("abc")

    def test_format_subscript_numeric(self):
        """Numeric subscripts are unquoted."""
        assert _format_subscript("1") == "1"
        assert _format_subscript("0") == "0"
        assert _format_subscript("-1") == "-1"
        assert _format_subscript(".5") == ".5"

    def test_format_subscript_string(self):
        """String subscripts are quoted."""
        assert _format_subscript("NAME") == '"NAME"'
        assert _format_subscript("GL") == '"GL"'
        # Value with quotes gets doubled inner quotes in ZWR format
        expected = '"say ""hi""' + '"'
        result = _format_subscript('say "hi"')
        assert result == expected

    def test_parse_subscripts_complex(self):
        """Parse subscripts with various patterns."""
        assert _parse_subscripts("1,2,3") == ["1", "2", "3"]
        assert _parse_subscripts('"A","B"') == ["A", "B"]
        assert _parse_subscripts('1,"A",2') == ["1", "A", "2"]
        assert _parse_subscripts('"say ""hi""' + '"') == ['say "hi"']

    def test_decode_value_simple(self):
        """Decode simple quoted value."""
        assert _decode_zwr_value('"hello"') == "hello"

    def test_decode_value_quotes(self):
        """Decode value with doubled quotes."""
        assert _decode_zwr_value('"say ""hi""' + '"') == 'say "hi"'

    def test_decode_value_dollar_c(self):
        """Decode $C() encoded value."""
        assert _decode_zwr_value("$C(65,66,67)") == "ABC"
        assert _decode_zwr_value('"a"_$C(10)_"b"') == "a\nb"

    def test_encode_value_simple(self):
        """Encode simple string."""
        assert _encode_zwr_value("hello") == '"hello"'

    def test_encode_value_empty(self):
        """Encode empty string."""
        assert _encode_zwr_value("") == '""'

    def test_encode_value_quotes(self):
        """Encode string with quotes."""
        assert _encode_zwr_value('say "hi"') == '"say ""hi""' + '"'

    def test_encode_value_non_printable(self):
        """Encode string with non-printable characters."""
        encoded = _encode_zwr_value("a\nb")
        assert "$C(10)" in encoded
        assert '"a"' in encoded
        assert '"b"' in encoded
