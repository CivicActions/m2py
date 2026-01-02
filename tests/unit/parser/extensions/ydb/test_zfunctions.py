"""Tests for Z-function parsing (YDB extension).

Reference: YottaDB implementation-defined $Z... functions
These are implementation-defined per FR-017.

Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
"""

import pytest


@pytest.mark.parser
@pytest.mark.ydb
class TestZISVsParsing:
    """Parser-level tests for Z-ISVs (YDB implementation-defined).

    Z-ISVs that can be SET/NEW are parsed as SpecialVariable (in SVARNAME pattern).

    Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
    """

    # Settable Z-ISVs (parsed as SpecialVariable)
    def test_ztrap_isv(self, parse_expression):
        """$ZTRAP Z-ISV for error trapping (YDB extension).

        Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
        """
        model = parse_expression("$ZTRAP")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ZTRAP"

    def test_zstatus_isv(self, parse_expression):
        """$ZSTATUS Z-ISV for status information (YDB extension).

        Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
        """
        model = parse_expression("$ZSTATUS")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ZSTATUS"

    def test_zlevel_isv(self, parse_expression):
        """$ZLEVEL Z-ISV for stack level (YDB extension).

        Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
        """
        model = parse_expression("$ZLEVEL")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ZLEVEL"

    def test_zposition_isv(self, parse_expression):
        """$ZPOSITION Z-ISV for position information (YDB extension).

        Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
        """
        model = parse_expression("$ZPOSITION")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ZPOSITION"

    def test_zeof_isv(self, parse_expression):
        """$ZEOF Z-ISV for end of file (YDB extension).

        Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
        """
        model = parse_expression("$ZEOF")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ZEOF"

    def test_zcmdline_isv(self, parse_expression):
        """$ZCMDLINE Z-ISV for command line (YDB extension).

        Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
        """
        model = parse_expression("$ZCMDLINE")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ZCMDLINE"

    def test_zgbldir_isv(self, parse_expression):
        """$ZGBLDIR Z-ISV for global directory (YDB extension).

        Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
        """
        model = parse_expression("$ZGBLDIR")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ZGBLDIR"

    def test_zjob_isv(self, parse_expression):
        """$ZJOB Z-ISV for job ID (YDB extension).

        Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
        """
        model = parse_expression("$ZJOB")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ZJOB"

    # Read-only Z-ISVs (parsed as IntrinsicFunctionNoArgs - not in SVARNAME)
    def test_zchset_isv(self, parse_expression):
        """$ZCHSET Z-ISV for character set (read-only) (YDB extension).

        Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
        """
        model = parse_expression("$ZCHSET")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunctionNoArgs"
        assert operand.name == "ZCHSET"

    def test_zsystem_isv(self, parse_expression):
        """$ZSYSTEM Z-ISV for OS return code (read-only) (YDB extension).

        Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
        """
        model = parse_expression("$ZSYSTEM")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunctionNoArgs"
        assert operand.name == "ZSYSTEM"

    def test_zysqlnull_isv(self, parse_expression):
        """$ZYSQLNULL Z-ISV for SQL null handling (read-only) (YDB extension).

        Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
        """
        model = parse_expression("$ZYSQLNULL")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunctionNoArgs"
        assert operand.name == "ZYSQLNULL"


@pytest.mark.parser
@pytest.mark.ydb
class TestZfunctionsParsing:
    """Parser-level tests for Z-functions (YDB implementation-defined).

    HIGH/MEDIUM priority Z-functions (from YDBTest analysis).

    Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
    """

    def test_zchar_function(self, parse_expression):
        """$ZCHAR Z-function for extended character handling (YDB extension).

        Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
        """
        model = parse_expression("$ZCHAR(65)")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZCHAR"
        assert len(operand.args.args) == 1

    def test_zwrite_function(self, parse_expression):
        """$ZWRITE Z-function for write format (YDB extension).

        Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
        """
        model = parse_expression("$ZWRITE(X)")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZWRITE"
        assert len(operand.args.args) == 1

    def test_zprevious_function(self, parse_expression):
        """$ZPREVIOUS Z-function for previous in order (YDB extension).

        Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
        """
        model = parse_expression("$ZPREVIOUS(^DATA)")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZPREVIOUS"
        assert len(operand.args.args) == 1

    def test_zextract_function(self, parse_expression):
        """$ZEXTRACT Z-function for extended extract (YDB extension).

        Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
        """
        model = parse_expression("$ZEXTRACT(STR,1,5)")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZEXTRACT"
        assert len(operand.args.args) == 3

    def test_zpiece_function(self, parse_expression):
        """$ZPIECE Z-function for extended piece (YDB extension).

        Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
        """
        model = parse_expression('$ZPIECE(STR,",",1)')
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZPIECE"
        assert len(operand.args.args) == 3

    def test_ztranslate_function(self, parse_expression):
        """$ZTRANSLATE Z-function for extended translate (YDB extension).

        Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
        """
        model = parse_expression('$ZTRANSLATE(STR,"abc","xyz")')
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZTRANSLATE"
        assert len(operand.args.args) == 3

    def test_zparse_function(self, parse_expression):
        """$ZPARSE Z-function for file path parsing (YDB extension).

        Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
        """
        model = parse_expression('$ZPARSE("/path/to/file")')
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZPARSE"
        assert len(operand.args.args) == 1

    def test_zsearch_function(self, parse_expression):
        """$ZSEARCH Z-function for file search (YDB extension).

        Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
        """
        model = parse_expression('$ZSEARCH("*.m")')
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZSEARCH"
        assert len(operand.args.args) == 1

    def test_zgetjpi_function(self, parse_expression):
        """$ZGETJPI Z-function for job/process info (YDB extension).

        Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
        """
        model = parse_expression('$ZGETJPI(0,"PID")')
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZGETJPI"
        assert len(operand.args.args) == 2

    def test_zconvert_function(self, parse_expression):
        """$ZCONVERT Z-function for character conversion (YDB extension).

        Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
        """
        model = parse_expression('$ZCONVERT(STR,"L")')
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZCONVERT"
        assert len(operand.args.args) == 2

    def test_zascii_function(self, parse_expression):
        """$ZASCII Z-function for extended ASCII (YDB extension).

        Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
        """
        model = parse_expression("$ZASCII(STR)")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZASCII"
        assert len(operand.args.args) == 1

    def test_zlength_function(self, parse_expression):
        """$ZLENGTH Z-function for extended length (YDB extension).

        Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
        """
        model = parse_expression("$ZLENGTH(STR)")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZLENGTH"
        assert len(operand.args.args) == 1

    def test_zfind_function(self, parse_expression):
        """$ZFIND Z-function for extended find (YDB extension).

        Migrated from: tests/unit/test_expression_grammar.py::TestZFunctionsAndISVs
        """
        model = parse_expression('$ZFIND(STR,"pattern")')
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZFIND"
        assert len(operand.args.args) == 2
