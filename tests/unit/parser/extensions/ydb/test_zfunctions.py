"""Tests for Z-function parsing (YDB extension).

Reference: YottaDB implementation-defined $Z... functions
These are implementation-defined per FR-017.
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_expression_classes


@pytest.fixture(scope="module")
def expr_metamodel():
    """Create expression metamodel for parsing."""
    grammar_path = (
        Path(__file__).parent.parent.parent.parent.parent.parent
        / "src"
        / "m2py"
        / "grammar"
        / "expressions.tx"
    )
    return metamodel_from_file(
        str(grammar_path), classes=get_expression_classes(), skipws=True
    )


@pytest.mark.parser
@pytest.mark.ydb
class TestZFunctionsAndISVs:
    """Test YottaDB/GT.M Z-function and Z-ISV parsing.

    Z-functions are parsed via IntrinsicFunction (with args) or IntrinsicFunctionNoArgs (without args).
    Z-ISVs that can be SET/NEW are parsed as SpecialVariable (in SVARNAME pattern).

    The distinction is important:
    - Functions: $ZCHAR(x), $ZWRITE(x) - callable with args
    - Settable ISVs: $ZTRAP, $ZGBLDIR - can be SET or NEW'd
    - Read-only ISVs: $ZCHSET, $ZYSQLNULL - implementation-specific, not settable
    """

    # Settable Z-ISVs (parsed as SpecialVariable)
    def test_ztrap_isv(self, expr_metamodel):
        """Parse $ZTRAP Z-ISV for error trapping."""
        model = expr_metamodel.model_from_str("$ZTRAP", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ZTRAP"

    def test_zstatus_isv(self, expr_metamodel):
        """Parse $ZSTATUS Z-ISV for status information."""
        model = expr_metamodel.model_from_str("$ZSTATUS", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ZSTATUS"

    def test_zlevel_isv(self, expr_metamodel):
        """Parse $ZLEVEL Z-ISV for stack level."""
        model = expr_metamodel.model_from_str("$ZLEVEL", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ZLEVEL"

    def test_zposition_isv(self, expr_metamodel):
        """Parse $ZPOSITION Z-ISV for position information."""
        model = expr_metamodel.model_from_str("$ZPOSITION", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ZPOSITION"

    def test_zeof_isv(self, expr_metamodel):
        """Parse $ZEOF Z-ISV for end of file."""
        model = expr_metamodel.model_from_str("$ZEOF", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ZEOF"

    def test_zcmdline_isv(self, expr_metamodel):
        """Parse $ZCMDLINE Z-ISV for command line."""
        model = expr_metamodel.model_from_str("$ZCMDLINE", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ZCMDLINE"

    def test_zgbldir_isv(self, expr_metamodel):
        """Parse $ZGBLDIR Z-ISV for global directory."""
        model = expr_metamodel.model_from_str("$ZGBLDIR", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ZGBLDIR"

    def test_zjob_isv(self, expr_metamodel):
        """Parse $ZJOB Z-ISV for job ID."""
        model = expr_metamodel.model_from_str("$ZJOB", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ZJOB"

    # Read-only Z-ISVs (parsed as IntrinsicFunctionNoArgs - not in SVARNAME)
    def test_zchset_isv(self, expr_metamodel):
        """Parse $ZCHSET Z-ISV for character set (read-only)."""
        model = expr_metamodel.model_from_str("$ZCHSET", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunctionNoArgs"
        assert operand.name == "ZCHSET"

    def test_zsystem_isv(self, expr_metamodel):
        """Parse $ZSYSTEM Z-ISV for OS return code (read-only)."""
        model = expr_metamodel.model_from_str("$ZSYSTEM", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunctionNoArgs"
        assert operand.name == "ZSYSTEM"

    def test_zysqlnull_isv(self, expr_metamodel):
        """Parse $ZYSQLNULL Z-ISV for SQL null handling (read-only)."""
        model = expr_metamodel.model_from_str("$ZYSQLNULL", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunctionNoArgs"
        assert operand.name == "ZYSQLNULL"

    # HIGH/MEDIUM priority Z-functions (from YDBTest analysis)
    def test_zchar_function(self, expr_metamodel):
        """Parse $ZCHAR Z-function for extended character handling."""
        model = expr_metamodel.model_from_str("$ZCHAR(65)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZCHAR"
        assert len(operand.args.args) == 1

    def test_zwrite_function(self, expr_metamodel):
        """Parse $ZWRITE Z-function for write format."""
        model = expr_metamodel.model_from_str("$ZWRITE(X)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZWRITE"
        assert len(operand.args.args) == 1

    def test_zprevious_function(self, expr_metamodel):
        """Parse $ZPREVIOUS Z-function for previous in order."""
        model = expr_metamodel.model_from_str("$ZPREVIOUS(^DATA)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZPREVIOUS"
        assert len(operand.args.args) == 1

    def test_zextract_function(self, expr_metamodel):
        """Parse $ZEXTRACT Z-function for extended extract."""
        model = expr_metamodel.model_from_str("$ZEXTRACT(STR,1,5)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZEXTRACT"
        assert len(operand.args.args) == 3

    def test_zpiece_function(self, expr_metamodel):
        """Parse $ZPIECE Z-function for extended piece."""
        model = expr_metamodel.model_from_str('$ZPIECE(STR,",",1)', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZPIECE"
        assert len(operand.args.args) == 3

    def test_ztranslate_function(self, expr_metamodel):
        """Parse $ZTRANSLATE Z-function for extended translate."""
        model = expr_metamodel.model_from_str('$ZTRANSLATE(STR,"abc","xyz")', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZTRANSLATE"
        assert len(operand.args.args) == 3

    def test_zparse_function(self, expr_metamodel):
        """Parse $ZPARSE Z-function for file path parsing."""
        model = expr_metamodel.model_from_str('$ZPARSE("/path/to/file")', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZPARSE"
        assert len(operand.args.args) == 1

    def test_zsearch_function(self, expr_metamodel):
        """Parse $ZSEARCH Z-function for file search."""
        model = expr_metamodel.model_from_str('$ZSEARCH("*.m")', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZSEARCH"
        assert len(operand.args.args) == 1

    def test_zgetjpi_function(self, expr_metamodel):
        """Parse $ZGETJPI Z-function for job/process info."""
        model = expr_metamodel.model_from_str('$ZGETJPI(0,"PID")', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZGETJPI"
        assert len(operand.args.args) == 2

    def test_zconvert_function(self, expr_metamodel):
        """Parse $ZCONVERT Z-function for character conversion."""
        model = expr_metamodel.model_from_str('$ZCONVERT(STR,"L")', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZCONVERT"
        assert len(operand.args.args) == 2

    def test_zascii_function(self, expr_metamodel):
        """Parse $ZASCII Z-function for extended ASCII."""
        model = expr_metamodel.model_from_str("$ZASCII(STR)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZASCII"
        assert len(operand.args.args) == 1

    def test_zlength_function(self, expr_metamodel):
        """Parse $ZLENGTH Z-function for extended length."""
        model = expr_metamodel.model_from_str("$ZLENGTH(STR)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZLENGTH"
        assert len(operand.args.args) == 1

    def test_zfind_function(self, expr_metamodel):
        """Parse $ZFIND Z-function for extended find."""
        model = expr_metamodel.model_from_str('$ZFIND(STR,"pattern")', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZFIND"
        assert len(operand.args.args) == 2


@pytest.mark.parser
@pytest.mark.ydb
class TestZfunctionsStubs:
    """Stub tests for other Z-functions not yet covered (YDB implementation-defined)."""

    @pytest.mark.skip(reason="Implementation-defined: $ZBITAND per FR-017")
    def test_zbitand(self, expr_metamodel):
        """$ZBITAND parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZBITCOUNT per FR-017")
    def test_zbitcount(self, expr_metamodel):
        """$ZBITCOUNT parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZBITFIND per FR-017")
    def test_zbitfind(self, expr_metamodel):
        """$ZBITFIND parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZBITGET per FR-017")
    def test_zbitget(self, expr_metamodel):
        """$ZBITGET parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZBITNOT per FR-017")
    def test_zbitnot(self, expr_metamodel):
        """$ZBITNOT parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZBITOR per FR-017")
    def test_zbitor(self, expr_metamodel):
        """$ZBITOR parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZBITSET per FR-017")
    def test_zbitset(self, expr_metamodel):
        """$ZBITSET parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZBITSTR per FR-017")
    def test_zbitstr(self, expr_metamodel):
        """$ZBITSTR parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZBITXOR per FR-017")
    def test_zbitxor(self, expr_metamodel):
        """$ZBITXOR parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZCOLLATE per FR-017")
    def test_zcollate(self, expr_metamodel):
        """$ZCOLLATE parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZDATA per FR-017")
    def test_zdata(self, expr_metamodel):
        """$ZDATA parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZDATE per FR-017")
    def test_zdate(self, expr_metamodel):
        """$ZDATE parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZDIRECTORY per FR-017")
    def test_zdirectory(self, expr_metamodel):
        """$ZDIRECTORY parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZEDIT per FR-017")
    def test_zedit(self, expr_metamodel):
        """$ZEDIT parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZFF per FR-017")
    def test_zff(self, expr_metamodel):
        """$ZFF parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZINCR per FR-017")
    def test_zincr(self, expr_metamodel):
        """$ZINCR parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZIO per FR-017")
    def test_zio(self, expr_metamodel):
        """$ZIO parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZJOBEXAM per FR-017")
    def test_zjobexam(self, expr_metamodel):
        """$ZJOBEXAM parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZMESSAGE per FR-017")
    def test_zmessage(self, expr_metamodel):
        """$ZMESSAGE parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZMODE per FR-017")
    def test_zmode(self, expr_metamodel):
        """$ZMODE parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZNAME per FR-017")
    def test_zname(self, expr_metamodel):
        """$ZNAME parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZNEXT per FR-017")
    def test_znext(self, expr_metamodel):
        """$ZNEXT parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZORDER per FR-017")
    def test_zorder(self, expr_metamodel):
        """$ZORDER parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZPEEK per FR-017")
    def test_zpeek(self, expr_metamodel):
        """$ZPEEK parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZPID per FR-017")
    def test_zpid(self, expr_metamodel):
        """$ZPID parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZPREFERREDLANG per FR-017")
    def test_zpreferredlang(self, expr_metamodel):
        """$ZPREFERREDLANG parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZPRINT per FR-017")
    def test_zprint(self, expr_metamodel):
        """$ZPRINT parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZQGBLMOD per FR-017")
    def test_zqgblmod(self, expr_metamodel):
        """$ZQGBLMOD parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZQSUB per FR-017")
    def test_zqsub(self, expr_metamodel):
        """$ZQSUB parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZSOCKET per FR-017")
    def test_zsocket(self, expr_metamodel):
        """$ZSOCKET parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZSUB per FR-017")
    def test_zsub(self, expr_metamodel):
        """$ZSUB parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZSUFFIX per FR-017")
    def test_zsuffix(self, expr_metamodel):
        """$ZSUFFIX parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZSUPERMASK per FR-017")
    def test_zsupermask(self, expr_metamodel):
        """$ZSUPERMASK parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZSYSLOG per FR-017")
    def test_zsyslog(self, expr_metamodel):
        """$ZSYSLOG parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZTRIGGER per FR-017")
    def test_ztrigger(self, expr_metamodel):
        """$ZTRIGGER parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZTRNLNM per FR-017")
    def test_ztrnlnm(self, expr_metamodel):
        """$ZTRNLNM parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZVERSION per FR-017")
    def test_zversion(self, expr_metamodel):
        """$ZVERSION parsing."""
        pass

    @pytest.mark.skip(reason="Implementation-defined: $ZWIDTH per FR-017")
    def test_zwidth(self, expr_metamodel):
        """$ZWIDTH parsing."""
        pass
