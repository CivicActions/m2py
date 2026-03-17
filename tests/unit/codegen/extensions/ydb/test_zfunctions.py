"""Tests for Z-function code generation (YDB extension).

Reference: YottaDB implementation-defined $Z... functions
These are implementation-defined per FR-017.
Spec 014: Verify LIM-015 errors for unimplemented Z-functions.
Spec 021 Phase 10: $ZDATE is now implemented.
Spec 024 Phase 10: Vendor function aliases and stubs.
Spec 024 Phase 14: $ZBITSTR, SET $ZSTEP, ZSTEP command, $ZCO, $ZSIGPROC.
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

    def test_zs_abbreviation_generates_zstatus(self):
        """$ZS abbreviation maps to $ZSTATUS, not $ZSEARCH.

        In MUMPS, $ZS without parentheses is the abbreviation for $ZSTATUS.
        $ZSEARCH requires parentheses: $ZS(expr).
        This was a bug where $ZS was parsed as IntrinsicFunctionNoArgs
        and mapped to $ZSEARCH instead of SpecialVariable $ZSTATUS.
        """
        code = "TEST\n W $ZS\n Q"
        result = generate_python(code)
        assert "_rt.zstatus()" in result
        assert "zsearch" not in result.lower()

    def test_zs_lowercase_abbreviation_generates_zstatus(self):
        """$zs (lowercase) maps to $ZSTATUS — grammar is case-insensitive."""
        code = "TEST\n W $zs\n Q"
        result = generate_python(code)
        assert "_rt.zstatus()" in result
        assert "zsearch" not in result.lower()

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
        """m_zparse with empty path returns current directory with trailing /."""
        from m2py.runtime.helpers import m_zparse
        import os

        result = m_zparse("")
        assert result == os.getcwd() + "/"

    def test_m_zparse_dir_trailing_slash_exists(self, tmp_path):
        """m_zparse preserves trailing / for existing directories."""
        from m2py.runtime.helpers import m_zparse

        path = str(tmp_path) + "/"
        assert m_zparse(path) == path

    def test_m_zparse_dir_trailing_slash_nonexistent(self):
        """m_zparse returns empty for non-existent directory with trailing /."""
        from m2py.runtime.helpers import m_zparse

        assert m_zparse("/nonexistent_dir_12345/") == ""

    def test_m_zparse_file_parent_exists(self):
        """m_zparse returns resolved path when parent directory exists."""
        from m2py.runtime.helpers import m_zparse

        result = m_zparse("/tmp/somefile.txt")
        assert result == "/tmp/somefile.txt"

    def test_m_zparse_file_parent_nonexistent(self):
        """m_zparse returns empty when parent directory doesn't exist."""
        from m2py.runtime.helpers import m_zparse

        assert m_zparse("/nonexistent_dir_12345/file.txt") == ""

    def test_m_zparse_relative_path(self):
        """m_zparse resolves relative paths to absolute."""
        from m2py.runtime.helpers import m_zparse
        import os

        result = m_zparse("somefile.txt")
        assert result == os.path.join(os.getcwd(), "somefile.txt")

    def test_m_zparse_root_slash(self):
        """m_zparse with '/' returns '/' (root always exists)."""
        from m2py.runtime.helpers import m_zparse

        assert m_zparse("/") == "/"

    def test_m_zparse_nested_nonexistent(self):
        """m_zparse returns empty for deeply nested non-existent dir."""
        from m2py.runtime.helpers import m_zparse

        assert m_zparse("/no/such/path/here/") == ""

    def test_m_zparse_dir_no_trailing_slash(self):
        """m_zparse with existing dir without trailing / returns resolved path."""
        from m2py.runtime.helpers import m_zparse

        # /tmp exists as a directory; without trailing slash it's treated as a file path
        result = m_zparse("/tmp")
        assert result == "/tmp"

    def test_m_zparse_empty_with_item(self):
        """m_zparse with empty path and DIRECTORY item returns dirname of cwd."""
        from m2py.runtime.helpers import m_zparse

        result = m_zparse("", "DIRECTORY")
        # empty path → dirname of "" → ""
        assert result == ""

    def test_m_zparse_dir_trailing_slash_with_spaces_in_name(self, tmp_path):
        """m_zparse handles directories with spaces."""
        from m2py.runtime.helpers import m_zparse

        subdir = tmp_path / "my dir"
        subdir.mkdir()
        path = str(subdir) + "/"
        assert m_zparse(path) == path

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


# =============================================================================
# Phase 12A: Vendor Function Stubs (Spec 024, T065-T073)
# =============================================================================


# ── T065: $ZSORT ─────────────────────────────────────────────────────


@pytest.mark.codegen
@pytest.mark.ydb
class TestZsortCodegen:
    """$ZSORT is a DSM alias for $ORDER (T065)."""

    def test_zsort_generates_order_call(self):
        """$ZSORT generates the same code as $ORDER."""
        code = "TEST\n S X=$ZSORT(^A(1))\n Q"
        result = generate_python(code)
        # Should delegate to $ORDER codegen, producing m_order_global
        assert "m_order_global" in result

    def test_zsort_with_direction(self):
        """$ZSORT with direction argument works like $ORDER(x,dir)."""
        code = "TEST\n S X=$ZSORT(^A(1),-1)\n Q"
        result = generate_python(code)
        assert "m_order_global" in result

    def test_zsort_local_variable(self):
        """$ZSORT on a local variable generates m_order."""
        code = "TEST\n S X=$ZSORT(A(1))\n Q"
        result = generate_python(code)
        assert "m_order" in result


