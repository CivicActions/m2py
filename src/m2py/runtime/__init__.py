"""Minimal runtime for executing generated MUMPS code.

Provides output capture and execution support for generated Python code.
Includes MArray class for MUMPS array semantics.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict


class MArray:
    """MUMPS array with hierarchical subscript support.

    Spec 006 (T051-T052): Implements MUMPS sparse array semantics where
    each node can have BOTH a value AND children. This is different from
    Python dicts where a key maps to a single value.

    Example MUMPS:
        S A=1           ; Root node has value 1
        S A(1)=2        ; A(1) has value 2
        S A(1,2)=3      ; A(1,2) has value 3
        ; All three coexist - A's value doesn't prevent A(1) from existing

    Usage:
        arr = MArray()
        arr.value = 1           # S A=1
        arr[1].value = 2        # S A(1)=2
        arr[1, 2].value = 3     # S A(1,2)=3

        # Alternative syntax for setting
        arr[1] = 2              # S A(1)=2
        arr[1, 2] = 3           # S A(1,2)=3

        # Access
        print(arr.value)        # 1
        print(arr.get(1))       # 2
        print(arr.get(1, 2))    # 3

        # $DATA semantics
        arr.defined()           # Returns 0, 1, 10, or 11
    """

    def __init__(self, value: Any = None):
        """Initialize array node.

        Args:
            value: Initial value at this node (None = undefined)
        """
        self._value: Any = value
        self._children: Dict[Any, "MArray"] = {}

    @property
    def value(self) -> Any:
        """Get value at this node (empty string if undefined).

        MUMPS semantics: undefined variables return empty string.
        """
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

        Args:
            key: Subscript (single value or tuple of values)

        Returns:
            MArray node at that subscript (created if doesn't exist)
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

        Args:
            key: Subscript (single value or tuple of values)
            value: Value to set at that subscript
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

        Args:
            *subscripts: Path to the value (empty for root)

        Returns:
            Value at subscripts, or empty string if undefined

        Examples:
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

        Args:
            *args: Subscript path (empty for root value)
            value: Value to set (must be keyword argument)

        Raises:
            ValueError: If value= not provided

        Examples:
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

        MUMPS $DATA returns:
            0 - Not defined (no value, no children)
            1 - Has value only
            10 - Has children only (no value at this node)
            11 - Has both value and children

        Args:
            *subscripts: Path to check (empty for root)

        Returns:
            Integer 0, 1, 10, or 11 per MUMPS $DATA semantics
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
        """Delete node and all descendants (KILL command).

        Args:
            *subscripts: Path to kill (empty kills entire array)
        """
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
        """Get next subscript ($ORDER equivalent).

        Returns the next subscript after 'start' in collation order.
        MUMPS collation: numbers before strings, sorted within type.

        Args:
            *subscripts: Path to the array level to search
            start: Starting point (empty string = first subscript)

        Returns:
            Next subscript, or empty string if no more
        """
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
        """String representation for debugging."""
        parts = []
        if self._value is not None:
            parts.append(f"value={self._value!r}")
        if self._children:
            parts.append(f"children={list(self._children.keys())}")
        return f"MArray({', '.join(parts)})"


@dataclass
class ExecutionResult:
    """Result of executing generated MUMPS code.

    Attributes:
        output: Captured WRITE output (empty string if capture_output=False)
        success: True if execution completed without exception
        error: Exception message if success=False, else None
        test_value: Final value of $TEST after execution
        locals: Optional dict of local variables at end of execution (for debugging)
    """

    output: str = ""
    success: bool = True
    error: str | None = None
    test_value: bool = False
    locals: dict[str, Any] | None = field(default=None)


class MUMPSRuntime:
    """Minimal runtime for executing generated MUMPS code.

    Provides output capture for WRITE statements and execution support
    for generated Python code. Thread-unsafe - use one instance per thread.
    """

    def __init__(self) -> None:
        """Initialize runtime with empty state."""
        self._output: list[str] = []

    def write(self, value: str) -> None:
        """Capture WRITE output.

        Args:
            value: String value to write

        Note:
            Does not add newlines automatically (MUMPS WRITE doesn't either).
            Non-string values should be converted to string by caller.
        """
        self._output.append(value)

    def get_output(self) -> str:
        """Return accumulated WRITE output.

        Returns:
            Concatenated string of all write() calls
        """
        return "".join(self._output)

    def clear(self) -> None:
        """Clear accumulated output."""
        self._output.clear()

    def execute(
        self,
        python_code: str,
        *,
        capture_output: bool = True,
        entry_point: str | None = None,
    ) -> ExecutionResult:
        """Execute generated Python code.

        Creates an isolated namespace for execution, injects the runtime
        and helpers, executes module-level code (defines functions), then
        calls the entry point function.

        Args:
            python_code: Generated Python source code
            capture_output: If True, capture WRITE output
            entry_point: Label to execute (default: first label)

        Returns:
            ExecutionResult with output, status, and error info
        """
        # Clear output buffer if capturing
        if capture_output:
            self.clear()

        # Create isolated namespace
        namespace: dict[str, Any] = {"_rt": self}

        # Inject helpers
        from m2py.codegen.helpers import m_compare, m_num, m_truth

        namespace["m_num"] = m_num
        namespace["m_truth"] = m_truth
        namespace["m_compare"] = m_compare

        try:
            # Execute the module code (defines functions)
            exec(python_code, namespace)

            # Re-inject runtime after module execution
            # (the generated code creates its own _rt, but we want to use ours)
            namespace["_rt"] = self

            # Find entry point
            if entry_point is None:
                # Find first function defined (look for def statements)
                entry_point = self._find_first_function(python_code)

            # Call entry point if found
            if entry_point and entry_point in namespace:
                func = namespace[entry_point]
                if callable(func):
                    func()

            # Get final $TEST value
            test_value = namespace.get("_test", False)

            return ExecutionResult(
                output=self.get_output() if capture_output else "",
                success=True,
                error=None,
                test_value=bool(test_value),
            )

        except Exception as e:
            return ExecutionResult(
                output=self.get_output() if capture_output else "",
                success=False,
                error=str(e),
                test_value=False,
            )

    def _find_first_function(self, python_code: str) -> str | None:
        """Find the name of the first user function defined in the code.

        Skips helper functions (those starting with _) to find the first
        MUMPS label function.

        Args:
            python_code: Python source code

        Returns:
            Name of first user function, or None if no functions found
        """
        # Look for all "def FUNCNAME(" patterns
        for match in re.finditer(r"^def\s+(\w+)\s*\(", python_code, re.MULTILINE):
            func_name = match.group(1)
            # Skip helper functions (prefixed with _)
            if not func_name.startswith("_"):
                return func_name
        return None


__all__ = ["MUMPSRuntime", "ExecutionResult", "MArray"]
