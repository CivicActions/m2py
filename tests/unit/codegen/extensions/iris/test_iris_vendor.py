"""Tests for IRIS/Caché vendor functions and special variables.

Validates Contracts 12-19 from the 024-vista-transpilation-fixes spec:
- Contract 12: $REPLACE — string replacement
- Contract 13: $ZBOOLEAN — 16-op bitwise Boolean
- Contract 14: $ZVERSION — version string
- Contract 15: $ZF(-1) — subprocess execution
- Contract 16: $ZA — I/O activity status
- Contract 17: $ZREFERENCE — last global reference
- Contract 18: $NAMESPACE — current namespace
- Contract 19: $ZU(168) — current working directory
"""

import pytest


# =============================================================================
# Contract 12: $REPLACE
# =============================================================================


@pytest.mark.codegen
class TestReplace:
    """Tests for m_replace() — $REPLACE string replacement."""

    def test_basic_replace(self, execute_mumps):
        """$REPLACE replaces all occurrences of search string."""
        result = execute_mumps('TEST\n W $REPLACE("hello world","world","earth"),!\n Q')
        assert result.output == "hello earth\n"

    def test_remove_characters(self, execute_mumps):
        """$REPLACE with empty replacement removes occurrences."""
        result = execute_mumps('TEST\n W $REPLACE("aXbXc","X",""),!\n Q')
        assert result.output == "abc\n"

    def test_empty_search_noop(self, execute_mumps):
        """$REPLACE with empty search returns original string."""
        result = execute_mumps('TEST\n W $REPLACE("abc","","x"),!\n Q')
        assert result.output == "abc\n"

    def test_start_and_count(self, execute_mumps):
        """$REPLACE with start and count limits replacements."""
        result = execute_mumps('TEST\n W $REPLACE("aXbXcXd","X","-",1,2),!\n Q')
        assert result.output == "a-b-cXd\n"

    def test_case_insensitive(self, execute_mumps):
        """$REPLACE with case=1 does case-insensitive replacement."""
        result = execute_mumps(
            'TEST\n W $REPLACE("Hello HELLO hello","hello","X",1,-1,1),!\n Q'
        )
        assert result.output == "X X X\n"

    def test_start_position(self, execute_mumps):
        """$REPLACE with start>1 drops prefix and replaces in remainder."""
        result = execute_mumps('TEST\n W $REPLACE("Hello World","o","0",5),!\n Q')
        # start=5 means: drop first 4 chars, replace in "o World"
        assert result.output == "0 W0rld\n"

    def test_contract_12_full(self, execute_mumps):
        """Full Contract 12 test — all $REPLACE cases."""
        source = (
            "REPL\n"
            ' W $REPLACE("hello world","world","earth"),!\n'
            ' W $REPLACE("aXbXc","X",""),!\n'
            ' W $REPLACE("abc","","x"),!\n'
            ' W $REPLACE("aXbXcXd","X","-",1,2),!\n'
            ' W $REPLACE("Hello HELLO hello","hello","X",1,-1,1),!\n'
            ' W $REPLACE("Hello World","o","0",5),!\n'
            " Q"
        )
        result = execute_mumps(source)
        expected = "hello earth\nabc\nabc\na-b-cXd\nX X X\n0 W0rld\n"
        assert result.output == expected


# =============================================================================
# Contract 13: $ZBOOLEAN
# =============================================================================