@pytest.mark.codegen
@pytest.mark.ydb
class TestZsortExecution:
    """$ZSORT runtime behavior matches $ORDER (T065)."""

    def test_zsort_traverses_array(self, execute_mumps):
        """$ZSORT traverses subscripts like $ORDER."""
        result = execute_mumps(
            'TEST\n S A(1)="a",A(3)="c",A(5)="e"\n'
            ' S X="" F  S X=$ZSORT(A(X)) Q:X=""  W X,!\n Q'
        )
        assert result.output == "1\n3\n5\n"

    def test_zsort_reverse(self, execute_mumps):
        """$ZSORT with -1 traverses in reverse."""
        result = execute_mumps(
            'TEST\n S A(1)="a",A(3)="c",A(5)="e"\n'
            ' S X="" F  S X=$ZSORT(A(X),-1) Q:X=""  W X,!\n Q'
        )
        assert result.output == "5\n3\n1\n"

    def test_zsort_empty_array(self, execute_mumps):
        """$ZSORT on empty array returns empty string."""
        result = execute_mumps('TEST\n K A S X=$ZSORT(A("")) W X="",!\n Q')
        assert result.output == "1\n"


# ── T066: $ZABS ──────────────────────────────────────────────────────


@pytest.mark.codegen
@pytest.mark.ydb
class TestZabsCodegen:
    """$ZABS generates m_zabs() call (T066)."""

    def test_zabs_generates_helper_call(self):
        """$ZABS(expr) generates m_zabs() call."""
        code = "TEST\n S X=$ZABS(-42)\n Q"
        result = generate_python(code)
        assert "m_zabs" in result

    def test_zabs_in_write(self):
        """$ZABS in WRITE generates correct code."""
        code = "TEST\n W $ZABS(-5)\n Q"
        result = generate_python(code)
        assert "m_zabs" in result


@pytest.mark.codegen
@pytest.mark.ydb
class TestZabsExecution:
    """$ZABS end-to-end execution tests (T066)."""

    def test_zabs_write_negative(self, execute_mumps):
        """W $ZABS(-42) outputs '42'."""
        result = execute_mumps("TEST\n W $ZABS(-42)\n Q")
        assert result.output == "42"

    def test_zabs_write_zero(self, execute_mumps):
        """W $ZABS(0) outputs '0'."""
        result = execute_mumps("TEST\n W $ZABS(0)\n Q")
        assert result.output == "0"

    def test_zabs_write_positive_decimal(self, execute_mumps):
        """W $ZABS(3.14) outputs '3.14'."""
        result = execute_mumps("TEST\n W $ZABS(3.14)\n Q")
        assert result.output == "3.14"

    def test_zabs_in_expression(self, execute_mumps):
        """$ZABS can be used inside arithmetic expressions."""
        result = execute_mumps("TEST\n W $ZABS(-10)+$ZABS(-20)\n Q")
        assert result.output == "30"


# ── T067: $NOW ────────────────────────────────────────────────────────


@pytest.mark.codegen
@pytest.mark.ydb
class TestNowCodegen:
    """$NOW generates m_now() call (T067)."""

    def test_now_generates_helper_call(self):
        """$NOW() generates m_now() call."""
        code = "TEST\n S X=$NOW()\n Q"
        result = generate_python(code)
        assert "m_now" in result


@pytest.mark.codegen
@pytest.mark.ydb
class TestNowExecution:
    """$NOW end-to-end execution tests (T067)."""

    def test_now_day_matches_horolog(self, execute_mumps):
        """$P($NOW(),',',1) equals $P($H,',',1) — same day part."""
        result = execute_mumps('TEST\n W $P($NOW(),",",1)=$P($H,",",1)\n Q')
        assert result.output == "1"

    def test_now_has_two_parts(self, execute_mumps):
        """$NOW returns comma-separated format."""
        result = execute_mumps('TEST\n S X=$NOW() W $L(X,",")\n Q')
        assert result.output == "2"


# ── T068: $ZBITOR / $ZBITXOR / $ZBITNOT ──────────────────────────────


@pytest.mark.codegen
@pytest.mark.ydb
class TestZbitorCodegen:
    """$ZBITOR generates m_zbitor() call (T068)."""

    def test_zbitor_generates_helper_call(self):
        """$ZBITOR generates m_zbitor() call."""
        code = 'TEST\n S X=$ZBITOR("A","B")\n Q'
        result = generate_python(code)
        assert "m_zbitor" in result

    def test_zbitxor_generates_helper_call(self):
        """$ZBITXOR generates m_zbitxor() call."""
        code = 'TEST\n S X=$ZBITXOR("A","B")\n Q'
        result = generate_python(code)
        assert "m_zbitxor" in result

    def test_zbitnot_generates_helper_call(self):
        """$ZBITNOT generates m_zbitnot() call."""
        code = 'TEST\n S X=$ZBITNOT("A")\n Q'
        result = generate_python(code)
        assert "m_zbitnot" in result


# ── T069: $ZGETDVI ───────────────────────────────────────────────────


