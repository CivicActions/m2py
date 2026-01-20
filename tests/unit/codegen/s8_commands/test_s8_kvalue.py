"""Tests for §8 kvalue code generation.

Reference: MUMPS 1995 ANSI Standard, Section 8.2 KVALUE

Note: KVALUE is an ANSI MUMPS command that deletes only the root value of a
variable, leaving subscripted descendants intact. This command is NOT
supported by YDB ("Invalid command keyword").

m2py targets YDB compatibility, so this command raises NotImplementedError.
"""

import pytest


@pytest.mark.codegen
class TestKvalueCodegen:
    """Codegen-level tests for kvalue code generation."""

    def test_kvalue_codegen(self, generate_python):
        """KVALUE command raises NotImplementedError.

        KVALUE (KV) is an ANSI MUMPS command not supported by YDB.
        m2py raises NotImplementedError when encountering this command.
        """
        source = "TEST KV A Q"
        with pytest.raises(
            NotImplementedError, match="Unsupported statement type: MKValueStatement"
        ):
            generate_python(source)