@pytest.mark.codegen
class TestZBoolean:
    """Tests for m_zboolean() — $ZBOOLEAN bitwise Boolean."""

    def test_and_op(self, execute_mumps):
        """$ZBOOLEAN op 1 = AND."""
        result = execute_mumps("TEST\n W $ZBOOLEAN(3,5,1),!\n Q")
        assert result.output == "1\n"

    def test_xor_op(self, execute_mumps):
        """$ZBOOLEAN op 6 = XOR."""
        result = execute_mumps("TEST\n W $ZBOOLEAN(3,5,6),!\n Q")
        assert result.output == "6\n"

    def test_or_op(self, execute_mumps):
        """$ZBOOLEAN op 7 = OR."""
        result = execute_mumps("TEST\n W $ZBOOLEAN(3,5,7),!\n Q")
        assert result.output == "7\n"

    def test_not_and_op(self, execute_mumps):
        """$ZBOOLEAN op 12 = NOT arg1 AND arg2."""
        result = execute_mumps("TEST\n W $ZBOOLEAN(5,5,12),!\n Q")
        assert result.output == "-6\n"

    def test_false_op(self, execute_mumps):
        """$ZBOOLEAN op 0 = FALSE (always 0)."""
        result = execute_mumps("TEST\n W $ZBOOLEAN(3,5,0),!\n Q")
        assert result.output == "0\n"

    def test_true_op(self, execute_mumps):
        """$ZBOOLEAN op 15 = TRUE (always -1)."""
        result = execute_mumps("TEST\n W $ZBOOLEAN(3,5,15),!\n Q")
        assert result.output == "-1\n"

    def test_string_mode(self, execute_mumps):
        """$ZBOOLEAN with string arguments does per-byte Boolean."""
        result = execute_mumps('TEST\n W $ZBOOLEAN("abcd","_",1),!\n Q')
        assert result.output == "ABCD\n"

    def test_contract_13_full(self, execute_mumps):
        """Full Contract 13 test — all $ZBOOLEAN cases."""
        source = (
            "ZBOOL\n"
            " W $ZBOOLEAN(3,5,1),!\n"
            " W $ZBOOLEAN(3,5,6),!\n"
            " W $ZBOOLEAN(3,5,7),!\n"
            " W $ZBOOLEAN(5,5,12),!\n"
            " W $ZBOOLEAN(3,5,0),!\n"
            " W $ZBOOLEAN(3,5,15),!\n"
            ' W $ZBOOLEAN("abcd","_",1),!\n'
            " Q"
        )
        result = execute_mumps(source)
        assert result.output == "1\n6\n7\n-6\n0\n-1\nABCD\n"


# =============================================================================
# Contract 14: $ZVERSION
# =============================================================================


@pytest.mark.codegen
class TestZVersion:
    """Tests for $ZVERSION ($ZV) — version string."""

    def test_zversion_nonempty(self, execute_mumps):
        """$ZV returns a non-empty string."""
        result = execute_mumps("ZVER\n W $L($ZV)>0,!\n Q")
        assert result.output == "1\n"

    def test_zversion_contains_m2py(self, execute_mumps):
        """$ZV contains the M2PY identifier."""
        result = execute_mumps('TEST\n W $ZV["M2PY",!\n Q')
        assert result.output == "1\n"


# =============================================================================
# Contract 15: $ZF(-1) — subprocess execution
# =============================================================================


@pytest.mark.codegen
class TestZF:
    """Tests for $ZF(-1) — subprocess execution."""

    def test_zf_minus1_success(self, execute_mumps):
        """$ZF(-1) returns 0 on successful command."""
        result = execute_mumps('ZFM1\n S X=$ZF(-1,"echo test > /dev/null") W X,!\n Q')
        assert result.output == "0\n"

    def test_zf_minus1_failure(self, execute_mumps):
        """$ZF(-1) returns non-zero on failed command."""
        result = execute_mumps('TEST\n S X=$ZF(-1,"false") W X\'=0,!\n Q')
        assert result.output == "1\n"


# =============================================================================
# Contract 16: $ZA — I/O activity status
# =============================================================================


@pytest.mark.codegen
class TestZA:
    """Tests for $ZA — I/O activity status."""

    def test_za_default(self, execute_mumps):
        """$ZA defaults to 0."""
        result = execute_mumps("ZAST\n W $ZA,!\n Q")
        assert result.output == "0\n"


# =============================================================================
# Contract 17: $ZREFERENCE — last global reference
# =============================================================================


