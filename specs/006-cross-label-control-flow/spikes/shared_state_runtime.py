#!/usr/bin/env python3
"""Shared State Pattern: Runtime Dict Approach.

This spike tests using a runtime dictionary for variable storage,
accessed via _rt.get() and _rt.set() methods.

Pattern:
    _rt = Runtime()
    _rt.set("X", 10)
    val = _rt.get("X")

Run: uv run python specs/006-cross-label-control-flow/spikes/shared_state_runtime.py
"""

from typing import Optional, Callable, Dict, Any
import io


class Runtime:
    """Runtime variable storage using dictionary.

    Advantages:
    - Dynamic variable creation (no pre-declaration needed)
    - Matches MUMPS semantics exactly (variables created on first SET)
    - Easy to implement NEW (push/pop scopes)
    - Easy to dump all variables for debugging
    - Natural fit for subscripted variables (nested dicts)

    Disadvantages:
    - No IDE autocomplete for variable names
    - No type checking on variables
    - String-based access is error-prone (typos not caught)
    - Slightly more verbose syntax
    - Rope cannot rename variable references (strings not symbols)
    """

    def __init__(self):
        self._vars: Dict[str, Any] = {}
        self._output = io.StringIO()

    def get(self, name: str, default: Any = "") -> Any:
        """Get variable value (empty string if undefined, per MUMPS)."""
        return self._vars.get(name, default)

    def set(self, name: str, value: Any) -> None:
        """Set variable value."""
        self._vars[name] = value

    def defined(self, name: str) -> bool:
        """Check if variable is defined ($DATA equivalent)."""
        return name in self._vars

    def kill(self, name: str) -> None:
        """Delete variable (KILL command)."""
        self._vars.pop(name, None)

    def write(self, *args: Any) -> None:
        """Simulate MUMPS WRITE command."""
        for arg in args:
            if arg == "!":
                self._output.write("\n")
            else:
                self._output.write(str(arg))

    def get_output(self) -> str:
        return self._output.getvalue()

    def dump(self) -> Dict[str, Any]:
        """Return all variables (for debugging)."""
        return dict(self._vars)


# Type alias for label functions
LabelFunc = Callable[[Runtime], tuple[Optional[str], Runtime]]

# Label registry
_labels: Dict[str, LabelFunc] = {}


def label(name: str):
    """Decorator to register a label function."""

    def decorator(func: LabelFunc) -> LabelFunc:
        _labels[name] = func
        return func

    return decorator


# =============================================================================
# Test Routine: Simple variable passing across labels
# =============================================================================


@label("ENTRY")
def ENTRY(rt: Runtime) -> tuple[Optional[str], Runtime]:
    """Set X, jump to ADDONE."""
    rt.set("X", 10)
    rt.write("ENTRY: X=", rt.get("X"), "!")
    return ("ADDONE", rt)


@label("ADDONE")
def ADDONE(rt: Runtime) -> tuple[Optional[str], Runtime]:
    """Add 1 to X, jump to DOUBLE."""
    rt.set("X", rt.get("X") + 1)
    rt.write("ADDONE: X=", rt.get("X"), "!")
    return ("DOUBLE", rt)


@label("DOUBLE")
def DOUBLE(rt: Runtime) -> tuple[Optional[str], Runtime]:
    """Double X, store in Y, jump to SHOW."""
    rt.set("Y", rt.get("X") * 2)
    rt.write("DOUBLE: Y=", rt.get("Y"), "!")
    return ("SHOW", rt)


@label("SHOW")
def SHOW(rt: Runtime) -> tuple[Optional[str], Runtime]:
    """Show final results."""
    rt.write("SHOW: X=", rt.get("X"), " Y=", rt.get("Y"), "!")
    rt.set("RESULT", rt.get("Y"))
    return (None, rt)


# =============================================================================
# Trampoline
# =============================================================================