@pytest.mark.codegen
@pytest.mark.ydb
class TestZgetdviCodegen:
    """$ZGETDVI generates empty string stub (T069)."""

    def test_zgetdvi_generates_code(self):
        """$ZGETDVI generates empty string literal."""
        code = 'TEST\n S X=$ZGETDVI("TTA0:","DEVNAM")\n Q'
        result = generate_python(code)
        # Should generate '""' (empty string)
        assert '""' in result

    def test_zgetdvi_does_not_raise(self):
        """$ZGETDVI no longer raises NotImplementedError."""
        code = 'TEST\n S X=$ZGETDVI("TTA0:","DEVNAM")\n Q'
        # Should not raise — it's a stub
        generate_python(code)


@pytest.mark.codegen
@pytest.mark.ydb
class TestZgetdviExecution:
    """$ZGETDVI end-to-end execution (T069)."""

    def test_zgetdvi_returns_empty(self, execute_mumps):
        """$ZGETDVI returns empty string at runtime."""
        result = execute_mumps('TEST\n W $ZGETDVI("TTA0:","DEVNAM")=""\n Q')
        assert result.output == "1"


# ── T070: $ZGETSYI ───────────────────────────────────────────────────


@pytest.mark.codegen
@pytest.mark.ydb
class TestZgetsyiCodegen:
    """$ZGETSYI generates m_zgetsyi() call (T070)."""

    def test_zgetsyi_generates_helper_call(self):
        """$ZGETSYI generates m_zgetsyi() call."""
        code = 'TEST\n S X=$ZGETSYI("NODENAME")\n Q'
        result = generate_python(code)
        assert "m_zgetsyi" in result


@pytest.mark.codegen
@pytest.mark.ydb
class TestZgetsyiExecution:
    """$ZGETSYI end-to-end execution (T070)."""

    def test_zgetsyi_nodename_nonempty(self, execute_mumps):
        """$ZGETSYI("NODENAME") returns a non-empty string."""
        result = execute_mumps('TEST\n W $ZGETSYI("NODENAME")\n Q')
        assert len(result.output) > 0

    def test_zgetsyi_unknown_empty(self, execute_mumps):
        """$ZGETSYI("BOGUS") returns empty string."""
        result = execute_mumps('TEST\n W $ZGETSYI("BOGUS")=""\n Q')
        assert result.output == "1"


# ── T071: $ZTIME / $ZT ──────────────────────────────────────────────


@pytest.mark.codegen
@pytest.mark.ydb
class TestZtimeCodegen:
    """$ZTIME/$ZT generates m_ztime() call (T071)."""

    def test_ztime_generates_helper_call(self):
        """$ZTIME(expr) generates m_ztime() call."""
        code = "TEST\n S X=$ZTIME(3661)\n Q"
        result = generate_python(code)
        assert "m_ztime" in result

    def test_zt_generates_helper_call(self):
        """$ZT(expr) generates m_ztime() call (short form)."""
        code = "TEST\n S X=$ZT(3661)\n Q"
        result = generate_python(code)
        assert "m_ztime" in result


@pytest.mark.codegen
@pytest.mark.ydb
class TestZtimeExecution:
    """$ZTIME end-to-end execution tests (T071)."""

    def test_zt_midnight(self, execute_mumps):
        """W $ZT(0) outputs '00:00:00'."""
        result = execute_mumps("TEST\n W $ZT(0)\n Q")
        assert result.output == "00:00:00"

    def test_zt_combined(self, execute_mumps):
        """W $ZT(3661) outputs '01:01:01'."""
        result = execute_mumps("TEST\n W $ZT(3661)\n Q")
        assert result.output == "01:01:01"

    def test_zt_end_of_day(self, execute_mumps):
        """W $ZT(86399) outputs '23:59:59'."""
        result = execute_mumps("TEST\n W $ZT(86399)\n Q")
        assert result.output == "23:59:59"

    def test_ztime_long_form(self, execute_mumps):
        """W $ZTIME(3600) outputs '01:00:00'."""
        result = execute_mumps("TEST\n W $ZTIME(3600)\n Q")
        assert result.output == "01:00:00"

    def test_zt_from_horolog(self, execute_mumps):
        """$ZT applied to $P($H,',',2) produces valid time string."""
        result = execute_mumps('TEST\n S T=$ZT($P($H,",",2)) W T?2N1":"2N1":"2N\n Q')
        assert result.output == "1"


# ── T072: $ZDIR ─────────────────────────────────────────────────────


@pytest.mark.codegen
@pytest.mark.ydb
class TestZdirCodegen:
    """$ZDIR generates _rt_os_getcwd() call (T072)."""

    def test_zdir_generates_code(self):
        """$ZDIR() generates _rt_os_getcwd() call."""
        code = "TEST\n S X=$ZDIR()\n Q"
        result = generate_python(code)
        assert "_rt_os_getcwd" in result


@pytest.mark.codegen
@pytest.mark.ydb
class TestZdirExecution:
    """$ZDIR end-to-end execution (T072)."""

    def test_zdir_returns_nonempty(self, execute_mumps):
        """$ZDIR returns a non-empty string."""
        result = execute_mumps("TEST\n W $ZDIR()\n Q")
        assert len(result.output) > 0

    def test_zdir_returns_absolute_path(self, execute_mumps):
        """$ZDIR returns a path starting with /."""
        result = execute_mumps("TEST\n W $ZDIR()\n Q")
        assert result.output.startswith("/")


# ── T073: $ZGLD ──────────────────────────────────────────────────────