@pytest.mark.codegen
class TestZReference:
    """Tests for $ZREFERENCE ($ZR) — last global reference tracking."""

    def test_zreference_after_set(self, execute_mumps):
        """$ZR tracks SET to global."""
        result = execute_mumps('ZREF\n S ^ZZTEST(1,2)="hello" W $ZR,!\n K ^ZZTEST\n Q')
        assert result.output == "^ZZTEST(1,2)\n"

    def test_zreference_no_subscripts(self, execute_mumps):
        """$ZR tracks global without subscripts."""
        result = execute_mumps('TEST\n S ^ZZTEST="v" W $ZR,!\n K ^ZZTEST\n Q')
        assert result.output == "^ZZTEST\n"

    def test_zreference_after_kill(self, execute_mumps):
        """$ZR tracks KILL of global."""
        result = execute_mumps(
            'TEST\n S ^ZZTEST(1)="v"\n K ^ZZTEST(1)\n W $ZR,!\n K ^ZZTEST\n Q'
        )
        assert result.output == "^ZZTEST(1)\n"

    def test_zreference_empty_initially(self, execute_mumps):
        """$ZR is empty before any global access."""
        result = execute_mumps('TEST\n W $ZR="",!\n Q')
        assert result.output == "1\n"


# =============================================================================
# Contract 18: $NAMESPACE
# =============================================================================


@pytest.mark.codegen
class TestNamespace:
    """Tests for $NAMESPACE — current namespace."""

    def test_namespace_default(self, execute_mumps):
        """$NAMESPACE defaults to VISTA."""
        result = execute_mumps("NSPC\n W $NAMESPACE,!\n Q")
        assert result.output == "VISTA\n"

    def test_set_namespace(self, execute_mumps):
        """SET $NAMESPACE changes the namespace."""
        result = execute_mumps('TEST\n S $NAMESPACE="MYNS"\n W $NAMESPACE,!\n Q')
        assert result.output == "MYNS\n"


# =============================================================================
# Contract 19: $ZU(168) — current working directory
# =============================================================================


@pytest.mark.codegen
class TestZU:
    """Tests for $ZU — utility function dispatch."""

    def test_zu_168_nonempty(self, execute_mumps):
        """$ZU(168) returns a non-empty string (cwd)."""
        result = execute_mumps("ZU168\n W $L($ZU(168))>0,!\n Q")
        assert result.output == "1\n"

    def test_zu_0_pid(self, execute_mumps):
        """$ZU(0) returns a non-empty PID string."""
        result = execute_mumps("TEST\n W $L($ZU(0))>0,!\n Q")
        assert result.output == "1\n"


# =============================================================================
# $ZCONVERT
# =============================================================================


@pytest.mark.codegen
class TestZConvert:
    """Tests for $ZCONVERT/$ZCVT — string case conversion."""

    def test_upper(self, execute_mumps):
        """$ZCVT converts to uppercase."""
        result = execute_mumps('TEST\n W $ZCVT("hello","U"),!\n Q')
        assert result.output == "HELLO\n"

    def test_lower(self, execute_mumps):
        """$ZCVT converts to lowercase."""
        result = execute_mumps('TEST\n W $ZCVT("HELLO","L"),!\n Q')
        assert result.output == "hello\n"


# =============================================================================
# $VIEW stub
# =============================================================================


@pytest.mark.codegen
class TestViewFunction:
    """Tests for $VIEW function stub."""

    def test_view_returns_empty(self, execute_mumps):
        """$VIEW returns empty string (stub)."""
        result = execute_mumps('TEST\n W $V(0)="",!\n Q')
        assert result.output == "1\n"


# =============================================================================
# External call stub
# =============================================================================


@pytest.mark.codegen
class TestExternalCallStub:
    """Tests for $& external call stub."""

    def test_external_call_returns_empty(self, generate_python):
        """$& external calls generate stub code instead of raising."""
        code = generate_python("TEST\n S X=$&MYFUNC(1)\n Q")
        assert "m_zcall_stub" in code


