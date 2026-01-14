"""Minimal runtime for executing generated MUMPS code.

Provides output capture and execution support for generated Python code.
Includes MArray class for MUMPS array semantics.

Spec 009: Extended with global variable storage and helper functions:
- GlobalStorageBackend: Protocol for global variable storage
- m_set_piece, m_set_extract: LHS function helpers
- m_data, m_data_global: $DATA function helpers
"""

from __future__ import annotations

import re
import types
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

# Spec 009: Import global storage backend protocol
from m2py.runtime.globals import GlobalStorageBackend, InMemoryGlobalStorage

# Spec 009: Import helper functions
from m2py.runtime.helpers import (
    m_data,
    m_data_global,
    m_set_extract,
    m_set_piece,
)

# Spec 010: Import runtime exception class
from m2py.runtime.exceptions import MRuntimeError


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

    def data(self, *subscripts: Any) -> int:
        """Return $DATA code for this node or subscripted path.

        Spec 009 (T003): Alias for defined() using MUMPS $DATA naming.

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
        return self.defined(*subscripts)

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


# =============================================================================
# Spec 008: External Call Exception Classes
# =============================================================================


class GotoExternal(Exception):
    """Raised to transfer control to external routine (no return).

    Used by external GOTO (G ^ROUTINE, G LABEL^ROUTINE) to unwind the stack
    and transfer control to a different routine. The trampoline dispatcher
    catches this exception and transfers to the target module.

    Attributes:
        module: Target module (already imported via standard Python import)
        label: Target label name (None = entry label, same name as routine)
        offset: Optional line offset for G LABEL+N^ROUTINE pattern
        _rt: MUMPSRuntime instance to pass to target routine (Phase 13)
    """

    def __init__(
        self,
        module: types.ModuleType,
        label: Optional[str] = None,
        offset: Optional[int] = None,
        _rt: Optional["MUMPSRuntime"] = None,
    ) -> None:
        self.module = module
        self.label = label
        self.offset = offset
        self._rt = _rt
        routine_name = getattr(module, "_routine_name", module.__name__)
        label_str = label or ""
        super().__init__(f"GOTO {label_str}^{routine_name}")


class LabelNotFoundError(Exception):
    """Raised when label doesn't exist in loaded routine.

    Attributes:
        label: The label name that was not found
        routine: The routine name that was searched
        available_labels: List of labels that do exist in the routine
    """

    def __init__(
        self, label: str, routine: str, available_labels: Optional[List[str]] = None
    ) -> None:
        self.label = label
        self.routine = routine
        self.available_labels = available_labels or []
        super().__init__(f"Label '{label}' not found in routine '{routine}'")


def run_with_goto_support(
    entry_func: Callable[..., Any],
    _rt: "MUMPSRuntime",
    _scope: Optional[Dict[str, Any]] = None,
) -> Any:
    """Execute a routine entry point with external GOTO support.

    Spec 008 Phase 6 (T039): This function wraps routine execution to catch
    GotoExternal exceptions and transfer control to external routines.

    When a GOTO to an external routine is executed (G ^ROUTINE, G LABEL^ROUTINE),
    it raises GotoExternal. This function catches it and transfers control to
    the target routine, which may itself GOTO to another routine, creating a
    chain of transfers that only ends when a routine QUITs normally.

    Phase 13 (T082): The runtime instance is passed explicitly to all routines
    to ensure shared state across external calls.

    Args:
        entry_func: The entry function to execute (routine's first label)
        _rt: MUMPSRuntime instance to pass to all routines
        _scope: Optional shared scope for cross-routine variable visibility

    Returns:
        The return value of the final routine that QUITs normally

    Raises:
        LabelNotFoundError: If GOTO targets a non-existent label
        ImportError: If GOTO targets a routine that cannot be imported
    """
    if _scope is None:
        _scope = {}

    current_func = entry_func
    current_rt = _rt
    while True:
        try:
            return current_func(current_rt, _scope=_scope)
        except GotoExternal as goto:
            # Transfer to external routine
            module = goto.module
            label = goto.label
            offset = goto.offset
            # Use _rt from exception if available, else current
            current_rt = goto._rt if goto._rt is not None else current_rt

            # Get the entry function from target module
            if offset is not None:
                # G +N^ROUTINE or G LABEL+N^ROUTINE - use line dispatch
                if label is not None:
                    # G LABEL+N^ROUTINE - compute line from label
                    if label not in module._label_lines:
                        raise LabelNotFoundError(
                            label,
                            module._routine_name,
                            list(module._label_lines.keys()),
                        ) from goto
                    target_line = module._label_lines[label] + offset
                else:
                    # G +N^ROUTINE - absolute line offset (1-based to 0-indexed)
                    target_line = offset - 1

                # Look up function via _line_map
                if target_line not in module._line_map:
                    # Find next valid line
                    valid_lines = [ln for ln in module._line_map if ln >= target_line]
                    if not valid_lines:
                        raise ValueError(
                            f"Entry point +{offset} not valid in {module._routine_name}"
                        )
                    target_line = min(valid_lines)

                # Get the function from line map
                label_name, line_offset = module._line_map[target_line]
                # For offset dispatch, we need to call internal trampoline function
                # with the proper offset - but the entry function doesn't support this
                # For simplicity, call the label's entry function (offset=0 behavior)
                # Full offset support requires passing offset through, which is complex
                # For now, just call the label function directly
                current_func = getattr(module, label_name)
            elif label is not None:
                # G LABEL^ROUTINE - call specific label
                label_func_name = label  # Already canonical
                if not hasattr(module, label_func_name):
                    raise LabelNotFoundError(
                        label,
                        module._routine_name,
                        list(getattr(module, "_label_lines", {}).keys()),
                    ) from goto
                current_func = getattr(module, label_func_name)
            else:
                # G ^ROUTINE - call entry label (same name as routine)
                entry_name = module._routine_name
                if not hasattr(module, entry_name):
                    # Fall back to lowercase
                    entry_name = module._routine_name.lower()
                current_func = getattr(module, entry_name)


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


# =============================================================================
# Spec 009: Global Storage Backend Factory (T009)
# =============================================================================


def get_global_storage(backend: str | None = None) -> GlobalStorageBackend:
    """Get global storage backend instance.

    Spec 009 (T009): Factory function for global storage backends.

    Backend selection priority:
    1. Explicit `backend` parameter if provided
    2. M2PY_GLOBAL_BACKEND environment variable
    3. Default: 'inmemory'

    Args:
        backend: Backend name ('inmemory', 'yottadb', 'iris') or None

    Returns:
        GlobalStorageBackend instance

    Raises:
        ImportError: If requested backend is not available
        ValueError: If backend name is not recognized
    """
    import os

    from m2py.runtime.globals import (
        IRISGlobalStorage,
        YottaDBGlobalStorage,
    )

    if backend is None:
        backend = os.environ.get("M2PY_GLOBAL_BACKEND", "inmemory")

    backend = backend.lower()

    if backend == "inmemory":
        return InMemoryGlobalStorage()
    elif backend == "yottadb":
        return YottaDBGlobalStorage()
    elif backend == "iris":
        return IRISGlobalStorage()
    else:
        raise ValueError(
            f"Unknown global storage backend: {backend!r}. "
            "Valid options: 'inmemory', 'yottadb', 'iris'"
        )


class MUMPSRuntime:
    """Minimal runtime for executing generated MUMPS code.

    Provides output capture for WRITE statements and execution support
    for generated Python code. Thread-unsafe - use one instance per thread.

    Spec 008: Extended for external call support with:
    - _current_routine: Current routine name for $TEXT(+0)
    - _current_source_lines: Source lines for $TEXT(+N)
    - _current_label_lines: Label->line mapping for $TEXT(LABEL+N)
    - get_text(): Implement $TEXT function

    Spec 009: Extended for global storage configuration with:
    - global_storage parameter for programmatic backend selection
    - M2PY_GLOBAL_BACKEND env var support via get_global_storage()
    """

    def __init__(self, global_storage: GlobalStorageBackend | None = None) -> None:
        """Initialize runtime with empty state.

        Args:
            global_storage: Optional global storage backend. If None,
                uses get_global_storage() which respects M2PY_GLOBAL_BACKEND
                environment variable (default: 'inmemory').
        """
        self._output: list[str] = []
        # Spec 008: External call context tracking
        self._current_routine: Optional[str] = None
        self._current_source_lines: Optional[List[str]] = None
        self._current_label_lines: Optional[Dict[str, int]] = None
        # Spec 009: Global variable storage (T008)
        # Use provided backend or fall back to factory function
        self._globals: GlobalStorageBackend = (
            global_storage if global_storage is not None else get_global_storage()
        )

    @property
    def globals(self) -> GlobalStorageBackend:
        """Get global variable storage backend.

        Spec 009 (T008): Provides access to global variable storage for
        generated code. The backend is selected via M2PY_GLOBAL_BACKEND
        environment variable (default: 'inmemory').
        """
        return self._globals

    def get_text(
        self,
        offset: int,
        label: Optional[str] = None,
        module: Optional[types.ModuleType] = None,
    ) -> str:
        """Get source text line ($TEXT function).

        Implements MUMPS $TEXT function which returns source code lines.
        - $TEXT(+0) returns routine name
        - $TEXT(+N) returns Nth line of routine (1-indexed)
        - $TEXT(LABEL) returns the label line itself
        - $TEXT(LABEL+N) returns line at label offset
        - $TEXT(+N^ROUTINE) returns Nth line of external routine
        - $TEXT(LABEL^ROUTINE) returns label line in external routine

        Args:
            offset: Line offset (0 = routine name, 1+ = source line index)
            label: Optional label for label+offset lookup
            module: Module containing _source_lines (None = current routine)

        Returns:
            Source line text, or empty string if:
            - Offset is past end of routine
            - Offset is negative
            - Label not found
        """
        # $TEXT(+0) returns routine name
        if offset == 0 and label is None:
            if module is not None:
                return getattr(module, "_routine_name", module.__name__)
            return self._current_routine or ""

        # Handle negative offsets (return empty per YDB)
        if offset < 0 and label is None:
            return ""

        # Get source lines and label map from module or current context
        if module is not None:
            lines = getattr(module, "_source_lines", [])
            label_lines = getattr(module, "_label_lines", {})
        else:
            lines = self._current_source_lines or []
            label_lines = self._current_label_lines or {}

        # Calculate actual line index
        if label is not None:
            base_idx = label_lines.get(label, -1)
            if base_idx < 0:
                return ""  # Label not found
            line_idx = base_idx + offset
        else:
            # Convert 1-based offset to 0-based index
            line_idx = offset - 1

        # Bounds check and return
        if 0 <= line_idx < len(lines):
            return lines[line_idx]
        return ""

    def write(self, value: Any) -> None:
        """Capture WRITE output.

        Args:
            value: Value to write (converted to string)

        Note:
            Does not add newlines automatically (MUMPS WRITE doesn't either).
            None values are treated as empty string (MUMPS undefined semantics).
        """
        if value is None:
            self._output.append("")
        else:
            self._output.append(str(value))

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
            # (the generated code no longer creates its own _rt since Phase 13)
            namespace["_rt"] = self

            # Find entry point
            if entry_point is None:
                # Find first function defined (look for def statements)
                entry_point = self._find_first_function(python_code)

            # Call entry point if found
            # Phase 13 (T076): Entry point functions now require _rt as first parameter
            if entry_point and entry_point in namespace:
                func = namespace[entry_point]
                if callable(func):
                    func(self)

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


__all__ = [
    "MUMPSRuntime",
    "ExecutionResult",
    "MArray",
    "GotoExternal",
    "LabelNotFoundError",
    "run_with_goto_support",
    # Spec 009: Global storage and helpers
    "GlobalStorageBackend",
    "InMemoryGlobalStorage",
    "get_global_storage",
    "m_set_piece",
    "m_set_extract",
    "m_data",
    "m_data_global",
    # Spec 010: Runtime exceptions
    "MRuntimeError",
]
