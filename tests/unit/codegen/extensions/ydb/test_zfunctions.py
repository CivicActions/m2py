"""Tests for Z-function code generation (YDB extension).

Reference: YottaDB implementation-defined $Z... functions
These are implementation-defined per FR-017.
"""

import pytest


@pytest.mark.codegen
@pytest.mark.ydb
class TestZfunctionsCodegen:
    """Codegen-level tests for Z-functions (YDB implementation-defined).

    All Z-functions are implementation-defined per FR-017.
    Parser and ASG tests pass - codegen is not yet implemented.
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: Z-function codegen")
    def test_zdate_codegen(self, generate_python):
        """$ZDATE generates runtime call."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: Z-function codegen")
    def test_zmessage_codegen(self, generate_python):
        """$ZMESSAGE generates runtime call."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: Z-function codegen")
    def test_zwidth_codegen(self, generate_python):
        """$ZWIDTH generates runtime call."""
        pytest.fail("Stub - implement test")