# =============================================================================
# Unit tests for helper functions (standalone, no transpilation)
# =============================================================================


@pytest.mark.codegen
class TestReplaceHelper:
    """Direct unit tests for m_replace()."""

    def test_no_match(self):
        from m2py.runtime.helpers import m_replace

        assert m_replace("hello", "xyz", "abc") == "hello"

    def test_replace_all(self):
        from m2py.runtime.helpers import m_replace

        assert m_replace("aaa", "a", "b") == "bbb"

    def test_count_zero(self):
        from m2py.runtime.helpers import m_replace

        # count=0 means replace none
        assert m_replace("aXbXc", "X", "-", 1, 0) == "aXbXc"

    def test_replace_longer(self):
        from m2py.runtime.helpers import m_replace

        assert m_replace("ab", "a", "xyz") == "xyzb"

    def test_overlapping_search(self):
        from m2py.runtime.helpers import m_replace

        # $REPLACE does non-overlapping replacement
        assert m_replace("aaa", "aa", "b") == "ba"


@pytest.mark.codegen
class TestZBooleanHelper:
    """Direct unit tests for m_zboolean()."""

    def test_all_16_ops_integer(self):
        """Verify all 16 operation codes produce expected results."""
        from m2py.runtime.helpers import m_zboolean

        # Op 0: FALSE → always 0
        assert m_zboolean("3", "5", 0) == 0
        # Op 1: AND
        assert m_zboolean("3", "5", 1) == 1
        # Op 2: arg1 AND NOT arg2
        assert m_zboolean("3", "5", 2) == 2
        # Op 3: arg1
        assert m_zboolean("3", "5", 3) == 3
        # Op 4: NOT arg1 AND arg2
        assert m_zboolean("3", "5", 4) == 4
        # Op 5: arg2
        assert m_zboolean("3", "5", 5) == 5
        # Op 6: XOR
        assert m_zboolean("3", "5", 6) == 6
        # Op 7: OR
        assert m_zboolean("3", "5", 7) == 7
        # Op 8: NOR
        assert m_zboolean("3", "5", 8) == -8
        # Op 9: XNOR
        assert m_zboolean("3", "5", 9) == -7
        # Op 10: NOT arg2
        assert m_zboolean("3", "5", 10) == -6
        # Op 11: arg1 OR NOT arg2
        assert m_zboolean("3", "5", 11) == -5
        # Op 12: NOT arg1
        assert m_zboolean("3", "5", 12) == -4
        # Op 13: NOT arg1 OR arg2
        assert m_zboolean("3", "5", 13) == -3
        # Op 14: NAND
        assert m_zboolean("3", "5", 14) == -2
        # Op 15: TRUE → always -1
        assert m_zboolean("3", "5", 15) == -1


@pytest.mark.codegen
class TestZUHelper:
    """Direct unit tests for m_zu()."""

    def test_zu_5_returns_string(self):
        from m2py.runtime.helpers import m_zu

        result = m_zu(5)
        assert isinstance(result, str)

    def test_zu_12_returns_string(self):
        from m2py.runtime.helpers import m_zu

        result = m_zu(12)
        assert isinstance(result, str)

    def test_zu_unknown_empty(self):
        from m2py.runtime.helpers import m_zu

        result = m_zu(9999)
        assert result == ""


@pytest.mark.codegen
class TestZConvertHelper:
    """Direct unit tests for m_zconvert()."""

    def test_title_mode_is_upper(self):
        from m2py.runtime.helpers import m_zconvert

        # In IRIS, "T" mode is same as "U" (upper)
        assert m_zconvert("hello world", "T") == "HELLO WORLD"

    def test_sentence_case(self):
        from m2py.runtime.helpers import m_zconvert

        assert m_zconvert("hello world", "S") == "Hello world"

    def test_word_case(self):
        from m2py.runtime.helpers import m_zconvert

        assert m_zconvert("hello world", "W") == "Hello World"

    def test_unknown_mode(self):
        from m2py.runtime.helpers import m_zconvert

        assert m_zconvert("hello", "X") == "hello"


