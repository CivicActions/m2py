"""Unit tests for YDB SVNs ($ZSEARCH, $ZMESSAGE, $ZRO, $ZJOB).

Spec 021 Phase 14 (T090-T092): Tests for YDB-specific special variables.
"""

import pytest
from m2py.runtime import MUMPSRuntime
from m2py.runtime.helpers import m_zmessage


@pytest.mark.codegen
class TestZsearch:
    """Tests for $ZSEARCH — file system search with iterator."""

    def test_first_call_returns_match(self, tmp_path):
        """$ZSEARCH returns first matching file."""
        # Create test files
        (tmp_path / "test1.txt").write_text("a")
        (tmp_path / "test2.txt").write_text("b")
        rt = MUMPSRuntime()
        result = rt.zsearch(str(tmp_path / "*.txt"))
        assert result != ""
        assert "test" in result

    def test_successive_calls_iterate(self, tmp_path):
        """Successive $ZSEARCH("") returns next matches."""
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        rt = MUMPSRuntime()
        first = rt.zsearch(str(tmp_path / "*.txt"))
        second = rt.zsearch("")
        assert first != ""
        assert second != ""
        assert first != second

    def test_empty_on_exhaustion(self, tmp_path):
        """$ZSEARCH returns '' when no more matches."""
        (tmp_path / "only.txt").write_text("x")
        rt = MUMPSRuntime()
        rt.zsearch(str(tmp_path / "*.txt"))
        # Second call should exhaust
        result = rt.zsearch("")
        assert result == ""

    def test_no_matches(self, tmp_path):
        """$ZSEARCH returns '' for no matching files."""
        rt = MUMPSRuntime()
        result = rt.zsearch(str(tmp_path / "*.nonexistent"))
        assert result == ""

    def test_new_pattern_resets_iterator(self, tmp_path):
        """New pattern resets the search iterator."""
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.log").write_text("b")
        rt = MUMPSRuntime()
        rt.zsearch(str(tmp_path / "*.txt"))
        # Start new search with different pattern
        result = rt.zsearch(str(tmp_path / "*.log"))
        assert result.endswith("b.log")


@pytest.mark.codegen
class TestZmessageText:
    """Tests for $ZMESSAGE — error code to message text."""

    def test_known_code_returns_message(self):
        """Known error code returns formatted message."""
        result = m_zmessage(150373850)
        assert result == "%YDB-E-LVUNDEF"

    def test_unknown_code_returns_string(self):
        """Unknown code returns code as string."""
        result = m_zmessage(999999)
        assert result == "999999"

    def test_string_code(self):
        """String code is converted to int."""
        result = m_zmessage("150373850")
        assert result == "%YDB-E-LVUNDEF"

    def test_non_numeric_returns_as_is(self):
        """Non-numeric string returns as-is."""
        result = m_zmessage("abc")
        assert result == "abc"

    def test_divzero(self):
        """$ZMESSAGE for DIVZERO."""
        result = m_zmessage(150372826)
        assert "DIVZERO" in result

    def test_selectfalse(self):
        """$ZMESSAGE for SELECTFALSE."""
        result = m_zmessage(150374562)
        assert "SELECTFALSE" in result


@pytest.mark.codegen
class TestZro:
    """Tests for $ZRO — routine search path."""

    def test_default_returns_dot(self):
        """$ZRO returns '.' by default."""
        rt = MUMPSRuntime()
        assert rt.zro() == "."


@pytest.mark.codegen
class TestZjob:
    """Tests for $ZJOB — last JOB'd process ID."""

    def test_initial_value_is_zero(self):
        """$ZJOB is '0' before any JOB command."""
        rt = MUMPSRuntime()
        assert rt.zjob() == "0"
