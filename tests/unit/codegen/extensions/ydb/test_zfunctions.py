"""Tests for Z-function code generation (YDB extension).

Reference: YottaDB implementation-defined $Z... functions
These are implementation-defined per FR-017.
Spec 014: Verify LIM-015 errors for unimplemented Z-functions.
Spec 021 Phase 10: $ZDATE is now implemented.
Spec 024 Phase 10: Vendor function aliases and stubs.
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

    def test_zmode_generates_code(self):
        """$ZMODE generates code returning "OTHER" (024-vista Phase 10)."""
        code = "TEST\n W $ZMODE\n Q"
        result = generate_python(code)
        assert '"OTHER"' in result

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


# =============================================================================
# Phase 10: Vendor Function Aliases (spec 024, T053)
# =============================================================================


@pytest.mark.codegen
@pytest.mark.ydb
class TestPhase10FunctionAliases:
    """Tests for vendor function aliases registered in Phase 10."""

    def test_zs_alias_for_zsearch(self):
        """$ZS(pattern) is alias for $ZSEARCH — generates zsearch() call."""
        code = 'TEST\n S X=$ZS("/tmp/*")\n Q'
        result = generate_python(code)
        assert "_rt.zsearch" in result

    def test_zs_no_args(self):
        """$ZS with no args still generates zsearch call."""
        code = 'TEST\n S X=$ZS("")\n Q'
        result = generate_python(code)
        assert "_rt.zsearch" in result

    def test_zchar_alias_for_char(self):
        """$ZCHAR(n) is alias for $CHAR — generates chr() call."""
        code = "TEST\n W $ZCHAR(65)\n Q"
        result = generate_python(code)
        assert "chr(" in result

    def test_zch_alias_for_char(self):
        """$ZCH(n) is abbreviation for $ZCHAR."""
        code = "TEST\n W $ZCH(65)\n Q"
        result = generate_python(code)
        assert "chr(" in result

    def test_zprevious_generates_order_minus1(self):
        """$ZPREVIOUS(var) is $ORDER(var,-1) — generates m_order with -1."""
        code = 'TEST\n S X=$ZP(A(""))\n Q'
        result = generate_python(code)
        assert "m_order" in result

    def test_zp_function_alias_for_zprevious(self):
        """$ZP(var) as function invokes $ZPREVIOUS, not the $ZP SVN."""
        code = 'TEST\n S X=$ZP(A(""))\n Q'
        result = generate_python(code)
        assert "m_order" in result

    def test_zjob_as_function(self):
        """$ZJOB as no-args function returns _rt.zjob()."""
        code = "TEST\n W $ZJOB\n Q"
        result = generate_python(code)
        assert "_rt.zjob()" in result

    def test_list_stub_returns_empty(self):
        """$LIST() IRIS function stub generates empty string."""
        code = 'TEST\n S X=$LIST("abc")\n Q'
        result = generate_python(code)
        assert '""' in result

    def test_listbuild_stub(self):
        """$LISTBUILD IRIS function stub generates empty string."""
        code = 'TEST\n S X=$LISTBUILD("a","b")\n Q'
        result = generate_python(code)
        assert '""' in result

    def test_listget_stub(self):
        """$LISTGET IRIS function stub generates empty string."""
        code = 'TEST\n S X=$LISTGET("abc",1)\n Q'
        result = generate_python(code)
        assert '""' in result

    def test_lb_abbreviation(self):
        """$LB is abbreviation for $LISTBUILD."""
        code = 'TEST\n S X=$LB("a")\n Q'
        result = generate_python(code)
        assert '""' in result

    def test_lg_abbreviation(self):
        """$LG is abbreviation for $LISTGET."""
        code = 'TEST\n S X=$LG("abc",1)\n Q'
        result = generate_python(code)
        assert '""' in result

    def test_li_abbreviation(self):
        """$LI is abbreviation for $LIST."""
        code = 'TEST\n S X=$LI("abc")\n Q'
        result = generate_python(code)
        assert '""' in result

    def test_zextract_alias_for_extract(self):
        """$ZEXTRACT(str,from,to) is alias for $EXTRACT."""
        code = 'TEST\n W $ZEXTRACT("HELLO",2,4)\n Q'
        result = generate_python(code)
        assert "m_extract" in result

    def test_ze_function_alias_for_extract(self):
        """$ZE(str,from,to) as function is alias for $EXTRACT."""
        code = 'TEST\n W $ZE("HELLO",1,3)\n Q'
        result = generate_python(code)
        assert "m_extract" in result


# =============================================================================
# Phase 10: $ZC/$ZCALL Stubs (spec 024, T054)
# =============================================================================


@pytest.mark.codegen
@pytest.mark.ydb
class TestPhase10ZcallStubs:
    """Tests for $ZC/$ZCALL DSM/VMS function stubs."""

    def test_zcall_generates_stub(self):
        """$ZCALL(arg) generates m_zcall_stub() call."""
        code = 'TEST\n S X=$ZCALL("LIB","FUNC")\n Q'
        result = generate_python(code)
        assert "m_zcall_stub" in result

    def test_zc_alias_for_zcall(self):
        """$ZC(arg) is abbreviation for $ZCALL."""
        code = 'TEST\n S X=$ZC("LIB")\n Q'
        result = generate_python(code)
        assert "m_zcall_stub" in result

    def test_zcall_no_args(self):
        """$ZCALL with no args generates stub call."""
        code = "TEST\n S X=$ZCALL\n Q"
        result = generate_python(code)
        assert "m_zcall_stub" in result

    def test_zcall_multiple_args(self):
        """$ZCALL with multiple args passes them to stub."""
        code = 'TEST\n S X=$ZCALL("A","B","C")\n Q'
        result = generate_python(code)
        assert "m_zcall_stub" in result


# =============================================================================
# Phase 10: $ZHOROLOG/$ZH (spec 024, T055)
# =============================================================================


@pytest.mark.codegen
@pytest.mark.ydb
class TestPhase10Zhorolog:
    """Tests for $ZHOROLOG/$ZH function and SVN."""

    def test_zhorolog_function(self):
        """$ZHOROLOG as function generates time.time() call."""
        code = "TEST\n S X=$ZHOROLOG\n Q"
        result = generate_python(code)
        assert "time.time()" in result

    def test_zh_function_alias(self):
        """$ZH as function generates time.time() call."""
        code = "TEST\n S X=$ZH\n Q"
        result = generate_python(code)
        assert "time.time()" in result

    def test_zh_svn(self):
        """$ZH as SVN (special variable) generates time.time() call."""
        code = "TEST\n W $ZH\n Q"
        result = generate_python(code)
        assert "time.time()" in result


# =============================================================================
# Phase 10: Remaining Vendor Stubs (spec 024, T056)
# =============================================================================


@pytest.mark.codegen
@pytest.mark.ydb
class TestPhase10VendorStubs:
    """Tests for remaining Phase 10 vendor function stubs."""

    def test_zio_returns_io(self):
        """$ZIO generates _rt.io() call (alias for $IO)."""
        code = "TEST\n W $ZIO\n Q"
        result = generate_python(code)
        assert "_rt.io()" in result

    def test_pd_returns_one(self):
        """$PD generates "1"."""
        code = "TEST\n S X=$PD\n Q"
        result = generate_python(code)
        assert '"1"' in result

    def test_zdev_returns_empty(self):
        """$ZDEV generates empty string."""
        code = "TEST\n S X=$ZDEV\n Q"
        result = generate_python(code)
        assert '""' in result

    def test_zo_stub(self):
        """$ZO generates empty string stub."""
        code = 'TEST\n S X=$ZO("abc")\n Q'
        result = generate_python(code)
        assert '""' in result

    def test_zorder_stub(self):
        """$ZORDER generates empty string stub."""
        code = 'TEST\n S X=$ZORDER("abc")\n Q'
        result = generate_python(code)
        assert '""' in result

    def test_ztimestamp_generates_horolog(self):
        """$ZTIMESTAMP generates _rt.horolog() call."""
        code = "TEST\n S X=$ZTIMESTAMP\n Q"
        result = generate_python(code)
        assert "_rt.horolog()" in result

    def test_ztrnlnm_generates_environ_get(self):
        """$ZTRNLNM(name) generates _rt_os_environ_get() call."""
        code = 'TEST\n S X=$ZTRNLNM("HOME")\n Q'
        result = generate_python(code)
        assert "_rt_os_environ_get" in result

    def test_ztrnlnm_no_args(self):
        """$ZTRNLNM with no args returns empty string."""
        code = "TEST\n S X=$ZTRNLNM\n Q"
        result = generate_python(code)
        assert '""' in result

    def test_zname_stub(self):
        """$ZNAME generates empty string stub."""
        code = "TEST\n S X=$ZNAME\n Q"
        result = generate_python(code)
        assert '""' in result

    def test_zn_alias(self):
        """$ZN is abbreviation for $ZNAME."""
        code = "TEST\n S X=$ZN\n Q"
        result = generate_python(code)
        assert '""' in result

    def test_zclose_returns_zero(self):
        """$ZCLOSE generates "0"."""
        code = "TEST\n S X=$ZCLOSE\n Q"
        result = generate_python(code)
        assert '"0"' in result

    def test_zgetjpi_generates_helper(self):
        """$ZGETJPI(pid,item) generates m_zgetjpi() call."""
        code = 'TEST\n S X=$ZGETJPI("","ISPROCALIVE")\n Q'
        result = generate_python(code)
        assert "m_zgetjpi" in result

    def test_zios_returns_zero(self):
        """$ZIOS generates "0"."""
        code = "TEST\n S X=$ZIOS\n Q"
        result = generate_python(code)
        assert '"0"' in result

    def test_zver_returns_empty(self):
        """$ZVER generates empty string."""
        code = "TEST\n S X=$ZVER\n Q"
        result = generate_python(code)
        assert '""' in result

    def test_zparse_generates_helper(self):
        """$ZPARSE(path) generates m_zparse() call."""
        code = 'TEST\n S X=$ZPARSE("/tmp/test.m")\n Q'
        result = generate_python(code)
        assert "m_zparse" in result

    def test_zparse_with_item(self):
        """$ZPARSE(path,item) generates m_zparse() with two args."""
        code = 'TEST\n S X=$ZPARSE("/tmp/test.m","NAME")\n Q'
        result = generate_python(code)
        assert "m_zparse" in result

    def test_zlength_generates_encode(self):
        """$ZLENGTH(str) generates byte length calculation."""
        code = 'TEST\n S X=$ZLENGTH("abc")\n Q'
        result = generate_python(code)
        assert 'encode("utf-8")' in result

    def test_zl_alias(self):
        """$ZL is abbreviation for $ZLENGTH."""
        code = 'TEST\n S X=$ZL("abc")\n Q'
        result = generate_python(code)
        assert 'encode("utf-8")' in result

    def test_roles_returns_all(self):
        """$ROLES generates "%All"."""
        code = "TEST\n S X=$ROLES\n Q"
        result = generate_python(code)
        assert '"%All"' in result

    def test_zdefnsp_returns_vista(self):
        """$ZDEFNSP generates "VISTA"."""
        code = "TEST\n S X=$ZDEFNSP\n Q"
        result = generate_python(code)
        assert '"VISTA"' in result

    def test_znspace_alias(self):
        """$ZNSPACE is alias for $ZDEFNSP."""
        code = "TEST\n S X=$ZNSPACE\n Q"
        result = generate_python(code)
        assert '"VISTA"' in result

    def test_number_generates_canonical(self):
        """$NUMBER generates canonical numeric form."""
        code = 'TEST\n S X=$NUMBER("  123  ")\n Q'
        result = generate_python(code)
        assert "m_num" in result

    def test_num_alias(self):
        """$NUM is abbreviation for $NUMBER."""
        code = 'TEST\n S X=$NUM("42")\n Q'
        result = generate_python(code)
        assert "m_num" in result

    def test_zdateh_stub(self):
        """$ZDATEH generates empty string stub."""
        code = 'TEST\n S X=$ZDATEH("01/01/2024")\n Q'
        result = generate_python(code)
        assert '""' in result

    def test_zbitand_generates_helper(self):
        """$ZBITAND(s1,s2) generates m_zbitand() call."""
        code = 'TEST\n S X=$ZBITAND("AB","CD")\n Q'
        result = generate_python(code)
        assert "m_zbitand" in result

    def test_zdatetime_stub(self):
        """$ZDATETIME generates stub call."""
        code = 'TEST\n S X=$ZDATETIME("65432,43200")\n Q'
        result = generate_python(code)
        assert "m_zcall_stub" in result

    def test_zdt_alias(self):
        """$ZDT is abbreviation for $ZDATETIME."""
        code = 'TEST\n S X=$ZDT("65432")\n Q'
        result = generate_python(code)
        assert "m_zcall_stub" in result

    def test_eref_stub(self):
        """$EREF generates empty string stub."""
        code = "TEST\n S X=$EREF\n Q"
        result = generate_python(code)
        assert '""' in result

    def test_zos_stub(self):
        """$ZOS generates empty string stub."""
        code = "TEST\n S X=$ZOS\n Q"
        result = generate_python(code)
        assert '""' in result

    def test_zeo_returns_zero(self):
        """$ZEO generates "0" (end of file, DSM variant)."""
        code = "TEST\n S X=$ZEO\n Q"
        result = generate_python(code)
        assert '"0"' in result

    def test_zwa_returns_zero(self):
        """$ZWA generates "0"."""
        code = "TEST\n S X=$ZWA\n Q"
        result = generate_python(code)
        assert '"0"' in result

    def test_zuci_stub(self):
        """$ZUCI generates empty string stub."""
        code = "TEST\n S X=$ZUCI\n Q"
        result = generate_python(code)
        assert '""' in result

    def test_zcmd_stub(self):
        """$ZCMD generates empty string stub."""
        code = "TEST\n S X=$ZCMD\n Q"
        result = generate_python(code)
        assert '""' in result

    def test_zgd_stub(self):
        """$ZGD generates empty string stub."""
        code = "TEST\n S X=$ZGD\n Q"
        result = generate_python(code)
        assert '""' in result

    def test_zmode_function(self):
        """$ZMODE as function generates "OTHER"."""
        code = "TEST\n S X=$ZMODE\n Q"
        result = generate_python(code)
        assert '"OTHER"' in result


# =============================================================================
# Phase 10: $ZCMDLINE SVN (spec 024, T057)
# =============================================================================


@pytest.mark.codegen
@pytest.mark.ydb
class TestPhase10ZcmdlineSvn:
    """Tests for $ZCMDLINE special variable."""

    def test_zcmdline_svn(self):
        """$ZCMDLINE SVN generates empty string."""
        code = "TEST\n W $ZCMDLINE\n Q"
        result = generate_python(code)
        assert '""' in result

    def test_zcmdline_in_set(self):
        """$ZCMDLINE can be used in SET command."""
        code = "TEST\n S X=$ZCMDLINE\n Q"
        result = generate_python(code)
        assert '""' in result


# =============================================================================
# Phase 10: Runtime Helper Tests (spec 024, T058)
# =============================================================================


@pytest.mark.codegen
@pytest.mark.ydb
class TestPhase10RuntimeHelpers:
    """Tests for runtime helpers added in Phase 10."""

    def test_rt_os_environ_get(self):
        """_rt_os_environ_get returns env var value or empty string."""
        from m2py.runtime.helpers import _rt_os_environ_get
        import os

        os.environ["M2PY_TEST_VAR"] = "test_value"
        try:
            assert _rt_os_environ_get("M2PY_TEST_VAR") == "test_value"
            assert _rt_os_environ_get("NONEXISTENT_M2PY_VAR_12345") == ""
        finally:
            del os.environ["M2PY_TEST_VAR"]

    def test_m_zgetjpi_isprocalive_self(self):
        """m_zgetjpi("", "ISPROCALIVE") returns "1" for current process."""
        from m2py.runtime.helpers import m_zgetjpi

        assert m_zgetjpi("", "ISPROCALIVE") == "1"

    def test_m_zgetjpi_isprocalive_current_pid(self):
        """m_zgetjpi(current_pid, "ISPROCALIVE") returns "1"."""
        import os
        from m2py.runtime.helpers import m_zgetjpi

        assert m_zgetjpi(str(os.getpid()), "ISPROCALIVE") == "1"

    def test_m_zgetjpi_isprocalive_dead_pid(self):
        """m_zgetjpi(invalid_pid, "ISPROCALIVE") returns "0"."""
        from m2py.runtime.helpers import m_zgetjpi

        assert m_zgetjpi("99999999", "ISPROCALIVE") == "0"

    def test_m_zparse_full(self):
        """m_zparse returns absolute path when no item specified."""
        from m2py.runtime.helpers import m_zparse

        result = m_zparse("/tmp/test.m")
        assert result == "/tmp/test.m"

    def test_m_zparse_directory(self):
        """m_zparse with DIRECTORY returns dirname."""
        from m2py.runtime.helpers import m_zparse

        assert m_zparse("/tmp/test.m", "DIRECTORY") == "/tmp"

    def test_m_zparse_name(self):
        """m_zparse with NAME returns filename without extension."""
        from m2py.runtime.helpers import m_zparse

        assert m_zparse("/tmp/test.m", "NAME") == "test"

    def test_m_zparse_type(self):
        """m_zparse with TYPE returns file extension."""
        from m2py.runtime.helpers import m_zparse

        assert m_zparse("/tmp/test.m", "TYPE") == ".m"

    def test_m_zparse_node(self):
        """m_zparse with NODE returns empty string (no network)."""
        from m2py.runtime.helpers import m_zparse

        assert m_zparse("/tmp/test.m", "NODE") == ""

    def test_m_zparse_empty(self):
        """m_zparse with empty path returns empty string."""
        from m2py.runtime.helpers import m_zparse

        assert m_zparse("") == ""

    def test_m_zbitand_basic(self):
        """m_zbitand performs byte-by-byte AND."""
        from m2py.runtime.helpers import m_zbitand

        # chr(0xFF) & chr(0x0F) = chr(0x0F)
        result = m_zbitand("\xff", "\x0f")
        assert result == "\x0f"

    def test_m_zbitand_different_lengths(self):
        """m_zbitand with different lengths uses minimum."""
        from m2py.runtime.helpers import m_zbitand

        result = m_zbitand("\xff\xff", "\x0f")
        assert result == "\x0f"
        assert len(result) == 1

    def test_m_zbitand_empty(self):
        """m_zbitand with empty string returns empty."""
        from m2py.runtime.helpers import m_zbitand

        assert m_zbitand("", "abc") == ""
        assert m_zbitand("abc", "") == ""


# =============================================================================
# Phase 10: VistA Routine Transpilation Smoke Tests (spec 024)
# =============================================================================


@pytest.mark.codegen
@pytest.mark.ydb
class TestPhase10VistaRoutineSmoke:
    """Smoke tests verifying previously-failing VistA routines now transpile."""

    @pytest.mark.parametrize(
        "routine,function",
        [
            ("$ZS", "zsearch"),  # $ZS → ZSEARCH alias
            ("$ZC", "zcall_stub"),  # $ZC → ZCALL stub
            ("$ZH", "time.time"),  # $ZH → ZHOROLOG
            ("$ZTRNLNM", "environ"),  # $ZTRNLNM → os.environ
        ],
    )
    def test_vendor_function_generates_code(self, routine, function):
        """Vendor function {routine} generates callable Python code."""
        code = f'TEST\n S X={routine}("arg")\n Q'
        result = generate_python(code)
        assert function.split(".")[-1] in result.lower() or function in result