@pytest.mark.codegen
class TestGlobalRefTracking:
    """Direct unit tests for $ZREFERENCE tracking in global storage."""

    def test_set_updates_ref(self):
        from m2py.runtime.globals import InMemoryGlobalStorage

        gs = InMemoryGlobalStorage()
        gs.set("TEST", ("1", "2"), "hello")
        assert gs.last_global_ref == "^TEST(1,2)"

    def test_get_updates_ref(self):
        from m2py.runtime.globals import InMemoryGlobalStorage

        gs = InMemoryGlobalStorage()
        gs.set("TEST", ("1",), "v")
        gs.get("OTHER", (), update_naked=True)
        assert gs.last_global_ref == "^OTHER"

    def test_kill_updates_ref(self):
        from m2py.runtime.globals import InMemoryGlobalStorage

        gs = InMemoryGlobalStorage()
        gs.set("TEST", ("1",), "v")
        gs.kill("TEST", ("1",))
        assert gs.last_global_ref == "^TEST(1)"

    def test_string_subscript_quoted(self):
        from m2py.runtime.globals import InMemoryGlobalStorage

        gs = InMemoryGlobalStorage()
        gs.set("TEST", ("abc",), "v")
        assert gs.last_global_ref == '^TEST("abc")'


# =============================================================================
# Phase 6: Miscellaneous Fixes and Stubs (024-vista-transpilation-fixes, US5)
# =============================================================================


@pytest.mark.codegen
class TestDeviceControl:
    """Tests for device control mnemonic handling (WRITE /command)."""

    def test_write_eof_codegen(self):
        """WRITE /EOF generates device_control call."""
        from m2py.codegen import generate_python

        code = "TEST\n W /EOF\n Q"
        result = generate_python(code)
        assert "_rt.device_control(" in result
        assert "'EOF'" in result

    def test_write_listen_with_params(self):
        """WRITE /LISTEN(5) generates device_control with params."""
        from m2py.codegen import generate_python

        code = "TEST\n W /LISTEN(5)\n Q"
        result = generate_python(code)
        assert "_rt.device_control(" in result
        assert "'LISTEN'" in result

    def test_device_control_runtime_noop(self):
        """device_control() is a no-op by default on MUMPSRuntime."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        # Should not raise
        rt.device_control("EOF")
        rt.device_control("LISTEN", 5)
        rt.device_control("WAIT", 10)
        rt.device_control("CLEAR")

    def test_device_control_on_base_device(self):
        """device_control() is a no-op on base MUMPSDevice."""
        from m2py.runtime.devices import PrincipalDevice

        device = PrincipalDevice()
        # Should not raise
        device.device_control("EOF")
        device.device_control("LISTEN", 5)

    def test_runtime_delegates_to_device(self, execute_mumps):
        """Device control in transpiled code doesn't crash."""
        result = execute_mumps('TEST\n W /EOF\n W "ok",!\n Q')
        assert result.output == "ok\n"

    def test_write_clear_device_control(self):
        """WRITE /CLEAR generates device_control call."""
        from m2py.codegen import generate_python

        code = "TEST\n W /CLEAR\n Q"
        result = generate_python(code)
        assert "_rt.device_control(" in result
        assert "'CLEAR'" in result


@pytest.mark.codegen
class TestDeviceSpecialVariable:
    """Tests for $DEVICE special variable."""

    def test_device_read_codegen(self):
        """$DEVICE generates runtime call."""
        from m2py.codegen import generate_python

        code = "TEST\n W $DEVICE,!\n Q"
        result = generate_python(code)
        assert "_rt.device_status()" in result

    def test_device_returns_empty(self, execute_mumps):
        """$DEVICE returns empty string (no error)."""
        result = execute_mumps("TEST\n W $DEVICE,!\n Q")
        assert result.output == "\n"

    def test_device_in_conditional(self, execute_mumps):
        """$DEVICE in IF — tests truthiness (empty=false)."""
        result = execute_mumps('TEST\n I $DEVICE W "error",! Q\n W "ok",!\n Q')
        assert result.output == "ok\n"

    def test_device_d_abbreviation(self):
        """$D (no args) as special variable generates device_status()."""
        from m2py.codegen import generate_python

        # Note: $D with args is $DATA, $D without args is $DEVICE
        code = "TEST\n S X=$D\n Q"
        result = generate_python(code)
        assert "_rt.device_status()" in result


