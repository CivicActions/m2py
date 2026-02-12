"""Unit tests for READ #maxlen (Spec 021 Phase 9).

Tests for:
- T058: m_read_maxlen() — basic limit, early newline, edge cases
- T059: m_read_maxlen_timeout() — combined maxlen+timeout
- T060: $KEY population after READ
"""

import io
from unittest.mock import patch

import pytest

from m2py.runtime.helpers import m_read_maxlen, m_read_maxlen_timeout


@pytest.mark.codegen
class TestReadMaxlen:
    """T058: Tests for m_read_maxlen()."""

    def test_basic_limit(self):
        """READ X#5 reads at most 5 characters."""
        with patch("sys.stdin", io.StringIO("ABCDEFGH")):
            value, key = m_read_maxlen(5)
        assert value == "ABCDE"
        assert key == ""  # maxlen reached, no terminator

    def test_early_newline(self):
        """READ X#10 stops at newline before maxlen."""
        with patch("sys.stdin", io.StringIO("ABC\nDEF")):
            value, key = m_read_maxlen(10)
        assert value == "ABC"
        assert key == "\n"  # terminated by newline

    def test_exact_length(self):
        """Input exactly matches maxlen."""
        with patch("sys.stdin", io.StringIO("ABC")):
            value, key = m_read_maxlen(3)
        assert value == "ABC"
        assert key == ""  # maxlen reached

    def test_eof_before_maxlen(self):
        """EOF before maxlen reached."""
        with patch("sys.stdin", io.StringIO("AB")):
            value, key = m_read_maxlen(5)
        assert value == "AB"
        assert key == ""  # EOF, no explicit terminator

    def test_maxlen_1(self):
        """READ X#1 reads single character."""
        with patch("sys.stdin", io.StringIO("Hello")):
            value, key = m_read_maxlen(1)
        assert value == "H"
        assert key == ""

    def test_maxlen_zero_raises(self):
        """READ X#0 raises ValueError (YDB: %YDB-E-RDFLTOOSHORT)."""
        with pytest.raises(ValueError, match="less than or equal to zero"):
            m_read_maxlen(0)

    def test_maxlen_negative_raises(self):
        """READ X#-1 raises ValueError."""
        with pytest.raises(ValueError, match="less than or equal to zero"):
            m_read_maxlen(-1)

    def test_newline_only_input(self):
        """READ X#5 with only newline in input returns empty string."""
        with patch("sys.stdin", io.StringIO("\n")):
            value, key = m_read_maxlen(5)
        assert value == ""
        assert key == "\n"

    def test_empty_input(self):
        """READ X#5 with empty stdin returns empty string."""
        with patch("sys.stdin", io.StringIO("")):
            value, key = m_read_maxlen(5)
        assert value == ""
        assert key == ""


@pytest.mark.codegen
class TestReadMaxlenTimeout:
    """T059: Tests for m_read_maxlen_timeout()."""

    def test_immediate_data(self):
        """Data available immediately within timeout."""
        import select as select_mod

        stdin_mock = io.StringIO("ABCDEFGH")
        with (
            patch("sys.stdin", stdin_mock),
            patch.object(select_mod, "select", return_value=([stdin_mock], [], [])),
        ):
            value, key, test = m_read_maxlen_timeout(5, 10.0)
        assert value == "ABCDE"
        assert key == ""
        assert test == 1

    def test_newline_before_maxlen(self):
        """Newline terminates before maxlen within timeout."""
        import select as select_mod

        stdin_mock = io.StringIO("AB\nCD")
        with (
            patch("sys.stdin", stdin_mock),
            patch.object(select_mod, "select", return_value=([stdin_mock], [], [])),
        ):
            value, key, test = m_read_maxlen_timeout(5, 10.0)
        assert value == "AB"
        assert key == "\n"
        assert test == 1

    def test_maxlen_zero_raises(self):
        """Combined maxlen+timeout with maxlen=0 raises."""
        with pytest.raises(ValueError, match="less than or equal to zero"):
            m_read_maxlen_timeout(0, 5.0)

    def test_timeout_returns_empty(self):
        """Timeout with no data returns empty string and test=0."""
        import select as select_mod

        stdin_mock = io.StringIO("")
        with (
            patch("sys.stdin", stdin_mock),
            patch.object(select_mod, "select", return_value=([], [], [])),
        ):
            value, key, test = m_read_maxlen_timeout(5, 0.001)
        assert value == ""
        assert key == ""
        assert test == 0


@pytest.mark.codegen
class TestKeyPopulation:
    """T060: Tests for $KEY population after READ."""

    def test_key_set_on_newline(self):
        """$KEY is newline when READ terminated by Enter."""
        with patch("sys.stdin", io.StringIO("ABC\n")):
            value, key = m_read_maxlen(10)
        assert key == "\n"

    def test_key_empty_on_maxlen(self):
        """$KEY is empty when READ terminated by maxlen."""
        with patch("sys.stdin", io.StringIO("ABCDEFGH")):
            value, key = m_read_maxlen(5)
        assert key == ""

    def test_key_empty_on_eof(self):
        """$KEY is empty when READ terminated by EOF."""
        with patch("sys.stdin", io.StringIO("AB")):
            value, key = m_read_maxlen(5)
        assert key == ""
