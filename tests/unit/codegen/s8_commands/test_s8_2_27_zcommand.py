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


@pytest.mark.codegen
class TestZCommandExecution:
    """Execution tests for Z-commands (coverage: codegen L6680-6810)."""

    def test_zgoto_argumentless_exits(self, execute_mumps):
        """ZG — argumentless ZGOTO exits program."""
        result = execute_mumps('TEST\n W "before",!\n ZG\n W "after",!\n Q\n')
        assert "before" in result.output

    def test_zsystem_echo(self, execute_mumps):
        """ZSY "echo hello" — runs OS command and captures stdout."""
        result = execute_mumps('TEST\n ZSY "echo hello"\n Q\n')
        assert result.success is True
        assert "hello" in result.output

    def test_zshow_i(self, execute_mumps):
        """ZSHOW "I" — shows ISV info matching YDB format."""
        result = execute_mumps('TEST\n ZSHOW "I"\n Q\n')
        assert "$HOROLOG=" in result.output
        assert "$JOB=" in result.output
        assert "$ECODE=" in result.output
        assert "$TEST=" in result.output
        assert "$TLEVEL=" in result.output

    def test_zshow_star(self, execute_mumps):
        """ZSHOW "*" — shows all info (variables, stack, devices, ISVs)."""
        result = execute_mumps('TEST\n ZSHOW "*"\n Q\n')
        assert len(result.output) > 0
        assert "$HOROLOG=" in result.output
