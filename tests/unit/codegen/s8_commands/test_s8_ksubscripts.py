"""Tests for §8 ksubscripts code generation.

Reference: MUMPS 1995 ANSI Standard, Section 8.2 KSUBSCRIPTS

Note: KSUBSCRIPTS is an ANSI MUMPS command that deletes only the subscripted
descendants of a variable, leaving the root value intact. This command is
NOT supported by YDB ("Invalid command keyword").

m2py targets YDB compatibility, so this command raises NotImplementedError.
See LIM-016 in docs/limitations.md.
"""

import pytest


@pytest.mark.codegen
class TestKsubscriptsCodegen:
    """Codegen-level tests for ksubscripts code generation."""

    def test_ksubscripts_codegen(self, generate_python):
        """KSUBSCRIPTS command raises NotImplementedError (LIM-016).

        KSUBSCRIPTS (KS) is an ANSI MUMPS command not supported by YDB.
        m2py raises NotImplementedError when encountering this command.
        """
        source = "TEST KS A Q"
        with pytest.raises(
            NotImplementedError,
            match="LIM-016: KSUBSCRIPTS command not supported",
        ):
            generate_python(source)
