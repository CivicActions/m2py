"""Tests for external C function ($&) code generation.

Spec 015: External C functions are parsed and analyzed. They are transpiled
to stub calls (m_zcall_stub) that emit a runtime warning and return empty
string. This allows VistA routines referencing $& functions to transpile
successfully rather than failing at codegen time.

Reference: MUMPS standard, YottaDB external functions documentation
"""

import pytest


@pytest.mark.codegen
class TestExternalFunctionCodegen:
    """Codegen-level tests for external C functions ($&)."""

    def test_external_function_generates_stub(self, generate_python):
        """External function $&RAND generates a stub call."""
        code = generate_python("TEST W $&RAND(1) Q")
        assert "m_zcall_stub" in code
        assert "$&RAND" in code

    def test_external_function_with_package_generates_stub(self, generate_python):
        """Package-qualified external function $&pkg.name generates stub."""
        code = generate_python('TEST W $&ydbposix.signalval("SIGTERM",.x) Q')
        assert "m_zcall_stub" in code
        assert "$&ydbposix.signalval" in code

    def test_external_function_stub_contains_identifier(self, generate_python):
        """External function stub includes the function identifier for warnings."""
        code = generate_python("TEST W $&TEST() Q")
        assert "m_zcall_stub" in code
        assert "$&TEST" in code

    def test_external_function_with_byref_arg_generates_stub(self, generate_python):
        """External function with by-ref argument generates stub."""
        code = generate_python("TEST W $&RAND(.X) Q")
        assert "m_zcall_stub" in code
        assert "$&RAND" in code


@pytest.mark.codegen
class TestExternalFunctionParsing:
    """Verify external functions parse correctly and generate stubs."""

    def test_external_function_parses_name_only(self, generate_python):
        """External function parses correctly and generates stub."""
        code = generate_python("TEST W $&RANDOM(1,100) Q")
        assert "m_zcall_stub" in code
        assert "$&RANDOM" in code

    def test_external_function_parses_package_qualified(self, generate_python):
        """Package-qualified external function parses and generates stub."""
        code = generate_python("TEST W $&math.sqrt(16) Q")
        assert "m_zcall_stub" in code
        assert "$&math.sqrt" in code

    def test_external_function_no_args(self, generate_python):
        """External function without arguments generates stub."""
        code = generate_python("TEST W $&NOW Q")
        assert "m_zcall_stub" in code
        assert "$&NOW" in code
