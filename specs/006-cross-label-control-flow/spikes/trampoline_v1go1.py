#!/usr/bin/env python3
"""Trampoline pattern prototype for V1GO1.m.

This spike implements the V1GO1.m MUMPS routine using the trampoline pattern:
- Each label becomes a function returning (next_label, state) or (None, state) to exit
- A dispatcher loop (trampoline) calls functions until None is returned
- Shared state is passed through a state object

Run: uv run python specs/006-cross-label-control-flow/spikes/trampoline_v1go1.py
"""

from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Any
import io


@dataclass
class RoutineState:
    """Shared state for V1GO1 routine."""

    PASS_COUNT: int = 0
    FAIL: int = 0
    ITEM: str = ""
    VCOMP: str = ""
    VCORR: str = ""
    ROUTINE: str = ""
    TESTS: int = 0
    AUTO: int = 0
    VISUAL: int = 0
    # Output buffer for capturing WRITE output
    _output: io.StringIO = field(default_factory=io.StringIO)

    def write(self, *args: Any) -> None:
        """Simulate MUMPS WRITE command."""
        for arg in args:
            if arg == "!":
                self._output.write("\n")
            elif arg == "#":
                self._output.write("\f")  # Form feed
            else:
                self._output.write(str(arg))

    def get_output(self) -> str:
        return self._output.getvalue()


# Type alias for label functions
LabelFunc = Callable[[RoutineState], tuple[Optional[str], RoutineState]]

# Label registry - maps label names to functions
_labels: Dict[str, LabelFunc] = {}


def label(name: str):
    """Decorator to register a label function."""

    def decorator(func: LabelFunc) -> LabelFunc:
        _labels[name] = func
        return func

    return decorator


# =============================================================================
# V1GO1.m Labels as Functions (Trampoline Pattern)
# =============================================================================


