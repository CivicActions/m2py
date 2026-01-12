#!/usr/bin/env python3
"""MArray Spike: Subscripted Local Variables for Cross-Label Visibility.

MUMPS arrays are sparse, hierarchical structures where each node can have:
1. A value at that node
2. Child nodes (subscripts)

Example: S A=1, S A(1)=2, S A(1,2)=3
- A has value 1
- A(1) has value 2
- A(1,2) has value 3
- All three coexist - A's value doesn't prevent A(1) from existing

This spike validates MArray for cross-label array visibility:
- Set array in one label, read in another after GOTO
- Nested subscripts work correctly
- Integrates with RoutineState class pattern

Run: uv run python specs/006-cross-label-control-flow/spikes/marray_spike.py
"""

from dataclasses import dataclass, field
from typing import Any, Optional, Callable, Dict, Tuple
import io


class MArray:
    """MUMPS array with hierarchical subscript support.

    Each node can have both a value AND children.
    Undefined nodes return empty string (MUMPS semantics).

    Usage:
        arr = MArray()
        arr.value = 1           # Set value at root: S A=1
        arr[1].value = 2        # Set value at subscript: S A(1)=2
        arr[1, 2].value = 3     # Set nested subscript: S A(1,2)=3

        # Alternative syntax
        arr.set(1, 2, value=3)  # S A(1,2)=3
        val = arr.get(1, 2)     # Returns 3

        # Access
        print(arr.value)        # 1
        print(arr[1].value)     # 2
        print(arr[1, 2].value)  # 3
    """

    def __init__(self, value: Any = None):
        self._value: Any = value
        self._children: Dict[Any, "MArray"] = {}

    @property
    def value(self) -> Any:
        """Get value at this node (empty string if undefined)."""
        return self._value if self._value is not None else ""

    @value.setter
    def value(self, val: Any) -> None:
        """Set value at this node."""
        self._value = val

    def __getitem__(self, key: Any) -> "MArray":
        """Get child node, creating if needed.

        Supports both single and tuple keys:
            arr[1]      -> arr._children[1]
            arr[1, 2]   -> arr._children[1]._children[2]
        """
        if isinstance(key, tuple):
            node = self
            for k in key:
                node = node[k]
            return node

        if key not in self._children:
            self._children[key] = MArray()
        return self._children[key]

    def __setitem__(self, key: Any, value: Any) -> None:
        """Set value at subscript.

        Supports both single and tuple keys:
            arr[1] = 10         -> arr._children[1]._value = 10
            arr[1, 2] = 20      -> arr._children[1]._children[2]._value = 20
        """
        if isinstance(key, tuple):
            node = self
            for k in key[:-1]:
                node = node[k]
            node[key[-1]] = value
        else:
            if key not in self._children:
                self._children[key] = MArray()
            self._children[key]._value = value

    def get(self, *subscripts: Any) -> Any:
        """Get value at subscripts (empty string if undefined).

        arr.get()       -> arr.value (root value)
        arr.get(1)      -> arr[1].value
        arr.get(1, 2)   -> arr[1, 2].value
        """
        if not subscripts:
            return self.value

        node = self
        for sub in subscripts:
            if sub not in node._children:
                return ""  # Undefined subscript
            node = node._children[sub]
        return node.value

    def set(self, *args: Any, value: Any = None) -> None:
        """Set value at subscripts.

        arr.set(value=10)           -> arr.value = 10
        arr.set(1, value=10)        -> arr[1].value = 10
        arr.set(1, 2, value=10)     -> arr[1, 2].value = 10
        """
        if value is None:
            raise ValueError("Must provide value= keyword argument")

        if not args:
            self._value = value
        else:
            self[args].value = value

    def defined(self, *subscripts: Any) -> int:
        """Check if node is defined ($DATA equivalent).

        Returns:
            0 - Not defined (no value, no children)
            1 - Has value only
            10 - Has children only
            11 - Has both value and children
        """
        if not subscripts:
            node = self
        else:
            node = self
            for sub in subscripts:
                if sub not in node._children:
                    return 0  # Path doesn't exist
                node = node._children[sub]

        has_value = node._value is not None
        has_children = bool(node._children)

        if has_value and has_children:
            return 11
        elif has_children:
            return 10
        elif has_value:
            return 1
        else:
            return 0

    def kill(self, *subscripts: Any) -> None:
        """Delete node and all descendants (KILL command)."""
        if not subscripts:
            self._value = None
            self._children.clear()
        else:
            parent = self
            for sub in subscripts[:-1]:
                if sub not in parent._children:
                    return  # Path doesn't exist
                parent = parent._children[sub]

            last = subscripts[-1]
            if last in parent._children:
                del parent._children[last]

    def order(self, *subscripts: Any, start: Any = "") -> Any:
        """Get next subscript ($ORDER equivalent)."""
        if not subscripts:
            children = self._children
        else:
            node = self
            for sub in subscripts:
                if sub not in node._children:
                    return ""
                node = node._children[sub]
            children = node._children

        # Get sorted keys (MUMPS collation: numbers before strings)
        keys = sorted(children.keys(), key=lambda x: (isinstance(x, str), x))

        if start == "":
            return keys[0] if keys else ""

        try:
            idx = keys.index(start)
            return keys[idx + 1] if idx + 1 < len(keys) else ""
        except ValueError:
            # Start not found, return first key greater than start
            for k in keys:
                if (isinstance(start, str), start) < (isinstance(k, str), k):
                    return k
            return ""

    def __repr__(self) -> str:
        parts = []
        if self._value is not None:
            parts.append(f"value={self._value!r}")
        if self._children:
            parts.append(f"children={list(self._children.keys())}")
        return f"MArray({', '.join(parts)})"