@pytest.mark.codegen
@pytest.mark.ydb
class TestZgldCodegen:
    """$ZGLD generates empty string stub (T073)."""

    def test_zgld_function_generates_code(self):
        """$ZGLD() function call generates empty string."""
        code = "TEST\n S X=$ZGLD()\n Q"
        result = generate_python(code)
        assert '""' in result

    def test_zgld_svn_generates_code(self):
        """$ZGLD as special variable generates empty string."""
        code = "TEST\n S X=$ZGLD\n Q"
        result = generate_python(code)
        assert '""' in result


@pytest.mark.codegen
@pytest.mark.ydb
class TestZgldExecution:
    """$ZGLD end-to-end execution (T073)."""

    def test_zgld_returns_empty(self, execute_mumps):
        """$ZGLD returns empty string."""
        result = execute_mumps('TEST\n W $ZGLD=""\n Q')
        assert result.output == "1"


# ── Cross-function integration tests ─────────────────────────────────


@pytest.mark.codegen
@pytest.mark.ydb
class TestPhase12ACrossFunctionIntegration:
    """Integration tests combining multiple Phase 12A functions."""

    def test_zabs_with_ztime(self, execute_mumps):
        """$ZABS and $ZTIME can be used together."""
        result = execute_mumps("TEST\n W $ZT($ZABS(-3661))\n Q")
        assert result.output == "01:01:01"

    def test_multiple_functions_in_one_line(self, execute_mumps):
        """Multiple Phase 12A functions in a single WRITE."""
        result = execute_mumps('TEST\n W $ZABS(-5)," ",$ZT(60)\n Q')
        assert result.output == "5 00:01:00"


# =============================================================================
# Phase 12B/C: SVN Readers & SET $ZD (024-vista-transpilation-fixes)
# =============================================================================


# ── $ZTIMEZONE (T074) ─────────────────────────────────────────────────


@pytest.mark.codegen
@pytest.mark.ydb
class TestZtimezoneCodegen:
    """$ZTIMEZONE SVN reader codegen (T074)."""

    def test_ztimezone_generates_time_timezone(self):
        """$ZTIMEZONE generates time.timezone reference."""
        code = "TEST\n S X=$ZTIMEZONE\n Q"
        result = generate_python(code)
        assert "time.timezone" in result

    def test_ztimezone_in_expression(self):
        """$ZTIMEZONE can be used in arithmetic expressions."""
        code = "TEST\n W $ZTIMEZONE/60\n Q"
        result = generate_python(code)
        assert "time.timezone" in result


@pytest.mark.codegen
@pytest.mark.ydb
class TestZtimezoneExecution:
    """$ZTIMEZONE end-to-end execution (T074)."""

    def test_ztimezone_returns_integer(self, execute_mumps):
        """$ZTIMEZONE returns an integer (seconds west of UTC)."""
        result = execute_mumps("TEST\n W $ZTIMEZONE\\1\n Q")
        val = int(result.output)
        # Timezone offset should be between -12*3600 and +14*3600
        assert -43200 <= val <= 50400

    def test_ztimezone_division(self, execute_mumps):
        """$ZTIMEZONE/60 gives minutes west of UTC."""
        result = execute_mumps("TEST\n W $ZTIMEZONE/60\\1\n Q")
        val = int(result.output)
        assert -720 <= val <= 840


# ── $ZTIMESTAMP (T074) ─────────────────────────────────────────────────


@pytest.mark.codegen
@pytest.mark.ydb
class TestZtimestampCodegen:
    """$ZTIMESTAMP SVN reader codegen (T074)."""

    def test_ztimestamp_generates_code(self):
        """$ZTIMESTAMP generates $HOROLOG-format UTC timestamp code."""
        code = "TEST\n S X=$ZTIMESTAMP\n Q"
        result = generate_python(code)
        # Uses _rt.horolog() as the generator for $ZTIMESTAMP
        assert "_rt.horolog()" in result

    def test_ztimestamp_function_form(self):
        """$ZTIMESTAMP() function form generates code."""
        code = "TEST\n W $ZTIMESTAMP\n Q"
        result = generate_python(code)
        assert "_rt.horolog()" in result


# ── $ZLEVEL (T075) ─────────────────────────────────────────────────────


@pytest.mark.codegen
@pytest.mark.ydb
class TestZlevelCodegen:
    """$ZLEVEL/$ZL SVN reader codegen (T075)."""

    def test_zlevel_generates_stub(self):
        """$ZLEVEL generates stack depth stub."""
        code = "TEST\n S X=$ZLEVEL\n Q"
        result = generate_python(code)
        assert '"1"' in result

    def test_zl_abbreviation(self):
        """$ZL as SVN (no args) generates $ZLEVEL stub."""
        # $ZL without args = $ZLEVEL SVN; $ZL(x) = $ZLENGTH function
        code = "TEST\n S X=$ZL\n Q"
        result = generate_python(code)
        assert '"1"' in result


@pytest.mark.codegen
@pytest.mark.ydb
class TestZlevelExecution:
    """$ZLEVEL end-to-end execution (T075)."""

    def test_zlevel_returns_one(self, execute_mumps):
        """$ZLEVEL returns 1 (stub)."""
        result = execute_mumps("TEST\n W $ZLEVEL\n Q")
        assert result.output == "1"

    def test_zlevel_in_arithmetic(self, execute_mumps):
        """$ZLEVEL can be used in arithmetic."""
        result = execute_mumps("TEST\n W $ZLEVEL+10\n Q")
        assert result.output == "11"