@label("V1GO1")
def V1GO1(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    """Entry point."""
    s.PASS_COUNT = 0
    s.FAIL = 0
    s.ITEM = ""
    s.write("!", "!", "V1GO1: TEST OF GOTO COMMAND (LOCAL BRANCHING) -1-", "!")
    s.write("!", "GOTO label", "!")
    s.write("!", "I-382/383  label is % followed by alpha and digit")
    s.ITEM = "I-382/383.1  label is %"
    s.VCOMP = "%"
    return ("%", s)  # GOTO %


@label("%")
def pct(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "%"
    s = _examiner(s)
    s.ITEM = "I-382/383.2  label is % followed by a alpha"
    s.VCOMP = "%A"
    return ("%A", s)  # GOTO %A


@label("%A")
def pctA(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "%A"
    s = _examiner(s)
    s.ITEM = "I-382/383.3  label is % followed by alphas"
    s.VCOMP = "%ABCDEFG"
    return ("%ABCDEFG", s)  # G %ABCDEFG


@label("%ABCDEFG")
def pctABCDEFG(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "%ABCDEFG"
    s = _examiner(s)
    s.ITEM = "I-382/383.4  label is % followed by a digit"
    s.VCOMP = "%0"
    return ("%0", s)  # G %0


@label("%0")
def pct0(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "%0"
    s = _examiner(s)
    s.ITEM = "I-382/383.5  label is % followed by 2 digits"
    s.VCOMP = "%90"
    return ("%90", s)  # G %90


@label("%90")
def pct90(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "%90"
    s = _examiner(s)
    s.ITEM = "I-382/383.6  label is % followed by 7 digits"
    s.VCOMP = "%0000000"
    return ("%0000000", s)  # G %0000000


@label("%0000000")
def pct0000000(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "%0000000"
    s = _examiner(s)
    s.ITEM = "I-382/383.7  label is % followed by another 7 digits"
    s.VCOMP = "%2345678"
    return ("%2345678", s)  # G %2345678


@label("%2345678")
def pct2345678(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "%2345678"
    s = _examiner(s)
    s.ITEM = "I-382/383.8  label is % followed by combination of a alpha and a digit"
    s.VCOMP = "%A1"
    return ("%A1", s)  # G %A1


@label("%A1")
def pctA1(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "%A1"
    s = _examiner(s)
    s.ITEM = "I-382/383.9  label is % followed by combination of alphas and digits"
    s.VCOMP = "%A1B2C3D"
    return ("%A1B2C3D", s)  # G %A1B2C3D


@label("%A1B2C3D")
def pctA1B2C3D(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "%A1B2C3D"
    s = _examiner(s)
    s.write("!", "I-380  label is alpha")
    s.ITEM = "I-380.1  label is a alpha"
    s.VCOMP = "A"
    return ("A", s)  # G A


@label("A")
def A(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "A"
    s = _examiner(s)
    s.ITEM = "I-380.2  label is different alpha"
    s.VCOMP = "Q"
    return ("Q", s)  # G Q


@label("Q")
def Q(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "Q"
    s = _examiner(s)
    s.ITEM = "I-380.3  label is different alpha"
    s.VCOMP = "Z"
    return ("Z", s)  # G Z


@label("Z")
def Z(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "Z"
    s = _examiner(s)
    s.ITEM = "I-380.4  label is 2 alphas"
    s.VCOMP = "DO"
    return ("DO", s)  # G DO


@label("DO")
def DO(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "DO"
    s = _examiner(s)
    s.ITEM = "I-380.5  label is another 2 alphas"
    s.VCOMP = "IF"
    return ("IF", s)  # G IF


@label("IF")
def IF(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "IF"
    s = _examiner(s)
    s.ITEM = "I-380.6  label is 4 alphas"
    s.VCOMP = "QUIT"
    return ("QUIT", s)  # G QUIT


@label("QUIT")
def QUIT(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "QUIT"
    s = _examiner(s)
    s.ITEM = "I-380.7  label is 3 alphas"
    s.VCOMP = "SET"
    return ("SET", s)  # G SET


@label("SET")
def SET(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "SET"
    s = _examiner(s)
    s.ITEM = "I-380.8  label is 8 alphas"
    s.VCOMP = "ABCDEFGH"
    return ("ABCDEFGH", s)  # G ABCDEFGH


@label("ABCDEFGH")
def ABCDEFGH(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "ABCDEFGH"
    s = _examiner(s)
    s.write("!", "I-381  label is intlit")
    s.ITEM = "I-381.1  0"
    s.VCOMP = "0"
    return ("0", s)  # G 0


@label("0")
def n0(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "0"
    s = _examiner(s)
    s.ITEM = "I-381.2  1"
    s.VCOMP = "1"
    return ("1", s)  # G 1


@label("1")
def n1(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "1"
    s = _examiner(s)
    s.ITEM = "I-381.3  01"
    s.VCOMP = "01"
    return ("01", s)  # G 01


@label("01")
def n01(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "01"
    s = _examiner(s)
    s.ITEM = "I-381.4  10"
    s.VCOMP = "10"
    return ("10", s)  # G 10


@label("10")
def n10(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "10"
    s = _examiner(s)
    s.ITEM = "I-381.5  12"
    s.VCOMP = "12"
    return ("12", s)  # G 12


@label("12")
def n12(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "12"
    s = _examiner(s)
    s.ITEM = "I-381.6  100"
    s.VCOMP = "100"
    return ("100", s)  # G 100


@label("100")
def n100(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "100"
    s = _examiner(s)
    s.ITEM = "I-381.7  012"
    s.VCOMP = "012"
    return ("012", s)  # G 012


@label("012")
def n012(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "012"
    s = _examiner(s)
    s.ITEM = "I-381.8  0012"
    s.VCOMP = "0012"
    return ("0012", s)  # G 0012


@label("0012")
def n0012(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "0012"
    s = _examiner(s)
    s.ITEM = "I-381.9  92345678"
    s.VCOMP = "92345678"
    return ("92345678", s)  # G 92345678


@label("92345678")
def n92345678(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "92345678"
    s = _examiner(s)
    s.ITEM = "I-381.10  00000000"
    s.VCOMP = "00000000"
    return ("00000000", s)  # G 00000000


@label("00000000")
def n00000000(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "00000000"
    s = _examiner(s)
    s.write("!", "I-384  label is combination of alpha and digit")
    s.ITEM = "I-384.1  label is combination of a alpha and a digit"
    s.VCOMP = "A1"
    return ("A1", s)  # G A1


@label("A1")
def A1(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "A1"
    s = _examiner(s)
    s.ITEM = "I-384.2  label is combination of a alpha and digits"
    s.VCOMP = "Z012"
    return ("Z012", s)  # G Z012


@label("Z012")
def Z012(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "Z012"
    s = _examiner(s)
    s.ITEM = "I-384.3  label is combination of alphas and digits"
    s.VCOMP = "ZXY987A0"
    return ("ZXY987A0", s)  # G ZXY987A0


@label("ZXY987A0")
def ZXY987A0(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.VCORR = "ZXY987A0"
    s = _examiner(s)
    return ("END", s)  # Fall through to END


@label("END")
def END(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.write("!", "!", "END OF V1GO1", "!")
    s.ROUTINE = "V1GO1"
    s.TESTS = 30
    s.AUTO = 30
    s.VISUAL = 0
    # D ^VREPORT - skip external call
    return (None, s)  # Q - end of routine


# =============================================================================
# Helper Functions
# =============================================================================


def _examiner(s: RoutineState) -> RoutineState:
    """EXAMINER subroutine - compares VCORR to VCOMP."""
    if s.VCORR == s.VCOMP:
        s.PASS_COUNT += 1
        s.write("!", "   PASS  ", s.ITEM)
    else:
        s.FAIL += 1
        s.write("!", "** FAIL  ", s.ITEM)
        s.write("!", '           COMPUTED ="', s.VCOMP, '"')
        s.write("!", '           CORRECT  ="', s.VCORR, '"')
    return s


# =============================================================================
# Trampoline Dispatcher
# =============================================================================


def run_trampoline(entry_label: str = "V1GO1") -> RoutineState:
    """Execute routine via trampoline dispatch loop."""
    state = RoutineState()
    label = entry_label
    iterations = 0

    while label is not None:
        if label not in _labels:
            raise RuntimeError(f"Unknown label: {label}")
        func = _labels[label]
        label, state = func(state)
        iterations += 1

        # Safety check for infinite loops
        if iterations > 100000:
            raise RuntimeError("Trampoline exceeded 100000 iterations")

    return state


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    state = run_trampoline()
    print(state.get_output())
    print("\n--- Spike Results ---")
    print(f"PASS: {state.PASS_COUNT}, FAIL: {state.FAIL}")
    print(f"Total labels: {len(_labels)}")