@pytest.mark.codegen
class TestReferenceSpecialVariable:
    """Tests for $REFERENCE ($R) special variable."""

    def test_reference_read_codegen(self):
        """$REFERENCE generates runtime call."""
        from m2py.codegen import generate_python

        code = "TEST\n W $REFERENCE,!\n Q"
        result = generate_python(code)
        assert "_rt.reference()" in result

    def test_reference_r_abbreviation(self):
        """$R (single letter) generates reference() call."""
        from m2py.codegen import generate_python

        code = "TEST\n W $R,!\n Q"
        result = generate_python(code)
        assert "_rt.reference()" in result

    def test_reference_tracks_globals(self, execute_mumps):
        """$REFERENCE tracks last global reference."""
        result = execute_mumps(
            'TEST\n S ^ZZTEST(1,2)="v" W $REFERENCE,!\n K ^ZZTEST\n Q'
        )
        assert "^ZZTEST(1,2)" in result.output

    def test_reference_empty_initially(self, execute_mumps):
        """$REFERENCE is empty initially."""
        result = execute_mumps("TEST\n W $REFERENCE,!\n Q")
        assert result.output == "\n"


@pytest.mark.codegen
class TestZGblDir:
    """Tests for $ZGBLDIR special variable."""

    def test_zgbldir_read_codegen(self):
        """$ZGBLDIR generates runtime call."""
        from m2py.codegen import generate_python

        code = "TEST\n W $ZGBLDIR,!\n Q"
        result = generate_python(code)
        assert "_rt.zgbldir()" in result

    def test_zgbldir_returns_empty(self, execute_mumps):
        """$ZGBLDIR returns empty string by default."""
        result = execute_mumps("TEST\n W $ZGBLDIR,!\n Q")
        assert result.output == "\n"

    def test_set_zgbldir(self, execute_mumps):
        """SET $ZGBLDIR stores value."""
        result = execute_mumps('TEST\n S $ZGBLDIR="/path/to/gbldir" W $ZGBLDIR,!\n Q')
        assert result.output == "/path/to/gbldir\n"


@pytest.mark.codegen
class TestSetZInterrupt:
    """Tests for SET $ZINTERRUPT / $ZINT."""

    def test_set_zinterrupt_codegen(self):
        """SET $ZINTERRUPT generates set_zinterrupt() call."""
        from m2py.codegen import generate_python

        code = 'TEST\n S $ZINTERRUPT="I $$HANDLER^UTIL"\n Q'
        result = generate_python(code)
        assert "_rt.set_zinterrupt(" in result

    def test_set_zint_abbreviation(self):
        """SET $ZINT generates set_zinterrupt() call."""
        from m2py.codegen import generate_python

        code = 'TEST\n S $ZINT="handler code"\n Q'
        result = generate_python(code)
        assert "_rt.set_zinterrupt(" in result

    def test_read_zinterrupt_codegen(self):
        """W $ZINTERRUPT generates zinterrupt() call."""
        from m2py.codegen import generate_python

        code = "TEST\n W $ZINTERRUPT,!\n Q"
        result = generate_python(code)
        assert "_rt.zinterrupt()" in result

    def test_zinterrupt_round_trip(self, execute_mumps):
        """SET and read $ZINTERRUPT round-trip."""
        result = execute_mumps('TEST\n S $ZINTERRUPT="I $$HANDLER" W $ZINTERRUPT,!\n Q')
        assert result.output == "I $$HANDLER\n"

    def test_zinterrupt_initially_empty(self, execute_mumps):
        """$ZINTERRUPT is empty initially."""
        result = execute_mumps("TEST\n W $ZINTERRUPT,!\n Q")
        assert result.output == "\n"

    def test_zinterrupt_in_tuple_set(self):
        """$ZINTERRUPT works in tuple SET: S ($ZINTERRUPT,X)=val."""
        from m2py.codegen import generate_python

        code = 'TEST\n S ($ZINTERRUPT,X)="handler"\n Q'
        result = generate_python(code)
        assert "_rt.set_zinterrupt(" in result