# ── GET $ZD/$ZDIRECTORY (T076) ─────────────────────────────────────────


@pytest.mark.codegen
@pytest.mark.ydb
class TestZdirectoryGetCodegen:
    """GET $ZD/$ZDIRECTORY codegen (T076)."""

    def test_zd_generates_getcwd(self):
        """$ZD generates os.getcwd() wrapper."""
        code = "TEST\n W $ZD\n Q"
        result = generate_python(code)
        assert "_rt_os_getcwd" in result

    def test_zdirectory_full_name(self):
        """$ZDIRECTORY full name generates same code."""
        code = "TEST\n W $ZDIRECTORY\n Q"
        result = generate_python(code)
        assert "_rt_os_getcwd" in result


@pytest.mark.codegen
@pytest.mark.ydb
class TestZdirectoryGetExecution:
    """GET $ZD/$ZDIRECTORY end-to-end execution (T076)."""

    def test_zd_returns_nonempty_path(self, execute_mumps):
        """$ZD returns a non-empty directory path."""
        result = execute_mumps("TEST\n W $L($ZD)>0\n Q")
        assert result.output == "1"

    def test_zdirectory_returns_nonempty_path(self, execute_mumps):
        """$ZDIRECTORY returns a non-empty directory path."""
        result = execute_mumps("TEST\n W $L($ZDIRECTORY)>0\n Q")
        assert result.output == "1"


# ── SET $ZD/$ZDIRECTORY (T076) ─────────────────────────────────────────


@pytest.mark.codegen
@pytest.mark.ydb
class TestZdirectorySetCodegen:
    """SET $ZD/$ZDIRECTORY codegen (T076)."""

    def test_set_zd_generates_chdir(self):
        """SET $ZD generates os.chdir() call."""
        code = 'TEST\n S $ZD="/tmp"\n Q'
        result = generate_python(code)
        assert "os.chdir" in result

    def test_set_zdirectory_generates_chdir(self):
        """SET $ZDIRECTORY generates os.chdir() call."""
        code = 'TEST\n S $ZDIRECTORY="/tmp"\n Q'
        result = generate_python(code)
        assert "os.chdir" in result


@pytest.mark.codegen
@pytest.mark.ydb
class TestZdirectorySetExecution:
    """SET $ZD/$ZDIRECTORY end-to-end execution (T076)."""

    def test_set_and_get_zd(self, execute_mumps):
        """SET $ZD changes directory, GET $ZD reads it back."""
        result = execute_mumps('TEST\n S $ZD="/tmp" W $ZD\n Q')
        # On macOS, /tmp is a symlink to /private/tmp; os.getcwd() resolves it
        import os

        assert result.output == os.path.realpath("/tmp")

    def test_set_zdirectory_changes_dir(self, execute_mumps):
        """SET $ZDIRECTORY changes directory."""
        result = execute_mumps('TEST\n S $ZDIRECTORY="/tmp" W $ZD\n Q')
        import os

        assert result.output == os.path.realpath("/tmp")


# ── $ZPIECE alias ─────────────────────────────────────────────────────


@pytest.mark.codegen
@pytest.mark.ydb
class TestZpieceCodegen:
    """$ZPIECE as alias for $PIECE codegen."""

    def test_zpiece_generates_m_piece(self):
        """$ZPIECE generates m_piece() call."""
        code = 'TEST\n W $ZPIECE("A^B^C","^",2)\n Q'
        result = generate_python(code)
        assert "m_piece" in result


@pytest.mark.codegen
@pytest.mark.ydb
class TestZpieceExecution:
    """$ZPIECE end-to-end execution."""

    def test_zpiece_extracts_piece(self, execute_mumps):
        """$ZPIECE extracts delimited pieces like $PIECE."""
        result = execute_mumps('TEST\n W $ZPIECE("A^B^C","^",2)\n Q')
        assert result.output == "B"

    def test_zpiece_range(self, execute_mumps):
        """$ZPIECE with range extracts multiple pieces."""
        result = execute_mumps('TEST\n W $ZPIECE("A^B^C","^",2,3)\n Q')
        assert result.output == "B^C"


# ── Batch transpilation (T078) ─────────────────────────────────────────


