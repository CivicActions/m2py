#!/usr/bin/env python3
"""State machine pattern prototype for V1GO1.m.

This spike implements the V1GO1.m MUMPS routine using the state machine pattern:
- Single function with match/case dispatching by label name (state)
- All variables in outer scope (not passed through state object)
- State transitions via state = "LABEL" assignment

Run: uv run python specs/006-cross-label-control-flow/spikes/state_machine_v1go1.py
"""

import io


def V1GO1() -> str:
    """Execute V1GO1 routine using state machine pattern."""
    # Shared routine variables (in outer scope)
    PASS_COUNT = 0
    FAIL = 0
    ITEM = ""
    VCOMP = ""
    VCORR = ""
    ROUTINE = ""
    TESTS = 0
    AUTO = 0
    VISUAL = 0

    # Output buffer
    _output = io.StringIO()

    def write(*args):
        """Simulate MUMPS WRITE command."""
        for arg in args:
            if arg == "!":
                _output.write("\n")
            elif arg == "#":
                _output.write("\f")
            else:
                _output.write(str(arg))

    def examiner():
        """EXAMINER subroutine - compares VCORR to VCOMP."""
        nonlocal PASS_COUNT, FAIL
        if VCORR == VCOMP:
            PASS_COUNT += 1
            write("!", "   PASS  ", ITEM)
        else:
            FAIL += 1
            write("!", "** FAIL  ", ITEM)
            write("!", '           COMPUTED ="', VCOMP, '"')
            write("!", '           CORRECT  ="', VCORR, '"')

    # State machine
    state = "V1GO1"
    iterations = 0

    while state is not None:
        match state:
            case "V1GO1":
                # Entry point
                PASS_COUNT = 0
                FAIL = 0
                ITEM = ""
                write(
                    "!", "!", "V1GO1: TEST OF GOTO COMMAND (LOCAL BRANCHING) -1-", "!"
                )
                write("!", "GOTO label", "!")
                write("!", "I-382/383  label is % followed by alpha and digit")
                ITEM = "I-382/383.1  label is %"
                VCOMP = "%"
                state = "%"  # GOTO %

            case "%":
                VCORR = "%"
                examiner()
                ITEM = "I-382/383.2  label is % followed by a alpha"
                VCOMP = "%A"
                state = "%A"  # GOTO %A

            case "%A":
                VCORR = "%A"
                examiner()
                ITEM = "I-382/383.3  label is % followed by alphas"
                VCOMP = "%ABCDEFG"
                state = "%ABCDEFG"  # G %ABCDEFG

            case "%ABCDEFG":
                VCORR = "%ABCDEFG"
                examiner()
                ITEM = "I-382/383.4  label is % followed by a digit"
                VCOMP = "%0"
                state = "%0"  # G %0

            case "%0":
                VCORR = "%0"
                examiner()
                ITEM = "I-382/383.5  label is % followed by 2 digits"
                VCOMP = "%90"
                state = "%90"  # G %90

            case "%90":
                VCORR = "%90"
                examiner()
                ITEM = "I-382/383.6  label is % followed by 7 digits"
                VCOMP = "%0000000"
                state = "%0000000"  # G %0000000

            case "%0000000":
                VCORR = "%0000000"
                examiner()
                ITEM = "I-382/383.7  label is % followed by another 7 digits"
                VCOMP = "%2345678"
                state = "%2345678"  # G %2345678

            case "%2345678":
                VCORR = "%2345678"
                examiner()
                ITEM = "I-382/383.8  label is % followed by combination of a alpha and a digit"
                VCOMP = "%A1"
                state = "%A1"  # G %A1

            case "%A1":
                VCORR = "%A1"
                examiner()
                ITEM = "I-382/383.9  label is % followed by combination of alphas and digits"
                VCOMP = "%A1B2C3D"
                state = "%A1B2C3D"  # G %A1B2C3D

            case "%A1B2C3D":
                VCORR = "%A1B2C3D"
                examiner()
                write("!", "I-380  label is alpha")
                ITEM = "I-380.1  label is a alpha"
                VCOMP = "A"
                state = "A"  # G A

            case "A":
                VCORR = "A"
                examiner()
                ITEM = "I-380.2  label is different alpha"
                VCOMP = "Q"
                state = "Q"  # G Q

            case "Q":
                VCORR = "Q"
                examiner()
                ITEM = "I-380.3  label is different alpha"
                VCOMP = "Z"
                state = "Z"  # G Z

            case "Z":
                VCORR = "Z"
                examiner()
                ITEM = "I-380.4  label is 2 alphas"
                VCOMP = "DO"
                state = "DO"  # G DO

            case "DO":
                VCORR = "DO"
                examiner()
                ITEM = "I-380.5  label is another 2 alphas"
                VCOMP = "IF"
                state = "IF"  # G IF

            case "IF":
                VCORR = "IF"
                examiner()
                ITEM = "I-380.6  label is 4 alphas"
                VCOMP = "QUIT"
                state = "QUIT"  # G QUIT

            case "QUIT":
                VCORR = "QUIT"
                examiner()
                ITEM = "I-380.7  label is 3 alphas"
                VCOMP = "SET"
                state = "SET"  # G SET

            case "SET":
                VCORR = "SET"
                examiner()
                ITEM = "I-380.8  label is 8 alphas"
                VCOMP = "ABCDEFGH"
                state = "ABCDEFGH"  # G ABCDEFGH

            case "ABCDEFGH":
                VCORR = "ABCDEFGH"
                examiner()
                write("!", "I-381  label is intlit")
                ITEM = "I-381.1  0"
                VCOMP = "0"
                state = "0"  # G 0

            case "0":
                VCORR = "0"
                examiner()
                ITEM = "I-381.2  1"
                VCOMP = "1"
                state = "1"  # G 1

            case "1":
                VCORR = "1"
                examiner()
                ITEM = "I-381.3  01"
                VCOMP = "01"
                state = "01"  # G 01

            case "01":
                VCORR = "01"
                examiner()
                ITEM = "I-381.4  10"
                VCOMP = "10"
                state = "10"  # G 10

            case "10":
                VCORR = "10"
                examiner()
                ITEM = "I-381.5  12"
                VCOMP = "12"
                state = "12"  # G 12

            case "12":
                VCORR = "12"
                examiner()
                ITEM = "I-381.6  100"
                VCOMP = "100"
                state = "100"  # G 100

            case "100":
                VCORR = "100"
                examiner()
                ITEM = "I-381.7  012"
                VCOMP = "012"
                state = "012"  # G 012

            case "012":
                VCORR = "012"
                examiner()
                ITEM = "I-381.8  0012"
                VCOMP = "0012"
                state = "0012"  # G 0012

            case "0012":
                VCORR = "0012"
                examiner()
                ITEM = "I-381.9  92345678"
                VCOMP = "92345678"
                state = "92345678"  # G 92345678

            case "92345678":
                VCORR = "92345678"
                examiner()
                ITEM = "I-381.10  00000000"
                VCOMP = "00000000"
                state = "00000000"  # G 00000000

            case "00000000":
                VCORR = "00000000"
                examiner()
                write("!", "I-384  label is combination of alpha and digit")
                ITEM = "I-384.1  label is combination of a alpha and a digit"
                VCOMP = "A1"
                state = "A1"  # G A1

            case "A1":
                VCORR = "A1"
                examiner()
                ITEM = "I-384.2  label is combination of a alpha and digits"
                VCOMP = "Z012"
                state = "Z012"  # G Z012

            case "Z012":
                VCORR = "Z012"
                examiner()
                ITEM = "I-384.3  label is combination of alphas and digits"
                VCOMP = "ZXY987A0"
                state = "ZXY987A0"  # G ZXY987A0

            case "ZXY987A0":
                VCORR = "ZXY987A0"
                examiner()
                state = "END"  # Fall through to END

            case "END":
                write("!", "!", "END OF V1GO1", "!")
                # These would be used by VREPORT (external call we skip)
                ROUTINE = "V1GO1"  # noqa: F841
                TESTS = 30  # noqa: F841
                AUTO = 30  # noqa: F841
                VISUAL = 0  # noqa: F841
                # D ^VREPORT - skip external call
                state = None  # Q - end of routine

            case _:
                raise RuntimeError(f"Unknown state: {state}")

        iterations += 1
        if iterations > 100000:
            raise RuntimeError("State machine exceeded 100000 iterations")

    return _output.getvalue(), PASS_COUNT, FAIL


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    output, pass_count, fail_count = V1GO1()
    print(output)
    print("\n--- Spike Results ---")
    print(f"PASS: {pass_count}, FAIL: {fail_count}")
