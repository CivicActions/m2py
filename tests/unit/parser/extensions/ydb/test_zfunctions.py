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
class TestZfunctionsAdditional:
    """Additional Z-function parsing tests (YDB implementation-defined).

    These Z-functions are all supported by the parser. Per FR-017, all $Z...
    function names are accepted by the grammar as implementation-defined.
    """

    def test_zbitand(self, expr_metamodel):
        """$ZBITAND parsing - bitwise AND."""
        model = expr_metamodel.model_from_str("$ZBITAND(A,B)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZBITAND"

    def test_zbitcount(self, expr_metamodel):
        """$ZBITCOUNT parsing - count set bits."""
        model = expr_metamodel.model_from_str("$ZBITCOUNT(X)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZBITCOUNT"

    def test_zbitfind(self, expr_metamodel):
        """$ZBITFIND parsing - find bit."""
        model = expr_metamodel.model_from_str("$ZBITFIND(X,1)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZBITFIND"

    def test_zbitget(self, expr_metamodel):
        """$ZBITGET parsing - get bit value."""
        model = expr_metamodel.model_from_str("$ZBITGET(X,5)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZBITGET"

    def test_zbitnot(self, expr_metamodel):
        """$ZBITNOT parsing - bitwise NOT."""
        model = expr_metamodel.model_from_str("$ZBITNOT(X)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZBITNOT"

    def test_zbitor(self, expr_metamodel):
        """$ZBITOR parsing - bitwise OR."""
        model = expr_metamodel.model_from_str("$ZBITOR(A,B)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZBITOR"

    def test_zbitset(self, expr_metamodel):
        """$ZBITSET parsing - set bit value."""
        model = expr_metamodel.model_from_str("$ZBITSET(X,5,1)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZBITSET"

    def test_zbitstr(self, expr_metamodel):
        """$ZBITSTR parsing - create bit string."""
        model = expr_metamodel.model_from_str("$ZBITSTR(8)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZBITSTR"

    def test_zbitxor(self, expr_metamodel):
        """$ZBITXOR parsing - bitwise XOR."""
        model = expr_metamodel.model_from_str("$ZBITXOR(A,B)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZBITXOR"

    def test_zcollate(self, expr_metamodel):
        """$ZCOLLATE parsing - collation function."""
        model = expr_metamodel.model_from_str("$ZCOLLATE(X)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZCOLLATE"

    def test_zdata(self, expr_metamodel):
        """$ZDATA parsing - extended data function."""
        model = expr_metamodel.model_from_str("$ZDATA(X)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZDATA"

    def test_zdate(self, expr_metamodel):
        """$ZDATE parsing - date formatting."""
        model = expr_metamodel.model_from_str("$ZDATE(123)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZDATE"

    def test_zdirectory(self, expr_metamodel):
        """$ZDIRECTORY parsing - directory path (read-only ISV)."""
        model = expr_metamodel.model_from_str("$ZDIRECTORY", "Expr")
        assert model is not None
        operand = model.left.operand
        # May parse as IntrinsicFunctionNoArgs or SpecialVariable
        assert operand.name == "ZDIRECTORY"

    def test_zedit(self, expr_metamodel):
        """$ZEDIT parsing - edit distance."""
        model = expr_metamodel.model_from_str('$ZEDIT("abc","abd")', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZEDIT"

    def test_zff(self, expr_metamodel):
        """$ZFF parsing - form feed (read-only ISV)."""
        model = expr_metamodel.model_from_str("$ZFF", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.name == "ZFF"

    def test_zincr(self, expr_metamodel):
        """$ZINCR parsing - increment function."""
        model = expr_metamodel.model_from_str("$ZINCR(X)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZINCR"

    def test_zio(self, expr_metamodel):
        """$ZIO parsing - I/O device (read-only ISV)."""
        model = expr_metamodel.model_from_str("$ZIO", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.name == "ZIO"

    def test_zjobexam(self, expr_metamodel):
        """$ZJOBEXAM parsing - job examination."""
        model = expr_metamodel.model_from_str("$ZJOBEXAM()", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZJOBEXAM"

    def test_zmessage(self, expr_metamodel):
        """$ZMESSAGE parsing - error message."""
        model = expr_metamodel.model_from_str("$ZMESSAGE(123)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZMESSAGE"

    def test_zmode(self, expr_metamodel):
        """$ZMODE parsing - mode (read-only ISV)."""
        model = expr_metamodel.model_from_str("$ZMODE", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.name == "ZMODE"

    def test_zname(self, expr_metamodel):
        """$ZNAME parsing - name validation."""
        model = expr_metamodel.model_from_str('$ZNAME("varname")', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZNAME"

    def test_znext(self, expr_metamodel):
        """$ZNEXT parsing - next subscript (deprecated)."""
        model = expr_metamodel.model_from_str("$ZNEXT(^X)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZNEXT"

    def test_zorder(self, expr_metamodel):
        """$ZORDER parsing - order function."""
        model = expr_metamodel.model_from_str("$ZORDER(^X)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZORDER"

    def test_zpeek(self, expr_metamodel):
        """$ZPEEK parsing - memory peek."""
        model = expr_metamodel.model_from_str('$ZPEEK("region",0)', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZPEEK"

    def test_zpid(self, expr_metamodel):
        """$ZPID parsing - process ID."""
        model = expr_metamodel.model_from_str("$ZPID(0)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZPID"

    def test_zpreferredlang(self, expr_metamodel):
        """$ZPREFERREDLANG parsing - preferred language (read-only ISV)."""
        model = expr_metamodel.model_from_str("$ZPREFERREDLANG", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.name == "ZPREFERREDLANG"

    def test_zprint(self, expr_metamodel):
        """$ZPRINT parsing - print routine."""
        model = expr_metamodel.model_from_str('$ZPRINT("routine")', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZPRINT"

    def test_zqgblmod(self, expr_metamodel):
        """$ZQGBLMOD parsing - global modification count."""
        model = expr_metamodel.model_from_str("$ZQGBLMOD(^X)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZQGBLMOD"

    def test_zqsub(self, expr_metamodel):
        """$ZQSUB parsing - subscript query."""
        model = expr_metamodel.model_from_str("$ZQSUB(X,1)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZQSUB"

    def test_zsocket(self, expr_metamodel):
        """$ZSOCKET parsing - socket information."""
        model = expr_metamodel.model_from_str('$ZSOCKET(dev,"SOCKETHANDLE")', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZSOCKET"

    def test_zsub(self, expr_metamodel):
        """$ZSUB parsing - subscript function."""
        model = expr_metamodel.model_from_str("$ZSUB(X,1)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZSUB"

    def test_zsuffix(self, expr_metamodel):
        """$ZSUFFIX parsing - suffix function."""
        model = expr_metamodel.model_from_str('$ZSUFFIX("file.txt")', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZSUFFIX"

    def test_zsupermask(self, expr_metamodel):
        """$ZSUPERMASK parsing - supermask function."""
        model = expr_metamodel.model_from_str("$ZSUPERMASK(X,Y)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZSUPERMASK"

    def test_zsyslog(self, expr_metamodel):
        """$ZSYSLOG parsing - system log."""
        model = expr_metamodel.model_from_str('$ZSYSLOG("message")', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZSYSLOG"

    def test_ztrigger(self, expr_metamodel):
        """$ZTRIGGER parsing - trigger function."""
        model = expr_metamodel.model_from_str('$ZTRIGGER("FILE",file)', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZTRIGGER"

    def test_ztrnlnm(self, expr_metamodel):
        """$ZTRNLNM parsing - translate logical name."""
        model = expr_metamodel.model_from_str('$ZTRNLNM("logname")', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZTRNLNM"

    def test_zversion(self, expr_metamodel):
        """$ZVERSION parsing - version string (read-only ISV)."""
        model = expr_metamodel.model_from_str("$ZVERSION", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.name == "ZVERSION"

    def test_zwidth(self, expr_metamodel):
        """$ZWIDTH parsing - display width."""
        model = expr_metamodel.model_from_str("$ZWIDTH(STR)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZWIDTH"
