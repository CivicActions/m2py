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
from typing import TYPE_CHECKING, Any, Callable, Dict, List, NamedTuple, Optional, Tuple

if TYPE_CHECKING:
    pass  # Reserved for future type imports


# =============================================================================
# Spec 012: Variable Name Validation Helper (T012)
# =============================================================================

# MUMPS variable name pattern: starts with letter or %, followed by alphanumerics
# Global variables start with ^ followed by the same pattern
# Examples: X, VAR1, %ZTMP, ^GLO, ^GLO123
_VARNAME_PATTERN = re.compile(r"^[A-Za-z%][A-Za-z0-9]*$")
_GLOBAL_VARNAME_PATTERN = re.compile(r"^\^[A-Za-z%][A-Za-z0-9]*$")


def _is_valid_varname(name: str) -> bool:
    """Check if name is a valid MUMPS variable name.

    Spec 012 (T012): Validates variable names for name indirection.

    MUMPS variable naming rules:
    - Must start with letter (A-Z, a-z) or %
    - Followed by zero or more alphanumeric characters
    - Global variables start with ^ followed by valid name
    - Names are case-insensitive but we preserve case

    Does NOT handle subscripted names - call _parse_subscripted_name first
    to extract the base name and subscripts.

    Args:
        name: Variable name to validate (without subscripts)

    Returns:
        True if valid MUMPS variable name, False otherwise

    Examples:
        >>> _is_valid_varname("X")
        True
        >>> _is_valid_varname("VAR1")
        True
        >>> _is_valid_varname("%ZTMP")
        True
        >>> _is_valid_varname("^GLO")
        True
        >>> _is_valid_varname("123BAD")
        False
        >>> _is_valid_varname("")
        False
        >>> _is_valid_varname("VAR(1)")  # Subscripts not allowed here
        False
    """
    if not name:
        return False
    # Check global or local pattern
    if name.startswith("^"):
        return bool(_GLOBAL_VARNAME_PATTERN.match(name))
    return bool(_VARNAME_PATTERN.match(name))


def _parse_subscripted_name(name: str) -> Tuple[str, Optional[Tuple[Any, ...]]]:
    """Parse a variable name that may include subscripts.

    Spec 012 (T007-T008): Extracts base name and subscripts from
    name indirection targets like "ARR(1,2)" or "^GLO(sub)".

    Args:
        name: Variable name, optionally with subscripts
              Examples: "X", "ARR(1,2)", "^GLO", "^GLO(1)"

    Returns:
        Tuple of (base_name, subscripts) where:
        - base_name: The variable name without subscripts
        - subscripts: Tuple of subscript values, or None if no subscripts

    Raises:
        IndirectionError: If subscript syntax is malformed

    Examples:
        >>> _parse_subscripted_name("X")
        ("X", None)
        >>> _parse_subscripted_name("ARR(1,2)")
        ("ARR", (1, 2))
        >>> _parse_subscripted_name("^GLO(1)")
        ("^GLO", (1,))
    """
    # Find opening parenthesis
    paren_pos = name.find("(")
    if paren_pos == -1:
        return (name, None)

    base_name = name[:paren_pos]

    # Extract subscript portion - must end with )
    if not name.endswith(")"):
        raise IndirectionError(
            name, "malformed subscript - missing closing parenthesis"
        )

    subscript_str = name[paren_pos + 1 : -1]
    if not subscript_str:
        raise IndirectionError(name, "empty subscripts not allowed")

    # Parse subscripts - handle quoted strings and nested parens
    subscripts = _parse_subscript_list(subscript_str, name)
    return (base_name, tuple(subscripts))


def _parse_subscript_list(subscript_str: str, original_name: str) -> List[Any]:
    """Parse comma-separated subscript list.

    Handles:
    - Numeric subscripts: 1, 2, 3
    - String subscripts: "foo", 'bar'
    - Variable references: X, VAR (returned as strings)
    - Nested parentheses in expressions

    Args:
        subscript_str: The content between parentheses
        original_name: Original name for error messages

    Returns:
        List of subscript values

    Raises:
        IndirectionError: If subscript parsing fails
    """
    subscripts: List[Any] = []
    current = ""
    paren_depth = 0
    in_string = False
    string_char = ""

    for char in subscript_str:
        if in_string:
            current += char
            if char == string_char:
                in_string = False
        elif char in ('"', "'"):
            in_string = True
            string_char = char
            current += char
        elif char == "(":
            paren_depth += 1
            current += char
        elif char == ")":
            paren_depth -= 1
            current += char
        elif char == "," and paren_depth == 0:
            subscripts.append(_convert_subscript(current.strip(), original_name))
            current = ""
        else:
            current += char

    # Don't forget the last subscript
    if current.strip():
        subscripts.append(_convert_subscript(current.strip(), original_name))

    return subscripts


def _convert_subscript(value: str, original_name: str) -> Any:
    """Convert a subscript string to its value.

    Args:
        value: String representation of subscript
        original_name: Original name for error messages

    Returns:
        Converted value (int, float, or string)
    """
    if not value:
        raise IndirectionError(original_name, "empty subscript value")

    # Try numeric conversion
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass

    # Handle quoted strings - remove quotes
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]

    # Return as-is (variable reference or expression)
    return value


# =============================================================================
# Spec 012: Indirection & XECUTE Exceptions and Types
# =============================================================================


class IndirectionError(Exception):
    """Raised for invalid indirection operations at runtime.

    Spec 012 (T001): Exception for name indirection, XECUTE, and
    indirect DO/GOTO operations that fail at runtime.

    Attributes:
        expression: The expression that caused the error (string representation)
        reason: Human-readable error description
        variable_name: Name of the variable being indirected (if applicable)
        variable_value: Value found in the variable (if applicable)
    """

    def __init__(
        self,
        expression: str,
        reason: str,
        variable_name: Optional[str] = None,
        variable_value: Optional[Any] = None,
    ) -> None:
        self.expression = expression
        self.reason = reason
        self.variable_name = variable_name
        self.variable_value = variable_value
        super().__init__(str(self))

    def __str__(self) -> str:
        msg = f"Indirection error: {self.expression} - {self.reason}"
        if self.variable_name:
            msg += f" (variable '{self.variable_name}'"
            if self.variable_value is not None:
                msg += f" = '{self.variable_value}'"
            msg += ")"
        return msg