def run_trampoline(entry_label: str = "ENTRY") -> Runtime:
    """Execute routine via trampoline dispatch loop."""
    rt = Runtime()
    current_label = entry_label

    while current_label is not None:
        if current_label not in _labels:
            raise RuntimeError(f"Unknown label: {current_label}")
        func = _labels[current_label]
        current_label, rt = func(rt)

    return rt


# =============================================================================
# Advanced: Subscripted Variable Support
# =============================================================================


class RuntimeWithArrays(Runtime):
    """Extended runtime with subscripted variable support.

    MUMPS allows: S A=1, S A(1)=2, S A(1,2)=3
    Each node can have both a value AND children.
    """

    def get_subscripted(self, name: str, *subscripts: Any) -> Any:
        """Get subscripted variable: A(1,2) -> get_subscripted("A", 1, 2)"""
        if not subscripts:
            return self.get(name)

        # Navigate to node
        node = self._vars.get(name, {})
        if not isinstance(node, dict):
            node = {"_value": node}

        for sub in subscripts[:-1]:
            node = node.get(sub, {})
            if not isinstance(node, dict):
                return ""  # Path doesn't exist

        final = node.get(subscripts[-1], "")
        if isinstance(final, dict):
            return final.get("_value", "")
        return final

    def set_subscripted(self, name: str, *args: Any) -> None:
        """Set subscripted variable: A(1,2)=3 -> set_subscripted("A", 1, 2, 3)"""
        if len(args) < 1:
            raise ValueError("Must provide at least a value")

        *subscripts, value = args

        if not subscripts:
            self.set(name, value)
            return

        # Ensure root exists as dict
        if name not in self._vars:
            self._vars[name] = {}
        elif not isinstance(self._vars[name], dict):
            self._vars[name] = {"_value": self._vars[name]}

        # Navigate/create path
        node = self._vars[name]
        for sub in subscripts[:-1]:
            if sub not in node:
                node[sub] = {}
            elif not isinstance(node[sub], dict):
                node[sub] = {"_value": node[sub]}
            node = node[sub]

        # Set final value
        last_sub = subscripts[-1]
        if last_sub in node and isinstance(node[last_sub], dict):
            node[last_sub]["_value"] = value
        else:
            node[last_sub] = value


# =============================================================================
# Rope Refactorability Tests
# =============================================================================


def test_rope_compatibility():
    """Test that Rope can work with this pattern."""
    # 1. Can rename variable "X" to "VALUE"?
    #    - NO: "X" is a string, not a symbol. Must search/replace.

    # 2. Can extract a helper function?
    #    - YES: Helper takes Runtime as parameter, same pattern

    # 3. Can find all usages of "X"?
    #    - NO: IDE cannot track string references

    print("Rope compatibility: POOR")
    print("- Rename Symbol: NO (strings, not symbols)")
    print("- Extract Method: YES (pass Runtime as parameter)")
    print("- Find References: NO (string-based, not trackable)")


# =============================================================================
# Demonstration of typo risk
# =============================================================================


def demonstrate_typo_bug():
    """Show what happens with typos in variable names."""
    rt = Runtime()
    rt.set("COUNTER", 10)

    # Typo: "CONTER" instead of "COUNTER"
    value = rt.get("CONTER")  # Returns "" silently!

    print("\n--- Typo Risk Demo ---")
    print("Set COUNTER = 10")
    print(f"Get CONTER (typo) = '{value}'")  # Empty string!
    print(f"Get COUNTER = {rt.get('COUNTER')}")  # 10
    print("No error raised for typo - returns empty string per MUMPS semantics")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    rt = run_trampoline()
    print(rt.get_output())
    print("--- Results ---")
    print(f"Final RESULT: {rt.get('RESULT')}")
    print("Expected: 22 (10+1=11, 11*2=22)")
    print(f"Correct: {rt.get('RESULT') == 22}")
    print(f"All variables: {rt.dump()}")
    print()
    test_rope_compatibility()
    demonstrate_typo_bug()
