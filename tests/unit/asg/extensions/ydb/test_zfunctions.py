"""Tests for Z-function ASG analysis (YDB extension).

Reference: YottaDB implementation-defined $Z... functions
These are implementation-defined per FR-017.
"""

import pytest

from m2py.analysis.semantic_analyzer import analyze_expression
from m2py.asg.expressions import MIntrinsicFunction
from tests.helpers.parsing import parse_expression


@pytest.mark.asg
@pytest.mark.ydb
class TestZfunctionsAsg:
    """ASG-level tests for Z-functions (YDB implementation-defined).

    All Z-functions are implementation-defined per FR-017.
    The parser accepts $Z... function names and they analyze correctly.
    """

    def test_zdate_asg(self):
        """$ZDATE is correctly analyzed as an intrinsic function."""
        expr = parse_expression("$ZDATE(123)")
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "ZDATE"
        assert len(result.arguments) == 1

    def test_zmessage_asg(self):
        """$ZMESSAGE is correctly analyzed as an intrinsic function."""
        expr = parse_expression("$ZMESSAGE(150)")
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "ZMESSAGE"

    def test_zwidth_asg(self):
        """$ZWIDTH is correctly analyzed as an intrinsic function."""
        expr = parse_expression('$ZWIDTH("test")')
        result = analyze_expression(expr)
        assert isinstance(result, MIntrinsicFunction)
        assert result.name == "ZWIDTH"