@pytest.mark.codegen
class TestSetZErr:
    """Tests for SET $ZERR (non-standard abbreviation of $ZERROR)."""

    def test_set_zerr_codegen(self):
        """SET $ZERR generates set_zerror() call."""
        from m2py.codegen import generate_python

        code = 'TEST\n S $ZERR=""\n Q'
        result = generate_python(code)
        assert "_rt.set_zerror(" in result

    def test_zerr_round_trip(self, execute_mumps):
        """SET $ZERR="" and read $ZE (standard abbreviation) round-trip."""
        result = execute_mumps('TEST\n S $ZERR="" W $ZE,!\n Q')
        assert result.output == "\n"

    def test_vista_pattern_zerr(self, execute_mumps):
        """VistA pattern: save $ZE then clear $ZERR."""
        result = execute_mumps('TEST\n S OLDERR=$ZE S $ZERR="" W OLDERR,!\n Q')
        assert result.output == "\n"


@pytest.mark.codegen
class TestSetZSource:
    """Tests for SET $ZSOURCE."""

    def test_set_zsource_codegen(self):
        """SET $ZSOURCE generates set_zsource() call."""
        from m2py.codegen import generate_python

        code = 'TEST\n S $ZSOURCE="MYFILE"\n Q'
        result = generate_python(code)
        assert "_rt.set_zsource(" in result

    def test_read_zsource_codegen(self):
        """W $ZSOURCE generates zsource() call (parsed as IntrinsicFunctionNoArgs)."""
        from m2py.codegen import generate_python

        code = "TEST\n W $ZSOURCE,!\n Q"
        result = generate_python(code)
        assert "_rt.zsource()" in result

    def test_zsource_round_trip(self, execute_mumps):
        """SET and read $ZSOURCE round-trip."""
        result = execute_mumps('TEST\n S $ZSOURCE="ZOSVGUT2" W $ZSOURCE,!\n Q')
        assert result.output == "ZOSVGUT2\n"

    def test_zsource_initially_empty(self, execute_mumps):
        """$ZSOURCE is empty initially."""
        result = execute_mumps("TEST\n W $ZSOURCE,!\n Q")
        assert result.output == "\n"


@pytest.mark.codegen
class TestZPrintStub:
    """Tests for ZPRINT command stub."""

    def test_zprint_generates_pass(self):
        """ZPRINT generates pass statement."""
        from m2py.codegen import generate_python

        code = "TEST\n ZPRINT TEST^TEST\n Q"
        result = generate_python(code)
        assert "pass  # ZPRINT" in result

    def test_zprint_bare_generates_pass(self):
        """Bare ZPRINT generates pass statement."""
        from m2py.codegen import generate_python

        code = "TEST\n ZP\n Q"
        result = generate_python(code)
        assert "pass  # ZPRINT" in result

    def test_zprint_runs_without_error(self, execute_mumps):
        """ZPRINT in transpiled code runs without error."""
        result = execute_mumps('TEST\n ZPRINT TEST\n W "ok",!\n Q')
        assert result.output == "ok\n"