class CallTarget(NamedTuple):
    """Parsed indirect DO/GOTO target.

    Spec 012 (T002): Represents the components of a DO/GOTO target string.

    Examples:
        - "LABEL" → CallTarget(label="LABEL", routine=None, offset=None)
        - "^ROUTINE" → CallTarget(label=None, routine="ROUTINE", offset=None)
        - "LABEL^ROUTINE" → CallTarget(label="LABEL", routine="ROUTINE", offset=None)
        - "LABEL+5" → CallTarget(label="LABEL", routine=None, offset=5)
        - "LABEL+5^ROUTINE" → CallTarget(label="LABEL", routine="ROUTINE", offset=5)
    """

    label: Optional[str] = None
    routine: Optional[str] = None
    offset: Optional[int] = None


# Spec 009: Import global storage backend protocol
from m2py.runtime.globals import GlobalStorageBackend, InMemoryGlobalStorage  # noqa: E402

# Spec 009: Import helper functions
from m2py.runtime.helpers import (  # noqa: E402
    m_data,
    m_data_global,
    m_format_output,
    m_set_extract,
    m_set_piece,
)

# Spec 010: Import runtime exception class
from m2py.runtime.exceptions import MRuntimeError  # noqa: E402

# Spec 010: Import $ORDER and $QUERY helper functions (Phase 2)
# Spec 010: Import $SELECT helper function (Phase 3)
# Spec 010: Import $PIECE and $EXTRACT helper functions (Phase 5)
# Spec 010: Import $GET helper functions (Phase 6)
# Spec 010: Import $FIND helper function (Phase 7)
from m2py.runtime.helpers import (  # noqa: E402
    _raise_select_false,
    m_extract,
    m_find,
    m_get,
    m_get_global,
    m_order,
    m_order_global,
    m_piece,
    m_query,
    m_query_global,
)

# Spec 011: Import sorts-after (uses MUMPS collation) and pattern match helpers
# Note: Contains ([) and Follows (]) are inlined as Python expressions in codegen
from m2py.runtime.helpers import (  # noqa: E402
    m_pattern_match,
    m_sorts_after,
)

