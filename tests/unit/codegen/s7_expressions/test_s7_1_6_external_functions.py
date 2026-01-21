"""Tests for external C function ($&) code generation.

Spec 015: External C functions are parsed and analyzed but cannot be
transpiled to pure Python as they call native C code linked into the
MUMPS runtime.

Reference: MUMPS standard, YottaDB external functions documentation
"""

import pytest


@pytest.mark.codegen
class TestExternalFunctionCodegen:
    """Codegen-level tests for external C functions ($&)."""

    def test_external_function_raises_not_implemented(self, generate_python):
        """External function $&RAND raises NotImplementedError during codegen."""
        with pytest.raises(NotImplementedError) as exc:
            generate_python("TEST W $&RAND(1) Q")
        assert "$&RAND" in str(exc.value)
        assert "External C function" in str(exc.value)

    def test_external_function_with_package_raises_not_implemented(
        self, generate_python
    ):
        """Package-qualified external function $&pkg.name raises NotImplementedError."""
        with pytest.raises(NotImplementedError) as exc:
            generate_python('TEST W $&ydbposix.signalval("SIGTERM",.x) Q')
        assert "$&ydbposix.signalval" in str(exc.value)
        assert "External C function" in str(exc.value)

    def test_external_function_error_message_explains_limitation(self, generate_python):
        """External function error message explains why it's not supported."""
        with pytest.raises(NotImplementedError) as exc:
            generate_python("TEST W $&TEST() Q")
        msg = str(exc.value)
        assert "native C code" in msg
        assert "cannot be transpiled to pure Python" in msg

    def test_external_function_with_byref_arg_raises_not_implemented(
        self, generate_python
    ):
        """External function with by-ref argument still raises NotImplementedError."""
        with pytest.raises(NotImplementedError) as exc:
            generate_python("TEST W $&RAND(.X) Q")
        assert "$&RAND" in str(exc.value)


@pytest.mark.codegen
class TestExternalFunctionParsing:
    """Verify external functions parse correctly before hitting codegen limitation."""

    def test_external_function_parses_name_only(self, generate_python):
        """External function parses correctly before raising codegen error."""
        # The parse succeeds, codegen fails - error shows function was parsed
        with pytest.raises(NotImplementedError) as exc:
            generate_python("TEST W $&RANDOM(1,100) Q")
        # Function name was correctly extracted
        assert "$&RANDOM" in str(exc.value)

    def test_external_function_parses_package_qualified(self, generate_python):
        """Package-qualified external function parses correctly."""
        with pytest.raises(NotImplementedError) as exc:
            generate_python("TEST W $&math.sqrt(16) Q")
        # Package.name was correctly extracted
        assert "$&math.sqrt" in str(exc.value)

    def test_external_function_no_args(self, generate_python):
        """External function without arguments raises NotImplementedError."""
        with pytest.raises(NotImplementedError) as exc:
            generate_python("TEST W $&NOW Q")
        assert "$&NOW" in str(exc.value)