@pytest.mark.codegen
@pytest.mark.ydb
class TestPhase12BatchTranspilation:
    """Batch transpilation test for Phase 12 VistA routines (T078).

    Verifies that all routines unblocked by Phase 12A/B/C transpile
    without error. 3 routines have known non-Phase-12 blockers:
    - ZOSVGTM: $ZBITSTR not implemented
    - ZSY: SET $ZSTEP not supported
    - ZOSVGUT3: READ with $INCREMENT subscript (pre-existing)
    """

    TRANSPILABLE_ROUTINES = [
        # Phase 12A: intrinsic function stubs
        pytest.param("VA FileMan/Routines/DINVVXD.m", "DINVVXD", id="DINVVXD"),
        pytest.param("Kernel/Routines/ZOSVVXD.m", "ZOSVVXD", id="ZOSVVXD"),
        pytest.param("Kernel/Routines/ZTER1.m", "ZTER1", id="ZTER1"),
        pytest.param(
            "Capacity Management/Routines/KMPTCMRT.m", "KMPTCMRT", id="KMPTCMRT"
        ),
        pytest.param("Kernel/Routines/XLFSHAN.m", "XLFSHAN", id="XLFSHAN"),
        pytest.param("Kernel/Routines/ZIS4GTM.m", "ZIS4GTM", id="ZIS4GTM"),
        pytest.param("Kernel/Routines/ZOSVKRO.m", "ZOSVKRO", id="ZOSVKRO"),
        pytest.param("Kernel/Routines/ZISHGTM.m", "ZISHGTM", id="ZISHGTM"),
        pytest.param("MASH Utilities/Routines/ut.m", "ut", id="ut"),
        # Phase 12B: SVN readers
        pytest.param("Capacity Management/Routines/KMPUTLW.m", "KMPUTLW", id="KMPUTLW"),
        pytest.param(
            "Scheduling/Routines/SCANTYPEDEFS.m", "SCANTYPEDEFS", id="SCANTYPEDEFS"
        ),
        # Phase 12C: SET/GET $ZD
        pytest.param("Kernel/Routines/XPDOS.m", "XPDOS", id="XPDOS"),
        pytest.param("Kernel/Routines/ZISHGUX.m", "ZISHGUX", id="ZISHGUX"),
    ]

    @pytest.mark.parametrize("rel_path, routine_name", TRANSPILABLE_ROUTINES)
    def test_routine_transpiles(self, rel_path, routine_name):
        """Each Phase 12 routine should transpile without error."""
        import ast
        import warnings
        from pathlib import Path

        # Use project root to build absolute path
        project_root = Path(__file__).resolve().parents[5]
        routine_path = project_root / "VistA-VEHU-M" / "Packages" / rel_path
        if not routine_path.exists():
            pytest.skip(f"VistA routine not found: {routine_path}")

        source = routine_path.read_text(encoding="utf-8", errors="replace")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = generate_python(source, routine_name=routine_name)
        assert result
        ast.parse(result)


# =============================================================================
# Phase 14: $ZBITSTR runtime helper tests
# =============================================================================


@pytest.mark.codegen
@pytest.mark.ydb
class TestZbitstrHelper:
    """Unit tests for m_zbitstr() runtime helper.

    $ZBITSTR(n[,v]) creates a YDB-format bitstring:
    1-byte header (unused bits in last byte) + data bytes.
    Verified against YDB output.
    """

    def test_zbitstr_8_zero(self):
        """$ZBITSTR(8,0) → 2 bytes: header=0, data=0x00."""
        from m2py.runtime.helpers import m_zbitstr

        result = m_zbitstr("8", "0")
        b = result.encode("latin-1")
        assert len(b) == 2
        assert b[0] == 0  # header: 0 unused bits
        assert b[1] == 0  # 8 zero bits

    def test_zbitstr_8_one(self):
        """$ZBITSTR(8,1) → 2 bytes: header=0, data=0xFF."""
        from m2py.runtime.helpers import m_zbitstr

        result = m_zbitstr("8", "1")
        b = result.encode("latin-1")
        assert len(b) == 2
        assert b[0] == 0  # header: 0 unused bits
        assert b[1] == 0xFF  # 8 one bits

    def test_zbitstr_16_zero(self):
        """$ZBITSTR(16,0) → 3 bytes: header=0, data=0x00, 0x00."""
        from m2py.runtime.helpers import m_zbitstr

        result = m_zbitstr("16", "0")
        b = result.encode("latin-1")
        assert len(b) == 3
        assert b[0] == 0  # header: 0 unused bits
        assert b[1] == 0
        assert b[2] == 0

    def test_zbitstr_4_zero(self):
        """$ZBITSTR(4,0) → 2 bytes: header=4, data=0x00 (4 unused bits)."""
        from m2py.runtime.helpers import m_zbitstr

        result = m_zbitstr("4", "0")
        b = result.encode("latin-1")
        assert len(b) == 2
        assert b[0] == 4  # header: 4 unused bits
        assert b[1] == 0  # data byte with 4 zero bits + 4 unused

    def test_zbitstr_default_value_is_zero(self):
        """$ZBITSTR(8) defaults to 0 (all zero bits)."""
        from m2py.runtime.helpers import m_zbitstr

        result = m_zbitstr("8")
        b = result.encode("latin-1")
        assert len(b) == 2
        assert b[0] == 0
        assert b[1] == 0

    def test_zbitstr_zero_length(self):
        """$ZBITSTR(0) → 1 byte header only."""
        from m2py.runtime.helpers import m_zbitstr

        result = m_zbitstr("0")
        b = result.encode("latin-1")
        assert len(b) == 1
        assert b[0] == 0

    def test_zbitstr_negative_length(self):
        """$ZBITSTR(-1) → same as zero length (1 byte header)."""
        from m2py.runtime.helpers import m_zbitstr

        result = m_zbitstr("-1")
        b = result.encode("latin-1")
        assert len(b) == 1

    def test_zbitstr_9_bits(self):
        """$ZBITSTR(9,0) → 3 bytes: header=7, 2 data bytes (7 unused bits)."""
        from m2py.runtime.helpers import m_zbitstr

        result = m_zbitstr("9", "0")
        b = result.encode("latin-1")
        assert len(b) == 3  # header + 2 data bytes (ceil(9/8)=2)
        assert b[0] == 7  # (8-9%8)%8 = (8-1)%8 = 7

    def test_zbitstr_1_bit(self):
        """$ZBITSTR(1,1) → 2 bytes: header=7, data=0xFF."""
        from m2py.runtime.helpers import m_zbitstr

        result = m_zbitstr("1", "1")
        b = result.encode("latin-1")
        assert len(b) == 2
        assert b[0] == 7  # 7 unused bits
        assert b[1] == 0xFF  # 1 set bit + 7 unused

    def test_zbitstr_xor_with_char(self):
        """Verify $ZBITSTR works with $ZBITXOR (ZOSVGTM LPC pattern).

        LPC(X):
          S R=$ZBITSTR(8,0)
          F I=1:1:$L(X) S R=$ZBITXOR(R,$C(0)_$E(X,I))
          Q $A(R,2)
        """
        from m2py.runtime.helpers import m_zbitstr, m_zbitxor

        # $ZBITSTR(8,0) = [0, 0x00]
        r = m_zbitstr("8", "0")
        # XOR with $C(0)_"A" = [0x00, 0x41]
        char_str = "\x00A"
        r = m_zbitxor(r, char_str)
        b = r.encode("latin-1")
        # Result: [0^0, 0x00^0x41] = [0, 0x41]
        assert b[1] == 0x41  # ASCII 'A'

        # XOR with another char: $C(0)_"B" = [0x00, 0x42]
        char_str = "\x00B"
        r = m_zbitxor(r, char_str)
        b = r.encode("latin-1")
        # Result: [0, 0x41^0x42] = [0, 0x03]
        assert b[1] == 0x03