# =============================================================================
# Integration with RoutineState Pattern
# =============================================================================


@dataclass
class RoutineState:
    """Shared state with MArray support for subscripted variables."""

    # Simple variables
    RESULT: Any = None

    # Array variables (MArray instances)
    A: MArray = field(default_factory=MArray)
    B: MArray = field(default_factory=MArray)

    # Output buffer
    _output: io.StringIO = field(default_factory=io.StringIO)

    def write(self, *args: Any) -> None:
        for arg in args:
            if arg == "!":
                self._output.write("\n")
            else:
                self._output.write(str(arg))

    def get_output(self) -> str:
        return self._output.getvalue()


# Type alias for label functions
LabelFunc = Callable[[RoutineState], Tuple[Optional[str], RoutineState]]

# Label registry
_labels: Dict[str, LabelFunc] = {}


def label(name: str):
    def decorator(func: LabelFunc) -> LabelFunc:
        _labels[name] = func
        return func

    return decorator


# =============================================================================
# Test Case 1: Cross-Label Array Access (T026)
# MUMPS: S A(1)=10,A(2)=20 G SUM / SUM W A(1)+A(2)
# Expected output: 30
# =============================================================================


@label("ENTRY1")
def ENTRY1(s: RoutineState) -> Tuple[Optional[str], RoutineState]:
    """Set array values, then GOTO SUM."""
    s.A[1] = 10  # S A(1)=10
    s.A[2] = 20  # S A(2)=20
    s.write("ENTRY1: Set A(1)=10, A(2)=20", "!")
    return ("SUM", s)  # G SUM


@label("SUM")
def SUM(s: RoutineState) -> Tuple[Optional[str], RoutineState]:
    """Read array values set in previous label."""
    result = s.A.get(1) + s.A.get(2)  # A(1)+A(2)
    s.write("SUM: A(1)+A(2)=", result, "!")
    s.RESULT = result
    return (None, s)


# =============================================================================
# Test Case 2: Nested Subscripts with Value at Each Level (T027)
# MUMPS: S A=1,A(1)=2,A(1,2)=3
# Each node has both value AND children
# =============================================================================


@label("ENTRY2")
def ENTRY2(s: RoutineState) -> Tuple[Optional[str], RoutineState]:
    """Set nested subscripts with values at each level."""
    s.B.value = 1  # S B=1 (root has value)
    s.B[1] = 2  # S B(1)=2
    s.B[1, 2] = 3  # S B(1,2)=3
    s.write("ENTRY2: Set B=1, B(1)=2, B(1,2)=3", "!")
    return ("SHOW", s)


@label("SHOW")
def SHOW(s: RoutineState) -> Tuple[Optional[str], RoutineState]:
    """Show all values at different levels."""
    s.write("SHOW: B=", s.B.value, "!")  # Should be 1
    s.write("SHOW: B(1)=", s.B.get(1), "!")  # Should be 2
    s.write("SHOW: B(1,2)=", s.B.get(1, 2), "!")  # Should be 3

    # Verify $DATA equivalent
    s.write("SHOW: $D(B)=", s.B.defined(), "!")  # 11 (has value AND children)
    s.write("SHOW: $D(B,1)=", s.B.defined(1), "!")  # 11 (has value AND children)
    s.write("SHOW: $D(B,1,2)=", s.B.defined(1, 2), "!")  # 1 (has value only)
    s.write("SHOW: $D(B,9)=", s.B.defined(9), "!")  # 0 (not defined)

    return (None, s)


