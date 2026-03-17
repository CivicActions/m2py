"""Tests for TRAMPOLINE strategy with optional formal parameters.

Bug I: When a TRAMPOLINE-strategy routine has labels with formal parameters,
calling those labels with fewer arguments than parameters should work.
In MUMPS, omitted arguments leave the formal parameter undefined.

The TRAMPOLINE strategy is triggered when a routine uses GOTO across labels.
Labels with formal parameters (e.g., WS(ERN)) should generate Python functions
where all formals default to None, matching MUMPS semantics where omitted
arguments result in undefined variables.

Real-world case: MXMLPRS0 (VistA XML Parser) uses `D WS()` to call the
`WS(ERN)` label with no actual arguments — ERN must be allowed to be undefined.
"""

import pytest

from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime


@pytest.mark.codegen
class TestTrampolineOptionalParams:
    """Optional formal parameters in TRAMPOLINE-strategy routines."""

    @pytest.fixture
    def execute_mumps(self):
        def _execute(source: str):
            python_code = generate_python(source)
            runtime = MUMPSRuntime()
            return runtime.execute(python_code, capture_output=True)

        return _execute

    def test_call_label_with_no_args(self, execute_mumps):
        """D LABEL() where LABEL(X) has one formal param — X should be undefined."""
        # GOTO forces TRAMPOLINE strategy
        source = (
            "TEST\n"
            " D SUB()\n"
            " GOTO END\n"
            " QUIT\n"
            "SUB(X)\n"
            ' W $S($D(X):"def","1":"undef"),!\n'
            " QUIT\n"
            "END\n"
            ' W "done",!\n'
            " QUIT\n"
        )
        result = execute_mumps(source)
        assert result.output == "undef\ndone\n"

    def test_call_label_with_partial_args(self, execute_mumps):
        """D LABEL(1) where LABEL(X,Y) has two formals — Y should be undefined."""
        source = (
            "TEST\n"
            " D SUB(1)\n"
            " GOTO END\n"
            " QUIT\n"
            "SUB(X,Y)\n"
            ' W X,",",$S($D(Y):"def","1":"undef"),!\n'
            " QUIT\n"
            "END\n"
            ' W "done",!\n'
            " QUIT\n"
        )
        result = execute_mumps(source)
        assert result.output == "1,undef\ndone\n"

    def test_call_label_with_all_args(self, execute_mumps):
        """D LABEL(1,2) where LABEL(X,Y) has two formals — both defined."""
        source = (
            "TEST\n"
            " D SUB(1,2)\n"
            " GOTO END\n"
            " QUIT\n"
            "SUB(X,Y)\n"
            ' W X,",",Y,!\n'
            " QUIT\n"
            "END\n"
            ' W "done",!\n'
            " QUIT\n"
        )
        result = execute_mumps(source)
        assert result.output == "1,2\ndone\n"

    def test_internal_call_with_empty_parens(self, execute_mumps):
        """Internal D WS() call to label WS(ERN) within same TRAMPOLINE routine.

        Mirrors MXMLPRS0 pattern: state 0 does 'D WS()' to call WS(ERN).
        """
        source = (
            "TEST\n"
            ' S RESULT=""\n'
            " D WS()\n"
            " GOTO END\n"
            " QUIT\n"
            "WS(ERN)\n"
            ' S RESULT=$S($D(ERN):"has-ern",1:"no-ern")\n'
            " W RESULT,!\n"
            " QUIT\n"
            "END\n"
            ' W "end",!\n'
            " QUIT\n"
        )
        result = execute_mumps(source)
        assert result.output == "no-ern\nend\n"