@pytest.mark.codegen
@pytest.mark.ydb
class TestZbitstrCodegen:
    """Codegen tests for $ZBITSTR — transpile and compile."""

    def test_zbitstr_two_args_transpiles(self):
        """$ZBITSTR(8,0) generates m_zbitstr() call."""
        code = "TEST\n S R=$ZBITSTR(8,0)\n Q"
        result = generate_python(code)
        assert "m_zbitstr" in result
        import ast

        ast.parse(result)

    def test_zbitstr_one_arg_transpiles(self):
        """$ZBITSTR(8) generates m_zbitstr() call with one arg."""
        code = "TEST\n S R=$ZBITSTR(8)\n Q"
        result = generate_python(code)
        assert "m_zbitstr" in result
        import ast

        ast.parse(result)

    def test_zbitstr_lpc_pattern_transpiles(self):
        """ZOSVGTM LPC CRC pattern transpiles and compiles."""
        code = """LPC
 N R,I
 S R=$ZBITSTR(8,0)
 S R=$ZBITXOR(R,$C(0)_"A")
 W $A(R,2),!
 Q
"""
        result = generate_python(code)
        assert "m_zbitstr" in result
        assert "m_zbitxor" in result
        import ast

        ast.parse(result)

    def test_zbitstr_transpile_execute(self):
        """$ZBITSTR(8,0) + $ZBITXOR CRC computation matches expected output."""
        code = """TEST
 N R,I,X
 S X="AB"
 S R=$ZBITSTR(8,0)
 F I=1:1:$L(X) S R=$ZBITXOR(R,$C(0)_$E(X,I))
 W $A(R,2),!
 Q
"""
        result = generate_python(code)

        from m2py.runtime import MUMPSRuntime, run_with_goto_support

        ns = {}
        exec(result, ns)
        rt = MUMPSRuntime()
        rt._capture_output = True
        rt._current_routine = "TEST"
        rt._current_source_lines = ns.get("_source_lines", [])
        rt._current_label_lines = ns.get("_label_lines", {})
        run_with_goto_support(ns["TEST"], rt, {})
        # A=0x41, B=0x42; 0x41^0x42=0x03
        assert rt.get_output() == "3\n"


@pytest.mark.codegen
@pytest.mark.ydb
class TestSetZstepCodegen:
    """Codegen tests for SET $ZSTEP — no-op stub."""

    def test_set_zstep_transpiles(self):
        """SET $ZSTEP generates a pass (no-op)."""
        code = 'TEST\n S $ZSTEP="D ZSTEP^ZSY"\n Q'
        result = generate_python(code)
        assert "pass  # SET $ZSTEP no-op" in result

    def test_set_zstep_abbreviation_transpiles(self):
        """SET $ZSTE generates a pass (no-op) — abbreviation form."""
        code = 'TEST\n S $ZSTE="code"\n Q'
        result = generate_python(code)
        assert "pass  # SET $ZSTEP no-op" in result

    def test_set_zstep_in_tuple_set(self):
        """SET ($ZSTEP,X)="val" — tuple SET with $ZSTEP."""
        code = 'TEST\n S ($ZSTEP,X)="val"\n Q'
        result = generate_python(code)
        assert "pass  # SET $ZSTEP no-op" in result
        import ast

        ast.parse(result)

    def test_set_zstep_compiles_and_runs(self):
        """SET $ZSTEP generates compilable, runnable code."""
        code = 'TEST\n S $ZSTEP="D ZSTEP^ZSY"\n W "ok",!\n Q'
        result = generate_python(code)

        from m2py.runtime import MUMPSRuntime, run_with_goto_support

        ns = {}
        exec(result, ns)
        rt = MUMPSRuntime()
        rt._capture_output = True
        rt._current_routine = "TEST"
        rt._current_source_lines = ns.get("_source_lines", [])
        rt._current_label_lines = ns.get("_label_lines", {})
        run_with_goto_support(ns["TEST"], rt, {})
        assert rt.get_output() == "ok\n"


