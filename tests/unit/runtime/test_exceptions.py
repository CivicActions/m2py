"""Tests for runtime exceptions."""

import pytest

from m2py.runtime.exceptions import MRuntimeError


class TestMRuntimeError:
    """Tests for MRuntimeError exception."""

    def test_basic_error(self):
        """MRuntimeError can be raised with a message."""
        with pytest.raises(MRuntimeError) as exc_info:
            raise MRuntimeError("Test error")
        # MRuntimeError prefixes with "M-"
        assert str(exc_info.value) == "M-Test error"

    def test_with_error_code(self):
        """MRuntimeError can include MUMPS error code."""
        err = MRuntimeError("UNDEF", "Variable X is undefined")
        assert "Variable X is undefined" in str(err)

    def test_inherits_from_exception(self):
        """MRuntimeError inherits from Exception."""
        assert issubclass(MRuntimeError, Exception)

    def test_catch_as_exception(self):
        """MRuntimeError can be caught as Exception."""
        try:
            raise MRuntimeError("Test")
        except Exception as e:
            assert isinstance(e, MRuntimeError)