# Spec 011 Phase 20: Import READ command helpers
from m2py.runtime.helpers import (  # noqa: E402
    m_read_char,
    m_read_timeout,
)


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

    def kill_node(self, subscripts: tuple[Any, ...]) -> None:
        """Delete node value but preserve descendants (ZKILL command).

        Spec 013 Phase 19 (T135): ZKILL removes value but keeps children.

        Unlike kill() which removes the entire subtree, kill_node()
        only removes the value at the specified node, leaving all
        subscripted descendants intact.

        Args:
            subscripts: Path to the node to zkill (empty for root)

        Example:
            arr.set(value=1)
            arr.set(1, value=2)
            arr.kill_node(())  # Removes root value, keeps arr(1)
            arr.defined()      # Returns 10 (has children, no value)
        """
        if not subscripts:
            self._value = None
            return

        # Navigate to parent of target
        parent = self
        for sub in subscripts[:-1]:
            if sub not in parent._children:
                return  # Path doesn't exist
            parent = parent._children[sub]

        last = subscripts[-1]
        if last in parent._children:
            # Only remove value, keep children intact
            parent._children[last]._value = None

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

    def merge_from(self, source: "MArray") -> None:
        """Merge source tree into this node (MERGE command).

        Spec 011 Phase 16: Implements MERGE semantics:
        - Copies source's value to this node (if source has value)
        - Recursively copies all descendants from source
        - Does NOT delete any existing nodes in this tree

        Args:
            source: Source MArray to merge from
        """
        # Copy source's value if it has one
        if source._value is not None:
            self._value = source._value

        # Recursively merge children
        for key, child_source in source._children.items():
            if key not in self._children:
                self._children[key] = MArray()
            self._children[key].merge_from(child_source)

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
        # Spec 011: Column/line position tracking for $X, $Y
        self._x: int = 0  # Current column position (0-based)
        self._y: int = 0  # Current line position
        # Spec 011: Stack level tracking for $STACK
        self._stack_level: int = 0
        # Spec 011: I/O device tracking for $IO
        self._io: str = "0"  # Default I/O device
        # Spec 013: Device table for OPEN/CLOSE/USE
        # Maps device name -> file object (or None for special devices)
        self._devices: Dict[str, Any] = {"0": None}  # "0" is principal device
        # Spec 011: Extrinsic function context for $QUIT
        self._in_extrinsic: bool = False
        # Spec 013 Phase 11: $ZJOB - last JOB'd process ID
        self._zjob: str = "0"
        # Spec 013 Phase 12: Error processing special variables
        # $ECODE - comma-delimited list of active error codes (empty = no errors)
        self._ecode: str = ""
        # $ETRAP - code string to execute when error occurs
        self._etrap: str = ""
        # $ZERROR - application-supplied error message text
        self._zerror: str = ""
        # Spec 013 Phase 19: Routine registry for ZLINK
        self._routines: Dict[str, Any] = {}

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
        """Capture WRITE output and update $X/$Y position tracking.

        Args:
            value: Value to write (converted to string)

        Note:
            Does not add newlines automatically (MUMPS WRITE doesn't either).
            None values are treated as empty string (MUMPS undefined semantics).
            Spec 011: Updates _x (column) and _y (line) for $X/$Y tracking.
            Spec 011 Phase 9: Uses m_format_output for canonical number formatting.
        """
        if value is None:
            s = ""
        else:
            s = m_format_output(value)

        # Spec 011: Update $X/$Y position tracking
        for char in s:
            if char == "\n":
                self._x = 0
                self._y += 1
            elif char == "\f":
                self._x = 0
                self._y = 0  # Form feed resets line too
            else:
                self._x += 1

        self._output.append(s)

    def write_tab(self, column: int) -> None:
        """Tab to specified column position (MUMPS ?n format control).

        MUMPS semantics: If current column ($X) < target, write spaces to reach
        the target column. If current column >= target, do nothing.

        Args:
            column: Target column (0-based, same as $X)

        Spec 011 (T008): Implements column positioning for WRITE ?n.
        """
        if self._x < column:
            spaces = column - self._x
            self.write(" " * spaces)

    def get_output(self) -> str:
        """Return accumulated WRITE output.

        Returns:
            Concatenated string of all write() calls
        """
        return "".join(self._output)

    def clear(self) -> None:
        """Clear accumulated output and reset position tracking."""
        self._output.clear()
        self._x = 0
        self._y = 0

    # =========================================================================
    # Spec 013 Phase 19: Z-Command Support Methods
    # =========================================================================

    def _quote_value(self, value: Any) -> str:
        """Quote a value for ZWRITE output format.

        Args:
            value: Value to quote

        Returns:
            Quoted string suitable for SET @ input
        """
        if value is None or value == "":
            return '""'
        s = str(value)
        # Check if it's a number (doesn't need quoting)
        try:
            float(s)
            return s
        except ValueError:
            pass
        # Quote strings, escaping internal quotes
        escaped = s.replace('"', '""')
        return f'"{escaped}"'

    def zwrite(self, scope: dict[str, Any]) -> None:
        """ZWRITE - display all local variables.

        Spec 013 Phase 19 (T132): Argumentless ZWRITE shows all locals.

        Args:
            scope: Variable scope dictionary
        """
        for name in sorted(scope.keys()):
            if name.startswith("_"):
                continue  # Skip internal variables
            value = scope[name]
            self._zwrite_var(name, value)

    def _format_subscript(self, sub: Any) -> str:
        """Format a subscript value for ZWRITE output.

        Numeric subscripts are not quoted, string subscripts are.

        Args:
            sub: Subscript value

        Returns:
            Formatted subscript (quoted if string, unquoted if numeric)
        """
        s = str(sub)
        # Check if it's numeric
        try:
            float(s)
            # Return numeric subscripts unquoted
            return s
        except ValueError:
            pass
        # Quote string subscripts
        escaped = s.replace('"', '""')
        return f'"{escaped}"'

    def zwrite_local(
        self, name: str, subscripts: tuple[str, ...], scope: dict[str, Any]
    ) -> None:
        """ZWRITE - display a local variable and its descendants.

        Args:
            name: Variable name
            subscripts: Subscript path (empty for unsubscripted)
            scope: Variable scope dictionary
        """
        if name not in scope:
            return  # Variable not defined

        var = scope[name]
        if not isinstance(var, MArray):
            # Simple value
            if subscripts:
                return  # Can't subscript a simple value
            self.write(f"{name}={self._quote_value(var)}\n")
            return

        # Navigate to subscript position and collect path
        node = var
        subs_list = list(subscripts)
        for sub in subscripts:
            if sub not in node._children:
                return  # Subscript doesn't exist
            node = node._children[sub]

        # Output this node and descendants
        self._zwrite_marray(name, subs_list, node)

    def _zwrite_marray(
        self, base_name: str, subscripts: list[Any], node: "MArray"
    ) -> None:
        """Output an MArray node and its descendants in ZWRITE format.

        Args:
            base_name: Variable name (e.g., "X")
            subscripts: List of subscripts to this node (may be empty)
            node: The MArray node to output
        """
        # Build the path string with comma-separated subscripts
        if subscripts:
            subs_str = ",".join(self._format_subscript(s) for s in subscripts)
            path = f"{base_name}({subs_str})"
        else:
            path = base_name

        # Output value at this node if it exists
        if node._value is not None:
            self.write(f"{path}={self._quote_value(node._value)}\n")

        # Output children recursively in sorted order
        for sub in sorted(node._children.keys(), key=str):
            child = node._children[sub]
            self._zwrite_marray(base_name, subscripts + [sub], child)

    def zwrite_global(self, name: str, subscripts: tuple[str, ...]) -> None:
        """ZWRITE - display a global variable and its descendants.

        Args:
            name: Global name (without ^)
            subscripts: Subscript path (empty for unsubscripted)
        """
        # Get value at this node
        value = self.globals.get(name, subscripts)
        if value is not None:
            if subscripts:
                sub_str = ",".join(self._format_subscript(s) for s in subscripts)
                self.write(f"^{name}({sub_str})={self._quote_value(value)}\n")
            else:
                self.write(f"^{name}={self._quote_value(value)}\n")

        # Get descendants using $ORDER
        current = subscripts
        while True:
            # Find next subscript at this level (direction=1 means forward)
            next_sub = self.globals.order(name, current, direction=1)
            if not next_sub:
                break
            # Construct new subscripts tuple
            new_subs = subscripts + (next_sub,)
            # Recursively output this subtree
            self.zwrite_global(name, new_subs)
            # Move to next sibling
            current = subscripts + (next_sub,)

    def _zwrite_var(self, name: str, value: Any) -> None:
        """Output a single variable in ZWRITE format."""
        if isinstance(value, MArray):
            self._zwrite_marray(name, [], value)
        else:
            self.write(f"{name}={self._quote_value(value)}\n")

    def zshow(self, codes: str, scope: dict[str, Any], destination: Any = None) -> None:
        """ZSHOW - display system information.

        Spec 013 Phase 19 (T140): ZSHOW displays process info.

        Codes:
        - S: Stack trace
        - V: Local variables
        - D: Devices
        - I: Intrinsic special variables
        - *: All of the above

        Args:
            codes: Information code string
            scope: Variable scope dictionary
            destination: Optional output destination (not implemented)
        """
        import traceback

        codes = codes.upper() if codes else "*"

        for code in codes:
            if code == "V" or code == "*":
                # Variables - like ZWRITE
                self.zwrite(scope)
            if code == "S" or code == "*":
                # Stack trace
                self.write("Stack trace:\n")
                for line in traceback.format_stack():
                    self.write(line)
            if code == "D" or code == "*":
                # Devices
                self.write(f"$IO={self._io}\n")
                self.write("$PRINCIPAL=0\n")  # Principal device is always "0"
            if code == "I" or code == "*":
                # Intrinsic special variables
                self.write(f"$HOROLOG={self.horolog()}\n")
                self.write(f"$JOB={self.job()}\n")
                self.write(f"$TLEVEL={self.tlevel()}\n")

    def zlink(self, routine_name: str) -> None:
        """ZLINK - dynamically link/load a routine.

        Spec 013 Phase 19 (T137): ZLINK imports a routine module.

        In the transpiler context, this imports a Python module and
        registers it in the routine registry.

        Args:
            routine_name: Name of routine to link
        """
        import importlib

        # Clean routine name
        name = str(routine_name).strip().strip('"').lower()

        try:
            # Try to import as a Python module
            module = importlib.import_module(name)
            self._routines[name.upper()] = module
        except ImportError:
            # Try m2py bundled routines
            try:
                module = importlib.import_module(
                    f"m2py.runtime.routines.{name.upper()}"
                )
                self._routines[name.upper()] = module
            except ImportError:
                # Routine not found - this is not an error in MUMPS
                # The routine may be linked later or not needed
                pass

    class ZGotoException(Exception):
        """Exception for ZGOTO stack unwinding.

        Spec 013 Phase 19 (T143): ZGOTO unwinds to specified stack level.
        """

        def __init__(self, level: int, target: str | None = None):
            self.level = level
            self.target = target
            super().__init__(
                f"ZGOTO to level {level}" + (f":{target}" if target else "")
            )

    # =========================================================================
    # Spec 011: Special Variable Accessor Methods
    # =========================================================================

    def horolog(self) -> str:
        """Return MUMPS $HOROLOG format: days,seconds.

        Days since December 31, 1840 (MUMPS epoch).
        Seconds since midnight.

        Returns:
            String in format "days,seconds"
        """
        import datetime

        now = datetime.datetime.now()
        epoch = datetime.date(1840, 12, 31)
        days = (now.date() - epoch).days
        seconds = now.hour * 3600 + now.minute * 60 + now.second
        return f"{days},{seconds}"

    def job(self) -> int:
        """Return process ID ($JOB).

        Returns:
            Current process ID
        """
        import os

        return os.getpid()

    def zjob(self) -> str:
        """Return last JOB'd process ID ($ZJOB).

        Spec 013 Phase 11: Returns the process ID of the last process
        started by the JOB command. Returns "0" if no JOB has been executed.

        Returns:
            Process ID as string (matches MUMPS convention)
        """
        return self._zjob

    def io(self) -> str:
        """Return current I/O device name ($IO).

        Returns:
            Current I/O device identifier (default "0")
        """
        return self._io

    def x(self) -> int:
        """Return current column position ($X).

        Returns:
            Current column position (0-based)
        """
        return self._x

    def y(self) -> int:
        """Return current line position ($Y).

        Returns:
            Current line position
        """
        return self._y

    def stack_level(self) -> int:
        """Return current stack level ($STACK).

        Returns:
            Current call stack depth
        """
        return self._stack_level

    def quit_flag(self) -> int:
        """Return extrinsic function context flag ($QUIT).

        Returns:
            1 if inside extrinsic function ($$label), 0 otherwise
        """
        return 1 if self._in_extrinsic else 0

    def tlevel(self) -> int:
        """Return current transaction nesting level ($TLEVEL).

        Spec 013 FR-015: Delegates to global storage backend.

        Returns:
            Current transaction depth (0 = no active transaction)
        """
        return self._globals.get_tlevel()

    def ecode(self) -> str:
        """Return current error code list ($ECODE).

        Spec 013 Phase 12 (FR-026): Returns comma-delimited list of active
        error codes. Empty string means no active errors.

        Format: ",code1,code2," - always starts and ends with comma when non-empty.
        Error codes:
        - M codes: Standard MUMPS errors (e.g., ",M6," for undefined)
        - Z codes: Implementation-specific errors
        - U codes: User-defined errors

        Returns:
            Comma-delimited error code list, or empty string
        """
        return self._ecode

    def set_ecode(self, value: str) -> None:
        """Set error code list ($ECODE).

        Spec 013 Phase 12 (FR-026): Setting $ECODE is how applications
        clear errors (SET $ECODE="") or trigger error handlers.

        Args:
            value: Error code list (empty string to clear)
        """
        self._ecode = value

    def etrap(self) -> str:
        """Return current error trap code ($ETRAP).

        Spec 013 Phase 12 (FR-026): Returns M code string to execute
        when an error occurs and $ECODE becomes non-empty.

        Returns:
            Error trap code string, or empty string if not set
        """
        return self._etrap

    def set_etrap(self, value: str) -> None:
        """Set error trap code ($ETRAP).

        Spec 013 Phase 12 (FR-026): Sets the M code to execute on error.
        Common patterns:
        - SET $ETRAP="D ^%ZTER Q"  ; Log error and quit
        - SET $ETRAP="G ERROR^ROUTINE"  ; Goto error handler

        Args:
            value: M code string to execute on error
        """
        self._etrap = value

    def zerror(self) -> str:
        """Return application error message ($ZERROR).

        Spec 013 Phase 12 (FR-045): Returns application-supplied error
        message text. Typically set by $ZYERROR routine using $ZSTATUS.

        Returns:
            Error message string, or empty string
        """
        return self._zerror

    def set_zerror(self, value: str) -> None:
        """Set application error message ($ZERROR).

        Spec 013 Phase 12 (FR-045): Sets error message text for application
        error handling. Usually set in error handler routines.

        Args:
            value: Error message text
        """
        self._zerror = value

    def _exception_to_ecode(self, exc: Exception) -> str:
        """Map Python exception to MUMPS $ECODE format.

        Spec 014 (T055): Converts Python exceptions to MUMPS error codes
        in the comma-delimited $ECODE format: ",Mnn," or ",Zxxx,"

        Error Code Mapping:
        | Python Exception          | MUMPS $ECODE       | Description              |
        |--------------------------|-------------------|--------------------------|
        | ZeroDivisionError         | ,M9,              | Divide by zero           |
        | KeyError                  | ,M6,              | Undefined local variable |
        | MRuntimeError(SELECTFALSE)| ,M4,              | No $SELECT argument true |
        | MRuntimeError(RANDARGNEG) | ,M28,             | $RANDOM argument negative|
        | IndirectionError          | ,M26,             | Non-existent environment |
        | LabelNotFoundError        | ,M13,             | Label not found          |
        | RuntimeError("NAKEDERR")  | ,M1,              | Naked reference error    |
        | RuntimeError("M44")       | ,M44,             | TCOMMIT without TSTART   |
        | Other                     | ,Z150373210,      | Generic system error     |

        Args:
            exc: The Python exception to map

        Returns:
            MUMPS $ECODE format string (e.g., ",M9,")
        """
        # Import MRuntimeError locally to avoid circular imports
        from m2py.runtime.exceptions import MRuntimeError

        if isinstance(exc, ZeroDivisionError):
            return ",M9,"  # Divide by zero
        elif isinstance(exc, KeyError):
            return ",M6,"  # Undefined local variable
        elif isinstance(exc, MRuntimeError):
            # Map MRuntimeError codes to MUMPS standard codes
            code_map = {
                "SELECTFALSE": "M4",  # $SELECT with no true condition
                "RANDARGNEG": "M28",  # $RANDOM argument must be > 0
            }
            mcode = code_map.get(exc.code, f"Z{exc.code}")
            return f",{mcode},"
        elif isinstance(exc, IndirectionError):
            return ",M26,"  # Non-existent environment
        elif isinstance(exc, LabelNotFoundError):
            return ",M13,"  # Label not found
        elif isinstance(exc, RuntimeError):
            # Check for specific RuntimeError messages
            msg = str(exc)
            if "NAKEDERR" in msg or "naked" in msg.lower():
                return ",M1,"  # Naked reference error
            elif "M44" in msg or "TCOMMIT" in msg:
                return ",M44,"  # TCOMMIT without TSTART
            return ",Z150373210,"  # Generic system error
        else:
            return ",Z150373210,"  # Generic system error (YDB code)

    def _handle_etrap(self, exc: Exception, _scope: dict) -> bool:
        """Handle an exception using $ETRAP if set.

        Spec 014 (T055): Implements MUMPS error handling semantics:
        1. If $ETRAP is empty, return False (exception should propagate)
        2. Set $ECODE based on exception type
        3. Set $ZERROR to exception message
        4. Execute $ETRAP code via execute_mumps()
        5. Return True if $ECODE was cleared (error handled), False otherwise

        When True is returned, the calling code should perform an implicit QUIT.
        When False is returned, the exception should propagate to the caller.

        Args:
            exc: The Python exception that occurred
            _scope: Current variable scope for execute_mumps()

        Returns:
            True if error was handled ($ECODE cleared), False otherwise

        Side Effects:
            - Sets $ECODE based on exception type
            - Sets $ZERROR to exception message
            - Executes $ETRAP code which may modify $ECODE and variables
        """
        if not self._etrap:
            return False  # No handler, propagate exception

        # Map Python exception to MUMPS $ECODE
        self._ecode = self._exception_to_ecode(exc)
        self._zerror = str(exc)

        # Execute $ETRAP code
        try:
            self.execute_mumps(self._etrap, _scope)
        except Exception:
            # Error in $ETRAP itself - propagate original error
            return False

        # Check if handler cleared $ECODE
        return self._ecode == ""

    def push_frame(self) -> None:
        """Push a new stack frame (for DO/extrinsic calls)."""
        self._stack_level += 1

    def pop_frame(self) -> None:
        """Pop a stack frame (for QUIT)."""
        if self._stack_level > 0:
            self._stack_level -= 1

    # =========================================================================
    # Spec 013: Device I/O Methods (Phase 10 - OPEN/CLOSE/USE)
    # =========================================================================

    def open_device(
        self,
        device: str,
        parameters: Optional[List[str]] = None,
        timeout: Optional[float] = None,
    ) -> bool:
        """Open a device for I/O (MUMPS OPEN command).

        Spec 013 Phase 10 (T091): Opens a device/file for I/O operations.

        Args:
            device: Device name (file path or special device name)
            parameters: Device parameters (NEWVERSION, READONLY, etc.)
            timeout: Optional timeout in seconds

        Returns:
            True if device opened successfully, False if timeout
        """
        params = parameters or []

        # Determine file mode from parameters
        mode = "r"  # Default read
        if "NEWVERSION" in params or "NEW" in params:
            mode = "w"
        elif "APPEND" in params:
            mode = "a"
        elif "WRITE" in params:
            mode = "r+"

        try:
            # Open the file (device)
            self._devices[device] = open(device, mode)  # noqa: SIM115
            return True
        except (FileNotFoundError, PermissionError, OSError):
            # For timeout operations, return False instead of raising
            if timeout is not None:
                return False
            raise

    def close_device(self, device: str, parameters: Optional[List[str]] = None) -> None:
        """Close a device (MUMPS CLOSE command).

        Spec 013 Phase 10 (T092): Closes a device/file.

        Args:
            device: Device name to close
            parameters: Optional close parameters (usually ignored)
        """
        if device in self._devices and self._devices[device] is not None:
            try:
                self._devices[device].close()
            except (OSError, IOError):
                pass  # Ignore errors closing
            del self._devices[device]

        # If closing current device, switch back to principal device
        if self._io == device:
            self._io = "0"

    def use_device(self, device: str, parameters: Optional[List[str]] = None) -> None:
        """Select current I/O device (MUMPS USE command).

        Spec 013 Phase 10 (T089): Switches the current I/O device.

        Args:
            device: Device name to make current
            parameters: Optional device parameters
        """
        # Device "0" is always available (principal device)
        if device == "0" or device in self._devices:
            self._io = device

    # =========================================================================
    # Spec 013 Phase 11: JOB Command Runtime Support
    # =========================================================================

    def start_job(
        self,
        label: Optional[str],
        routine: Optional[str],
        args: List[Any],
        params: Optional[List[str]],
        timeout: Optional[float],
    ) -> bool:
        """Start a new process executing a routine (MUMPS JOB command).

        Spec 013 Phase 11 (T095-T096): JOB spawns a new process.

        In Python transpilation context:
        - If routine is None, uses the current module
        - Spawns subprocess running the transpiled Python with entry point
        - Sets $ZJOB to the spawned process ID

        Timeout behavior per MUMPS spec 8.2.10:
        - No timeout: Returns True, does not affect $TEST
        - Timeout present: Returns True on success ($TEST=1), False on timeout ($TEST=0)

        Note: This is a simplified implementation. Full MUMPS JOB semantics
        include process parameters (DEFAULT, INPUT, OUTPUT, etc.) which are
        not yet supported.

        Args:
            label: Entry point label name
            routine: Routine name (None = current routine)
            args: Arguments to pass to the entry point
            params: Process parameters (currently ignored)
            timeout: Optional timeout in seconds

        Returns:
            bool: True if job started successfully within timeout, False on timeout
        """
        import os

        # For now, emit a comment about the JOB - full subprocess support
        # would require the transpiled module to be runnable as a standalone
        # Python program with the entry point callable
        #
        # Future enhancement: Use subprocess to run:
        #   python -c "from <module> import <label>; <label>(MUMPSRuntime())"
        #
        # For testing purposes, we simulate the JOB:
        # - $ZJOB gets set to a pseudo-PID (current process ID)
        # - Job always "succeeds" immediately

        self._zjob = str(os.getpid())  # Set $ZJOB to current PID as placeholder

        if timeout is not None:
            # With timeout, return True (success) - caller sets $TEST
            return True
        else:
            # Without timeout, just return True
            return True

    # =========================================================================
    # Spec 012: Indirection & XECUTE Runtime Methods (Phase 2 - T007-T011)
    # Phase 11: Edge case handling (T065-T072)
    # =========================================================================

    def get_indirection_source(self, varname: str, _scope: Dict[str, Any]) -> str:
        """Get value of an indirection source variable, validating existence.

        Spec 012 Phase 11 (T065): Unlike get_var(), this method raises an error
        if the source variable is undefined, matching YDB's LVUNDEF behavior.

        In MUMPS, @UNDEF should raise "Undefined local variable: UNDEF"
        rather than silently using an empty string.

        Args:
            varname: Variable name to get value of (the indirection source)
            _scope: Current scope dictionary

        Returns:
            str: The variable's value (which becomes the target variable name)

        Raises:
            IndirectionError: If varname is undefined in _scope

        Examples:
            >>> scope = {"X": MArray("Y")}
            >>> rt.get_indirection_source("X", scope)
            "Y"
            >>> rt.get_indirection_source("UNDEF", {})
            IndirectionError: Undefined local variable: UNDEF
        """
        if varname not in _scope:
            raise IndirectionError(
                varname,
                f"Undefined local variable: {varname}",
                variable_name=varname,
            )

        raw_value = _scope[varname]

        # Extract value from MArray if present
        if isinstance(raw_value, MArray):
            value = raw_value.value
        else:
            value = raw_value

        # Convert to string for use as variable name
        return str(value) if value is not None else ""

    def get_var(self, name: str, _scope: Dict[str, Any]) -> Any:
        """Get variable value by name (name indirection).

        Spec 012 (T007): Implements reading a variable by dynamic name.

        Behavior:
        - Local variables: Look up in _scope dict
        - Global variables (^prefix): Use global storage (MArray at _globals)
        - Subscripted variables: Access nested structure
        - Undefined variables: Return empty string ""
        - Invalid names: Raise IndirectionError

        Args:
            name: Variable name, optionally with subscripts
                  Examples: "X", "ARR(1,2)", "^GLO", "^GLO(1)"
            _scope: Current scope dictionary

        Returns:
            Variable value, or "" if undefined

        Raises:
            IndirectionError: If name is not a valid variable name

        Examples:
            >>> rt.get_var("X", {"X": 5})
            5
            >>> rt.get_var("UNDEF", {})
            ""
            >>> rt.get_var("ARR(1)", {"ARR": MArray()})
            # Returns value at subscript
        """
        if not name:
            raise IndirectionError("", "empty variable name")

        # Parse subscripts if present
        base_name, subscripts = _parse_subscripted_name(name)

        # Validate the base name
        if not _is_valid_varname(base_name):
            raise IndirectionError(
                name,
                f"invalid variable name - must start with letter or %, got '{base_name}'",
            )

        # Handle global variables
        if base_name.startswith("^"):
            return self._get_global_var(base_name, subscripts)

        # Handle local variables
        return self._get_local_var(base_name, subscripts, _scope)

    def _get_local_var(
        self, name: str, subscripts: Optional[Tuple[Any, ...]], _scope: Dict[str, Any]
    ) -> Any:
        """Get local variable value from scope.

        Args:
            name: Base variable name (no subscripts)
            subscripts: Optional tuple of subscript values
            _scope: Scope dictionary

        Returns:
            Variable value, or "" if undefined
        """
        raw_value = _scope.get(name, "")

        # Extract value from MArray if needed
        if isinstance(raw_value, MArray):
            if subscripts is None:
                # Simple variable - return value
                return raw_value.value
            else:
                # Subscripted access
                return raw_value.get(*subscripts)

        # Non-MArray value (shouldn't happen normally but handle gracefully)
        if subscripts is None:
            return raw_value
        elif raw_value == "":
            # Undefined base variable, subscript also undefined
            return ""
        else:
            # Non-array value with subscripts - undefined
            return ""

    def _get_global_var(self, name: str, subscripts: Optional[Tuple[Any, ...]]) -> Any:
        """Get global variable value.

        Args:
            name: Global variable name (starts with ^)
            subscripts: Optional tuple of subscript values

        Returns:
            Variable value, or "" if undefined
        """
        # Strip ^ for storage key
        key = name[1:]

        # Use the GlobalStorageBackend interface
        subs = () if subscripts is None else tuple(str(s) for s in subscripts)
        result = self._globals.get(key, subs)
        return result if result is not None else ""

    def set_var(self, name: str, value: Any, _scope: Dict[str, Any]) -> None:
        """Set variable value by name (name indirection).

        Spec 012 (T008): Implements writing a variable by dynamic name.

        Behavior:
        - Local variables: Store in _scope dict
        - Global variables (^prefix): Use global storage
        - Subscripted variables: Create nested structure as needed
        - Creates variable if doesn't exist
        - Invalid names: Raise IndirectionError

        Args:
            name: Variable name, optionally with subscripts
            value: Value to set
            _scope: Current scope dictionary

        Raises:
            IndirectionError: If name is not a valid variable name

        Examples:
            >>> scope = {}
            >>> rt.set_var("X", 5, scope)
            >>> scope["X"]
            5
            >>> rt.set_var("ARR(1,2)", 10, scope)
            >>> scope["ARR"].get(1, 2)
            10
        """
        if not name:
            raise IndirectionError("", "empty variable name")

        # Parse subscripts if present
        base_name, subscripts = _parse_subscripted_name(name)

        # Validate the base name
        if not _is_valid_varname(base_name):
            raise IndirectionError(
                name,
                f"invalid variable name - must start with letter or %, got '{base_name}'",
            )

        # Handle global variables
        if base_name.startswith("^"):
            self._set_global_var(base_name, subscripts, value)
            return

        # Handle local variables
        self._set_local_var(base_name, subscripts, value, _scope)

    def _set_local_var(
        self,
        name: str,
        subscripts: Optional[Tuple[Any, ...]],
        value: Any,
        _scope: Dict[str, Any],
    ) -> None:
        """Set local variable value in scope.

        Args:
            name: Base variable name (no subscripts)
            subscripts: Optional tuple of subscript values
            value: Value to set
            _scope: Scope dictionary
        """
        if subscripts is None:
            # Simple variable assignment - use MArray for consistency with codegen
            if name not in _scope or not isinstance(_scope[name], MArray):
                _scope[name] = MArray()
            _scope[name].value = value
            return

        # Subscripted assignment - ensure MArray exists
        if name not in _scope or not isinstance(_scope[name], MArray):
            _scope[name] = MArray()

        # Set value at subscript
        _scope[name][subscripts].value = value

    def _set_global_var(
        self, name: str, subscripts: Optional[Tuple[Any, ...]], value: Any
    ) -> None:
        """Set global variable value.

        Args:
            name: Global variable name (starts with ^)
            subscripts: Optional tuple of subscript values
            value: Value to set
        """
        # Strip ^ for storage key
        key = name[1:]

        # Use the GlobalStorageBackend interface
        subs = () if subscripts is None else tuple(str(s) for s in subscripts)
        self._globals.set(key, subs, str(value))

    def resolve_indirection(
        self, expr: str, levels: int, _scope: Dict[str, Any]
    ) -> Any:
        """Resolve N levels of name indirection.

        Spec 012 (T009): Resolves multi-level indirection like @X, @@X, @@@X.

        MUMPS indirection semantics:
        - @X means: evaluate X to get a name, then get value of that variable
        - @@X means: evaluate @X to get a name, then get value of that variable
        - Each @ adds one level of dereferencing

        For levels=1 (@X): X → name → get value of that name
        For levels=2 (@@X): X → name1 → get value → name2 → get value of that name
        For levels=3 (@@@X): X → name1 → name2 → name3 → get value of that name

        Args:
            expr: Initial variable name to start resolving
            levels: Number of indirection levels (1 for @, 2 for @@, etc.)
            _scope: Current scope dictionary

        Returns:
            Final resolved value

        Raises:
            IndirectionError: If any resolution step fails

        Examples:
            >>> scope = {"A": "B", "B": "C", "C": 100}
            >>> rt.resolve_indirection("A", 1, scope)  # @A
            "C"
            >>> rt.resolve_indirection("A", 2, scope)  # @@A
            100
            >>> # @@@A would be: A→"B"→"C"→100→get value of "100" (error: 100 is not a var name)
        """
        if levels < 1:
            raise IndirectionError(
                expr, f"indirection levels must be >= 1, got {levels}"
            )

        current_name = expr

        # Each level of indirection means:
        # 1. Get the value of the current variable (this gives us a new name)
        # 2. Use that name for the next level
        # After all levels, we have the final value (which might be a name or a value)

        for level in range(levels):
            # Validate the variable exists before dereferencing
            base_name, _ = _parse_subscripted_name(current_name)
            if base_name.startswith("^"):
                # Global: check via GlobalStorageBackend
                key = base_name[1:]
                if self._globals.get(key, ()) is None:
                    raise IndirectionError(
                        expr,
                        f"undefined variable in indirection chain at level {level}",
                        variable_name=current_name,
                    )
            else:
                # Local: check in _scope
                if base_name not in _scope:
                    raise IndirectionError(
                        expr,
                        f"undefined variable in indirection chain at level {level}",
                        variable_name=current_name,
                    )

            # Get the value of the current variable
            value = self.get_var(current_name, _scope)

            # Convert to string if not already (for use as variable name in next level)
            if not isinstance(value, str):
                value = str(value)

            if not value:
                raise IndirectionError(
                    expr,
                    f"empty value in indirection chain at level {level}",
                    variable_name=current_name,
                    variable_value=value,
                )

            # This value becomes the name for the next level
            current_name = value

        # After all indirection levels, get the final value
        # Validate final name exists
        base_name, _ = _parse_subscripted_name(current_name)
        if base_name.startswith("^"):
            key = base_name[1:]
            if self._globals.get(key, ()) is None:
                raise IndirectionError(
                    expr,
                    "undefined final target variable in indirection",
                    variable_name=current_name,
                )
        else:
            if base_name not in _scope:
                raise IndirectionError(
                    expr,
                    "undefined final target variable in indirection",
                    variable_name=current_name,
                )

        return self.get_var(current_name, _scope)

    def compile_pattern_indirect(self, pattern_str: str) -> str:
        """Compile MUMPS pattern string to regex at runtime.

        Spec 012 Phase 10 (T061): Implements pattern indirection by compiling
        pattern strings to regex at runtime.

        Uses the existing pattern compiler from analysis/pattern_compiler.py.

        Args:
            pattern_str: MUMPS pattern string like "1N.N", "1A.A"

        Returns:
            str: Regex pattern string for use with re.fullmatch()

        Raises:
            IndirectionError: If pattern is invalid or empty

        Examples:
            >>> rt.compile_pattern_indirect("1N.N")
            "^[0-9][0-9]*$"  # Matches one digit followed by any digits

            >>> rt.compile_pattern_indirect("1A.A")
            "^[A-Za-z][A-Za-z]*$"  # Matches one letter followed by any letters
        """
        # Import here to avoid circular dependency
        from m2py.analysis.pattern_compiler import (
            PatternCompileError,
            compile_pattern_to_regex,
        )

        if not pattern_str:
            raise IndirectionError(
                "",
                "empty pattern string in pattern indirection",
            )

        try:
            return compile_pattern_to_regex(pattern_str)
        except PatternCompileError as e:
            raise IndirectionError(
                pattern_str,
                f"invalid pattern: {e}",
            ) from e

    def parse_call_target(self, target_str: str) -> CallTarget:
        """Parse indirect DO/GOTO target into components.

        Spec 012 (T010): Parses target strings for indirect DO/GOTO.

        Formats supported:
        - "LABEL" → local label
        - "^ROUTINE" → entry label of external routine
        - "LABEL^ROUTINE" → specific label in external routine
        - "LABEL+N" → label with offset (N is integer)
        - "LABEL+N^ROUTINE" → external with offset

        Args:
            target_str: Target string from indirection resolution

        Returns:
            CallTarget(label, routine, offset)

        Raises:
            IndirectionError: If format is invalid

        Examples:
            >>> rt.parse_call_target("LABEL")
            CallTarget(label="LABEL", routine=None, offset=None)
            >>> rt.parse_call_target("LABEL^ROUTINE")
            CallTarget(label="LABEL", routine="ROUTINE", offset=None)
            >>> rt.parse_call_target("LABEL+5^ROUTINE")
            CallTarget(label="LABEL", routine="ROUTINE", offset=5)
        """
        if not target_str:
            raise IndirectionError("", "empty call target")

        target_str = target_str.strip()

        # Parse routine (^ROUTINE part)
        routine: Optional[str] = None
        if "^" in target_str:
            parts = target_str.split("^", 1)
            target_str = parts[0]  # Label part (may be empty)
            routine = parts[1]
            if not routine:
                raise IndirectionError(target_str, "empty routine name after ^")
            # Validate routine name
            if not _is_valid_varname(routine):
                raise IndirectionError(
                    target_str,
                    f"invalid routine name '{routine}'",
                )

        # Handle case where only ^ROUTINE is given (no label)
        if not target_str and routine:
            return CallTarget(label=None, routine=routine, offset=None)

        # Parse offset (LABEL+N part)
        offset: Optional[int] = None
        label: Optional[str] = None

        if "+" in target_str:
            parts = target_str.split("+", 1)
            label = parts[0] if parts[0] else None
            try:
                offset = int(parts[1])
            except ValueError:
                raise IndirectionError(
                    target_str,
                    f"invalid offset '{parts[1]}' - must be integer",
                )
        else:
            label = target_str if target_str else None

        # Validate label name if present
        if label and not _is_valid_varname(label):
            raise IndirectionError(
                target_str,
                f"invalid label name '{label}'",
            )

        return CallTarget(label=label, routine=routine, offset=offset)

    def execute_mumps(self, mumps_code: str, _scope: Dict[str, Any]) -> Any:
        """Execute MUMPS code string at runtime (XECUTE).

        Spec 012 (T011): Implements dynamic MUMPS code execution.

        Behavior:
        - Parses code as MUMPS using m2py parser
        - Generates Python via m2py codegen
        - Executes with exec() in shared _scope context
        - $TEST is NOT stacked (mutations visible to caller)
        - Supports all MUMPS constructs (depends on Specs 004-011)

        Note: Named execute_mumps() to distinguish from existing execute()
        which runs Python code. The contract specifies execute() but we
        need a different name to avoid shadowing the existing method.

        Args:
            mumps_code: MUMPS code to execute (one or more commands)
            _scope: Scope dictionary shared with caller

        Returns:
            Return value if code contains QUIT with value, else None

        Raises:
            SyntaxError: If MUMPS code has parse errors
            Any exception from executed code

        Examples:
            >>> scope = {}
            >>> rt.execute_mumps("S X=1", scope)
            >>> scope["X"]
            1

            >>> scope = {"Y": 5}
            >>> rt.execute_mumps("S X=Y+1", scope)
            >>> scope["X"]
            6
        """
        # Import here to avoid circular dependency
        from m2py.codegen import generate_python
        from m2py.codegen.helpers import m_compare, m_num, m_truth

        # Wrap the code in a routine format if it's just commands
        # MUMPS XECUTE executes commands without label context
        if not mumps_code.strip():
            return None

        # Check if code already has a label
        lines = mumps_code.strip().split("\n")
        first_line = lines[0].strip()

        # If first line starts with a command (space or tab), wrap it
        if first_line and (first_line[0].isspace() or first_line[0] in "SWRKQIDG"):
            # Wrap in a temporary routine with label
            wrapped_code = "XECUTE " + mumps_code.strip() + " Q"
        else:
            # Already has structure, use as-is
            wrapped_code = mumps_code

        # Generate Python code
        try:
            python_code = generate_python(wrapped_code, routine_name="XECUTE")
        except Exception as e:
            # T067: Provide useful context in XECUTE syntax error message
            # Include the original MUMPS code so user knows what failed
            error_msg = f"XECUTE parse error in '{mumps_code}': {e}"
            raise SyntaxError(error_msg) from e

        # Create execution namespace with shared scope
        namespace: Dict[str, Any] = {
            "_rt": self,
            "_scope": _scope,
            "_test": _scope.get("_test", False),
            "m_num": m_num,
            "m_truth": m_truth,
            "m_compare": m_compare,
            "MArray": MArray,
        }

        # Copy scope variables into namespace for direct access
        # Generated code uses _scope.get("VAR", "") pattern, so this works
        namespace.update(_scope)

        try:
            # Execute the generated code
            exec(python_code, namespace)

            # The generated code defines a function, we need to call it
            if "XECUTE" in namespace and callable(namespace["XECUTE"]):
                result = namespace["XECUTE"](self, _scope=_scope)
            else:
                result = None

            # Sync $TEST back - store in both _scope and self._test
            # Spec 012 Phase 6 (T038): XECUTE does NOT stack $TEST
            # The modified $TEST must be visible to caller
            if "_test" in namespace:
                _scope["_test"] = namespace["_test"]
                self._test = namespace["_test"]

            # Sync any modified variables back to _scope
            # (Generated code modifies _scope directly via _scope["X"] = value)

            return result

        except Exception:
            # Re-raise with context
            raise

    def execute(
        self,
        python_code: str,
        *,
        capture_output: bool = True,
        entry_point: str | None = None,
        entry_args: tuple | None = None,
    ) -> ExecutionResult:
        """Execute generated Python code.

        Creates an isolated namespace for execution, injects the runtime
        and helpers, executes module-level code (defines functions), then
        calls the entry point function.

        Args:
            python_code: Generated Python source code
            capture_output: If True, capture WRITE output
            entry_point: Label to execute (default: first label)
            entry_args: Optional tuple of arguments to pass to entry point

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

            # Set up runtime context for $TEXT function support
            # These are module-level variables set by generated code
            if "_routine_name" in namespace:
                self._current_routine = namespace["_routine_name"]
            if "_source_lines" in namespace:
                self._current_source_lines = namespace["_source_lines"]
            if "_label_lines" in namespace:
                self._current_label_lines = namespace["_label_lines"]

            # Find entry point
            if entry_point is None:
                # Find first function defined (look for def statements)
                entry_point = self._find_first_function(python_code)

            # Call entry point if found
            # Phase 13 (T076): Entry point functions now require _rt as first parameter
            if entry_point and entry_point in namespace:
                func = namespace[entry_point]
                if callable(func):
                    if entry_args:
                        func(self, *entry_args)
                    else:
                        func(self)

            # Get final $TEST value
            test_value = namespace.get("_test", False)

            return ExecutionResult(
                output=self.get_output() if capture_output else "",
                success=True,
                error=None,
                test_value=bool(test_value),
            )

        except SystemExit:
            # Spec 011 Phase 19: HALT command raises SystemExit(0)
            # This is a normal termination, not an error
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
    # Spec 010: $ORDER and $QUERY helpers
    "m_order",
    "m_order_global",
    "m_query",
    "m_query_global",
    # Spec 010: $SELECT helper
    "_raise_select_false",
    # Spec 010: $PIECE and $EXTRACT helpers (Phase 5)
    "m_piece",
    "m_extract",
    # Spec 010: $GET helpers (Phase 6)
    "m_get",
    "m_get_global",
    # Spec 010: $FIND helper (Phase 7)
    "m_find",
    # Spec 011: String comparison and pattern match helpers
    # Note: Contains ([) and Follows (]) are inlined; only sorts-after needs runtime
    "m_sorts_after",
    "m_pattern_match",
    # Spec 011 Phase 20: READ command helpers
    "m_read_timeout",
    "m_read_char",
    # Spec 012: Indirection & XECUTE
    "IndirectionError",
    "CallTarget",
]