@pytest.mark.codegen
@pytest.mark.ydb
class TestZcoAliasCodegen:
    """$ZCO is an abbreviation for $ZCONVERT."""

    def test_zco_transpiles(self):
        """$ZCO(X,"U") generates m_zconvert() call."""
        code = 'TEST\n S X=$ZCO("hello","U")\n Q'
        result = generate_python(code)
        assert "m_zconvert" in result

    def test_zco_execute(self):
        """$ZCO("hello","U") returns "HELLO"."""
        code = 'TEST\n W $ZCO("hello","U"),!\n Q'
        result = generate_python(code)

        from m2py.runtime import MUMPSRuntime, run_with_goto_support

        ns = {}
        exec(result, ns)
        rt = MUMPSRuntime()
        rt._capture_output = True
        rt._current_routine = "TEST"
        rt._current_source_lines = ns.get("_source_lines", [])
        rt._current_label_lines = ns.get("_label_lines", {})
        run_with_goto_support(ns["TEST"], rt, {})
        assert rt.get_output() == "HELLO\n"


@pytest.mark.codegen
@pytest.mark.ydb
class TestZsigprocCodegen:
    """$ZSIGPROC stub returns "1"."""

    def test_zsigproc_transpiles(self):
        """$ZSIGPROC(pid, signal) transpiles to stub."""
        code = "TEST\n S %=$ZSIGPROC(1234,15)\n Q"
        result = generate_python(code)
        import ast

        ast.parse(result)


@pytest.mark.codegen
@pytest.mark.ydb
class TestReadGlobalWithIncrementCodegen:
    """Phase 14C: READ with $INCREMENT in global subscript."""

    def test_read_global_simple_timeout(self):
        """R ^TMP($J,$I(^TMP($J))):0 generates valid Python."""
        code = """TEST
 K ^TMP(1)
 R ^TMP(1,$I(^TMP(1))):0
 Q
"""
        result = generate_python(code)
        # Should use _rt.globals.set() instead of assignment to generate_expr()
        assert "_rt.globals.set(" in result
        import ast

        ast.parse(result)

    def test_read_global_loop_pattern(self):
        """F  R ^TMP($J,$I(^TMP($J))):0 Q:... — the ZOSVGUT3 pattern."""
        code = """TEST
 K ^TMP(1)
 F  R ^TMP(1,$I(^TMP(1))):0 Q:1
 Q
"""
        result = generate_python(code)
        assert "_rt.globals.set(" in result
        import ast

        ast.parse(result)

    def test_read_global_no_subscript(self):
        """R ^TMP:0 — global without subscripts."""
        code = """TEST
 R ^TMP:0
 Q
"""
        result = generate_python(code)
        assert "_rt.globals.set(" in result
        import ast

        ast.parse(result)

    def test_read_local_variable_still_works(self):
        """R X:0 — local variable should still use direct assignment."""
        code = """TEST
 R X:0
 Q
"""
        result = generate_python(code)
        # Should NOT use _rt.globals.set() for locals
        assert "_rt.globals.set(" not in result
        import ast

        ast.parse(result)

    def test_read_global_basic(self):
        """R ^TMP — basic global read (no timeout)."""
        code = """TEST
 R ^TMP
 Q
"""
        result = generate_python(code)
        assert "_rt.globals.set(" in result
        import ast

        ast.parse(result)

    def test_read_global_maxlen(self):
        """R ^TMP#5 — global with maxlen."""
        code = """TEST
 R ^TMP(1)#5
 Q
"""
        result = generate_python(code)
        assert "_rt.globals.set(" in result
        import ast

        ast.parse(result)

    def test_read_global_char_read(self):
        """R *^X — character read into global (uncommon but valid)."""
        # Note: R *^X reads a single char code into a global
        # This may not be a common pattern but should be valid
        code = """TEST
 R *^TMP
 Q
"""
        result = generate_python(code)
        assert "_rt.globals.set(" in result
        import ast

        ast.parse(result)


@pytest.mark.codegen
@pytest.mark.ydb
class TestPhase14BatchTranspilation:
    """Phase 14: Batch transpilation of target routines."""

    TRANSPILABLE_ROUTINES = [
        pytest.param("Kernel/Routines/ZOSVGTM.m", "ZOSVGTM", id="ZOSVGTM-zbitstr"),
        pytest.param("Uncategorized/Routines/ZSY.m", "ZSY", id="ZSY-zstep"),
        pytest.param("Kernel/Routines/ZOSVGUT3.m", "ZOSVGUT3", id="ZOSVGUT3-read-incr"),
    ]

    @pytest.mark.parametrize("rel_path, routine_name", TRANSPILABLE_ROUTINES)
    def test_routine_transpiles(self, rel_path, routine_name):
        """Each Phase 14 target routine should transpile without error."""
        import ast
        import warnings
        from pathlib import Path

        project_root = Path(__file__).resolve().parents[5]
        routine_path = project_root / "VistA-VEHU-M" / "Packages" / rel_path
        if not routine_path.exists():
            pytest.skip(f"VistA routine not found: {routine_path}")

        source = routine_path.read_text(encoding="utf-8", errors="replace")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = generate_python(source, routine_name=routine_name)
        assert result
        ast.parse(result)
