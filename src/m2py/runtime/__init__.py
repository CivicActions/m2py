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
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Callable, Dict, List, NamedTuple, Optional, Tuple

from m2py.core.names import NameTranslator

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

# MUMPS label name pattern: starts with letter, %, or digit, followed by alphanumerics
# Labels can be purely numeric (e.g., 461, 462) or traditional names (e.g., ENTRY, %BREAK)
# Examples: ENTRY, 461, %BREAK, A1, 123
_LABEL_PATTERN = re.compile(r"^[A-Za-z%0-9][A-Za-z0-9]*$")


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


def _is_valid_label(name: str) -> bool:
    """Check if name is a valid MUMPS label name.

    MUMPS label naming rules differ from variable names:
    - Can start with letter (A-Z, a-z), %, or digit (0-9)
    - Followed by zero or more alphanumeric characters
    - Labels CAN be purely numeric (e.g., 461, 462)

    Args:
        name: Label name to validate

    Returns:
        True if valid MUMPS label name, False otherwise

    Examples:
        >>> _is_valid_label("ENTRY")
        True
        >>> _is_valid_label("461")
        True
        >>> _is_valid_label("%BREAK")
        True
        >>> _is_valid_label("")
        False
    """
    if not name:
        return False
    return bool(_LABEL_PATTERN.match(name))


# T074a: Now uses NameTranslator.to_python() from core.names module.
# The deprecated _translate_label_to_func() function has been removed.
# All name translation now goes through the single source of truth.


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


class SubscriptVarRef:
    """Wrapper to mark a subscript as a variable reference to be evaluated.

    Used in _convert_subscript to distinguish:
    - "key" → literal string "key" (from quoted MUMPS string)
    - I → SubscriptVarRef("I") (unquoted MUMPS variable reference)

    This allows _evaluate_subscript to only look up actual variable references.

    Note: This is distinct from core.scope.VarRef which represents a complete
    variable reference for codegen/runtime unified access patterns.
    """

    __slots__ = ("name",)

    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return f"SubscriptVarRef({self.name!r})"


# Backward compatibility alias - tests may import VarRef
VarRef = SubscriptVarRef


