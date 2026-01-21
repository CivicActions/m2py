"""Tests for ZTSTART/ZTCOMMIT command code generation (YDB extension).

Reference: YottaDB Z-Commands
Spec 015: Verify NotImplementedError for ZTSTART/ZTCOMMIT (YDB journaled transactions).

ZTSTART/ZTCOMMIT begin/commit journaled transactions in YDB.
Unlike TSTART/TCOMMIT, these are specifically for journaled transaction processing.
These are YDB-specific features that cannot be transpiled to pure Python.
"""

import pytest
from m2py.codegen import generate_python


@pytest.mark.codegen
@pytest.mark.ydb
class TestZtstartCodegen:
    """Codegen-level tests for ZTSTART command (YDB extension).

    ZTSTART begins a journaled transaction in YDB.
    It cannot be transpiled to pure Python and raises NotImplementedError.
    """

    def test_ztstart_raises_not_implemented(self):
        """ZTSTART raises NotImplementedError (unsupported YDB feature)."""
        code = "TEST\n ZTS\n Q"
        with pytest.raises(NotImplementedError, match="MZTStartStatement"):
            generate_python(code)

    def test_ztstart_full_command_raises_not_implemented(self):
        """ZTSTART (full keyword) raises NotImplementedError."""
        code = "TEST\n ZTSTART\n Q"
        with pytest.raises(NotImplementedError, match="MZTStartStatement"):
            generate_python(code)

    def test_ztstart_with_postcondition_raises_not_implemented(self):
        """ZTSTART with postcondition raises NotImplementedError."""
        code = "TEST\n ZTS:1\n Q"
        with pytest.raises(NotImplementedError, match="MZTStartStatement"):
            generate_python(code)


@pytest.mark.codegen
@pytest.mark.ydb
class TestZtcommitCodegen:
    """Codegen-level tests for ZTCOMMIT command (YDB extension).

    ZTCOMMIT commits a journaled transaction started with ZTSTART.
    It cannot be transpiled to pure Python and raises NotImplementedError.
    """

    def test_ztcommit_raises_not_implemented(self):
        """ZTCOMMIT raises NotImplementedError (unsupported YDB feature)."""
        code = "TEST\n ZTC\n Q"
        with pytest.raises(NotImplementedError, match="MZTCommitStatement"):
            generate_python(code)

    def test_ztcommit_full_command_raises_not_implemented(self):
        """ZTCOMMIT (full keyword) raises NotImplementedError."""
        code = "TEST\n ZTCOMMIT\n Q"
        with pytest.raises(NotImplementedError, match="MZTCommitStatement"):
            generate_python(code)

    def test_ztcommit_with_level_raises_not_implemented(self):
        """ZTCOMMIT with level argument raises NotImplementedError."""
        code = "TEST\n ZTC 1\n Q"
        with pytest.raises(NotImplementedError, match="MZTCommitStatement"):
            generate_python(code)

    def test_ztcommit_with_postcondition_raises_not_implemented(self):
        """ZTCOMMIT with postcondition raises NotImplementedError."""
        code = "TEST\n ZTC:1\n Q"
        with pytest.raises(NotImplementedError, match="MZTCommitStatement"):
            generate_python(code)
