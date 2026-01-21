"""Tests for TRESTART command code generation (§8.2.20).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.20

Note: TRESTART is a transaction command that restarts a restartable transaction.
This command is parsed by m2py but code generation is not yet implemented.
"""

import pytest


@pytest.mark.codegen
class TestTrestartCommandCodegen:
    """Codegen-level tests for TRESTART command code generation (§8.2.20)."""

    def test_trestart_to_restart(self, generate_python):
        """TRESTART command raises NotImplementedError - transaction restart not yet implemented.

        Per §8.2.20: TRESTART restarts a restartable transaction (started with TS:RESTART).
        m2py parses this command but does not yet generate code for transaction restart.
        """
        source = "TEST TRESTART Q"
        with pytest.raises(
            NotImplementedError, match="Unsupported statement type: MTRestartStatement"
        ):
            generate_python(source)
