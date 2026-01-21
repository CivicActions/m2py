"""Tests for ZLOAD command code generation (YDB extension).

Reference: YottaDB Z-Commands
Spec 015: Verify NotImplementedError for ZLOAD (YDB-specific routine loading).

ZLOAD (ZL) loads a routine object file without compilation, unlike ZLINK.
This is a YDB-specific feature that cannot be transpiled to pure Python.
"""

import pytest
from m2py.codegen import generate_python


@pytest.mark.codegen
@pytest.mark.ydb
class TestZloadCodegen:
    """Codegen-level tests for ZLOAD command (YDB extension).

    ZLOAD is a YDB-specific command for loading routine object files.
    It cannot be transpiled to pure Python and raises NotImplementedError.
    """

    def test_zload_raises_not_implemented(self):
        """ZLOAD raises NotImplementedError (unsupported YDB feature)."""
        code = 'TEST\n ZL "routine"\n Q'
        with pytest.raises(NotImplementedError, match="MZLoadStatement"):
            generate_python(code)

    def test_zload_full_command_raises_not_implemented(self):
        """ZLOAD (full keyword) raises NotImplementedError."""
        code = 'TEST\n ZLOAD "routine"\n Q'
        with pytest.raises(NotImplementedError, match="MZLoadStatement"):
            generate_python(code)

    def test_zload_with_postcondition_raises_not_implemented(self):
        """ZLOAD with postcondition raises NotImplementedError."""
        code = 'TEST\n ZL:1 "routine"\n Q'
        with pytest.raises(NotImplementedError, match="MZLoadStatement"):
            generate_python(code)