@pytest.mark.codegen
class TestZMessageStub:
    """Tests for ZMESSAGE command stub."""

    def test_zmessage_generates_raise(self):
        """ZMESSAGE generates RuntimeError raise."""
        from m2py.codegen import generate_python

        code = "TEST\n ZMESSAGE 150373210\n Q"
        result = generate_python(code)
        assert "raise RuntimeError(m_zmessage(" in result

    def test_zmessage_with_variable(self):
        """ZMESSAGE with variable generates raise."""
        from m2py.codegen import generate_python

        code = "TEST\n S CODE=100 ZMESSAGE CODE\n Q"
        result = generate_python(code)
        assert "raise RuntimeError(m_zmessage(" in result


@pytest.mark.codegen
class TestRuntimeISVProperties:
    """Direct unit tests for new runtime ISV properties."""

    def test_device_status_default(self):
        """MUMPSRuntime.device_status() returns empty string."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        assert rt.device_status() == ""

    def test_reference_aliases_zreference(self):
        """MUMPSRuntime.reference() returns same as zreference()."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        assert rt.reference() == rt.zreference()

    def test_reference_after_global_set(self):
        """MUMPSRuntime.reference() updates after global SET."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        rt.globals.set("TEST", ("1",), "v")
        assert rt.reference() == "^TEST(1)"

    def test_zgbldir_default_empty(self):
        """MUMPSRuntime.zgbldir() returns empty string by default."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        assert rt.zgbldir() == ""

    def test_set_zgbldir(self):
        """MUMPSRuntime.set_zgbldir() stores value."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        rt.set_zgbldir("/usr/lib/yottadb/r1.38/g/yottadb.gld")
        assert rt.zgbldir() == "/usr/lib/yottadb/r1.38/g/yottadb.gld"

    def test_zinterrupt_default_empty(self):
        """MUMPSRuntime.zinterrupt() returns empty string by default."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        assert rt.zinterrupt() == ""

    def test_set_zinterrupt(self):
        """MUMPSRuntime.set_zinterrupt() stores handler code."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        rt.set_zinterrupt("I $$JOBEXAM^ZU($ZPOSITION)")
        assert rt.zinterrupt() == "I $$JOBEXAM^ZU($ZPOSITION)"

    def test_zsource_default_empty(self):
        """MUMPSRuntime.zsource() returns empty string by default."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        assert rt.zsource() == ""

    def test_set_zsource(self):
        """MUMPSRuntime.set_zsource() stores source file name."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        rt.set_zsource("ZOSVGUT2")
        assert rt.zsource() == "ZOSVGUT2"


@pytest.mark.codegen
class TestVistARoutineTranspilation:
    """Verify specific VistA routines that were blocked by Phase 6 issues now transpile."""

    def _transpile(self, stem):
        """Transpile a VistA routine by name, return generated Python."""
        from pathlib import Path

        from m2py.codegen import generate_python

        # Search common VistA package locations
        base = Path("/workspaces/m2py/VistA-VEHU-M")
        for m_file in base.rglob(f"{stem}.m"):
            code = m_file.read_text(errors="replace")
            return generate_python(code, routine_name=stem)
        pytest.skip(f"VistA routine {stem}.m not found")

    def test_zzlog1_transpiles(self):
        """ZZLOG1 (SET $ZERR) transpiles successfully."""
        result = self._transpile("ZZLOG1")
        assert "set_zerror" in result

    def test_a1bflog1_transpiles(self):
        """A1BFLOG1 (SET $ZERR) transpiles successfully."""
        result = self._transpile("A1BFLOG1")
        assert "set_zerror" in result

    def test_hlcstcp1_transpiles(self):
        """HLCSTCP1 ($DEVICE) transpiles successfully."""
        result = self._transpile("HLCSTCP1")
        assert "device_status" in result

    def test_xwbrw_transpiles(self):
        """XWBRW ($DEVICE) transpiles successfully."""
        result = self._transpile("XWBRW")
        assert "device_status" in result

    def test_ztmgrset_transpiles(self):
        """ZTMGRSET (ZPRINT, $ZSOURCE) transpiles successfully."""
        result = self._transpile("ZTMGRSET")
        assert "pass  # ZPRINT" in result