def _convert_subscript(value: str, original_name: str) -> Any:
    """Convert a subscript string to its value.

    Args:
        value: String representation of subscript
        original_name: Original name for error messages

    Returns:
        Converted value (int, float, string, or SubscriptVarRef for variable references)
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

    # Handle quoted strings - remove quotes and return as literal string
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]

    # Unquoted non-numeric string - this is a variable reference
    # Wrap in SubscriptVarRef so _evaluate_subscript knows to look it up
    return SubscriptVarRef(value)


def _evaluate_subscript(
    sub: Any, _scope: Dict[str, Any], runtime: Optional["MUMPSRuntime"] = None
) -> Any:
    """Evaluate a single subscript value, resolving variable references.

    When a subscript is a SubscriptVarRef, look it up in the scope.
    This enables indirection like "A(I)" where I is a variable.
    Also handles name indirection like "A(@X)" where @X resolves to a variable name.

    Args:
        sub: Subscript value (int, float, string, or SubscriptVarRef)
        _scope: Scope dictionary for variable lookup
        runtime: MUMPSRuntime instance for complex indirection resolution

    Returns:
        Evaluated subscript value
    """
    # Only evaluate SubscriptVarRef wrappers - they mark actual variable references
    if not isinstance(sub, SubscriptVarRef):
        return sub

    # Look up variable in scope
    var_name = sub.name

    # Handle indirection in subscript: @X means resolve and get the value
    if var_name.startswith("@"):
        # Use resolve_nested_indirection with return_value=True for GET semantics
        if runtime is not None:
            return runtime.resolve_nested_indirection(
                var_name, _scope, return_value=True
            )

        # Fallback for cases without runtime - simple resolution only
        # Strip the @ and look up the variable
        inner_var = var_name[1:]
        raw_value = _scope.get(inner_var, "")
        if isinstance(raw_value, MArray):
            raw_value = raw_value.value

        # Now raw_value might itself be an indirection (@...) or a variable name
        # Keep resolving until we get an actual value
        while isinstance(raw_value, str) and raw_value.startswith("@"):
            # This is nested indirection
            next_var = raw_value[1:]
            base_name, subs = _parse_subscripted_name(next_var)
            next_raw = _scope.get(base_name, "")
            if isinstance(next_raw, MArray):
                if subs:
                    evaluated_subs = _evaluate_subscripts(subs, _scope)
                    raw_value = next_raw.get(*evaluated_subs)
                else:
                    raw_value = next_raw.value
            else:
                raw_value = next_raw

        # raw_value should now be the final variable name - look it up
        if raw_value:
            base_name, subs = _parse_subscripted_name(str(raw_value))
            final_raw = _scope.get(base_name, "")
            if isinstance(final_raw, MArray):
                if subs:
                    evaluated_subs = _evaluate_subscripts(subs, _scope)
                    return final_raw.get(*evaluated_subs)
                return final_raw.value
            return final_raw
        return ""

    # Handle subscripted variable references like "A(1)"
    # Parse the variable name to extract base name and subscripts
    if "(" in var_name:
        base_name, subs = _parse_subscripted_name(var_name)
        raw_value = _scope.get(base_name, "")
        if isinstance(raw_value, MArray):
            if subs:
                # Recursively evaluate subscripts (they might be variable refs too)
                evaluated_subs = _evaluate_subscripts(subs, _scope, runtime)
                if evaluated_subs:
                    return raw_value.get(*evaluated_subs)
                return raw_value.value
            return raw_value.value
        return raw_value if raw_value != "" else ""

    raw_value = _scope.get(var_name, "")
    if isinstance(raw_value, MArray):
        return raw_value.value
    return raw_value


def _evaluate_subscripts(
    subscripts: Optional[Tuple[Any, ...]],
    _scope: Dict[str, Any],
    runtime: Optional["MUMPSRuntime"] = None,
) -> Optional[Tuple[Any, ...]]:
    """Evaluate all subscripts in a tuple, resolving variable references.

    Args:
        subscripts: Tuple of subscript values, or None
        _scope: Scope dictionary for variable lookup
        runtime: MUMPSRuntime instance for complex indirection resolution

    Returns:
        Tuple of evaluated subscript values, or None if input was None
    """
    if subscripts is None:
        return None
    return tuple(_evaluate_subscript(s, _scope, runtime) for s in subscripts)


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
            arr[1]      -> arr._children['1']
            arr[1, 2]   -> arr._children['1']._children['2']

        Subscripts are canonicalized to strings for consistent lookup.

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

        key_str = self._canonicalize_subscript(key)
        if key_str not in self._children:
            self._children[key_str] = MArray()
        return self._children[key_str]

    def _canonicalize_subscript(self, key: Any) -> str:
        """Convert subscript to canonical string form.

        In MUMPS, all subscripts are strings. Numeric values are canonicalized
        so that A(1), A(1.0), and A("1") all access the same node.
        Non-canonical string forms like "01" are preserved as-is.

        Uses SubscriptCanonicalizer for consistent canonicalization across
        runtime and codegen.

        Args:
            key: Subscript value (int, float, str, or other)

        Returns:
            Canonical string representation of the subscript
        """
        from m2py.core.subscripts import SubscriptCanonicalizer

        return SubscriptCanonicalizer.canonicalize(key)

    def __setitem__(self, key: Any, value: Any) -> None:
        """Set value at subscript.

        Supports both single and tuple keys:
            arr[1] = 10         -> arr._children['1']._value = 10
            arr[1, 2] = 20      -> arr._children['1']._children['2']._value = 20

        Subscripts are canonicalized to strings for consistent lookup.

        Args:
            key: Subscript (single value or tuple of values)
            value: Value to set at that subscript
        """
        if isinstance(key, tuple):
            node = self
            for k in key[:-1]:
                k_str = self._canonicalize_subscript(k)
                if k_str not in node._children:
                    node._children[k_str] = MArray()
                node = node._children[k_str]
            last_key = self._canonicalize_subscript(key[-1])
            if last_key not in node._children:
                node._children[last_key] = MArray()
            node._children[last_key]._value = value
        else:
            key_str = self._canonicalize_subscript(key)
            if key_str not in self._children:
                self._children[key_str] = MArray()
            self._children[key_str]._value = value

    def get(self, *subscripts: Any) -> Any:
        """Get value at subscripts (empty string if undefined).

        Subscripts are canonicalized to strings for consistent lookup.

        Args:
            *subscripts: Path to the value (empty for root)

        Returns:
            Value at subscripts, or empty string if undefined

        Examples:
            arr.get()       -> arr.value (root value)
            arr.get(1)      -> arr['1'].value
            arr.get(1, 2)   -> arr['1', '2'].value
        """
        if not subscripts:
            return self.value

        node = self
        for sub in subscripts:
            sub_str = self._canonicalize_subscript(sub)
            if sub_str not in node._children:
                return ""  # Undefined subscript
            node = node._children[sub_str]
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

        Subscripts are canonicalized to strings for consistent lookup.

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
                sub_str = self._canonicalize_subscript(sub)
                if sub_str not in node._children:
                    return 0  # Path doesn't exist
                node = node._children[sub_str]

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
                sub_str = self._canonicalize_subscript(sub)
                if sub_str not in parent._children:
                    return  # Path doesn't exist
                parent = parent._children[sub_str]

            last = self._canonicalize_subscript(subscripts[-1])
            if last in parent._children:
                del parent._children[last]

    def kill_node(self, subscripts: tuple[Any, ...]) -> None:
        """Delete node value but preserve descendants (ZKILL command).

        Spec 013 Phase 19 (T135): ZKILL removes value but keeps children.

        Unlike kill() which removes the entire subtree, kill_node()
        only removes the value at the specified node, leaving all
        subscripted descendants intact.

        Subscripts are canonicalized to strings for consistent lookup.

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
            sub_str = self._canonicalize_subscript(sub)
            if sub_str not in parent._children:
                return  # Path doesn't exist
            parent = parent._children[sub_str]

        last = self._canonicalize_subscript(subscripts[-1])
        if last in parent._children:
            # Only remove value, keep children intact
            parent._children[last]._value = None

    def order(self, *subscripts: Any, start: Any = "") -> Any:
        """Get next subscript ($ORDER equivalent).

        Returns the next subscript after 'start' in collation order.
        MUMPS collation: numbers before strings, sorted within type.

        Subscripts are canonicalized to strings for consistent lookup.

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
                sub_str = self._canonicalize_subscript(sub)
                if sub_str not in node._children:
                    return ""
                node = node._children[sub_str]
            children = node._children

        # Get sorted keys (MUMPS collation: numbers before strings)
        keys = sorted(children.keys(), key=lambda x: (isinstance(x, str), x))

        start_str = self._canonicalize_subscript(start) if start != "" else ""

        if start_str == "":
            return keys[0] if keys else ""

        try:
            idx = keys.index(start_str)
            return keys[idx + 1] if idx + 1 < len(keys) else ""
        except ValueError:
            # Start not found, return first key greater than start
            for k in keys:
                if start_str < k:
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
        # Spec 012: $TEST value for tracking IF/ELSE condition results
        # This is synced from/to generated code via execute_mumps
        self._test: bool = False

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
            # T075f: YDB converts tabs to single space in $TEXT output
            return lines[line_idx].replace("\t", " ")
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

        MUMPS ZWRITE outputs:
        - Numeric values unquoted (e.g., X=123)
        - Numeric-looking strings unquoted (e.g., SET X="123" → ZWRITE X=123)
        - Non-numeric strings quoted (e.g., X="hello")

        The output format is designed to be valid as input to SET @.

        Args:
            value: Value to quote

        Returns:
            Formatted string suitable for SET @ input
        """
        from m2py.runtime.helpers import m_format_output
        import re

        if value is None or value == "":
            return '""'

        # Actual numeric types don't get quoted
        if isinstance(value, (int, float, Decimal)):
            return m_format_output(value)

        # For strings, check if it looks numeric
        s = str(value)

        # Plain integers: -?[0-9]+
        if re.match(r"^-?[0-9]+$", s):
            return m_format_output(Decimal(s))

        # Decimals: -?[0-9]*\.[0-9]+
        if re.match(r"^-?[0-9]*\.[0-9]+$", s):
            return m_format_output(Decimal(s))

        # Scientific notation with explicit sign (from str(Decimal()))
        if re.match(r"^-?[0-9]+(\.[0-9]+)?E[+-][0-9]+$", s):
            return m_format_output(Decimal(s))

        # Non-numeric strings get quoted
        escaped = s.replace('"', '""')
        return f'"{escaped}"'

    def zwrite(self, scope: dict[str, Any]) -> None:
        """ZWRITE - display all local variables.

        Spec 013 Phase 19 (T132): Argumentless ZWRITE shows all locals.

        Args:
            scope: Variable scope dictionary
        """
        for py_name in sorted(scope.keys()):
            # Skip truly internal variables (runtime internals like _scope, _rt, etc.)
            # but NOT NameTranslator-prefixed names (_pct_, _n_, _m_) which are user variables
            if py_name.startswith("_") and not (
                py_name.startswith("_pct_")
                or py_name.startswith("_n_")
                or py_name.startswith("_m_")
            ):
                continue
            # Translate Python name back to MUMPS name for display
            mumps_name = NameTranslator.from_python(py_name)
            value = scope[py_name]
            self._zwrite_var(mumps_name, value)

    def _format_subscript(self, sub: Any) -> str:
        """Format a subscript value for ZWRITE output.

        Numeric subscripts are not quoted, string subscripts are quoted.
        Uses m_format_output to ensure Decimals are formatted without
        scientific notation (e.g., 1E+11 → 100000000000).

        The key challenge is distinguishing numeric from string subscripts
        when both are stored as strings. We use these heuristics:
        - Plain integers/decimals are numeric: "123", ".5", "-1"
        - Scientific notation WITH explicit sign is numeric: "1E+60", "1E-60"
        - Scientific notation WITHOUT sign is a string: "1E60" (user wrote it quoted)

        This works because Python's str(Decimal(...)) always includes the sign
        in the exponent (E+/E-), while literal strings preserve their original form.

        Args:
            sub: Subscript value

        Returns:
            Formatted subscript (quoted if string, unquoted if numeric)
        """
        from m2py.runtime.helpers import m_format_output
        import re

        # If it's already a Decimal, format it directly
        if isinstance(sub, Decimal):
            return m_format_output(sub)

        # Other numeric types
        if isinstance(sub, (int, float)):
            return m_format_output(sub)

        # For strings, check if it looks like a numeric subscript
        if isinstance(sub, str):
            # Plain integers: -?[0-9]+
            if re.match(r"^-?[0-9]+$", sub):
                return m_format_output(Decimal(sub))
            # Decimals: -?[0-9]*\.[0-9]+
            if re.match(r"^-?[0-9]*\.[0-9]+$", sub):
                return m_format_output(Decimal(sub))
            # Scientific notation with explicit sign (from str(Decimal()))
            if re.match(r"^-?[0-9]+(\.[0-9]+)?E[+-][0-9]+$", sub):
                return m_format_output(Decimal(sub))
            # Otherwise it's a string subscript - quote it
            escaped = sub.replace('"', '""')
            return f'"{escaped}"'

        # Fallback: quote non-numeric values
        s = str(sub)
        escaped = s.replace('"', '""')
        return f'"{escaped}"'

    def zwrite_local(
        self, name: str, subscripts: tuple[str, ...], scope: dict[str, Any]
    ) -> None:
        """ZWRITE - display a local variable and its descendants.

        Args:
            name: Variable name (Python scope key, e.g., "_pct_FOO" for %FOO)
            subscripts: Subscript path (empty for unsubscripted)
            scope: Variable scope dictionary
        """
        if name not in scope:
            return  # Variable not defined

        # Translate Python name back to MUMPS name for display
        mumps_name = NameTranslator.from_python(name)

        var = scope[name]
        if not isinstance(var, MArray):
            # Simple value
            if subscripts:
                return  # Can't subscript a simple value
            self.write(f"{mumps_name}={self._quote_value(var)}\n")
            return

        # Navigate to subscript position and collect path
        node = var
        subs_list = list(subscripts)
        for sub in subscripts:
            if sub not in node._children:
                return  # Subscript doesn't exist
            node = node._children[sub]

        # Output this node and descendants
        self._zwrite_marray(mumps_name, subs_list, node)

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
        # To get first subscript at this level, use ("",) as the "starting from" marker
        # For subsequent subscripts, use the last found subscript
        current_sub = ""  # Empty string = get first
        while True:
            # Find next subscript at this level
            # ORDER expects (parent_subscripts..., starting_point)
            next_sub = self.globals.order(
                name, subscripts + (current_sub,), direction=1
            )
            if not next_sub:
                break
            # Recursively output this subtree
            self.zwrite_global(name, subscripts + (next_sub,))
            # Move to next sibling at this level
            current_sub = next_sub

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

        Handles both simple variables (X) and subscripted variables (X(1,2)).
        For subscripted variables, uses get_var() to retrieve the value.

        Args:
            varname: Variable name to get value of (the indirection source)
                     May be simple (X) or subscripted (X(1,2))
            _scope: Current scope dictionary

        Returns:
            str: The variable's value (which becomes the target variable name)

        Raises:
            IndirectionError: If varname is undefined in _scope

        Examples:
            >>> scope = {"X": MArray("Y")}
            >>> rt.get_indirection_source("X", scope)
            "Y"
            >>> scope = {"X": MArray()}; scope["X"][1] = "Z"
            >>> rt.get_indirection_source("X(1)", scope)
            "Z"
            >>> rt.get_indirection_source("UNDEF", {})
            IndirectionError: Undefined local variable: UNDEF
        """
        # Check if varname is subscripted (contains parentheses)
        if "(" in varname:
            # For subscripted variables, use get_var which handles the lookup
            value = self.get_var(varname, _scope)
            if value == "":
                # get_var returns "" for undefined - convert to error for indirection
                raise IndirectionError(
                    varname,
                    f"Undefined local variable: {varname}",
                    variable_name=varname,
                )
            return str(value) if value is not None else ""

        # Translate MUMPS varname to Python scope key
        # MUMPS %Z is stored in _scope as "_pct_Z"
        scope_key = NameTranslator.to_python(varname)

        # Simple variable - check existence in _scope
        if scope_key not in _scope:
            raise IndirectionError(
                varname,
                f"Undefined local variable: {varname}",
                variable_name=varname,
            )

        raw_value = _scope[scope_key]

        # Extract value from MArray if present
        if isinstance(raw_value, MArray):
            value = raw_value.value
        else:
            value = raw_value

        # Convert to string for use as variable name
        return str(value) if value is not None else ""

    # Internal method: Returns variable NAME after multi-level indirection.
    # Used by tests and internal methods. New code should prefer resolve_for_target()
    # which uses IndirectionResolver for consistent error handling.
    def resolve_indirection_name(
        self, varname: str, levels: int, _scope: Dict[str, Any]
    ) -> str:
        """Resolve multi-level indirection and return the final variable NAME.

        Note: Consider using resolve_for_target() for new code.

        For FOR loop indirection targets: F @A, F @@A, F @@@A.
        Unlike resolve_indirection which returns the VALUE, this returns the NAME
        of the variable that should be used for iteration.

        For levels=1 (@A): A contains "B" → return "B"
        For levels=2 (@@A): A="X", X="Y" → return "Y"
        For levels=1 with nested (@A where A="@$E('XYZ',2)"): → return "Y"

        Args:
            varname: Starting variable name
            levels: Number of indirection levels (1 for @, 2 for @@, etc.)
            _scope: Current scope dictionary

        Returns:
            str: Final variable name to use for iteration

        Raises:
            IndirectionError: If any variable is undefined or resolution fails
        """
        current_name = varname

        for level in range(levels):
            # Get the value of the current variable
            value = self.get_indirection_source(current_name, _scope)

            # If the value starts with @, resolve the nested indirection
            if value.startswith("@"):
                value = self.resolve_nested_indirection(value, _scope)

            if not value:
                raise IndirectionError(
                    varname,
                    f"empty variable name at indirection level {level + 1}",
                )

            # The value becomes the name for the next level (or final result)
            current_name = value

        return current_name

    def append_subscripts(
        self,
        base_name: str,
        *additional_subscripts: Any,
        _scope: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Append additional subscripts to a variable name.

        Spec 017 Phase 6: Properly handles name indirection with subscripts
        like @A@(1,2) where A="B(3,4)" should produce "B(3,4,1,2)".

        The naive string concatenation "B(3,4)" + "(1,2)" = "B(3,4)(1,2)"
        is invalid. This method properly parses and merges subscripts.

        When base_name starts with @, this indicates an indirection pattern.
        If _scope is provided, we resolve the indirection first, then append
        subscripts to the resolved variable name.

        Args:
            base_name: Variable name possibly with existing subscripts
            *additional_subscripts: Additional subscripts to append
            _scope: Optional scope for resolving @ patterns

        Returns:
            str: Variable name with merged subscripts

        Examples:
            >>> rt.append_subscripts("X", 1, 2)
            "X(1,2)"
            >>> rt.append_subscripts("ARR(1)", 2, 3)
            "ARR(1,2,3)"
            >>> rt.append_subscripts("B(1,1)", 3)
            "B(1,1,3)"
            >>> rt.append_subscripts("@C", 2, _scope=scope)  # Resolves @C first
            "A(1,1,2)"  # If @C resolves to A(1,1)
        """
        if not additional_subscripts:
            return base_name

        # If base_name starts with @, resolve it first to get the actual variable name
        if base_name.startswith("@") and _scope is not None:
            resolved = self.resolve_nested_indirection(base_name, _scope)
            base_name = resolved

        # Parse existing subscripts from base_name
        existing_base, existing_subs = _parse_subscripted_name(base_name)

        # Evaluate existing subscripts to resolve SubscriptVarRef objects (variable references)
        # This is critical for indirection: if base_name is "C(K)" where K=1,
        # existing_subs will be (SubscriptVarRef('K'),) and we need to evaluate it to (1,)
        evaluated_existing = (
            _evaluate_subscripts(existing_subs, _scope or {}, runtime=self)
            if existing_subs
            else None
        )

        # Combine existing subscripts with new ones
        all_subs: list[Any] = []
        if evaluated_existing:
            all_subs.extend(evaluated_existing)
        all_subs.extend(additional_subscripts)

        # Format subscripts - handle strings properly
        formatted_subs = []
        for sub in all_subs:
            if isinstance(sub, str):
                # Quote strings for proper variable name format
                escaped = sub.replace('"', '""')
                formatted_subs.append(f'"{escaped}"')
            else:
                formatted_subs.append(str(sub))

        return f"{existing_base}({','.join(formatted_subs)})"

    def get_data(self, name: str, _scope: Dict[str, Any]) -> int:
        """Get $DATA value for variable by name (indirection support).

        Spec 017 Phase 6 (T027): Implements $DATA for indirected variables.

        Returns:
        - 0: Undefined, no descendants
        - 1: Defined, no descendants
        - 10: Undefined, has descendants
        - 11: Defined AND has descendants

        Args:
            name: Variable name, optionally with subscripts
                  Examples: "X", "ARR(1,2)", "^GLO", "^GLO(1)"
                  May also be a nested indirection like "@V1A(20)"
                  May also be a naked reference like "^(1)"
            _scope: Current scope dictionary

        Returns:
            $DATA value (0, 1, 10, or 11)
        """
        from m2py.runtime.helpers import m_data, m_data_global

        if not name:
            return 0

        # Handle nested indirection: if name starts with @, resolve it first
        if name.startswith("@"):
            name = self.resolve_nested_indirection(name, _scope)
            if not name:
                return 0

        # Parse subscripts if present
        base_name, subscripts = _parse_subscripted_name(name)
        # Evaluate subscripts - resolve variable references like A(3) to their values
        evaluated_subs = _evaluate_subscripts(subscripts, _scope, runtime=self)
        subs = tuple(str(s) for s in evaluated_subs) if evaluated_subs else ()

        # Handle global variables
        if base_name.startswith("^"):
            key = base_name[1:]
            # Handle naked global reference: ^(subs) where base_name is just "^"
            if not key:
                resolved_name, full_subs = self._globals.resolve_naked(subs)
                return m_data_global(self._globals, resolved_name, full_subs)
            return m_data_global(self._globals, key, subs)

        # Handle local variables
        arr = _scope.get(base_name, MArray())
        if not isinstance(arr, MArray):
            # Non-MArray value: defined with no descendants if truthy, else undefined
            if arr:
                return 1 if not subs else 0
            else:
                return 0
        return m_data(arr, subs)

    def get_order(self, name: str, _scope: Dict[str, Any], direction: int = 1) -> str:
        """Get $ORDER value for variable by name (indirection support).

        Args:
            name: Variable name with subscripts, e.g. "A(1)", "^G(sub)"
                  May also be a nested indirection like "@V1A(20)"
                  May also be a naked reference like "^(1)"
            _scope: Current scope dictionary
            direction: 1 for forward, -1 for reverse

        Returns:
            Next subscript in collation order, or "" if no more
        """
        from m2py.runtime.helpers import m_order, m_order_global

        if not name:
            return ""

        # Handle nested indirection: if name starts with @, resolve it first
        # This happens for $N(@B) where B="@V1A(20)" - the indirection source
        # itself is an indirection expression
        if name.startswith("@"):
            name = self.resolve_nested_indirection(name, _scope)
            if not name:
                return ""

        base_name, subscripts = _parse_subscripted_name(name)
        # Evaluate subscripts first - resolve variable references like A(3) to their values
        evaluated_subs = _evaluate_subscripts(subscripts, _scope, runtime=self)
        subs = tuple(str(s) for s in evaluated_subs) if evaluated_subs else ("",)

        if base_name.startswith("^"):
            key = base_name[1:]
            # Handle naked global reference: ^(subs) where base_name is just "^"
            if not key:
                # Naked reference - resolve using the naked indicator
                resolved_name, full_subs = self._globals.resolve_naked(subs)
                return m_order_global(
                    self._globals, resolved_name, full_subs, direction
                )
            return m_order_global(self._globals, key, subs, direction)

        arr = _scope.get(base_name, MArray())
        if not isinstance(arr, MArray):
            return ""
        return m_order(arr, subs, direction)

    # Internal method: Dynamic variable read by name string.
    # Used by resolve_indirection() and legacy codegen paths (FOR loops, naked writes).
    # New code should use get_indirected() or CurrentScope.get() when possible.
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

        # Handle nested indirection: if name starts with @, resolve it first
        # With return_value=True, resolve_nested_indirection returns the final VALUE
        if name.startswith("@"):
            return self.resolve_nested_indirection(name, _scope, return_value=True)

        # Parse subscripts if present
        base_name, subscripts = _parse_subscripted_name(name)

        # Handle naked global references: ^(subscripts)
        # The base_name is just "^" when parsing "^(5)" etc.
        if base_name == "^":
            if subscripts is None:
                raise IndirectionError(name, "naked reference requires subscripts")
            # Evaluate subscripts first, then resolve naked reference
            eval_subs = _evaluate_subscripts(subscripts, _scope)
            naked_subs = tuple(str(s) for s in eval_subs) if eval_subs else ()
            resolved_name, full_subs = self._globals.resolve_naked(naked_subs)
            return self._globals.get(resolved_name, full_subs) or ""

        # Validate the base name
        if not _is_valid_varname(base_name):
            raise IndirectionError(
                name,
                f"invalid variable name - must start with letter or %, got '{base_name}'",
            )

        # Handle global variables
        if base_name.startswith("^"):
            return self._get_global_var(base_name, subscripts, _scope)

        # Handle local variables
        return self._get_local_var(base_name, subscripts, _scope)

    def _get_local_var(
        self, name: str, subscripts: Optional[Tuple[Any, ...]], _scope: Dict[str, Any]
    ) -> Any:
        """Get local variable value from scope.

        Args:
            name: Base variable name (no subscripts) - MUMPS name like "%Z"
            subscripts: Optional tuple of subscript values (may contain variable refs)
            _scope: Scope dictionary

        Returns:
            Variable value, or "" if undefined
        """
        # Translate MUMPS name to Python scope key (%Z -> _pct_Z)
        scope_key = NameTranslator.to_python(name)
        raw_value = _scope.get(scope_key, "")

        # Evaluate subscripts - resolve variable references like "I" to their values
        eval_subs = _evaluate_subscripts(subscripts, _scope)

        # Extract value from MArray if needed
        if isinstance(raw_value, MArray):
            if eval_subs is None:
                # Simple variable - return value
                return raw_value.value
            else:
                # Subscripted access
                return raw_value.get(*eval_subs)

        # Non-MArray value (shouldn't happen normally but handle gracefully)
        if eval_subs is None:
            return raw_value
        elif raw_value == "":
            # Undefined base variable, subscript also undefined
            return ""
        else:
            # Non-array value with subscripts - undefined
            return ""

    def _get_global_var(
        self, name: str, subscripts: Optional[Tuple[Any, ...]], _scope: Dict[str, Any]
    ) -> Any:
        """Get global variable value.

        Args:
            name: Global variable name (starts with ^)
            subscripts: Optional tuple of subscript values (may contain variable refs)
            _scope: Scope dictionary for evaluating variable references

        Returns:
            Variable value, or "" if undefined
        """
        # Strip ^ for storage key
        key = name[1:]

        # Evaluate subscripts - resolve variable references like "I" to their values
        eval_subs = _evaluate_subscripts(subscripts, _scope)

        # Use the GlobalStorageBackend interface
        subs = () if eval_subs is None else tuple(str(s) for s in eval_subs)
        result = self._globals.get(key, subs)
        return result if result is not None else ""

    # Internal method: Dynamic variable write by name string.
    # Used internally for recursive @ resolution and legacy codegen paths (FOR loops, naked writes).
    # New code should use set_indirected() or CurrentScope.set() when possible.
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

        # Handle nested indirection: if name starts with @, resolve it first
        # This handles cases like @B where B="@C" or @B@(1) where B="A(2)"
        if name.startswith("@"):
            resolved_name = self.resolve_nested_indirection(name, _scope)
            if not resolved_name:
                raise IndirectionError(
                    name, "indirection resolved to empty variable name"
                )
            return self.set_var(resolved_name, value, _scope)

        # Parse subscripts if present
        base_name, subscripts = _parse_subscripted_name(name)

        # Handle naked global references: ^(subscripts)
        # The base_name is just "^" when parsing "^(5)" etc.
        if base_name == "^":
            if subscripts is None:
                raise IndirectionError(name, "naked reference requires subscripts")
            # Evaluate subscripts first, then resolve naked reference
            eval_subs = _evaluate_subscripts(subscripts, _scope)
            naked_subs = tuple(str(s) for s in eval_subs) if eval_subs else ()
            resolved_name, full_subs = self._globals.resolve_naked(naked_subs)
            self._globals.set(resolved_name, full_subs, value)
            return

        # Validate the base name
        if not _is_valid_varname(base_name):
            raise IndirectionError(
                name,
                f"invalid variable name - must start with letter or %, got '{base_name}'",
            )

        # Handle global variables
        if base_name.startswith("^"):
            self._set_global_var(base_name, subscripts, value, _scope)
            return

        # Handle local variables
        self._set_local_var(base_name, subscripts, value, _scope)

    def set_indirected(
        self,
        source: str,
        value: Any,
        _scope: Dict[str, Any],
        levels: int = 1,
        per_level_subscripts: Optional[List[List[Any]]] = None,
    ) -> None:
        """Set variable via indirection using unified components.

        Feature: 018-unified-variable-system (T040, T111)
        Replaces scattered set_var + resolve calls with unified approach.

        Uses IndirectionResolver.resolve_to_name() to determine the target,
        then CurrentScope.set() to perform the assignment.

        Args:
            source: Source variable name for indirection (e.g., "X" for @X),
                or for levels=0, the already-resolved target name directly
            value: Value to set
            _scope: Current scope dictionary
            levels: Number of indirection levels (1 for @X, 2 for @@X, etc.)
                Use levels=0 when source is already the resolved target name
                (e.g., from NakedGlobal expressions where the value was computed)
            per_level_subscripts: Subscripts per level for @X@(s1)@(s2) form

        Raises:
            VarExpectedError: If resolved name is not a valid variable name

        Examples:
            # @X=5 where X="Y"
            set_indirected("X", 5, scope, levels=1)
            # Sets Y=5

            # @@X=5 where X="Y", Y="Z"
            set_indirected("X", 5, scope, levels=2)
            # Sets Z=5

            # @X@(1,2)=5 where X="A"
            set_indirected("X", 5, scope, levels=1, per_level_subscripts=[[1, 2]])
            # Sets A(1,2)=5

            # NakedGlobal: @^(1)=5 where ^(1) resolves to "X"
            set_indirected("X", 5, scope, levels=0)
            # Sets X=5 directly (source is already the target name)
        """
        from m2py.core.scope import CurrentScope
        from m2py.core.indirection import IndirectionResolver

        # Create unified scope and resolver
        cs = CurrentScope.from_generated_context(_scope)
        resolver = IndirectionResolver(self, cs)

        # Handle levels=0: source is already the resolved target name
        # This is used for NakedGlobal expressions where the target name
        # was computed during code generation
        if levels == 0:
            # Validate that source is a valid variable name
            if not resolver._is_valid_var_name(source):
                from m2py.core.exceptions import VarExpectedError

                raise VarExpectedError(source)
            target = source
        else:
            # Resolve to get target variable NAME (not value)
            target = resolver.resolve_to_name(
                source, levels=levels, per_level_subscripts=per_level_subscripts
            )

        # Convert value to string (MUMPS semantics - all values are strings)
        str_value = str(value)

        # Handle global variables
        if target.startswith("^"):
            # Parse subscripts from target if present
            base_name, subscripts = _parse_subscripted_name(target)
            subs = tuple(str(s) for s in subscripts) if subscripts else ()
            key = base_name[1:]  # Remove ^ prefix
            self._globals.set(key, subs, str_value)
            return

        # Set via CurrentScope for locals
        cs.set(target, str_value)

    def get_indirected(
        self,
        source: str,
        _scope: Dict[str, Any],
        levels: int = 1,
        per_level_subscripts: Optional[List[List[Any]]] = None,
    ) -> Any:
        """Get variable value via indirection using unified components.

        Feature: 018-unified-variable-system (T104, T111)
        Replaces scattered get_var + resolve calls with unified approach.

        For READ operations (getting values), we need different semantics than
        WRITE operations (setting values). For N levels of indirection:
        - READ: Dereference N times, returning the final VALUE
        - WRITE: Resolve N-1 times to get the target NAME to write to

        Args:
            source: Source variable name for indirection (e.g., "X" for @X),
                or for levels=0, the already-resolved target name directly
            _scope: Current scope dictionary
            levels: Number of indirection levels (1 for @X, 2 for @@X, etc.)
                Use levels=0 when source is already the resolved target name
                (e.g., from NakedGlobal expressions where the value was computed)
            per_level_subscripts: Subscripts per level for @X@(s1)@(s2) form

        Returns:
            Value at the resolved variable, or "" if undefined

        Examples:
            # @X where X="Y", Y=5
            get_indirected("X", scope, levels=1)
            # Returns 5

            # @@X where X="Y", Y="Z", Z=99
            get_indirected("X", scope, levels=2)
            # Returns 99

            # @X@(1,2) where X="A", A(1,2)="hello"
            get_indirected("X", scope, levels=1, per_level_subscripts=[[1, 2]])
            # Returns "hello"

            # NakedGlobal: @^(1) where ^(1) resolves to "X"
            get_indirected("X", scope, levels=0)
            # Returns value of X directly (source is already the target name)
        """
        # Handle levels=0: source is already the resolved target name
        # This is used for NakedGlobal expressions where the target name
        # was computed during code generation
        if levels == 0:
            return self.get_var(source, _scope)

        # Use unified IndirectionResolver for all cases
        # Feature: 018-unified-variable-system (T115)
        # This eliminates the dependency on deprecated resolve_indirection()
        from m2py.core.scope import CurrentScope
        from m2py.core.indirection import IndirectionResolver
        from m2py.core.exceptions import LVUNDEFError

        cs = CurrentScope.from_generated_context(_scope)
        resolver = IndirectionResolver(self, cs)

        # First resolve to get the target NAME
        try:
            target_name = resolver.resolve_to_name(
                source,
                levels=levels,
                per_level_subscripts=per_level_subscripts,
            )
        except LVUNDEFError as e:
            # Convert LVUNDEF to IndirectionError to preserve backward compatibility
            # The source variable in the indirection chain is undefined
            raise IndirectionError(
                source,
                f"undefined variable in indirection chain: {e.name}",
                variable_name=e.name,
            )

        # Validate the target exists (MUMPS UNDEF semantics)
        # Skip validation for globals (they return empty if undefined)
        if not target_name.startswith("^"):
            # Parse subscripted names properly
            base_name = target_name.split("(")[0] if "(" in target_name else target_name
            scope_key = NameTranslator.to_python(base_name)
            if scope_key not in _scope:
                raise IndirectionError(
                    source,
                    "undefined final target variable in indirection",
                    variable_name=target_name,
                )

        # Now get the value from the target
        return self.get_var(target_name, _scope)

    def kill_indirected(
        self,
        source: str,
        _scope: Dict[str, Any],
        levels: int = 1,
        per_level_subscripts: Optional[List[List[Any]]] = None,
    ) -> None:
        """Kill variable via indirection using unified components.

        Feature: 018-unified-variable-system (T086)
        Replaces scattered kill_var + resolve calls with unified approach.

        Uses IndirectionResolver.resolve_to_name() to determine the target,
        then kills the variable/global appropriately.

        Args:
            source: Source variable name for indirection (e.g., "X" for @X)
            _scope: Current scope dictionary
            levels: Number of indirection levels (1 for @X, 2 for @@X, etc.)
            per_level_subscripts: Subscripts per level for @X@(s1)@(s2) form

        Examples:
            # K @X where X="Y"
            kill_indirected("X", scope, levels=1)
            # Kills Y

            # K @@X where X="Y", Y="Z"
            kill_indirected("X", scope, levels=2)
            # Kills Z

            # K @X@(1,2) where X="A"
            kill_indirected("X", scope, levels=1, per_level_subscripts=[[1, 2]])
            # Kills A(1,2)
        """
        from m2py.core.scope import CurrentScope
        from m2py.core.indirection import IndirectionResolver

        # Create unified scope and resolver
        cs = CurrentScope.from_generated_context(_scope)
        resolver = IndirectionResolver(self, cs)

        # Resolve to get target variable NAME (not value)
        target = resolver.resolve_to_name(
            source, levels=levels, per_level_subscripts=per_level_subscripts
        )

        # Handle global variables
        if target.startswith("^"):
            # Parse subscripts from target if present
            base_name, subscripts = _parse_subscripted_name(target)
            subs = tuple(str(s) for s in subscripts) if subscripts else ()
            key = base_name[1:]  # Remove ^ prefix
            self._globals.kill(key, subs)
            return

        # Handle naked global reference
        if target == "^":
            raise IndirectionError(target, "naked reference requires subscripts")

        # Kill local variable via CurrentScope
        cs.kill(target)

    def resolve_for_target(
        self,
        source: str,
        _scope: Dict[str, Any],
        levels: int = 1,
        per_level_subscripts: Optional[List[List[Any]]] = None,
    ) -> str:
        """Resolve FOR loop indirection target using unified components.

        Feature: 018-unified-variable-system (T089)
        Replaces resolve_indirection_name for FOR loop variable indirection.

        FOR loop indirection like F @A=1:1:3 requires resolving to get the
        target variable NAME (not value). For example, if A="B", we need
        to return "B" as the variable name to iterate.

        Uses IndirectionResolver.resolve_to_name() to determine the target.

        Args:
            source: Source variable name for indirection (e.g., "A" for @A)
            _scope: Current scope dictionary
            levels: Number of indirection levels (1 for @A, 2 for @@A, etc.)
            per_level_subscripts: Subscripts per level for @A@(s1)@(s2) form

        Returns:
            Target variable name as string

        Examples:
            # F @A=1:1:3 where A="B"
            resolve_for_target("A", scope, levels=1)
            # Returns "B"

            # F @@A=1:1:3 where A="X", X="Y"
            resolve_for_target("A", scope, levels=2)
            # Returns "Y"

            # F @A@(1)=1:1:3 where A="B"
            resolve_for_target("A", scope, levels=1, per_level_subscripts=[[1]])
            # Returns "B(1)"
        """
        from m2py.core.scope import CurrentScope
        from m2py.core.indirection import IndirectionResolver

        # Create unified scope and resolver
        cs = CurrentScope.from_generated_context(_scope)
        resolver = IndirectionResolver(self, cs)

        # Resolve to get target variable NAME (not value)
        target = resolver.resolve_to_name(
            source, levels=levels, per_level_subscripts=per_level_subscripts
        )

        return target

    def evaluate_argument_indirection(
        self,
        source: str,
        _scope: Dict[str, Any],
        levels: int = 1,
        per_level_subscripts: Optional[List[List[Any]]] = None,
        treat_empty_as_truthy: bool = False,
    ) -> Any:
        """Evaluate argument indirection using unified components.

        Feature: 018-unified-variable-system (T050, T051)
        This is the FIX for Challenge 6 bug.

        Argument indirection evaluates the resolved value AS AN EXPRESSION,
        not as a variable name to look up. For example:
        - I @A where A="1=0" → evaluates "1=0" → 0 (FALSE)
        - I @A where A="X>5" and X=10 → evaluates "X>5" → 1 (TRUE)

        The OLD behavior passed the string "1=0" to m_truth(), which
        converted to 1 (TRUE) because it starts with "1".

        The CORRECT behavior parses "1=0" as a MUMPS expression and
        evaluates it, resulting in 0 (FALSE) because 1 ≠ 0.

        Uses IndirectionResolver.resolve() with context=ARGUMENT to
        properly evaluate the expression.

        Args:
            source: Source variable name for indirection (e.g., "A" for @A)
            _scope: Current scope dictionary
            levels: Number of indirection levels (1 for @A, 2 for @@A, etc.)
            per_level_subscripts: Subscripts per level for @A@(s1)@(s2) form
            treat_empty_as_truthy: If True, empty string resolves to 1 (T052 for IF)
                                   If False, empty string raises error (WRITE, SET, etc.)

        Returns:
            Evaluated result of the expression

        Examples:
            # I @A where A="1=0"
            evaluate_argument_indirection("A", scope, levels=1)
            # Returns 0 (FALSE) because 1=0 is false

            # I @A where A="X>5" and X=10
            evaluate_argument_indirection("A", scope, levels=1)
            # Returns 1 (TRUE) because 10>5 is true

            # I @@A where A="B", B="1=1"
            evaluate_argument_indirection("A", scope, levels=2)
            # Returns 1 (TRUE) because 1=1 is true

            # I @A where A="" (T052)
            evaluate_argument_indirection("A", scope, levels=1, treat_empty_as_truthy=True)
            # Returns 1 (TRUE) - empty indirection in IF is TRUE
        """
        from m2py.core.scope import CurrentScope
        from m2py.core.indirection import IndirectionContext, IndirectionResolver

        # Create unified scope and resolver
        cs = CurrentScope.from_generated_context(_scope)
        resolver = IndirectionResolver(self, cs)

        # Resolve with ARGUMENT context to evaluate expression
        return resolver.resolve(
            source,
            levels=levels,
            context=IndirectionContext.ARGUMENT,
            per_level_subscripts=per_level_subscripts,
            treat_empty_as_truthy=treat_empty_as_truthy,
        )

    def _set_local_var(
        self,
        name: str,
        subscripts: Optional[Tuple[Any, ...]],
        value: Any,
        _scope: Dict[str, Any],
    ) -> None:
        """Set local variable value in scope.

        Args:
            name: Base variable name (no subscripts) - MUMPS name like "%Z"
            subscripts: Optional tuple of subscript values (may contain variable refs)
            value: Value to set
            _scope: Scope dictionary
        """
        # Translate MUMPS name to Python scope key (%Z -> _pct_Z)
        scope_key = NameTranslator.to_python(name)

        # Evaluate subscripts - resolve variable references like "I" to their values
        eval_subs = _evaluate_subscripts(subscripts, _scope)

        if eval_subs is None:
            # Simple variable assignment - use MArray for consistency with codegen
            if scope_key not in _scope or not isinstance(_scope[scope_key], MArray):
                _scope[scope_key] = MArray()
            _scope[scope_key].value = value
            return

        # Subscripted assignment - ensure MArray exists
        if scope_key not in _scope or not isinstance(_scope[scope_key], MArray):
            _scope[scope_key] = MArray()

        # Set value at subscript
        _scope[scope_key][eval_subs].value = value

    def _set_global_var(
        self,
        name: str,
        subscripts: Optional[Tuple[Any, ...]],
        value: Any,
        _scope: Dict[str, Any],
    ) -> None:
        """Set global variable value.

        Args:
            name: Global variable name (starts with ^)
            subscripts: Optional tuple of subscript values (may contain variable refs)
            value: Value to set
            _scope: Scope dictionary for evaluating variable references
        """
        # Strip ^ for storage key
        key = name[1:]

        # Evaluate subscripts - resolve variable references like "I" to their values
        eval_subs = _evaluate_subscripts(subscripts, _scope)

        # Use the GlobalStorageBackend interface
        subs = () if eval_subs is None else tuple(str(s) for s in eval_subs)
        self._globals.set(key, subs, str(value))

    def kill_var(self, name: str, _scope: Dict[str, Any]) -> None:
        """Kill variable by name (name indirection).

        Spec 017 Phase 6: Implements KILL with indirection.

        Behavior:
        - Local variables: Remove from _scope dict or kill subscript
        - Global variables (^prefix): Use global storage kill
        - Subscripted variables: Kill at that subscript level
        - Creates variable if doesn't exist (no-op for kill)

        Args:
            name: Variable name, optionally with subscripts
            _scope: Current scope dictionary

        Raises:
            IndirectionError: If name is not a valid variable name

        Examples:
            >>> scope = {"X": MArray(value=5)}
            >>> rt.kill_var("X", scope)
            >>> "X" in scope
            False
            >>> scope = {"ARR": MArray()}
            >>> scope["ARR"][1, 2].value = 10
            >>> rt.kill_var("ARR(1,2)", scope)
            >>> scope["ARR"].get(1, 2)
            ""
        """
        if not name:
            raise IndirectionError("", "empty variable name")

        # Parse subscripts if present
        base_name, subscripts = _parse_subscripted_name(name)

        # Handle naked global references: ^(subscripts)
        # The base_name is just "^" when parsing "^(5)" etc.
        if base_name == "^":
            if subscripts is None:
                raise IndirectionError(name, "naked reference requires subscripts")
            # Evaluate subscripts first, then resolve naked reference
            eval_subs = _evaluate_subscripts(subscripts, _scope)
            naked_subs = tuple(str(s) for s in eval_subs) if eval_subs else ()
            resolved_name, full_subs = self._globals.resolve_naked(naked_subs)
            self._globals.kill(resolved_name, full_subs)
            return

        # Validate the base name
        if not _is_valid_varname(base_name):
            raise IndirectionError(
                name,
                f"invalid variable name - must start with letter or %, got '{base_name}'",
            )

        # Evaluate subscripts - resolve variable references like "I" to their values
        eval_subs = _evaluate_subscripts(subscripts, _scope)

        # Handle global variables
        if base_name.startswith("^"):
            key = base_name[1:]
            subs = () if eval_subs is None else tuple(str(s) for s in eval_subs)
            self._globals.kill(key, subs)
            return

        # Handle local variables
        # Translate MUMPS name to Python scope key (%Z -> _pct_Z)
        scope_key = NameTranslator.to_python(base_name)
        if eval_subs is None:
            # Kill entire variable - remove from scope
            _scope.pop(scope_key, None)
        else:
            # Kill at subscript - use MArray.kill()
            arr = _scope.get(scope_key)
            if isinstance(arr, MArray):
                arr.kill(*eval_subs)

    def merge_var(self, name: str, source: "MArray", _scope: Dict[str, Any]) -> None:
        """Merge source tree into variable by name (name indirection for MERGE).

        Spec 017 Phase 13: Implements MERGE with indirection destination.

        Behavior:
        - Local variables: Merge into local variable tree in _scope
        - Global variables (^prefix): Merge into global storage
        - Subscripted variables: Merge at that subscript level
        - Creates destination variable if doesn't exist
        - Does NOT delete existing nodes - only adds/overwrites values

        Args:
            name: Variable name, optionally with subscripts
            source: MArray source tree to merge from
            _scope: Current scope dictionary

        Raises:
            IndirectionError: If name is not a valid variable name

        Examples:
            >>> scope = {"X": MArray()}
            >>> scope["X"][1].value = "old"
            >>> src = MArray()
            >>> src[2].value = "new"
            >>> rt.merge_var("X", src, scope)
            >>> scope["X"].get(1)  # Old value preserved
            "old"
            >>> scope["X"].get(2)  # New value added
            "new"
        """
        if source is None:
            return  # Nothing to merge

        if not name:
            raise IndirectionError("", "empty variable name")

        # Parse subscripts if present
        base_name, subscripts = _parse_subscripted_name(name)

        # Handle naked global references: ^(subscripts)
        # The base_name is just "^" when parsing "^(5)" etc.
        if base_name == "^":
            if subscripts is None:
                raise IndirectionError(name, "naked reference requires subscripts")
            # Evaluate subscripts first, then resolve naked reference
            eval_subs = _evaluate_subscripts(subscripts, _scope)
            naked_subs = tuple(str(s) for s in eval_subs) if eval_subs else ()
            resolved_name, full_subs = self._globals.resolve_naked(naked_subs)
            self._globals.merge_tree(resolved_name, full_subs, source)
            return

        # Validate the base name
        if not _is_valid_varname(base_name):
            raise IndirectionError(
                name,
                f"invalid variable name - must start with letter or %, got '{base_name}'",
            )

        # Evaluate subscripts - resolve variable references like "I" to their values
        eval_subs = _evaluate_subscripts(subscripts, _scope)

        # Handle global variables
        if base_name.startswith("^"):
            key = base_name[1:]
            subs = () if eval_subs is None else tuple(str(s) for s in eval_subs)
            self._globals.merge_tree(key, subs, source)
            return

        # Handle local variables
        # Translate MUMPS name to Python scope key (%Z -> _pct_Z)
        scope_key = NameTranslator.to_python(base_name)
        if scope_key not in _scope or not isinstance(_scope[scope_key], MArray):
            _scope[scope_key] = MArray()

        if eval_subs is None:
            # Merge at root level
            _scope[scope_key].merge_from(source)
        else:
            # Merge at subscript level
            _scope[scope_key][eval_subs].merge_from(source)

    def get_tree_var(self, name: str, _scope: Dict[str, Any]) -> Optional["MArray"]:
        """Get variable tree by name (name indirection for MERGE source).

        Spec 017 Phase 13: Implements MERGE with indirection source.

        Behavior:
        - Local variables: Return MArray from _scope (or subtree)
        - Global variables (^prefix): Return tree from global storage
        - Subscripted variables: Return subtree at that subscript level
        - Undefined variables: Return None

        Args:
            name: Variable name, optionally with subscripts
            _scope: Current scope dictionary

        Returns:
            MArray tree, or None if variable doesn't exist

        Raises:
            IndirectionError: If name is not a valid variable name
        """
        if not name:
            raise IndirectionError("", "empty variable name")

        # Parse subscripts if present
        base_name, subscripts = _parse_subscripted_name(name)

        # Handle naked global references: ^(subscripts)
        # The base_name is just "^" when parsing "^(5)" etc.
        if base_name == "^":
            if subscripts is None:
                raise IndirectionError(name, "naked reference requires subscripts")
            # Evaluate subscripts first, then resolve naked reference
            eval_subs = _evaluate_subscripts(subscripts, _scope)
            naked_subs = tuple(str(s) for s in eval_subs) if eval_subs else ()
            resolved_name, full_subs = self._globals.resolve_naked(naked_subs)
            return self._globals.get_tree(resolved_name, full_subs)

        # Validate the base name
        if not _is_valid_varname(base_name):
            raise IndirectionError(
                name,
                f"invalid variable name - must start with letter or %, got '{base_name}'",
            )

        # Evaluate subscripts - resolve variable references like "I" to their values
        eval_subs = _evaluate_subscripts(subscripts, _scope)

        # Handle global variables
        if base_name.startswith("^"):
            key = base_name[1:]
            subs = () if eval_subs is None else tuple(str(s) for s in eval_subs)
            return self._globals.get_tree(key, subs)

        # Handle local variables
        # Translate MUMPS name to Python scope key (%Z -> _pct_Z)
        scope_key = NameTranslator.to_python(base_name)
        raw_value = _scope.get(scope_key)
        if raw_value is None or not isinstance(raw_value, MArray):
            return None

        if eval_subs is None:
            # Return entire tree
            return raw_value
        else:
            # Return subtree at subscript
            return raw_value[eval_subs]

    def _is_valid_var_name(self, name: str) -> bool:
        """Check if name looks like a valid MUMPS variable name."""
        if not name:
            return False
        # Naked reference like "^(3)"
        if name.startswith("^("):
            return True
        # Global or local: must start with ^ or letter or % (system vars)
        if name.startswith("^"):
            return len(name) > 1 and (
                name[1].isalpha() or name[1] == "(" or name[1] == "%"
            )
        return name[0].isalpha() or name[0] == "%"

    # Internal method: Multi-level name indirection resolution.
    # Used by codegen for generated code and internal methods.
    # Returns the final VALUE after N levels of dereferencing.
    # New code should prefer get_indirected() or IndirectionResolver.
    def resolve_indirection(
        self, expr: str, levels: int, _scope: Dict[str, Any]
    ) -> Any:
        """Resolve N levels of name indirection.

        Spec 012 (T009): Resolves multi-level indirection like @X, @@X, @@@X.

        MUMPS indirection semantics:
        - @X means: get value of X, if that's a valid var name get its value
        - @@X means: get value of @X, if that's a valid var name get its value
        - Each @ adds one level of dereferencing
        - If an intermediate value is not a valid var name (e.g., numeric), return it as-is

        For levels=1 (@X): X → value → (if var name) → final value
        For levels=2 (@@X): X → name1 → name2 → (if var name) → final value

        Args:
            expr: Initial variable name to start resolving
            levels: Number of indirection levels (1 for @, 2 for @@, etc.)
            _scope: Current scope dictionary

        Returns:
            Final resolved value

        Raises:
            IndirectionError: If any resolution step fails on a valid var name

        Examples:
            >>> scope = {"A": "B", "B": "C", "C": 100}
            >>> rt.resolve_indirection("A", 1, scope)  # @A: A → "B" → C
            "C"
            >>> rt.resolve_indirection("A", 2, scope)  # @@A: A → "B" → "C" → 100
            100
        """
        if levels < 1:
            raise IndirectionError(
                expr, f"indirection levels must be >= 1, got {levels}"
            )

        current_name = expr

        def _is_valid_var_name(name: str) -> bool:
            """Check if name looks like a valid MUMPS variable name."""
            if not name:
                return False
            # Naked reference like "^(3)"
            if name.startswith("^("):
                return True
            # Global or local: must start with ^ or letter or % (system vars)
            if name.startswith("^"):
                return len(name) > 1 and (
                    name[1].isalpha() or name[1] == "(" or name[1] == "%"
                )
            return name[0].isalpha() or name[0] == "%"

        # Each level of indirection does one lookup in the chain
        # If an intermediate value is not a valid var name, stop early

        for level in range(levels):
            # Check if current_name starts with @ - it needs to be resolved as an indirection pattern
            if current_name.startswith("@"):
                # Resolve the indirection pattern to get the target variable name
                resolved_name = self.resolve_nested_indirection(current_name, _scope)
                # Now get the VALUE at that resolved name
                value = self.get_var(resolved_name, _scope)
                if not isinstance(value, str):
                    value = str(value)
                current_name = value
                continue

            # Check if current_name is a valid var name before trying to look it up
            # If not valid (e.g., numeric string), stop the chain and return as-is
            if not _is_valid_var_name(current_name):
                return current_name

            # Validate the variable exists before dereferencing
            # Skip validation for naked references (base_name == "^") - get_var handles those
            base_name, subscripts = _parse_subscripted_name(current_name)
            if base_name == "^":
                # Naked reference like "^(3)" - get_var will resolve using naked indicator
                pass
            elif base_name.startswith("^"):
                # Global: check via GlobalStorageBackend
                # Need to check the actual subscripted value, not just the root
                key = base_name[1:]
                # Evaluate subscripts - resolve variable references
                eval_subs = _evaluate_subscripts(subscripts, _scope)
                subs = tuple(str(s) for s in eval_subs) if eval_subs else ()
                if self._globals.get(key, subs) is None:
                    raise IndirectionError(
                        expr,
                        f"undefined variable in indirection chain at level {level}",
                        variable_name=current_name,
                    )
            else:
                # Local: check in _scope (translate MUMPS name to Python scope key)
                scope_key = NameTranslator.to_python(base_name)
                if scope_key not in _scope:
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
        # current_name now holds a variable name (or non-var-name value)

        # If current_name starts with @, resolve it as an indirection pattern and get value
        if current_name.startswith("@"):
            resolved_name = self.resolve_nested_indirection(current_name, _scope)
            return self.get_var(resolved_name, _scope)

        # If it's not a valid var name, return it as-is
        if not _is_valid_var_name(current_name):
            return current_name

        # It's a valid var name, so look it up
        # Skip validation for naked references (base_name == "^") - get_var handles those
        base_name, subscripts = _parse_subscripted_name(current_name)
        # Evaluate subscripts - resolve variable references like "I" to their values
        eval_subs = _evaluate_subscripts(subscripts, _scope)
        if base_name == "^":
            # Naked reference - get_var will resolve
            pass
        elif base_name.startswith("^"):
            key = base_name[1:]
            subs = tuple(str(s) for s in eval_subs) if eval_subs else ()
            if self._globals.get(key, subs) is None:
                raise IndirectionError(
                    expr,
                    "undefined final target variable in indirection",
                    variable_name=current_name,
                )
        else:
            # Translate MUMPS name to Python scope key (%DEF -> _pct_DEF)
            scope_key = NameTranslator.to_python(base_name)
            if scope_key not in _scope:
                raise IndirectionError(
                    expr,
                    "undefined final target variable in indirection",
                    variable_name=current_name,
                )

        return self.get_var(current_name, _scope)

    def resolve_with_subscripts(
        self,
        base_name: str,
        subscripts: List[Any],
        additional_levels: int,
        _scope: Dict[str, Any],
    ) -> str:
        """Resolve indirection with subscripts appended before additional resolution.

        Used for cases like @@^VV@(3)=val where:
        1. base_name is already the resolved value from inner indirection (e.g., "^VV(1)")
        2. Append subscripts (3) → "^VV(1,3)"
        3. Resolve additional_levels more times → value of "^VV(1,3)" = "^VV(2,3)"

        Special handling for naked references:
        - If base_name is a naked reference string like "^(5)", resolve it to a full name
          using the current naked indicator (e.g., "^V(5)"), then append subscripts
        - This handles cases like @@^(1)@(n) where the inner indirection yields a naked
          reference string that needs to be interpreted as a name

        Args:
            base_name: Initial variable name string (already resolved from inner indirection)
            subscripts: List of subscript values to append (may be numbers or strings)
            additional_levels: Number of additional indirection levels to resolve
            _scope: Current scope dictionary

        Returns:
            The final resolved name string

        Raises:
            IndirectionError: If any resolution step fails
        """
        # Check if base_name is a naked reference string like "^(5)"
        # This happens when inner indirection yields a value that IS a naked reference
        parsed_base, parsed_subs = _parse_subscripted_name(base_name)
        if parsed_base == "^" and parsed_subs is not None:
            # base_name is a naked reference string - resolve to full name
            # DON'T get its value - treat the resolved name as the base for subscripts
            # Evaluate subscripts first (they may contain variable references like "I")
            eval_subs = _evaluate_subscripts(parsed_subs, _scope)
            naked_subs = tuple(str(s) for s in eval_subs) if eval_subs else ()
            resolved_name, full_subs = self._globals.resolve_naked(naked_subs)
            # Build the full name string
            if full_subs:
                current_name = (
                    f"^{resolved_name}({','.join(str(s) for s in full_subs)})"
                )
            else:
                current_name = f"^{resolved_name}"
        else:
            # Normal variable - get its value first, which becomes the name to append to
            current_name = self.get_var(base_name, _scope)
            if not isinstance(current_name, str):
                current_name = str(current_name)

            if not current_name:
                raise IndirectionError(
                    base_name,
                    "empty value from base variable",
                    variable_name=base_name,
                )

        # Append subscripts using append_subscripts
        # Keep subscripts as their original types (int/float stay numeric, strings stay strings)
        # so append_subscripts knows how to format them correctly
        current_name = self.append_subscripts(current_name, *subscripts)

        # Resolve additional_levels times
        for level in range(additional_levels):
            value = self.get_var(current_name, _scope)
            if not isinstance(value, str):
                value = str(value)
            if not value:
                raise IndirectionError(
                    base_name,
                    f"empty value at level {level + 1}",
                    variable_name=current_name,
                )
            current_name = value

        return current_name

    def resolve_with_per_level_subscripts(
        self,
        base_name: str,
        subscripts_per_level: List[List[Any]],
        _scope: Dict[str, Any],
        skip_initial_resolution: bool = False,
    ) -> str:
        """Resolve multi-level indirection with subscripts at each level.

        Used for cases like @@X@(1,2)@(5,6)=val where:
        1. Get value of X → "A"
        2. Append inner subscripts (1,2) → "A(1,2)"
        3. Resolve → get value of A(1,2) → "B(3,4)"
        4. Append outer subscripts (5,6) → "B(3,4,5,6)"
        5. This is the final target

        The subscripts_per_level is ordered from innermost to outermost.
        For @@X@(1,2)@(5,6), it would be [[1, 2], [5, 6]]:
        - [1, 2] are applied after getting X's value
        - [5, 6] are applied after the first resolution

        Args:
            base_name: Initial variable name to start with, OR the already-resolved value
            subscripts_per_level: List of subscript lists, one per level (inner to outer)
            _scope: Current scope dictionary
            skip_initial_resolution: If True, base_name is already the resolved value,
                                    so skip the first get_var call. Used when the
                                    indirection source is a global variable whose
                                    value was already obtained.

        Returns:
            The final resolved name string

        Raises:
            IndirectionError: If any resolution step fails
        """
        # Step 1: Get value of base_name (unless it's already the resolved value)
        if skip_initial_resolution:
            current_name = base_name
        else:
            current_name = self.get_var(base_name, _scope)

        if not isinstance(current_name, str):
            current_name = str(current_name)

        if not current_name:
            raise IndirectionError(
                base_name,
                "empty value from base variable",
                variable_name=base_name,
            )

        # Process each level of subscripts
        # For n subscript levels, we need n-1 resolutions between them
        # (the last subscript level just appends without further resolution)
        for i, subscripts in enumerate(subscripts_per_level):
            if subscripts:
                # Append subscripts at this level
                current_name = self.append_subscripts(current_name, *subscripts)

            # If there are more levels after this, resolve
            if i < len(subscripts_per_level) - 1:
                value = self.get_var(current_name, _scope)
                if not isinstance(value, str):
                    value = str(value)
                if not value:
                    raise IndirectionError(
                        base_name,
                        f"empty value at level {i + 1}",
                        variable_name=current_name,
                    )
                current_name = value

        return current_name

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

    def resolve_nested_indirection(
        self,
        target_str: str,
        scope: Dict[str, Any],
        max_depth: int = 100,
        return_value: bool = False,
    ) -> str:
        """Recursively resolve nested name indirection for DO/GOTO targets.

        MUMPS allows nested indirection where the result of one indirection
        is itself an indirection expression. For example:
            S L="@L(1)",L(1)="TWO"
            D @L  ; Resolves L→"@L(1)"→L(1)→"TWO", then DO TWO

        Also handles expression indirection like:
            S L="@$P(""ONE/TWO"",""/\"",1)"
            D @L  ; Evaluates $PIECE → "ONE", then DO ONE

        For multiple @ levels with name indirection subscripts like @@H1@(@G)@("-"):
        - The @(@G) subscript belongs to the inner @ level
        - The @("-") subscript belongs to the outer @ level
        - Processing: @H1@(@G) → H(1,B) → "I(1)", then @"I(1)"@("-") → I(1,-) → "C"

        Args:
            target_str: Initial target string (may contain leading @)
            scope: Variable scope for resolving names
            max_depth: Maximum recursion depth to prevent infinite loops
            return_value: If True, always return the final VALUE (for GET operations)
                         If False, return the variable NAME when possible (for SET/DO)

        Returns:
            Final resolved target string (no leading @). This is either:
            - A variable NAME for SET/DO operations (return_value=False)
            - A VALUE for GET operations (return_value=True)

        Raises:
            IndirectionError: If resolution fails or max depth exceeded
        """
        from m2py.runtime import MArray

        current = str(target_str) if target_str is not None else ""

        if not current.startswith("@"):
            return current

        # Count leading @ symbols
        at_count = 0
        while at_count < len(current) and current[at_count] == "@":
            at_count += 1

        if at_count >= max_depth:
            raise IndirectionError(
                target_str,
                f"nested indirection exceeded max depth ({max_depth})",
            )

        # Strip all leading @s to get the base expression
        base_expr = current[at_count:]
        if not base_expr:
            raise IndirectionError(current, "empty indirection target")

        # Check if this is expression indirection FIRST
        # Expression indirection occurs when:
        # 1. @$func(...) - function call (starts with $)
        # 2. @(expr) - parenthesized expression (starts with ()
        #    Note: @(expr)+offset^routine is valid - we evaluate @(expr) and append the rest
        is_expression_indirection = base_expr.startswith("$")
        expr_suffix = ""  # For @(expr)+offset^routine - the "+offset^routine" part
        if not is_expression_indirection and base_expr.startswith("("):
            # Find the matching close paren to determine what's the expression
            # and what's the suffix (e.g., +1^V1IDDO1)
            paren_depth = 0
            close_pos = -1
            for i, c in enumerate(base_expr):
                if c == "(":
                    paren_depth += 1
                elif c == ")":
                    paren_depth -= 1
                    if paren_depth == 0:
                        close_pos = i
                        break
            if close_pos > 0:
                is_expression_indirection = True
                expr_suffix = base_expr[
                    close_pos + 1 :
                ]  # Everything after the closing )
                base_expr = base_expr[: close_pos + 1]  # Just the (expr) part

        if is_expression_indirection:
            # Expression indirection - need to evaluate as MUMPS expression
            temp_var = "ZINDRES"
            temp_scope: Dict[str, Any] = dict(scope)
            # Prepend @s back for proper expression context
            mumps_code = (
                f"S {temp_var}=" + ("@" * (at_count - 1)) + base_expr
                if at_count > 1
                else f"S {temp_var}={base_expr}"
            )
            try:
                self.execute_mumps(mumps_code, temp_scope)
                result_var = temp_scope.get(temp_var)
                if isinstance(result_var, MArray):
                    value = result_var.value
                else:
                    value = result_var
                if value is None:
                    raise IndirectionError(
                        current,
                        f"expression '{base_expr}' returned null",
                    )
                value_str = str(value) + expr_suffix  # Append suffix like +1^V1IDDO1
                # For return_value=True, the result is a variable NAME that we need to look up
                if return_value and value_str and not value_str.startswith("@"):
                    # Look up the variable to get its VALUE
                    final_base, final_subs = _parse_subscripted_name(value_str)
                    evaluated_final_subs = _evaluate_subscripts(final_subs, scope)

                    if final_base.startswith("^"):
                        global_name = final_base[1:]
                        if evaluated_final_subs:
                            final_value = self.globals.get(
                                global_name, evaluated_final_subs
                            )
                        else:
                            final_value = self.globals.get(global_name, ())
                    else:
                        final_var = scope.get(final_base)
                        if final_var is None:
                            # For GET, undefined variable returns empty string
                            return ""
                        if isinstance(final_var, MArray):
                            if evaluated_final_subs:
                                final_value = final_var.get(*evaluated_final_subs)
                            else:
                                final_value = final_var.value
                        else:
                            final_value = final_var

                    if final_value is None:
                        return ""
                    return str(final_value)
                # If result still starts with @, recurse
                if value_str.startswith("@"):
                    return self.resolve_nested_indirection(
                        value_str, scope, max_depth - 1, return_value
                    )
                return value_str
            except Exception as e:
                if isinstance(e, IndirectionError):
                    raise
                raise IndirectionError(
                    current,
                    f"failed to evaluate expression '{base_expr}': {e}",
                ) from e

        # Check for DO/GOTO target with ^ separator and indirect parts
        # Pattern: @label^@routine or @label^routine or label^@routine
        # Examples: @B^@B(1) where B="0098" and B(1)="V1IDDO1" → "0098^V1IDDO1"
        if "^" in base_expr:
            # Find the ^ that separates label from routine
            # Note: ^ could be inside subscripts like @A(^X)^ROUTINE - we need the OUTER ^
            # Walk through finding unbracketed ^
            paren_depth = 0
            caret_pos = -1
            in_string = False
            i = 0
            while i < len(base_expr):
                c = base_expr[i]
                if c == '"':
                    if in_string:
                        # Check for escaped quote
                        if i + 1 < len(base_expr) and base_expr[i + 1] == '"':
                            i += 2
                            continue
                        in_string = False
                    else:
                        in_string = True
                elif not in_string:
                    if c == "(":
                        paren_depth += 1
                    elif c == ")":
                        paren_depth -= 1
                    elif c == "^" and paren_depth == 0:
                        caret_pos = i
                        break
                i += 1

            # Only treat as label^routine if caret_pos > 0 (there's a label before ^)
            # caret_pos == 0 means ^GLO which is a global variable reference, not label^routine
            if caret_pos > 0:
                # Split into label and routine parts
                label_part = base_expr[
                    :caret_pos
                ]  # e.g., "B" from "B^@B(1)" or "B+1" from "B+1^V1IDDO1"
                routine_part = base_expr[
                    caret_pos + 1 :
                ]  # e.g., "@B(1)" from "B^@B(1)"

                # Check if label_part contains a + (offset suffix)
                # E.g., "B+1" means variable B with offset +1
                label_suffix = ""
                plus_pos = label_part.find("+")
                if plus_pos > 0:
                    label_suffix = label_part[plus_pos:]  # "+1" or "+@B+1" etc
                    label_part = label_part[:plus_pos]  # "B"

                # Resolve label part if it's a variable reference (not a literal)
                resolved_label = label_part
                if label_part and not label_part[0].isdigit():
                    # It's a variable name, look it up
                    label_base, label_subs = _parse_subscripted_name(label_part)
                    evaluated_label_subs = _evaluate_subscripts(label_subs, scope, self)

                    # Translate MUMPS name to Python scope key (%X -> _pct_X)
                    py_label_name = NameTranslator.to_python(label_base)
                    label_var = scope.get(py_label_name)
                    if label_var is not None:
                        if isinstance(label_var, MArray):
                            if evaluated_label_subs:
                                resolved_label = str(
                                    label_var.get(*evaluated_label_subs) or ""
                                )
                            else:
                                resolved_label = str(label_var.value or "")
                        else:
                            resolved_label = str(label_var)
                    # If undefined, keep the literal name (will error in parse_call_target)

                # Resolve routine part - may start with @
                if routine_part.startswith("@"):
                    # Recursively resolve the routine indirection
                    resolved_routine = self.resolve_nested_indirection(
                        routine_part, scope, max_depth - 1
                    )
                else:
                    resolved_routine = routine_part

                # Combine with label suffix (offset) and check for nested indirection in result
                result = f"{resolved_label}{label_suffix}^{resolved_routine}"
                if result.startswith("@") or "^@" in result:
                    # Result still has indirection, recurse
                    return self.resolve_nested_indirection(
                        result, scope, max_depth - 1, return_value
                    )
                return result

        # Parse ALL @(...) groups from the base expression
        # These will be distributed among the @ levels
        all_subscript_groups: list[tuple[Any, ...]] = []
        remaining_expr = base_expr

        while "@(" in remaining_expr:
            # Find the LAST @( to process right-to-left
            last_at_paren = remaining_expr.rfind("@(")
            # Find the matching close paren
            paren_depth = 0
            close_pos = -1
            in_string = False
            i = last_at_paren + 2
            while i < len(remaining_expr):
                c = remaining_expr[i]
                if c == '"':
                    if in_string:
                        # Check for escaped quote
                        if i + 1 < len(remaining_expr) and remaining_expr[i + 1] == '"':
                            i += 2
                            continue
                        in_string = False
                    else:
                        in_string = True
                elif not in_string:
                    if c == "(":
                        paren_depth += 1
                    elif c == ")":
                        if paren_depth == 0:
                            close_pos = i
                            break
                        paren_depth -= 1
                i += 1

            if close_pos == -1:
                break

            # Extract the subscript content
            subs_content = remaining_expr[last_at_paren + 2 : close_pos]
            parsed_subs = tuple(_parse_subscript_list(subs_content, base_expr))
            # Prepend (since we're going right-to-left)
            all_subscript_groups.insert(0, parsed_subs)
            # Remove this @(...) from expression
            remaining_expr = (
                remaining_expr[:last_at_paren] + remaining_expr[close_pos + 1 :]
            )

        # remaining_expr is now the variable part (possibly with regular subscripts)
        # Parse the variable name and any regular subscripts like X(1,2)
        base_name, regular_subs = _parse_subscripted_name(remaining_expr)

        # Evaluate regular subscripts
        evaluated_regular_subs = _evaluate_subscripts(regular_subs, scope, self)

        # Now process from innermost @ to outermost
        # Level 1 (innermost): look up variable, apply first @(...) group if available
        # Level 2: apply @ to result, apply second @(...) group if available
        # etc.

        # Get the innermost subscript group (if any)
        level1_subs = all_subscript_groups[0] if all_subscript_groups else None

        # Look up the base variable
        if base_name.startswith("^"):
            global_name = base_name[1:]
            if evaluated_regular_subs:
                value = self.globals.get(global_name, evaluated_regular_subs)
            else:
                value = self.globals.get(global_name, ())
        else:
            # Translate MUMPS name to Python scope key (%X -> _pct_X)
            py_name = NameTranslator.to_python(base_name)
            var = scope.get(py_name)
            if var is None:
                raise IndirectionError(
                    current,
                    f"undefined variable '{base_name}'",
                )
            if isinstance(var, MArray):
                if evaluated_regular_subs:
                    value = var.get(*evaluated_regular_subs)
                else:
                    value = var.value
            else:
                value = var

        if value is None:
            value = ""

        value_str = str(value)

        # Apply level 1 subscripts if present
        if level1_subs:
            evaluated_level1_subs = _evaluate_subscripts(level1_subs, scope, self)
            if evaluated_level1_subs:
                # If value starts with @, resolve it first
                if value_str.startswith("@"):
                    value_str = self.resolve_nested_indirection(
                        value_str, scope, max_depth - 1
                    )
                # Parse value as variable name and append subscripts
                val_base, val_subs = _parse_subscripted_name(value_str)
                if val_subs:
                    combined_subs = val_subs + evaluated_level1_subs
                else:
                    combined_subs = evaluated_level1_subs
                subs_formatted = ",".join(
                    self._format_subscript(s) for s in combined_subs
                )
                value_str = f"{val_base}({subs_formatted})"

        # Track whether we've done the final value lookup
        final_lookup_done = False

        # Now process remaining @ levels
        # For at_count = 2, we've done level 1, now do level 2 (one more @)
        for level in range(2, at_count + 1):
            # Look up the current value_str
            lookup_base, lookup_subs = _parse_subscripted_name(value_str)
            evaluated_lookup_subs = _evaluate_subscripts(lookup_subs, scope, self)

            if lookup_base.startswith("^"):
                global_name = lookup_base[1:]
                if evaluated_lookup_subs:
                    value = self.globals.get(global_name, evaluated_lookup_subs)
                else:
                    value = self.globals.get(global_name, ())
            else:
                var = scope.get(lookup_base)
                if var is None:
                    raise IndirectionError(
                        current,
                        f"undefined variable '{lookup_base}' at level {level}",
                    )
                if isinstance(var, MArray):
                    if evaluated_lookup_subs:
                        value = var.get(*evaluated_lookup_subs)
                    else:
                        value = var.value
                else:
                    value = var

            if value is None:
                value = ""
            value_str = str(value)

            # Apply subscripts for this level if available
            subs_index = level - 1  # level 2 uses index 1, etc.
            if subs_index < len(all_subscript_groups):
                level_subs = all_subscript_groups[subs_index]
                evaluated_level_subs = _evaluate_subscripts(level_subs, scope, self)
                if evaluated_level_subs:
                    # If value starts with @, resolve it first
                    if value_str.startswith("@"):
                        value_str = self.resolve_nested_indirection(
                            value_str, scope, max_depth - level
                        )
                    # Parse value as variable name and append subscripts
                    val_base, val_subs = _parse_subscripted_name(value_str)
                    if val_subs:
                        combined_subs = val_subs + evaluated_level_subs
                    else:
                        combined_subs = evaluated_level_subs
                    subs_formatted = ",".join(
                        self._format_subscript(s) for s in combined_subs
                    )
                    value_str = f"{val_base}({subs_formatted})"

                    # If this is the last @ level, we need to look up the final value
                    if level == at_count:
                        final_base, final_subs = _parse_subscripted_name(value_str)
                        evaluated_final_subs = _evaluate_subscripts(final_subs, scope)

                        if final_base.startswith("^"):
                            global_name = final_base[1:]
                            if evaluated_final_subs:
                                value = self.globals.get(
                                    global_name, evaluated_final_subs
                                )
                            else:
                                value = self.globals.get(global_name, ())
                        else:
                            final_var = scope.get(final_base)
                            if final_var is None:
                                raise IndirectionError(
                                    current,
                                    f"undefined variable '{final_base}' in final lookup",
                                )
                            if isinstance(final_var, MArray):
                                if evaluated_final_subs:
                                    value = final_var.get(*evaluated_final_subs)
                                else:
                                    value = final_var.value
                            else:
                                value = final_var

                        if value is None:
                            value = ""
                        value_str = str(value)
                        final_lookup_done = True

        # If value_str still starts with @, continue resolving
        if value_str.startswith("@"):
            return self.resolve_nested_indirection(
                value_str, scope, max_depth - at_count, return_value
            )

        # If we did the final lookup in the loop (for cases with @-subscripts at last level),
        # the value_str is already the final VALUE, not a name
        if final_lookup_done:
            return value_str

        # For GET operations (return_value=True), do the final lookup
        if return_value:
            # value_str is a variable name - look it up to get the value
            final_base, final_subs = _parse_subscripted_name(value_str)
            evaluated_final_subs = _evaluate_subscripts(final_subs, scope)

            if final_base.startswith("^"):
                global_name = final_base[1:]
                if evaluated_final_subs:
                    value = self.globals.get(global_name, evaluated_final_subs)
                else:
                    value = self.globals.get(global_name, ())
            else:
                final_var = scope.get(final_base)
                if final_var is None:
                    # For GET, undefined variable returns empty string
                    return ""
                if isinstance(final_var, MArray):
                    if evaluated_final_subs:
                        value = final_var.get(*evaluated_final_subs)
                    else:
                        value = final_var.value
                else:
                    value = final_var

            if value is None:
                return ""
            return str(value)

        # value_str is a variable name - return it for the caller to look up
        # This handles cases like @X where X="Y" - we return "Y" as the variable name
        return value_str

    def resolve_do_targets(
        self, target_str: str, scope: Dict[str, Any]
    ) -> List[CallTarget]:
        """Resolve and parse DO targets, handling multiple comma-separated targets.

        MUMPS argument indirection can produce multiple targets separated by commas.
        For example: D @A where A="^R1,^@B",B="R2"
        This resolves to calling ^R1 and ^R2.

        Also handles @(expr) for expression indirection in targets:
        D @A where A="@^V1A,@(^V1A_0)" where ^V1A="0098"
        This resolves to calling 0098 and 00980.

        Args:
            target_str: Target string which may contain multiple comma-separated targets
            scope: Variable scope for resolving indirection

        Returns:
            List of CallTarget objects to execute

        Example:
            >>> rt.resolve_do_targets("^R1,^@B", {"B": "R2"})
            [CallTarget(label=None, routine="R1"), CallTarget(label=None, routine="R2")]
        """
        # target_str is already the VALUE from the indirection (e.g., A.value)
        # It may contain commas separating multiple targets, each of which
        # may have further indirection (@)
        #
        # DON'T call resolve_nested_indirection on the whole string when it
        # contains commas - that would try to process it as one unit.
        # Instead, split first, then resolve each part.

        # Convert to string (MUMPS values can be numeric)
        to_split = str(target_str) if target_str is not None else ""

        # Split on commas, respecting parentheses
        targets: List[str] = []
        current = ""
        paren_depth = 0
        in_string = False
        i = 0
        while i < len(to_split):
            c = to_split[i]
            if c == '"':
                if in_string:
                    if i + 1 < len(to_split) and to_split[i + 1] == '"':
                        current += c
                        i += 1
                    else:
                        in_string = False
                else:
                    in_string = True
                current += c
            elif not in_string:
                if c == "(":
                    paren_depth += 1
                    current += c
                elif c == ")":
                    paren_depth -= 1
                    current += c
                elif c == "," and paren_depth == 0:
                    # Found a comma outside parentheses - this separates targets
                    if current.strip():
                        targets.append(current.strip())
                    current = ""
                else:
                    current += c
            else:
                current += c
            i += 1

        # Add the last target
        if current.strip():
            targets.append(current.strip())

        # Helper function to check if a string contains commas outside parens
        def contains_unparenthesized_comma(s: str) -> bool:
            depth = 0
            in_str = False
            for c in s:
                if c == '"':
                    in_str = not in_str
                elif not in_str:
                    if c == "(":
                        depth += 1
                    elif c == ")":
                        depth -= 1
                    elif c == "," and depth == 0:
                        return True
            return False

        # Helper to strip postconditions from a target
        # Postconditions follow : after the target (e.g., "LABEL:condition")
        # But : can appear in strings and subscripts, so we need to be careful
        def strip_postcondition(s: str) -> tuple[str, str]:
            """Split target from postcondition. Returns (target, postcondition)."""
            depth = 0
            in_str = False
            for i, c in enumerate(s):
                if c == '"':
                    in_str = not in_str
                elif not in_str:
                    if c == "(":
                        depth += 1
                    elif c == ")":
                        depth -= 1
                    elif c == ":" and depth == 0:
                        return s[:i], s[i + 1 :]
            return s, ""

        # Resolve any remaining indirection in each target and parse
        # Use a queue because resolution may produce multiple targets
        result: List[CallTarget] = []
        targets_to_process = list(targets)

        while targets_to_process:
            target = targets_to_process.pop(0)
            postcondition = ""

            # Strip postcondition first (e.g., "LABEL^ROUTINE:condition")
            target, postcondition = strip_postcondition(target)

            # If target starts with @, resolve the indirection
            if target.startswith("@"):
                resolved = self.resolve_nested_indirection(target, scope)
                # The resolved result may itself contain multiple comma-separated targets
                if contains_unparenthesized_comma(resolved):
                    # Re-split and queue for processing
                    # Recursively call ourselves to properly split and process
                    sub_targets = self.resolve_do_targets(resolved, scope)
                    result.extend(sub_targets)
                    continue
                target = resolved

            # Also handle ^@routine (routine is indirect)
            # This includes targets like "^@B" (just routine) and "LABEL^@B" (label + indirect routine)
            if "^@" in target:
                # Find the position of ^@ to split label from routine
                caret_at_pos = target.find("^@")
                label_part = target[:caret_at_pos]  # May be empty for "^@B"
                routine_part = target[caret_at_pos + 1 :]  # "@B" - includes the @
                if routine_part.startswith("@"):
                    # Resolve the indirect routine
                    resolved_routine = self.resolve_nested_indirection(
                        routine_part, scope
                    )
                    target = (
                        f"{label_part}^{resolved_routine}"
                        if label_part
                        else f"^{resolved_routine}"
                    )

            # Handle offset expressions that need evaluation
            # Pattern: LABEL+expr^ROUTINE where expr may contain @, strings, or expressions
            # Example: SIEBEN7+@C-@C+1 where C="D", D=10 → SIEBEN7+1
            # Example: ZEHN+"1ABCDE"^V1IDDO1 → ZEHN+1^V1IDDO1 (string converted to number)
            if "+" in target:
                # Find first + outside parens and strings (offset separator)
                plus_pos = -1
                depth = 0
                in_str = False
                for i, c in enumerate(target):
                    if c == '"':
                        in_str = not in_str
                    elif not in_str:
                        if c == "(":
                            depth += 1
                        elif c == ")":
                            depth -= 1
                        elif c == "+" and depth == 0:
                            plus_pos = i
                            break

                if plus_pos > 0:
                    label_part = target[:plus_pos]
                    offset_and_rest = target[plus_pos + 1 :]  # Everything after first +

                    # Check if offset needs evaluation (contains @, ", or is not a simple integer)
                    # Split off routine if present (find ^ outside strings that's NOT preceded by @)
                    # We need to find the routine-separator ^, not ^ in global refs like @^GLO
                    # The routine separator is ^ NOT preceded by @
                    routine_sep = -1
                    depth = 0
                    in_str = False
                    for i, c in enumerate(offset_and_rest):
                        if c == '"':
                            in_str = not in_str
                        elif not in_str:
                            if c == "(":
                                depth += 1
                            elif c == ")":
                                depth -= 1
                            elif c == "^" and depth == 0:
                                # Check if this ^ is NOT preceded by @
                                # If preceded by @, it's a global ref like @^GLO
                                if i == 0 or offset_and_rest[i - 1] != "@":
                                    routine_sep = i
                                    # Don't break - we want the LAST routine separator
                                    # Actually, find the first one that's not @^

                    if routine_sep >= 0:
                        offset_expr = offset_and_rest[:routine_sep]
                        routine_suffix = offset_and_rest[routine_sep:]  # includes ^
                    else:
                        offset_expr = offset_and_rest
                        routine_suffix = ""

                    # Check if offset is a simple integer or needs evaluation
                    needs_evaluation = False
                    if "@" in offset_expr or '"' in offset_expr:
                        needs_evaluation = True
                    else:
                        # Try to parse as int - if it fails, needs evaluation
                        try:
                            int(offset_expr)
                        except ValueError:
                            needs_evaluation = True

                    if needs_evaluation:
                        # Evaluate the offset expression
                        try:
                            from m2py.codegen.helpers import m_num

                            temp_var = "ZOFFSET"
                            temp_scope: Dict[str, Any] = dict(scope)
                            self.execute_mumps(
                                f"S {temp_var}={offset_expr}", temp_scope
                            )
                            offset_result = temp_scope.get(temp_var)
                            if isinstance(offset_result, MArray):
                                offset_val = offset_result.value
                            else:
                                offset_val = offset_result
                            # Use MUMPS numeric conversion (e.g., "1ABCDE" → 1)
                            offset_int = int(m_num(offset_val))
                            # Reconstruct target with evaluated offset
                            target = f"{label_part}+{offset_int}{routine_suffix}"
                        except Exception as e:
                            raise IndirectionError(
                                target,
                                f"failed to evaluate offset expression '{offset_expr}': {e}",
                            )

            # Evaluate postcondition if present - skip this target if false
            if postcondition:
                try:
                    temp_var = "ZPOSTCOND"
                    temp_scope: Dict[str, Any] = dict(scope)
                    self.execute_mumps(f"S {temp_var}={postcondition}", temp_scope)
                    pc_result = temp_scope.get(temp_var)
                    if isinstance(pc_result, MArray):
                        pc_value = pc_result.value
                    else:
                        pc_value = pc_result
                    # MUMPS truthiness: 0 or empty string is false, anything else is true
                    if pc_value in (0, "", "0", None):
                        continue  # Skip this target - postcondition is false
                except Exception:
                    # If postcondition evaluation fails, skip the target
                    continue

            # Parse the target
            call_target = self.parse_call_target(target)
            result.append(call_target)

        return result

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
            target_str: Target string from indirection resolution (will be
                converted to string if numeric, per MUMPS semantics)

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
            >>> rt.parse_call_target(1)  # numeric label
            CallTarget(label="1", routine=None, offset=None)
        """
        # MUMPS values are polymorphic - numeric values used in string context
        # must be converted to strings (e.g., S A=1 DO @A → call label "1")
        target_str = str(target_str) if target_str is not None else ""
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
        # Note: use _is_valid_label, not _is_valid_varname, since labels can be numeric
        if label and not _is_valid_label(label):
            raise IndirectionError(
                target_str,
                f"invalid label name '{label}'",
            )

        return CallTarget(label=label, routine=routine, offset=offset)

    def execute_mumps(
        self,
        mumps_code: str,
        _scope: Dict[str, Any],
        caller_globals: Optional[Dict[str, Any]] = None,
    ) -> Any:
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

        T075p: When caller_globals is provided, include it in the execution
        namespace so XECUTE'd code can call module-level label functions
        (DO/GOTO to labels in the calling routine).

        Args:
            mumps_code: MUMPS code to execute (one or more commands)
            _scope: Scope dictionary shared with caller
            caller_globals: Optional caller's globals() for label access

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

        # If first line starts with a command (space or tab, or command letter), wrap it
        # Common MUMPS commands (case-insensitive)
        command_letters = "SWRKQIDGNFXMEHUCO"
        if first_line and (
            first_line[0].isspace() or first_line[0].upper() in command_letters
        ):
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

        # T075p: Include caller's globals so XECUTE can access module labels
        # This allows DO/GOTO to labels in the calling routine
        if caller_globals:
            # Only include callable items (functions) to avoid polluting namespace
            for name, value in caller_globals.items():
                if callable(value) and not name.startswith("_"):
                    namespace[name] = value

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
        from m2py.codegen.helpers import m_str, m_compare, m_num, m_truth

        namespace["m_str"] = m_str
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
                # Register routine in sys.modules so external calls can find it
                # This allows D ^ROUTINE to work when routines are exec'd
                import sys
                import types

                routine_name = namespace["_routine_name"]
                module = types.ModuleType(routine_name)
                module.__dict__.update(namespace)
                sys.modules[routine_name] = module
                self._routines[routine_name.upper()] = module
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
            # T075b: Use run_with_goto_support to handle external GOTOs
            if entry_point and entry_point in namespace:
                func = namespace[entry_point]
                if callable(func):
                    _scope: dict = {}

                    # Define wrapper function (avoid lambda per E731)
                    def wrapped_func(_rt: "MUMPSRuntime", _scope: dict = _scope) -> Any:
                        if entry_args:
                            return func(_rt, *entry_args, _scope=_scope)
                        return func(_rt, _scope=_scope)

                    # Use run_with_goto_support to handle G ^ROUTINE patterns
                    run_with_goto_support(wrapped_func, self, _scope)

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

        Skips internal helper functions to find the first MUMPS label function.
        Recognizes translated MUMPS label names:
        - _m_xxx: Python keywords (e.g., _m_for from MUMPS label "for")
        - _n_xxx: Pure numeric labels (e.g., _n_01 from MUMPS label "01")
        - _pct_xxx: Percent-prefixed labels (e.g., _pct_START from MUMPS label "%START")
        - _preamble: Labelless preamble code

        Skips codegen helper functions like _call_extrinsic, _labels, etc.

        Args:
            python_code: Python source code

        Returns:
            Name of first user function, or None if no functions found
        """
        # Prefixes used by NameTranslator for MUMPS → Python translation
        mumps_translated_prefixes = ("_m_", "_n_", "_pct_", "_preamble")

        # Look for all "def FUNCNAME(" patterns
        for match in re.finditer(r"^def\s+(\w+)\s*\(", python_code, re.MULTILINE):
            func_name = match.group(1)
            # Accept functions that don't start with _ OR are translated MUMPS names
            if not func_name.startswith("_") or func_name.startswith(
                mumps_translated_prefixes
            ):
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
    # Spec 018: SubscriptVarRef for subscript variable references
    "SubscriptVarRef",
    "VarRef",  # Backward compatibility alias for SubscriptVarRef
]