# =============================================================================
# Trampoline
# =============================================================================


def run_trampoline(entry_label: str) -> RoutineState:
    """Execute routine via trampoline dispatch loop."""
    state = RoutineState()
    current_label = entry_label

    while current_label is not None:
        if current_label not in _labels:
            raise RuntimeError(f"Unknown label: {current_label}")
        func = _labels[current_label]
        current_label, state = func(state)

    return state


# =============================================================================
# Tests
# =============================================================================


def test_cross_label_array():
    """T026: Test cross-label array access."""
    print("=" * 60)
    print("TEST T026: Cross-Label Array Access")
    print("=" * 60)
    print("MUMPS: S A(1)=10,A(2)=20 G SUM / SUM W A(1)+A(2)")
    print("Expected: 30")
    print("-" * 60)

    state = run_trampoline("ENTRY1")
    print(state.get_output())

    passed = state.RESULT == 30
    print(f"Result: {state.RESULT}")
    print(f"Status: {'PASS' if passed else 'FAIL'}")
    return passed


def test_nested_subscripts():
    """T027: Test nested subscripts with value at each level."""
    print("=" * 60)
    print("TEST T027: Nested Subscripts")
    print("=" * 60)
    print("MUMPS: S A=1,A(1)=2,A(1,2)=3")
    print("Each node has value AND children")
    print("-" * 60)

    state = run_trampoline("ENTRY2")
    print(state.get_output())

    # Verify all values
    passed = (
        state.B.value == 1
        and state.B.get(1) == 2
        and state.B.get(1, 2) == 3
        and state.B.defined() == 11  # Has value AND children
        and state.B.defined(1) == 11  # Has value AND children
        and state.B.defined(1, 2) == 1  # Has value only
    )

    print(f"Status: {'PASS' if passed else 'FAIL'}")
    return passed


def test_marray_unit():
    """Unit tests for MArray class."""
    print("=" * 60)
    print("TEST: MArray Unit Tests")
    print("=" * 60)

    arr = MArray()

    # Test basic set/get
    arr.value = "root"
    assert arr.value == "root", "Root value failed"

    arr[1] = "one"
    assert arr.get(1) == "one", "Subscript 1 failed"

    arr[1, 2] = "onetwo"
    assert arr.get(1, 2) == "onetwo", "Subscript 1,2 failed"

    # Test undefined returns empty string
    assert arr.get(99) == "", "Undefined should return empty string"
    assert arr.get(1, 99) == "", "Undefined nested should return empty string"

    # Test $DATA equivalent
    assert arr.defined() == 11, "$D(arr) should be 11"
    assert arr.defined(1) == 11, "$D(arr,1) should be 11"
    assert arr.defined(1, 2) == 1, "$D(arr,1,2) should be 1"
    assert arr.defined(99) == 0, "$D(arr,99) should be 0"

    # Test KILL
    arr.kill(1, 2)
    assert arr.defined(1, 2) == 0, "After kill, $D should be 0"
    assert arr.defined(1) == 1, "Parent should still have value"

    # Test set() method
    arr.set(3, 4, value="threefour")
    assert arr.get(3, 4) == "threefour", "set() method failed"

    print("All unit tests passed!")
    return True


def test_integration_with_state():
    """T028: Test MArray integrates with RoutineState pattern."""
    print("=" * 60)
    print("TEST T028: Integration with RoutineState")
    print("=" * 60)

    # MArray as field in dataclass works
    state = RoutineState()

    # Multiple arrays are independent
    state.A[1] = 10
    state.B[1] = 20
    assert state.A.get(1) == 10, "Array A failed"
    assert state.B.get(1) == 20, "Array B failed"

    # Arrays survive through trampoline
    state2 = run_trampoline("ENTRY1")
    assert state2.A.get(1) == 10, "Array not preserved through trampoline"

    print("Integration tests passed!")
    return True


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    results = []

    results.append(("MArray Unit Tests", test_marray_unit()))
    print()

    results.append(("T026: Cross-Label Array", test_cross_label_array()))
    print()

    results.append(("T027: Nested Subscripts", test_nested_subscripts()))
    print()

    results.append(("T028: Integration", test_integration_with_state()))
    print()

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, passed in results:
        print(f"  {name}: {'PASS' if passed else 'FAIL'}")

    all_passed = all(p for _, p in results)
    print()
    print(f"Overall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
