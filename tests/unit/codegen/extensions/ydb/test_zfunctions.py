"""Tests for Z-function code generation (YDB extension).

Reference: YottaDB implementation-defined $Z... functions
These are implementation-defined per FR-017.
Spec 014: Verify LIM-015 errors for unimplemented Z-functions.
Spec 021 Phase 10: $ZDATE is now implemented.
"""

import pytest
from m2py.codegen import generate_python


@pytest.mark.codegen
@pytest.mark.ydb
class TestZfunctionsCodegen:
    """Codegen-level tests for Z-functions (YDB implementation-defined).

    All Z-functions are implementation-defined per FR-017.
    Some are implemented (like $ZDATE), others raise NotImplementedError with LIM-015.
    """

    def test_zdate_generates_code(self):
        """$ZDATE generates m_zdate() call (Spec 021 Phase 10)."""
        code = "TEST\n S X=$ZDATE(12345)\n Q"
        result = generate_python(code)
        assert "m_zdate" in result

    def test_zmessage_function_generates_code(self):
        """$ZMESSAGE generates m_zmessage() call."""
        code = "TEST\n S X=$ZMESSAGE(150373210)\n Q"
        result = generate_python(code)
        assert "m_zmessage" in result

    def test_zwidth_raises_not_implemented(self):
        """$ZWIDTH raises NotImplementedError with LIM-015."""
        code = 'TEST\n S X=$ZWIDTH("ABC")\n Q'
        with pytest.raises(NotImplementedError, match="LIM-015"):
            generate_python(code)


@pytest.mark.codegen
@pytest.mark.ydb
class TestYdbSpecialVariablesCodegen:
    """Codegen-level tests for YDB-specific special variables.

    YDB provides implementation-specific special variables ($Z...).
    These are not part of the MUMPS standard and cannot be transpiled
    to pure Python.

    Spec 015: Document YDB special variables as not supported.
    """

    def test_zyerror_raises_not_implemented(self):
        """$ZYERROR raises NotImplementedError (YDB-specific variable)."""
        code = "TEST\n W $ZYERROR\n Q"
        with pytest.raises(NotImplementedError, match="ZYERROR"):
            generate_python(code)

    def test_zinterrupt_generates_code(self):
        """$ZINTERRUPT generates runtime call (024-vista-transpilation-fixes)."""
        code = "TEST\n W $ZINTERRUPT\n Q"
        result = generate_python(code)
        assert "_rt.zinterrupt()" in result

    def test_zmode_raises_not_implemented(self):
        """$ZMODE raises NotImplementedError (YDB-specific variable)."""
        code = "TEST\n W $ZMODE\n Q"
        with pytest.raises(NotImplementedError, match="ZMODE"):
            generate_python(code)

    def test_zstatus_generates_code(self):
        """$ZSTATUS generates runtime call (Spec 021 Phase 5)."""
        code = "TEST\n W $ZSTATUS\n Q"
        result = generate_python(code)
        assert "_rt.zstatus()" in result

    def test_zsystem_variable_generates_exit_code(self):
        """$ZSYSTEM generates zsystem_exit() call."""
        code = "TEST\n W $ZSYSTEM\n Q"
        result = generate_python(code)
        assert "_rt.zsystem_exit()" in result
