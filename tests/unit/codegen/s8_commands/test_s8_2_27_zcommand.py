"""Tests for Z-command code generation dispatch (§8.2.27).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.27

Z-commands are implementation-defined extensions. This file tests
that the code generator correctly dispatches Z-commands to their
implementation-specific handlers.

Note: Individual Z-command codegen tests are in
tests/unit/codegen/extensions/ydb/ (one file per Z-command).
"""

import pytest


@pytest.mark.codegen
@pytest.mark.ydb
class TestZCommandCodegenDispatch:
    """Codegen-level tests for Z-command dispatch (§8.2.27).

    Per §8.2.27, Z-commands are implementation-defined. The code
    generator must dispatch each Z-command to its appropriate handler.
    """

    def test_zwrite_dispatches_to_handler(self, generate_python):
        """ZWRITE dispatches to zwrite handler (§8.2.27)."""
        code = generate_python("TEST ZWR X Q")
        # Should generate zwrite-specific code
        assert "zwrite" in code.lower() or "_rt." in code

    def test_zgoto_dispatches_to_handler(self, generate_python):
        """ZGOTO dispatches to zgoto handler (§8.2.27)."""
        code = generate_python("TEST ZGOTO 0 Q")
        # Should generate zgoto-specific code (SystemExit or ZGotoException)
        assert "SystemExit" in code or "ZGoto" in code

    def test_zkill_dispatches_to_handler(self, generate_python):
        """ZKILL dispatches to kill handler (§8.2.27).

        ZKILL/ZWITHDRAW removes only the node, not descendants.
        """
        code = generate_python("TEST S X(1)=1,X(1,1)=2 ZK X(1) Q")
        assert "_rt." in code

    def test_zhalt_dispatches_to_handler(self, generate_python):
        """ZHALT dispatches to zhalt handler (§8.2.27)."""
        code = generate_python("TEST ZHALT 0 Q")
        assert "SystemExit" in code or "sys.exit" in code

    def test_zshow_dispatches_to_handler(self, generate_python):
        """ZSHOW dispatches to zshow handler (§8.2.27)."""
        code = generate_python('TEST ZSHOW "I" Q')
        assert "zshow" in code.lower() or "_rt." in code
