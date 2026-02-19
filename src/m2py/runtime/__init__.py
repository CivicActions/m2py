"""Minimal runtime for executing generated MUMPS code.

Provides output capture and execution support for generated Python code.
Includes MArray class for MUMPS array semantics, global variable storage,
LHS function helpers (m_set_piece, m_set_extract), and $DATA function
helpers (m_data, m_data_global).
"""

from __future__ import annotations

import copy
import re
import sys
import types
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Callable, Dict, List, NamedTuple, Optional, Tuple

from m2py.core.names import NameTranslator
from m2py.core.tokenizer import split_at_toplevel

if TYPE_CHECKING:
    pass  # Reserved for future type imports


# =============================================================================
# Variable Name Validation Helper
# =============================================================================

# Import the unified name validation from core
from m2py.core.names import is_valid_varname as _core_is_valid_varname

# MUMPS label name pattern: starts with letter, %, or digit, followed by alphanumerics
# Labels can be purely numeric (e.g., 461, 462) or traditional names (e.g., ENTRY, %BREAK)
# Examples: ENTRY, 461, %BREAK, A1, 123
_LABEL_PATTERN = re.compile(r"^[A-Za-z%0-9][A-Za-z0-9]*$")


def _is_valid_varname(name: str) -> bool:
    """Check if name is a valid MUMPS variable name.

    Now delegates to core.names.is_valid_varname() for unified validation.

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
    return _core_is_valid_varname(name, allow_subscripts=False)


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


# =============================================================================
# Data Structures for Error Handling & Transaction Support
# =============================================================================


@dataclass
class StackFrame:
    """A single entry in the MUMPS call stack.

    Used for $STACK(n,"info") introspection per ANSI §107.108.
    Each DO, $$, XECUTE, ZINTR, or TRIGGER entry pushes a frame.
    """

    frame_type: str  # "DO", "$$", "XECUTE", "ZINTR", "TRIGGER"
    routine: str = ""  # Routine name (e.g., "MYROUTINE")
    label: str = ""  # Label name (e.g., "MAIN")
    offset: int = 0  # Line offset from label (0-based)
    mcode: str = ""  # Original MUMPS source line
    ecode: str = ""  # Error code(s) at this level (if any)


@dataclass
class TransactionLocalSnapshot:
    """Snapshot of local variables at TSTART time.

    Used for TRESTART support (F-05). Stores deep copies of specified
    local variables. Discarded (not restored) on TROLLBACK/TCOMMIT per YDB.
    """

    restart_vars: Optional[list[str]] = None  # Named vars, or None = not restartable
    restart_all: bool = False  # True for TSTART *
    snapshot: dict[str, Any] = field(
        default_factory=dict
    )  # var_name → deepcopy(MArray)
    saved_test: Optional[bool] = None  # $TEST value at TSTART


def _parse_subscripted_name(name: str) -> Tuple[str, Optional[Tuple[Any, ...]]]:
    """Parse a variable name that may include subscripts.

    Extracts base name and subscripts from
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

    Delegates splitting to core.tokenizer.split_at_toplevel, then
    applies _convert_subscript to each raw subscript.

    Args:
        subscript_str: The content between parentheses
        original_name: Original name for error messages

    Returns:
        List of subscript values

    Raises:
        IndirectionError: If subscript parsing fails
    """
    parts = split_at_toplevel(subscript_str, delimiter=",", respect_quotes=True)
    return [
        _convert_subscript(part.strip(), original_name)
        for part in parts
        if part.strip()
    ]


def _split_argument_list(arg_str: str) -> List[str]:
    """Split comma-separated argument list respecting parentheses.

    Used for KILL @X, NEW @X where X may contain comma-separated
    variable names that include subscripts.

    Delegates to core.tokenizer.split_at_toplevel.

    Unlike naive str.split(','), this correctly handles:
    - Simple variables: "A,B,C" → ["A", "B", "C"]
    - Subscripted vars: "A(1,2),B" → ["A(1,2)", "B"]
    - Complex: "A(1,2),B(3),C" → ["A(1,2)", "B(3)", "C"]
    - Quoted strings inside subscripts: 'A("x,y"),B' → ['A("x,y")', "B"]

    Args:
        arg_str: Comma-separated argument string

    Returns:
        List of individual argument strings

    Examples:
        >>> _split_argument_list("E,F")
        ['E', 'F']
        >>> _split_argument_list("A(1,2),B")
        ['A(1,2)', 'B']
        >>> _split_argument_list("X")
        ['X']
    """
    if not arg_str:
        return []

    parts = split_at_toplevel(arg_str, delimiter=",", respect_quotes=True)
    return [p.strip() for p in parts if p.strip()]


def _find_toplevel_colon(s: str) -> int:
    """Find the first colon in string that's not inside quotes or parentheses.

    Used for XECUTE argument postcondition parsing: VAR:postcondition
    Must not split on colons inside function calls like $S(1>2:"code")

    Args:
        s: String to search

    Returns:
        Index of first top-level colon, or -1 if none found
    """
    depth = 0
    in_string = False

    for i, char in enumerate(s):
        if in_string:
            if char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == ":" and depth == 0:
            return i

    return -1


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


def _is_mumps_expression(name: str) -> bool:
    """Check if a name contains MUMPS expression operators that need evaluation.

    Args:
        name: Variable name or expression string

    Returns:
        True if the string contains operators and needs expression evaluation,
        False if it's a simple variable name that can be looked up directly.
    """
    # Skip if empty or starts with @ (handled separately)
    if not name or name.startswith("@"):
        return False

    # Check if it's a string literal
    if name.startswith('"'):
        return False

    # Check for operators outside of parentheses and quotes
    # MUMPS operators: + - * / \ # _ ' < > = [ ] ? &  !
    paren_depth = 0
    in_string = False
    i = 0
    while i < len(name):
        c = name[i]
        if c == '"':
            if in_string:
                # Check for escaped quote
                if i + 1 < len(name) and name[i + 1] == '"':
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
            elif paren_depth == 0:
                # Check for operators at top level
                if c in "+-*/%\\_'<>=[]?&!#":
                    return True
        i += 1
    return False


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
        raw_value = _scope.get(NameTranslator.to_python(inner_var), "")
        if isinstance(raw_value, MArray):
            raw_value = raw_value.value

        # Now raw_value might itself be an indirection (@...) or a variable name
        # Keep resolving until we get an actual value
        while isinstance(raw_value, str) and raw_value.startswith("@"):
            # This is nested indirection
            next_var = raw_value[1:]
            base_name, subs = _parse_subscripted_name(next_var)
            next_raw = _scope.get(NameTranslator.to_python(base_name), "")
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
            final_raw = _scope.get(NameTranslator.to_python(base_name), "")
            if isinstance(final_raw, MArray):
                if subs:
                    evaluated_subs = _evaluate_subscripts(subs, _scope)
                    return final_raw.get(*evaluated_subs)
                return final_raw.value
            return final_raw
        return ""

    # Handle expressions like "K+0" - evaluate as MUMPS expression
    if _is_mumps_expression(var_name):
        if runtime is not None:
            # Use execute_mumps to evaluate the expression
            temp_var = "ZSUBEXPR"
            temp_scope: Dict[str, Any] = dict(_scope)
            mumps_code = f"S {temp_var}={var_name}"
            try:
                runtime.execute_mumps(mumps_code, temp_scope)
                result_var = temp_scope.get(temp_var)
                if isinstance(result_var, MArray):
                    return result_var.value if result_var.value is not None else ""
                return result_var if result_var is not None else ""
            except Exception:
                # If evaluation fails, fall through to lookup
                pass

    # Handle subscripted variable references like "A(1)"
    # Parse the variable name to extract base name and subscripts
    if "(" in var_name:
        base_name, subs = _parse_subscripted_name(var_name)
        raw_value = _scope.get(NameTranslator.to_python(base_name), "")
        if isinstance(raw_value, MArray):
            if subs:
                # Recursively evaluate subscripts (they might be variable refs too)
                evaluated_subs = _evaluate_subscripts(subs, _scope, runtime)
                if evaluated_subs:
                    return raw_value.get(*evaluated_subs)
                return raw_value.value
            return raw_value.value
        return raw_value if raw_value != "" else ""

    raw_value = _scope.get(NameTranslator.to_python(var_name), "")
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
# Indirection & XECUTE Exceptions and Types
# =============================================================================


class IndirectionError(Exception):
    """Raised for invalid indirection operations at runtime.

    Exception for name indirection, XECUTE, and
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

    Represents the components of a DO/GOTO target string.

    Examples:
        - "LABEL" → CallTarget(label="LABEL", routine=None, offset=None)
        - "^ROUTINE" → CallTarget(label=None, routine="ROUTINE", offset=None)
        - "LABEL^ROUTINE" → CallTarget(label="LABEL", routine="ROUTINE", offset=None)
        - "LABEL+5" → CallTarget(label="LABEL", routine=None, offset=5)
        - "LABEL+5^ROUTINE" → CallTarget(label="LABEL", routine="ROUTINE", offset=5)
        - "LABEL:cond" → CallTarget(label="LABEL", postcondition="cond")
    """

    label: Optional[str] = None
    routine: Optional[str] = None
    offset: Optional[int] = None
    postcondition: Optional[str] = None  # Unevaluated postcondition string


# Global storage backend protocol
from m2py.runtime.globals import GlobalStorageBackend, InMemoryGlobalStorage  # noqa: E402

# Helper functions
from m2py.runtime.helpers import (  # noqa: E402
    m_data,
    m_data_global,
    m_format_output,
    m_set_extract,
    m_set_piece,
)

# Runtime exception class
from m2py.runtime.exceptions import MRuntimeError  # noqa: E402

# Intrinsic function helpers ($ORDER, $QUERY, $SELECT, $PIECE, $EXTRACT, $GET, $FIND)
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

# String comparison and pattern match helpers
# Contains ([) and Follows (]) are inlined as Python expressions in codegen
from m2py.runtime.helpers import (  # noqa: E402
    _mumps_collation_key,
    m_pattern_match,
    m_sorts_after,
)


class MArray:
    """MUMPS array with hierarchical subscript support.

    Implements MUMPS sparse array semantics where
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

    def __contains__(self, key: Any) -> bool:
        """Check if subscript key exists in this node's children.

        Used by 'key in array' syntax. Canonicalizes the key first.

        Args:
            key: Subscript to check

        Returns:
            True if key exists in children, False otherwise
        """
        key_str = self._canonicalize_subscript(key)
        return key_str in self._children

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

        Alias for defined() using MUMPS $DATA naming.

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
            # Track the path so we can clean up empty intermediate nodes
            path: list[tuple["MArray", str]] = []
            parent = self
            for sub in subscripts[:-1]:
                sub_str = self._canonicalize_subscript(sub)
                if sub_str not in parent._children:
                    return  # Path doesn't exist
                path.append((parent, sub_str))
                parent = parent._children[sub_str]

            last = self._canonicalize_subscript(subscripts[-1])
            if last in parent._children:
                del parent._children[last]

            # Clean up empty intermediate nodes (no value and no children)
            # Work backwards from deepest to root
            for ancestor, key in reversed(path):
                node = ancestor._children[key]
                if node._value is None and not node._children:
                    del ancestor._children[key]
                else:
                    break  # Stop if we find a non-empty node

    def kill_node(self, subscripts: tuple[Any, ...]) -> None:
        """Delete node value but preserve descendants (ZKILL command).

        ZKILL removes value but keeps children.

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

    def merge_from(self, source: "MArray") -> None:
        """Merge source tree into this node (MERGE command).

        Implements MERGE semantics:
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
# External Call Exception Classes
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
        _rt: MUMPSRuntime instance to pass to target routine
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


def _create_offset_entry_wrapper(
    internal_func: Callable[..., Any],
    offset: int,
    module: types.ModuleType,
    use_dataclass_sync: bool = True,
) -> Callable[..., Any]:
    """Create a wrapper function for entry points with line offset.

    This factory function creates a wrapper that handles entry points at a specific
    line offset within a label. It consolidates the two previously duplicated
    ~100-line offset_wrapper closures into a single parameterized implementation.

    The wrapper handles:
    1. Scope initialization from the shared _scope dict
    2. State creation from the module's RoutineState class
    3. Trampoline loop for internal GOTO handling
    4. GotoExternal handling for external routine transfers
    5. State-to-scope sync on exit

    Args:
        internal_func: The internal function (prefixed with _) to call with offset
        offset: The line offset within the label
        module: The target module containing the routine
        use_dataclass_sync: If True, use __dataclass_fields__ for state sync.
            If False, use dir(state) to find MArray attributes. The first variant
            (True) is more efficient but requires the state class to be a dataclass.
            The second variant (False) is more flexible but slower.

    Returns:
        A wrapper function with signature (rt, _scope=None) -> state

    Example:
        >>> wrapper = _create_offset_entry_wrapper(internal_fn, 5, module, True)
        >>> result = wrapper(runtime, _scope={'X': MArray()})
    """
    from m2py.runtime import MArray

    def offset_wrapper(
        _rt,
        _scope=None,
        _internal=internal_func,
        _offset=offset,
        _module=module,
    ):
        """Wrapper for external GOTO with offset."""
        _scope = _scope if _scope is not None else {}
        _rt._current_routine = _module._routine_name
        _rt._current_source_lines = _module._source_lines
        _rt._current_label_lines = _module._label_lines

        # Create state from scope
        state_class = getattr(_module, "RoutineState", None)
        if state_class:
            state = state_class()
            # Check if this routine uses dynamic locals (_locals dict)
            uses_dynamic = hasattr(state, "_locals")

            # Initialize state from scope
            if uses_dynamic:
                for k, v in _scope.items():
                    if isinstance(v, MArray):
                        state._locals[k] = v
                    else:
                        _m = MArray()
                        _m.value = v
                        state._locals[k] = _m
            else:
                # Static fields - copy from scope
                for k, v in _scope.items():
                    if hasattr(state, k):
                        if isinstance(v, MArray):
                            setattr(state, k, v)
                        else:
                            # For static state, check what the field expects
                            current_val = getattr(state, k)
                            if isinstance(current_val, MArray):
                                _m = MArray()
                                _m.value = v
                                setattr(state, k, _m)
                            else:
                                setattr(state, k, v)

            # Helper to sync state back to scope
            def sync_state_to_scope(state, uses_dynamic, use_dataclass):
                if uses_dynamic:
                    _scope.update({k: v for k, v in state._locals.items()})
                elif use_dataclass:
                    # Use __dataclass_fields__ for efficient access
                    for fld in state.__dataclass_fields__:
                        val = getattr(state, fld)
                        if val is not None:
                            _scope[fld] = val
                else:
                    # Use dir() to find MArray attributes
                    for attr in dir(state):
                        if not attr.startswith("_"):
                            val = getattr(state, attr)
                            if isinstance(val, MArray):
                                _scope[attr] = val

            # Helper function to handle GotoExternal
            def handle_goto_external(_goto, state, uses_dynamic, use_dataclass):
                # Sync state back to scope BEFORE transferring control
                sync_state_to_scope(state, uses_dynamic, use_dataclass)
                # Handle nested external GOTO
                run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)

            # Call internal function with offset - wrap in try to catch GotoExternal
            try:
                target, state = _internal(_rt, state, _scope, _start_offset=_offset)
            except GotoExternal as _goto:
                handle_goto_external(_goto, state, uses_dynamic, use_dataclass_sync)
                # Sync final state back to scope
                sync_state_to_scope(state, uses_dynamic, use_dataclass_sync)
                return state

            # Run trampoline
            while target is not None:
                try:
                    if hasattr(_module, "_line_map") and isinstance(target, int):
                        lbl, off = _module._line_map[target]
                        func = getattr(_module, "_" + lbl)
                        target, state = func(_rt, state, _scope, _start_offset=off)
                    else:
                        func = _module._labels[target]
                        target, state = func(_rt, state, _scope)
                except GotoExternal as _goto:
                    handle_goto_external(_goto, state, uses_dynamic, use_dataclass_sync)
                    target = None

            # Sync state back to scope
            sync_state_to_scope(state, uses_dynamic, use_dataclass_sync)
            return state
        else:
            # No state class - call target function directly
            from m2py.core.names import translate_name

            func_name = translate_name(_module._routine_name)
            target_func = getattr(_module, func_name)
            return target_func(_rt, _scope=_scope)

    return offset_wrapper


def resolve_goto_target(goto: GotoExternal) -> Callable[..., Any]:
    """Resolve a GotoExternal exception to the target entry function.

    This extracts the target function from a GotoExternal exception, handling:
    - G ^ROUTINE: Entry label (routine name)
    - G LABEL^ROUTINE: Specific label
    - G LABEL+N^ROUTINE: Label with offset

    Args:
        goto: The GotoExternal exception to resolve

    Returns:
        The target function to call

    Raises:
        LabelNotFoundError: If the target label doesn't exist
        ValueError: If the target offset is invalid
    """
    from m2py.core.names import translate_name

    module = goto.module
    label = goto.label
    offset = goto.offset

    if offset is not None:
        # G +N^ROUTINE or G LABEL+N^ROUTINE - use line dispatch
        if label is not None:
            # G LABEL+N^ROUTINE - compute line from label
            if label not in module._label_lines:
                raise LabelNotFoundError(
                    label,
                    module._routine_name,
                    list(module._label_lines.keys()),
                )
            # _label_lines uses 0-indexed line numbers, add offset
            # Then convert to 1-based for _line_map lookup
            target_line = module._label_lines[label] + offset + 1
        else:
            # G +N^ROUTINE - absolute line offset (already 1-based)
            target_line = offset

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
        # Translate label name to Python function name
        func_name = translate_name(label_name)
        target_func = getattr(module, func_name)

        # If there's a line_offset, create a wrapper that passes _start_offset
        if line_offset > 0:
            # Get the internal function (prefixed with _)
            internal_func_name = "_" + func_name
            if hasattr(module, internal_func_name):
                internal_func = getattr(module, internal_func_name)
                # Use factory to create offset wrapper with dataclass-based sync
                return _create_offset_entry_wrapper(
                    internal_func, line_offset, module, use_dataclass_sync=True
                )

        return target_func
    elif label is not None:
        # G LABEL^ROUTINE - call specific label
        # Translate label name to Python function name (handles digits, %, etc.)
        func_name = translate_name(label)
        if not hasattr(module, func_name):
            raise LabelNotFoundError(
                label,
                module._routine_name,
                list(getattr(module, "_label_lines", {}).keys()),
            )
        return getattr(module, func_name)
    else:
        # G ^ROUTINE - call entry label (same name as routine)
        entry_name = translate_name(module._routine_name)
        if not hasattr(module, entry_name):
            # Fall back to lowercase
            entry_name = translate_name(module._routine_name.lower())
        return getattr(module, entry_name)


def call_external_with_offset(
    module: Any,
    label_name: str,
    line_offset: int,
    _rt: "MUMPSRuntime",
    _scope: Dict[str, Any],
) -> None:
    """Call an external routine's internal function with offset, properly initializing state.

    This function handles the complexity of calling an external routine at a specific
    offset (e.g., D LABEL+N^ROUTINE). It:
    1. Creates a RoutineState for the target routine
    2. Initializes that state from the caller's _scope (so VCOMP, etc. are visible)
    3. Calls the internal function with the offset
    4. Runs the trampoline if control returns to the routine
    5. Syncs state changes back to _scope

    Args:
        module: The imported module for the target routine
        label_name: The label name (Python-translated) to call
        line_offset: The offset within the label
        _rt: MUMPSRuntime instance
        _scope: Shared scope dictionary for variable visibility
    """
    _scope = _scope if _scope is not None else {}

    # Save and set runtime context
    _saved_routine = _rt._current_routine
    _saved_source_lines = _rt._current_source_lines
    _saved_label_lines = _rt._current_label_lines
    _rt._current_routine = module._routine_name
    _rt._current_source_lines = module._source_lines
    _rt._current_label_lines = module._label_lines

    try:
        # Get state class and create instance
        state_class = getattr(module, "RoutineState", None)
        if not state_class:
            raise ValueError(f"Module {module._routine_name} has no RoutineState class")

        state = state_class()

        # Check if state uses dynamic locals or static fields
        uses_dynamic = hasattr(state, "_locals")

        # Initialize state from _scope
        for k, v in _scope.items():
            if isinstance(v, MArray):
                if uses_dynamic:
                    state._locals[k] = v
                else:
                    setattr(state, k, v)
            else:
                _m = MArray()
                _m.value = v
                if uses_dynamic:
                    state._locals[k] = _m
                else:
                    setattr(state, k, _m)

        # Get the internal function
        internal_name = "_" + label_name
        if not hasattr(module, internal_name):
            raise ValueError(
                f"Module {module._routine_name} has no function {internal_name}"
            )
        internal_func = getattr(module, internal_name)

        # Call internal function with offset
        target, state = internal_func(_rt, state, _scope, _start_offset=line_offset)

        # Run trampoline if control returns within the routine
        while target is not None:
            try:
                if hasattr(module, "_line_map") and isinstance(target, int):
                    lbl, off = module._line_map[target]
                    func = getattr(module, "_" + lbl)
                    target, state = func(_rt, state, _scope, _start_offset=off)
                elif isinstance(target, tuple):
                    lbl, off = target
                    func = module._labels[lbl]
                    target, state = func(_rt, state, _scope, _start_offset=off)
                else:
                    func = module._labels[target]
                    target, state = func(_rt, state, _scope)
            except GotoExternal as _goto:
                # Sync state back to scope BEFORE transferring control
                # This ensures variables set in this routine are visible
                # in the target routine (MUMPS has a single symbol table)
                if uses_dynamic:
                    _scope.update({k: v for k, v in state._locals.items()})
                else:
                    for attr in dir(state):
                        if not attr.startswith("_"):
                            val = getattr(state, attr)
                            if isinstance(val, MArray):
                                _scope[attr] = val
                # Handle nested external GOTO
                run_with_goto_support(resolve_goto_target(_goto), _rt, _scope)
                target = None

        # Sync state back to _scope based on state type
        if uses_dynamic:
            _scope.update({k: v for k, v in state._locals.items()})
        else:
            # For static state, copy fields that are MArrays or have values
            for attr in dir(state):
                if not attr.startswith("_"):
                    val = getattr(state, attr)
                    if isinstance(val, MArray):
                        _scope[attr] = val
                    elif val is not None:
                        # Wrap non-MArray values
                        _m = MArray()
                        _m.value = val
                        _scope[attr] = _m
    finally:
        # Restore runtime context
        _rt._current_routine = _saved_routine
        _rt._current_source_lines = _saved_source_lines
        _rt._current_label_lines = _saved_label_lines


def run_with_goto_support(
    entry_func: Callable[..., Any],
    _rt: "MUMPSRuntime",
    _scope: Optional[Dict[str, Any]] = None,
    _args: Optional[list[Any]] = None,
) -> Any:
    """Execute a routine entry point with external GOTO support.

    This function wraps routine execution to catch GotoExternal exceptions
    and transfer control to external routines.

    When a GOTO to an external routine is executed (G ^ROUTINE, G LABEL^ROUTINE),
    it raises GotoExternal. This function catches it and transfers control to
    the target routine, which may itself GOTO to another routine, creating a
    chain of transfers that only ends when a routine QUITs normally.

    The runtime instance is passed explicitly to all routines to ensure shared
    state across external calls. Save/restore of _in_extrinsic ensures correct
    $QUIT tracking — external DO calls are subroutine invocations, so $QUIT
    should be 0 inside them.

    Args:
        entry_func: The entry function to execute (routine's first label)
        _rt: MUMPSRuntime instance to pass to all routines
        _scope: Optional shared scope for cross-routine variable visibility
        _args: Optional list of positional arguments to pass to entry_func
               (used by JOB command to pass actuallist values)

    Returns:
        The return value of the final routine that QUITs normally

    Raises:
        LabelNotFoundError: If GOTO targets a non-existent label
        ImportError: If GOTO targets a routine that cannot be imported
    """
    if _scope is None:
        _scope = {}

    # Save/restore _in_extrinsic for $QUIT tracking
    # DO calls are subroutine invocations, so $QUIT=0 inside them
    _saved_extrinsic = _rt._in_extrinsic
    _rt._in_extrinsic = False

    current_func = entry_func
    current_rt = _rt
    extra_args: list[Any] = _args if _args else []
    while True:
        try:
            _result = current_func(current_rt, *extra_args, _scope=_scope)
            _rt._in_extrinsic = _saved_extrinsic
            return _result
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
                    # _label_lines uses 0-indexed line numbers, add offset
                    # Then convert to 1-based for _line_map lookup
                    target_line = module._label_lines[label] + offset + 1
                else:
                    # G +N^ROUTINE - absolute line offset (already 1-based)
                    target_line = offset

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
                # Translate label name to Python function name
                from m2py.core.names import translate_name

                func_name = translate_name(label_name)
                target_func = getattr(module, func_name)

                # If there's a line_offset, create a wrapper that passes _start_offset
                if line_offset > 0:
                    # Get the internal function (prefixed with _)
                    internal_func_name = "_" + func_name
                    if hasattr(module, internal_func_name):
                        internal_func = getattr(module, internal_func_name)
                        # Use factory to create offset wrapper with dir()-based sync
                        current_func = _create_offset_entry_wrapper(
                            internal_func, line_offset, module, use_dataclass_sync=False
                        )
                    else:
                        current_func = target_func
                else:
                    current_func = target_func
            elif label is not None:
                # G LABEL^ROUTINE - call specific label
                # Translate label name to Python function name (handles digits, %, etc.)
                from m2py.core.names import translate_name

                label_func_name = translate_name(label)
                if not hasattr(module, label_func_name):
                    raise LabelNotFoundError(
                        label,
                        module._routine_name,
                        list(getattr(module, "_label_lines", {}).keys()),
                    ) from goto
                current_func = getattr(module, label_func_name)
            else:
                # G ^ROUTINE - call entry label (same name as routine)
                from m2py.core.names import translate_name

                entry_name = translate_name(module._routine_name)
                if not hasattr(module, entry_name):
                    # Fall back to lowercase
                    entry_name = translate_name(module._routine_name.lower())
                current_func = getattr(module, entry_name)

            # Clear extra_args — JOB arguments only apply to the initial
            # entry point, not to subsequent GOTO targets
            extra_args = []


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
# Global Storage Backend Factory
# =============================================================================


def get_global_storage(backend: str | None = None) -> GlobalStorageBackend:
    """Get global storage backend instance.

    Factory function for global storage backends.

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

    if backend is None:
        backend = os.environ.get("M2PY_GLOBAL_BACKEND", "inmemory")

    backend = backend.lower()

    if backend == "inmemory":
        return InMemoryGlobalStorage()
    elif backend == "sqlite":
        from m2py.runtime.sqlite_storage import SQLiteGlobalStorage

        db_path = os.environ.get("M2PY_SQLITE_DB_PATH", None)
        return SQLiteGlobalStorage(db_path)
    elif backend == "yottadb":
        raise ImportError(
            "YottaDB backend requires the 'yottadb' package. "
            "Install with: pip install yottadb"
        )
    elif backend == "iris":
        raise ImportError(
            "IRIS backend requires the 'intersystems-iris' package. "
            "Install with: pip install intersystems-iris"
        )
    else:
        raise ValueError(
            f"Unknown global storage backend: {backend!r}. "
            "Valid options: 'inmemory', 'sqlite', 'yottadb', 'iris'"
        )


class MUMPSRuntime:
    """Minimal runtime for executing generated MUMPS code.

    Provides output capture for WRITE statements and execution support
    for generated Python code. One instance per process.

    Supports external call context tracking (_current_routine, _current_source_lines,
    _current_label_lines, get_text()), and global storage configuration via
    global_storage parameter or M2PY_GLOBAL_BACKEND environment variable.
    """

    def __init__(
        self,
        global_storage: GlobalStorageBackend | None = None,
        codegen_callback: Any = None,
        max_error_nesting: int = 20,
    ) -> None:
        """Initialize runtime with empty state.

        Args:
            global_storage: Optional global storage backend. If None,
                uses get_global_storage() which respects M2PY_GLOBAL_BACKEND
                environment variable (default: 'inmemory').
            codegen_callback: Optional callable with signature
                (code: str, routine_name: str) -> str
                Used for XECUTE to compile MUMPS code to Python at runtime.
                If None, auto-discovers m2py.codegen.generate_python when needed.
            max_error_nesting: Maximum error handler nesting depth before
                raising RuntimeError (prevents infinite error loops). Default 20.
        """
        # External call context tracking
        self._current_routine: Optional[str] = None
        self._current_source_lines: Optional[List[str]] = None
        self._current_label_lines: Optional[Dict[str, int]] = None
        # Global variable storage
        # Use provided backend or fall back to factory function
        self._globals: GlobalStorageBackend = (
            global_storage if global_storage is not None else get_global_storage()
        )
        # Device abstraction layer
        # _output used by PrincipalDevice via back-reference
        self._output: list[str] = []
        # PrincipalDevice wraps stdout/stdin, accesses self._output via back-reference
        from m2py.runtime.devices import PrincipalDevice

        self._principal_device: PrincipalDevice = PrincipalDevice(runtime=self)
        # Device table: maps device name → MUMPSDevice instance
        self._device_table: dict[str, Any] = {"0": self._principal_device}
        # Current active device for I/O dispatch
        self._current_device: Any = self._principal_device
        # Column/line position tracking for $X, $Y
        # $X/$Y are tracked per-device on the device object.
        # Accessors x() and y() delegate to _current_device.
        # Stack frame tracking for $STACK introspection
        # Replaces the simple _stack_level counter with metadata-rich frames
        self._stack_frames: list[StackFrame] = []
        # $IO — tracked via _current_device.name
        # Extrinsic function context for $QUIT
        self._in_extrinsic: bool = False
        # $ZJOB - last JOB'd process ID
        self._zjob: str = "0"
        # Track all JOB'd child processes for cleanup
        self._job_processes: list = []
        # $PRINCIPAL - principal I/O device
        self._principal: str = "0"  # Initial value of $IO
        # $KEY — tracked per-device on device.key
        # Accessor key() delegates to _current_device.key
        # $SYSTEM - system identification (V,S format)
        self._system: str = "47,m2py"
        # Error processing special variables
        # $ECODE - comma-delimited list of active error codes (empty = no errors)
        self._ecode: str = ""
        # $ETRAP - code string to execute when error occurs
        self._etrap: str = ""
        # $ZERROR - application-supplied error message text
        self._zerror: str = ""
        # Enhanced error handling ISVs
        # $ZTRAP - YDB error trap (label ref or XECUTE code)
        self._ztrap: str = ""
        # $ZSTATUS - full error message from last error
        self._zstatus: str = ""
        # $ZPOSITION - routine+offset of last error
        self._zposition: str = ""
        # Nested error detection flag
        self._in_error_handler: bool = False
        # Stack level where $ETRAP was SET (for unwind target)
        self._etrap_set_level: int = 0
        # Maximum error handler nesting depth (prevents infinite loops)
        self._max_error_nesting: int = max_error_nesting
        # Current error handler nesting depth
        self._error_nesting_depth: int = 0
        # ZSYSTEM exit code
        self._zsystem_exit: int = 0
        # $ZSEARCH iterator state
        self._zsearch_results: list[str] = []
        self._zsearch_index: int = 0
        # Transaction restart variable snapshots (one per $TLEVEL)
        self._transaction_snapshots: list[TransactionLocalSnapshot] = []
        # $STACK snapshot (frozen on error)
        self._stack_snapshot: Optional[list[StackFrame]] = None
        self._stack_snapshot_depth: int = 0
        # $ZRO — routine search path (configurable)
        self._zro: str = "."
        # Routine registry for ZLINK
        self._routines: Dict[str, Any] = {}
        # $TEST value for tracking IF/ELSE condition results
        # This is synced from/to generated code via execute_mumps
        self._test: bool = False
        # IRIS/Caché special variables (024-vista-transpilation-fixes, US4)
        # $ZA — last I/O activity status (read-only, default 0)
        self._za: int = 0
        # $ZREFERENCE / $ZR — last global reference (read+set)
        self._zreference: str = ""
        # $NAMESPACE — current namespace (read+set+NEW, default "VISTA")
        self._namespace: str = "VISTA"
        # Miscellaneous ISVs (024-vista-transpilation-fixes, US5)
        # $ZINTERRUPT / $ZINT — interrupt handler code string
        self._zinterrupt: str = ""
        # $ZSOURCE — source file being loaded/compiled
        self._zsource: str = ""
        # $ZGBLDIR — global directory path
        self._zgbldir: str = ""
        # JOB command support: virtual process ID for child processes
        # None = use os.getpid() (main process). Set to a unique ID for child processes.
        self._job_id: int | None = None
        # Codegen callback for XECUTE: (code, routine_name) -> python_source
        # If None, auto-discovered from m2py.codegen when first needed.
        self._codegen_callback = codegen_callback

    def _get_codegen_callback(self) -> Any:
        """Get the codegen callback, using auto-discovery if not explicitly set."""
        if self._codegen_callback is not None:
            return self._codegen_callback
        # Lazy auto-discovery via importlib (avoids `from m2py.codegen` import)
        import importlib

        try:
            codegen_mod = importlib.import_module("m2py.codegen")
            self._codegen_callback = codegen_mod.generate_python
            return self._codegen_callback
        except ImportError:
            raise RuntimeError(
                "XECUTE requires codegen support. "
                "Pass codegen_callback to MUMPSRuntime(), or ensure m2py.codegen is available."
            ) from None

    @property
    def globals(self) -> GlobalStorageBackend:
        """Get global variable storage backend.

        Provides access to global variable storage for
        generated code. The backend is selected via M2PY_GLOBAL_BACKEND
        environment variable (default: 'inmemory').
        """
        return self._globals

    def _get_module_safe(self, routine_name: str) -> Optional[types.ModuleType]:
        """Safely get a module by name, returning None if not found.

        Used by $TEXT to handle non-existent routines gracefully.
        Per MUMPS spec, $TEXT returns empty string for non-existent routines.

        Args:
            routine_name: Name of the routine/module to import

        Returns:
            The imported module, or None if import fails
        """
        import importlib

        # First check if already in sys.modules
        if routine_name in sys.modules:
            return sys.modules[routine_name]

        # Try to import
        try:
            return importlib.import_module(routine_name)
        except (ModuleNotFoundError, ImportError):
            return None

    def get_text(
        self,
        offset: int,
        label: Optional[str] = None,
        module: Optional[types.ModuleType] = None,
        is_external: bool = False,
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
            module: Module containing _source_lines (None = current routine,
                    unless is_external=True in which case None means not found)
            is_external: True if this is an external routine reference.
                        When True and module is None, returns empty (routine not found).

        Returns:
            Source line text, or empty string if:
            - Offset is past end of routine
            - Offset is negative
            - Label not found
            - External routine not found (is_external=True, module=None)
        """
        # Handle case where external routine was requested but not found
        if is_external and module is None:
            return ""

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
            # YDB converts tabs to single space in $TEXT output
            return lines[line_idx].replace("\t", " ")
        return ""

    def get_text_indirect(self, label: str, offset: int = 0, module: Any = None) -> str:
        """Get source text line with indirected label ($TEXT with @).

        Handles $TEXT(@X) and $TEXT(@X+N) where X contains a label name.
        The resolved label is used to look up the source line.

        Args:
            label: Label name (resolved from indirection)
            offset: Line offset from label (default 0)
            module: Optional external routine module. If provided, use its
                    _source_lines and _label_lines instead of the current routine's.

        Returns:
            Source line text, or empty string if label not found or offset
            is out of bounds.
        """
        if module is not None:
            lines = getattr(module, "_source_lines", [])
            label_lines = getattr(module, "_label_lines", {})
        else:
            lines = self._current_source_lines or []
            label_lines = self._current_label_lines or {}

        # Look up the label
        base_idx = label_lines.get(label, -1)
        if base_idx < 0:
            return ""  # Label not found

        line_idx = base_idx + offset

        # Bounds check and return
        if 0 <= line_idx < len(lines):
            return lines[line_idx].replace("\t", " ")
        return ""

    def write(self, value: Any) -> None:
        """Capture WRITE output and update $X/$Y position tracking.

        Delegates to the current device's write method. The device handles
        $X tracking internally. Output goes to the device's buffer.

        Args:
            value: Value to write (converted to string)

        Note:
            Does not add newlines automatically (MUMPS WRITE doesn't either).
            None values are treated as empty string (MUMPS undefined semantics).
            Uses m_format_output for canonical number formatting.

        YDB verified: When writing strings, $X is incremented only for printable
        characters (ord >= 32). Control characters (ord 0-31) do NOT affect $X.
        $Y is NEVER changed by write(). Only format controls (W !, W #) affect $Y.
        """
        if value is None:
            s = ""
        else:
            s = m_format_output(value)

        self._current_device.write(s)

    def write_newline(self) -> None:
        """Write newline with proper $X/$Y handling (W ! format control).

        MUMPS W ! (newline) behavior (YDB verified):
        - Outputs newline character
        - $X is reset to 0
        - $Y is incremented by 1

        This is different from writing a newline in a string, which does NOT
        affect $X or $Y position tracking.
        """
        self._current_device.write_newline()

    def write_raw(self, s: str) -> None:
        """Write raw string to output without updating $X/$Y.

        Used for output that should appear in the byte stream but should not
        affect the MUMPS position tracking. For example, when simulating the
        YDB> prompt placeholder in test output normalization.

        Args:
            s: String to write directly to output
        """
        self._current_device.write_raw(s)

    def write_formfeed(self, debug: bool = False) -> None:
        """Write form feed with proper $X/$Y handling.

        MUMPS W # (form feed) behavior (YDB verified):
        1. If $X > 0, outputs a newline first (moves to new line)
        2. Outputs form feed character (0x0C)
        3. $X is reset to 0, $Y is reset to 0

        Note: YDB does NOT output a trailing newline after form feed.
        The form feed character is output alone.
        """
        self._current_device.write_formfeed(debug=debug)

    def write_tab(self, column: int) -> None:
        """Tab to specified column position (MUMPS ?n format control).

        MUMPS semantics: If current column ($X) < target, write spaces to reach
        the target column. If current column >= target, do nothing.

        Args:
            column: Target column (0-based, same as $X)

        Implements column positioning for WRITE ?n.
        """
        self._current_device.write_tab(column)

    def get_output(self) -> str:
        """Return accumulated WRITE output.

        Returns:
            Concatenated string of all write() calls
        """
        return "".join(self._output)

    def clear(self) -> None:
        """Clear accumulated output and reset position tracking."""
        self._output.clear()
        self._principal_device.x_pos = 0
        self._principal_device.y_pos = 0

    # =========================================================================
    # Device-Routed READ Methods
    # =========================================================================

    def read_line(self) -> str:
        """Read a full line from the current device (MUMPS READ X).

        Delegates to self._current_device.read(). Updates $KEY on the
        current device. Returns the data read (without terminator).

        Routes READ through device layer so that USE "file" followed by
        READ X reads from the file, not stdin.

        Returns:
            String data read from the current device.
        """
        data, key = self._current_device.read()
        return data

    def read_line_timeout(self, timeout: float) -> tuple[str, int]:
        """Read from current device with timeout (MUMPS READ X:t).

        Delegates to self._current_device.read(timeout=timeout).
        Sets $TEST to 1 on success, 0 on timeout. Updates $KEY.

        Args:
            timeout: Timeout in seconds.

        Returns:
            Tuple of (data, test_flag) where test_flag is 1 if data
            was read, 0 if timeout expired.
        """
        data, key = self._current_device.read(timeout=timeout)
        if key:
            # Read succeeded (got a terminator)
            return (data, 1)
        elif data:
            # Got data but no terminator (e.g., EOF)
            return (data, 1)
        else:
            # Timeout — no data, no key
            return ("", 0)

    def read_char(self) -> str:
        """Read single character from current device (MUMPS READ *X).

        Returns the ASCII value of the character as a string, matching
        MUMPS semantics where R *X sets X to the ASCII code.

        Returns:
            ASCII code of read character as string, or "-1" on EOF.
        """
        char = self._current_device.read_char()
        if char:
            return str(ord(char))
        return "-1"

    def read_maxlen(self, maxlen: int) -> tuple[str, str]:
        """Read up to maxlen characters from current device (MUMPS READ X#n).

        Updates $KEY on the current device.

        Args:
            maxlen: Maximum number of characters to read.

        Returns:
            Tuple of (data, key) where key is the terminator character
            or empty string if maxlen was reached.
        """
        data, key = self._current_device.read(maxlen=maxlen)
        return (data, key)

    def read_maxlen_timeout(self, maxlen: int, timeout: float) -> tuple[str, str, int]:
        """Read up to maxlen chars with timeout (MUMPS READ X#n:t).

        Updates $KEY and $TEST on current device.

        Args:
            maxlen: Maximum number of characters to read.
            timeout: Timeout in seconds.

        Returns:
            Tuple of (data, key, test_flag) where test_flag is 1 if
            read completed, 0 if timeout expired.
        """
        data, key = self._current_device.read(maxlen=maxlen, timeout=timeout)
        if key:
            return (data, key, 1)
        elif data:
            return (data, "", 1)
        else:
            return ("", "", 0)

    # =========================================================================
    # Z-Command Support Methods
    # =========================================================================

    @staticmethod
    def _zwr_encode_string(s: str) -> str:
        """Encode a string in YDB ZWR format, handling non-printable characters.

        ZWR format encodes non-printable characters (ASCII 0-31, 127) using
        $C(n) or $CHAR(n) syntax. Printable segments are quoted, and non-
        printable characters are concatenated with _.

        Examples:
            "hello"           -> "hello"
            "hello\\x00"      -> "hello"_$C(0)
            "\\x00world"      -> $C(0)_"world"
            "a\\x00\\x01b"    -> "a"_$C(0,1)_"b"
            "a\\x00b\\x01c"   -> "a"_$C(0)_"b"_$C(1)_"c"

        Args:
            s: String to encode

        Returns:
            ZWR-encoded string (with quotes/escaping as needed)
        """
        # Check if string has any non-printable characters
        has_nonprintable = any(ord(c) < 32 or ord(c) == 127 for c in s)
        if not has_nonprintable:
            # Simple case: just quote with double-quote escaping
            escaped = s.replace('"', '""')
            return f'"{escaped}"'

        # Build segments: alternating printable and non-printable
        segments: list[str] = []
        i = 0
        while i < len(s):
            c = s[i]
            if ord(c) < 32 or ord(c) == 127:
                # Collect consecutive non-printable characters
                codes: list[int] = []
                while i < len(s) and (ord(s[i]) < 32 or ord(s[i]) == 127):
                    codes.append(ord(s[i]))
                    i += 1
                segments.append("$C(" + ",".join(str(c) for c in codes) + ")")
            else:
                # Collect consecutive printable characters
                start = i
                while i < len(s) and not (ord(s[i]) < 32 or ord(s[i]) == 127):
                    i += 1
                chunk = s[start:i]
                escaped = chunk.replace('"', '""')
                segments.append(f'"{escaped}"')

        return "_".join(segments)

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

        # Non-numeric strings get ZWR-encoded (handles non-printable chars)
        return self._zwr_encode_string(s)

    def zwrite(self, scope: dict[str, Any]) -> None:
        """ZWRITE - display all local variables.

        Argumentless ZWRITE shows all locals.

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
            # Otherwise it's a string subscript - ZWR-encode it
            return self._zwr_encode_string(sub)

        # Fallback: ZWR-encode non-numeric values
        return self._zwr_encode_string(str(sub))

    def zwrite_local(
        self,
        name: str,
        subscripts: tuple[str, ...],
        scope: dict[str, Any],
        *,
        range_start: Any = None,
        range_end: Any = None,
    ) -> None:
        """ZWRITE - display a local variable and its descendants.

        Args:
            name: Variable name (Python scope key, e.g., "_pct_FOO" for %FOO)
            subscripts: Subscript path (empty for unsubscripted)
            scope: Variable scope dictionary
            range_start: Optional lower bound for subscript range (inclusive)
            range_end: Optional upper bound for subscript range (inclusive)
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

        # Output this node and descendants (with optional range filtering)
        self._zwrite_marray(
            mumps_name,
            subs_list,
            node,
            range_start=range_start,
            range_end=range_end,
        )

    def _zwrite_marray(
        self,
        base_name: str,
        subscripts: list[Any],
        node: "MArray",
        *,
        range_start: Any = None,
        range_end: Any = None,
    ) -> None:
        """Output an MArray node and its descendants in ZWRITE format.

        Args:
            base_name: Variable name (e.g., "X")
            subscripts: List of subscripts to this node (may be empty)
            node: The MArray node to output
            range_start: If set, only output children >= this value (MUMPS collation)
            range_end: If set, only output children <= this value (MUMPS collation)
        """
        # Build the path string with comma-separated subscripts
        if subscripts:
            subs_str = ",".join(self._format_subscript(s) for s in subscripts)
            path = f"{base_name}({subs_str})"
        else:
            path = base_name

        # Output value at this node if it exists
        # (only when no range filter is active — ranges apply to children)
        if node._value is not None and range_start is None and range_end is None:
            self.write(f"{path}={self._quote_value(node._value)}\n")

        # Compute collation keys for range bounds (if applicable)
        start_key = (
            _mumps_collation_key(range_start) if range_start is not None else None
        )
        end_key = _mumps_collation_key(range_end) if range_end is not None else None

        # Output children recursively in MUMPS collation order
        for sub in sorted(node._children.keys(), key=_mumps_collation_key):
            # Apply range filtering at this level
            if start_key is not None:
                if _mumps_collation_key(sub) < start_key:
                    continue
            if end_key is not None:
                if _mumps_collation_key(sub) > end_key:
                    break  # Sorted order — no more matches possible

            child = node._children[sub]
            # Children of range-filtered nodes are NOT range-filtered
            self._zwrite_marray(base_name, subscripts + [sub], child)

    def zwrite_global(
        self,
        name: str,
        subscripts: tuple[str, ...],
        *,
        range_start: Any = None,
        range_end: Any = None,
    ) -> None:
        """ZWRITE - display a global variable and its descendants.

        Args:
            name: Global name (without ^)
            subscripts: Subscript path (empty for unsubscripted)
            range_start: Optional lower bound for subscript range (inclusive)
            range_end: Optional upper bound for subscript range (inclusive)
        """
        # If no range filtering, output value at this node
        if range_start is None and range_end is None:
            value = self.globals.get(name, subscripts)
            if value is not None:
                if subscripts:
                    sub_str = ",".join(self._format_subscript(s) for s in subscripts)
                    self.write(f"^{name}({sub_str})={self._quote_value(value)}\n")
                else:
                    self.write(f"^{name}={self._quote_value(value)}\n")

        # Get descendants using $ORDER
        current_sub: Any = ""  # Empty string = get first
        if range_start is not None:
            # Start from just before range_start by using ORDER from ""
            # and skipping until >= range_start
            pass  # We'll filter below

        while True:
            next_sub = self.globals.order(
                name, subscripts + (current_sub,), direction=1
            )
            if not next_sub:
                break

            # Apply range filtering
            if range_start is not None:
                if _mumps_collation_key(next_sub) < _mumps_collation_key(range_start):
                    current_sub = next_sub
                    continue
            if range_end is not None:
                if _mumps_collation_key(next_sub) > _mumps_collation_key(range_end):
                    break  # Sorted — no more matches

            # Recursively output this subtree (no range filter for children)
            self.zwrite_global(name, subscripts + (next_sub,))
            current_sub = next_sub

    def _zwrite_var(self, name: str, value: Any) -> None:
        """Output a single variable in ZWRITE format."""
        if isinstance(value, MArray):
            self._zwrite_marray(name, [], value)
        else:
            self.write(f"{name}={self._quote_value(value)}\n")

    def zshow(self, codes: str, scope: dict[str, Any], destination: Any = None) -> None:
        """ZSHOW - display system information.

        Displays process information based on the codes parameter.

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
        codes = codes.upper() if codes else "*"

        for code in codes:
            if code == "V" or code == "*":
                # Variables - like ZWRITE
                self.zwrite(scope)
            if code == "S" or code == "*":
                # Stack trace — use MUMPS-style frames, not Python traceback
                for i, frame in enumerate(self._stack_frames):
                    place = frame.label or ""
                    if frame.routine:
                        place = (
                            f"{place}^{frame.routine}" if place else f"^{frame.routine}"
                        )
                    self.write(f"{place}\n")
                if not self._stack_frames:
                    # No stack frames — show at least a top-level marker
                    self.write("\n")
            if code == "D" or code == "*":
                # Devices
                self.write(f"$IO={self._io}\n")
                self.write("$PRINCIPAL=0\n")  # Principal device is always "0"
            if code == "J" or code == "*":
                # Job/process information
                import os

                self.write(f"$JOB={self.job()}\n")
                self.write(f"$ZJOB={self._zjob}\n")
                self.write(f"PID={os.getpid()}\n")
                backend = type(self._globals).__name__
                self.write(f"Global storage={backend}\n")
            if code == "L" or code == "*":
                # Lock information
                self._zshow_locks()
            if code == "I" or code == "*":
                # Intrinsic special variables — output all ISVs m2py tracks,
                # matching YDB's alphabetical ZSHOW "I" format.
                self.write(f'$DEVICE="{self.device_status()}"\n')
                self.write(f'$ECODE="{self._ecode}"\n')
                self.write(f"$ESTACK={self.estack()}\n")
                self.write(f'$ETRAP="{self._etrap}"\n')
                self.write(f'$HOROLOG="{self.horolog()}"\n')
                self.write(f"$IO={self.io()}\n")
                self.write(f"$JOB={self.job()}\n")
                self.write(f'$KEY="{self.key()}"\n')
                self.write(f"$PRINCIPAL={self.principal()}\n")
                self.write(f"$QUIT={self.quit_flag()}\n")
                self.write(f'$REFERENCE="{self.reference()}"\n')
                self.write(f"$STACK={self.stack_level()}\n")
                self.write("$STORAGE=2147483647\n")
                self.write(f'$SYSTEM="{self.system()}"\n')
                self.write(f"$TEST={1 if self._test else 0}\n")
                self.write(f"$TLEVEL={self.tlevel()}\n")
                self.write("$TRESTART=0\n")
                self.write(f"$X={self.x()}\n")
                self.write(f"$Y={self.y()}\n")
                self.write(f'$ZERROR="{self._zerror}"\n')
                self.write(f'$ZPOSITION="{self._zposition}"\n')
                self.write(f'$ZSTATUS="{self._zstatus}"\n')
                self.write(f"$ZSYSTEM={self._zsystem_exit}\n")
                self.write(f'$ZTRAP="{self._ztrap}"\n')

    def _zshow_locks(self) -> None:
        """Display lock information for ZSHOW "L".

        Queries SQLite lock table for current
        process's locks. Format matches YDB:
            MLG:n,MLT:0
            LOCK ^name LEVEL=count
            LOCK ^name(sub) LEVEL=count
        """
        import json

        rows = self._globals.get_locks()

        total_locks = len(rows)
        self.write(f"MLG:{total_locks},MLT:0\n")

        for name, json_subs, count in rows:
            subs = json.loads(json_subs)
            if subs:
                sub_str = (
                    "("
                    + ",".join(
                        f'"{s}"' if not self._is_mumps_number(s) else s for s in subs
                    )
                    + ")"
                )
                self.write(f"LOCK ^{name}{sub_str} LEVEL={count}\n")
            else:
                self.write(f"LOCK ^{name} LEVEL={count}\n")

    @staticmethod
    def _is_mumps_number(s: str) -> bool:
        """Check if string is a MUMPS canonical number."""
        try:
            float(s)
            return True
        except ValueError:
            return False

    def zlink(self, routine_name: str) -> None:
        """ZLINK - dynamically link/load a routine.

        Imports a routine module and registers it in the routine registry.

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

        ZGOTO unwinds to specified stack level.
        """

        def __init__(self, level: int, target: str | None = None):
            self.level = level
            self.target = target
            super().__init__(
                f"ZGOTO to level {level}" + (f":{target}" if target else "")
            )

    def zsystem(self, command: str = "") -> None:
        """ZSYSTEM - execute a shell command.

        Executes command via subprocess and stores exit
        code in _zsystem_exit. Captured stdout is written to the
        WRITE buffer so it appears in the routine's output (matching YDB).
        Empty string is a no-op that sets exit code to 0.

        Args:
            command: Shell command string to execute
        """
        import subprocess

        cmd = str(command)
        if not cmd:
            self._zsystem_exit = 0
            return

        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        self._zsystem_exit = result.returncode
        if result.stdout:
            self.write(result.stdout)

    def zsystem_exit(self) -> int:
        """Return $ZSYSTEM - exit code from last ZSYSTEM command.

        Accessor for _zsystem_exit field.

        Returns:
            Exit code from last ZSYSTEM command (0 if never executed)
        """
        return self._zsystem_exit

    # =========================================================================
    # Special Variable Accessor Methods
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

        Returns the virtual job ID for child processes spawned by JOB,
        or the actual OS process ID for the main process.

        Returns:
            Process ID (real or virtual)
        """
        import os

        if self._job_id is not None:
            return self._job_id
        return os.getpid()

    def zjob(self) -> str:
        """Return last JOB'd process ID ($ZJOB).

        Returns the process ID of the last process
        started by the JOB command. Returns "0" if no JOB has been executed.

        Returns:
            Process ID as string (matches MUMPS convention)
        """
        return self._zjob

    def zsearch(self, pattern: str) -> str:
        """Implement $ZSEARCH — file system search with iterator state.

        First call with a non-empty pattern performs glob.glob(pattern),
        stores results, and returns the first match. Subsequent calls with
        empty string return the next match. Returns empty string when exhausted.

        Args:
            pattern: File glob pattern, or "" for next match

        Returns:
            Full path of matching file, or "" if no more matches
        """
        import glob

        pat = str(pattern)
        if pat:
            # New search — perform glob and reset iterator
            self._zsearch_results = sorted(glob.glob(pat))
            self._zsearch_index = 0

        if self._zsearch_index < len(self._zsearch_results):
            result = self._zsearch_results[self._zsearch_index]
            self._zsearch_index += 1
            return result
        return ""

    def zro(self) -> str:
        """Return $ZRO — routine search path.

        Returns the configured routine search path.

        Returns:
            Routine search path string
        """
        return self._zro

    def set_zro(self, value: str) -> None:
        """Set $ZRO — routine search path.

        Allows runtime configuration of the routine search path.

        Args:
            value: New routine search path string
        """
        self._zro = str(value)

    @property
    def _io(self) -> str:
        """Current I/O device name, derived from _current_device.name."""
        return self._current_device.name

    @_io.setter
    def _io(self, value: str) -> None:
        """Setter kept for backward compat — ignored (device switch handles it)."""
        pass

    def io(self) -> str:
        """Return current I/O device name ($IO).

        Returns the name of the current device.

        Returns:
            Current I/O device identifier (default "0")
        """
        return self._current_device.name

    def principal(self) -> str:
        """Return principal I/O device name ($PRINCIPAL).

        $PRINCIPAL identifies the principal I/O device.
        It is constant throughout the active life of a process.
        The initial value equals the initial value of $IO.

        Returns:
            Principal device identifier (default "0")
        """
        return self._principal

    def key(self) -> str:
        """Return last READ terminator ($KEY).

        Returns $KEY from the current device — the control sequence that
        terminated the last READ command. Empty string if no READ
        has been executed or if READ timed out.

        Returns:
            Last READ terminator character(s), or empty string
        """
        return self._current_device.key

    def system(self) -> str:
        """Return system identification ($SYSTEM).

        $SYSTEM returns "V,S" where V is the MDC-assigned implementor
        number and S is implementor-defined. Value format must match
        pattern 1.N1\",\"1.E.

        Returns:
            System identification string (e.g., "47,m2py")
        """
        return self._system

    def x(self) -> int:
        """Return current column position ($X).

        Returns $X from the current device.

        Returns:
            Current column position (0-based)
        """
        return self._current_device.x_pos

    def y(self) -> int:
        """Return current line position ($Y).

        Returns $Y from the current device.

        Returns:
            Current line position
        """
        return self._current_device.y_pos

    def set_x(self, value) -> None:
        """Set cursor column position ($X).

        MUMPS allows SET $X=n to control cursor column position.
        Common VistA pattern: S $X=0 to reset column after manual positioning.

        Args:
            value: New column position (coerced to int via MUMPS numeric rules)
        """
        from m2py.codegen.helpers import m_num

        self._current_device.x_pos = int(m_num(value))

    def set_y(self, value) -> None:
        """Set cursor line position ($Y).

        MUMPS allows SET $Y=n to control cursor line position.
        Common VistA pattern: S $Y=0 to reset line counter after page break.

        Args:
            value: New line position (coerced to int via MUMPS numeric rules)
        """
        from m2py.codegen.helpers import m_num

        self._current_device.y_pos = int(m_num(value))

    def device_control(self, keyword: str, *params) -> None:
        """Handle device control mnemonics (W /keyword).

        Device control commands are implementation-specific extensions for device I/O:
        /EOF, /WAIT, /LISTEN, /ACCEPT, /PASS, /CLEAR, /FLUSH, etc.

        Delegates to the current device's device_control() method, which is a
        no-op by default. Specific device subclasses may override for
        device-specific behavior (e.g., TCP socket operations).

        Args:
            keyword: Control keyword (e.g. 'EOF', 'WAIT', 'LISTEN')
            *params: Optional parameters
        """
        self._current_device.device_control(keyword, *params)

    # -----------------------------------------------------------------
    # IRIS/Caché special variable accessors (024-vista-transpilation-fixes)
    # -----------------------------------------------------------------

    def zversion(self) -> str:
        """Return $ZVERSION — transpiler version string.

        IRIS returns something like ``"IRIS for UNIX (Ubuntu Server LTS for x86-64) ..."``.
        We return an M2PY marker so ``$L($ZV)>0`` is true.
        """
        import platform

        return f"M2PY for Python 1.0 ({platform.system()} {platform.machine()})"

    def za(self) -> int:
        """Return $ZA — last I/O activity status (read-only, default 0)."""
        return self._za

    def zreference(self) -> str:
        """Return $ZREFERENCE ($ZR) — last global reference.

        Delegates to the global storage backend which tracks references
        automatically on every get/set/kill operation.
        """
        return self._globals.last_global_ref

    def set_zreference(self, value: str) -> None:
        """Set $ZREFERENCE ($ZR)."""
        self._zreference = str(value)

    def namespace(self) -> str:
        """Return $NAMESPACE."""
        return self._namespace

    def set_namespace(self, value: str) -> None:
        """Set $NAMESPACE."""
        self._namespace = str(value)

    # -----------------------------------------------------------------
    # Miscellaneous ISV accessors (024-vista-transpilation-fixes, US5)
    # -----------------------------------------------------------------

    def device_status(self) -> str:
        """Return $DEVICE — current device error status.

        Returns: Empty string (no error) or error description.
        """
        return ""

    def reference(self) -> str:
        """Return $REFERENCE ($R) — last global reference.

        Standard MUMPS $REFERENCE is equivalent to YDB/IRIS $ZREFERENCE.
        """
        return self._globals.last_global_ref

    def zgbldir(self) -> str:
        """Return $ZGBLDIR — global directory file path.

        Returns the path to the current global directory file.
        In m2py, returns an empty string or the configured value.
        """
        return self._zgbldir

    def set_zgbldir(self, value: str) -> None:
        """Set $ZGBLDIR."""
        self._zgbldir = str(value)

    def zinterrupt(self) -> str:
        """Return $ZINTERRUPT ($ZINT) — interrupt handler code string."""
        return self._zinterrupt

    def set_zinterrupt(self, value: str) -> None:
        """Set $ZINTERRUPT ($ZINT) — install interrupt handler."""
        self._zinterrupt = str(value)

    def zsource(self) -> str:
        """Return $ZSOURCE — source file being loaded/compiled."""
        return self._zsource

    def set_zsource(self, value: str) -> None:
        """Set $ZSOURCE — set source file name."""
        self._zsource = str(value)

    def zeof(self) -> int:
        """Return end-of-file indicator ($ZEOF).

        Returns $ZEOF from the current device.
        0 = not at EOF, 1 = at EOF.

        Returns:
            1 if current device is at EOF, 0 otherwise
        """
        return 1 if self._current_device.zeof else 0

    def stack_level(self) -> int:
        """Return current stack level ($STACK).

        Returns:
            Current call stack depth
        """
        return len(self._stack_frames)

    def quit_flag(self) -> int:
        """Return extrinsic function context flag ($QUIT).

        Returns:
            1 if inside extrinsic function ($$label), 0 otherwise
        """
        return 1 if self._in_extrinsic else 0

    def estack(self) -> int:
        """Return $ESTACK — relative error stack depth.

        $ESTACK returns the difference between the current $STACK level
        and the level where NEW $ESTACK was issued (stored in
        _etrap_set_level). This gives a relative stack depth for
        error handling contexts.

        Returns:
            Current stack depth minus the NEW $ESTACK anchor level
        """
        return len(self._stack_frames) - self._etrap_set_level

    def tlevel(self) -> int:
        """Return current transaction nesting level ($TLEVEL).

        Delegates to global storage backend.

        Returns:
            Current transaction depth (0 = no active transaction)
        """
        return self._globals.get_tlevel()

    def ecode(self) -> str:
        """Return current error code list ($ECODE).

        Returns comma-delimited list of active
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

        Setting $ECODE is how applications clear errors (SET $ECODE="")
        or trigger error handlers.

        When $ECODE is cleared (set to ""), the stack snapshot is also reset
        so the next error will capture a fresh snapshot.

        Args:
            value: Error code list (empty string to clear)
        """
        self._ecode = value
        # Clear stack snapshot when $ECODE is cleared
        # Reset to None so _freeze_stack_snapshot() can re-freeze on next error
        if value == "":
            self._stack_snapshot = None
            self._stack_snapshot_depth = 0

    def _append_ecode(self, code: str) -> None:
        """Append an error code to $ECODE accumulator.

        MUMPS $ECODE accumulates error codes with surrounding commas.
        Each code is appended in ",CODE," format. If $ECODE is already non-empty,
        the leading comma of the new code merges with the trailing comma of the
        existing value.

        Examples:
            - Empty $ECODE + "M6" → ",M6,"
            - ",M6," + "M9" → ",M6,M9,"
            - ",M6,M9," + "Z150373850" → ",M6,M9,Z150373850,"

        Args:
            code: Error code without commas (e.g., "M6", "Z150373850")
        """
        if not self._ecode:
            # First error: wrap with commas
            self._ecode = f",{code},"
        else:
            # Append: existing ends with comma, add code + comma
            self._ecode = f"{self._ecode}{code},"

    def etrap(self) -> str:
        """Return current error trap code ($ETRAP).

        Returns M code string to execute when an error occurs
        and $ECODE becomes non-empty.

        Returns:
            Error trap code string, or empty string if not set
        """
        return self._etrap

    def set_etrap(self, value: str) -> None:
        """Set error trap code ($ETRAP).

        Sets the M code to execute on error. Also tracks the stack level
        where $ETRAP was set for QUIT-from-trap unwinding.

        Common patterns:
        - SET $ETRAP="D ^%ZTER Q"  ; Log error and quit
        - SET $ETRAP="G ERROR^ROUTINE"  ; Goto error handler

        SET $ETRAP implicitly NEWs $ZTRAP at this level.
        This provides mutual exclusion - only one trap can be active per level.

        Args:
            value: M code string to execute on error
        """
        self._etrap = value
        # Track level where $ETRAP was SET for unwinding
        self._etrap_set_level = len(self._stack_frames)
        # Mutual exclusion — setting $ETRAP clears $ZTRAP
        if value:
            self._ztrap = ""

    def zerror(self) -> str:
        """Return application error message ($ZERROR).

        Returns application-supplied error message text.
        Typically set by $ZYERROR routine using $ZSTATUS.

        Returns:
            Error message string, or empty string
        """
        return self._zerror

    def set_zerror(self, value: str) -> None:
        """Set application error message ($ZERROR).

        Sets error message text for application error handling.
        Usually set in error handler routines.

        Args:
            value: Error message text
        """
        self._zerror = value

    def ztrap(self) -> str:
        """Return error trap code ($ZTRAP).

        Returns M code to execute on error when $ETRAP is empty.
        $ZTRAP provides GOTO-based error handling semantics.

        Returns:
            Error trap code string, or empty string if not set
        """
        return self._ztrap

    def set_ztrap(self, value: str) -> None:
        """Set error trap code ($ZTRAP).

        Sets M code to execute on error. Unlike $ETRAP,
        $ZTRAP supports GOTO semantics for error transfer:
        - "G label" or "G ^routine" - GOTO to label/routine
        - Other code - executed via XECUTE

        SET $ZTRAP implicitly clears $ETRAP at this level.
        $ETRAP and $ZTRAP are mutually exclusive — setting one clears the other.

        Args:
            value: M code string to execute on error
        """
        self._ztrap = value
        # Mutual exclusion — setting $ZTRAP clears $ETRAP
        if value:
            self._etrap = ""

    def zstatus(self) -> str:
        """Return error status text ($ZSTATUS).

        Returns last error information in YDB format:
        "errorcode,label+offset^routine,%YDB-E-ERRNAME, message"

        Returns:
            Error status string, or empty string if no error
        """
        return self._zstatus

    def set_zstatus(self, value: str) -> None:
        """Set error status text ($ZSTATUS).

        Sets error status string. Normally set by
        the runtime on error, but can be set by application code.

        Args:
            value: Error status text
        """
        self._zstatus = value

    def zposition(self) -> str:
        """Return current code position ($ZPOSITION).

        Returns current position in format:
        "label+offset^routine"

        Note: After error transfer, this shows where the error handler
        is, not where the error occurred. Use $STACK to get error site.

        Returns:
            Current position string, or empty string
        """
        return self._zposition

    def set_zposition(self, value: str) -> None:
        """Set current code position ($ZPOSITION).

        Sets position string. Normally set by
        the runtime during execution.

        Args:
            value: Position string in format "label+offset^routine"
        """
        self._zposition = value

    def _exception_to_ecode(self, exc: Exception) -> str:
        """Map Python exception to MUMPS $ECODE format.

        Converts Python exceptions to MUMPS error codes
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

        from m2py.core.exceptions import LVUNDEFError

        if isinstance(exc, ZeroDivisionError):
            return ",M9,"  # Divide by zero
        elif isinstance(exc, (KeyError, LVUNDEFError)):
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

    def _handle_etrap(
        self,
        exc: Exception,
        _scope: dict,
        *,
        routine: str = "",
        label: str = "",
        offset: int = 0,
    ) -> bool:
        """Handle an exception using $ETRAP or $ZTRAP.

        Implements enhanced MUMPS error handling semantics:
        1. Check for nested error (error during error processing)
        2. If nested: TROLLBACK:$TLEVEL QUIT:$QUIT "" QUIT (unwind)
        3. Populate $ZSTATUS/$ZPOSITION with error info
        4. Freeze stack snapshot (first error only)
        5. Set $ECODE based on exception type
        6. Set $ZERROR to exception message
        7. If $ETRAP is set, execute it
        8. If $ETRAP is empty but $ZTRAP is set, dispatch via _dispatch_ztrap()
        9. Return True if $ECODE was cleared, False otherwise

        When True is returned, the calling code should perform an implicit QUIT.
        When False is returned, the exception should propagate to the caller.

        Args:
            exc: The Python exception that occurred
            _scope: Current variable scope for execute_mumps()
            routine: Routine name where error occurred
            label: Label name where error occurred
            offset: Line offset from label where error occurred

        Returns:
            True if error was handled ($ECODE cleared), False otherwise

        Side Effects:
            - Sets $ECODE, $ZERROR, $ZSTATUS, $ZPOSITION
            - Freezes stack snapshot on first error
            - Executes $ETRAP or $ZTRAP code
        """
        # Nested error detection with depth counting
        self._error_nesting_depth += 1
        if self._error_nesting_depth > self._max_error_nesting:
            # Too many nested errors - prevent infinite loop
            self._error_nesting_depth = 0
            raise RuntimeError(
                f"Maximum error handler nesting depth ({self._max_error_nesting}) exceeded"
            )

        if self._in_error_handler:
            # Error during error processing - unwind
            # TROLLBACK:$TLEVEL QUIT:$QUIT "" QUIT
            if self.tlevel() > 0:
                try:
                    self._globals.transaction_rollback()
                except Exception:
                    pass  # Best effort rollback
            # Propagate to unwind the stack
            self._error_nesting_depth -= 1
            return False

        # Set nested error guard
        self._in_error_handler = True
        try:
            # Check if there's any handler to process the error
            if not self._etrap and not self._ztrap:
                # No handler set - propagate exception without setting $ECODE
                return False

            # Populate $ZSTATUS and $ZPOSITION
            ecode = self._exception_to_ecode(exc)
            # Extract just the error code (e.g., "M6" from ",M6,")
            mcode = ecode.strip(",").split(",")[0] if ecode else ""
            error_code = self._extract_error_code(ecode)
            ydb_code = self._get_ydb_error_name(exc)
            message = str(exc)

            self._zstatus = self._format_zstatus(
                error_code=error_code,
                label=label,
                offset=offset,
                routine=routine,
                ydb_code=ydb_code,
                message=message,
            )
            # $ZPOSITION shows current position (where handler starts, not error site)
            if label and routine:
                self._zposition = f"{label}+{offset}^{routine}"
            elif routine:
                self._zposition = f"+{offset}^{routine}"
            else:
                self._zposition = ""

            # Freeze stack snapshot on first error (empty→non-empty $ECODE)
            # Only accumulate $ECODE on the first occurrence (not during unwind)
            was_empty = self._ecode == ""

            if was_empty:
                # First error: set $ECODE and $ZERROR, freeze snapshot
                self._append_ecode(mcode)
                self._zerror = message
                self._freeze_stack_snapshot()
            # If $ECODE already set, this is a re-fire during unwind — don't re-accumulate

            # Try $ETRAP first, then $ZTRAP fallback
            if self._etrap:
                try:
                    self.execute_mumps(self._etrap, _scope)
                except Exception:
                    # Error in $ETRAP itself - propagate original error
                    return False
            elif self._ztrap:
                # $ZTRAP fallback
                try:
                    self._dispatch_ztrap(_scope)
                except Exception:
                    return False

            # Check if handler cleared $ECODE
            return self._ecode == ""
        finally:
            # Clear nested error guard
            self._in_error_handler = False
            self._error_nesting_depth -= 1

    # Regex to detect GOTO syntax in $ZTRAP values:
    # "G label", "G ^routine", "GOTO label", "GOTO ^routine"
    _ZTRAP_GOTO_RE = __import__("re").compile(
        r"^G(?:OTO)?\s+", __import__("re").IGNORECASE
    )
    # Regex to detect bare label reference (implicit GOTO):
    # "ERR", "ERR^ROUTINE", "ERR+2^ROUTINE"
    _ZTRAP_LABEL_RE = __import__("re").compile(
        r"^[A-Za-z%][A-Za-z0-9]*(?:\+\d+)?(?:\^[A-Za-z%][A-Za-z0-9]*)?$"
    )

    def _dispatch_ztrap(self, _scope: dict) -> None:
        """Dispatch $ZTRAP error handler.

        Handles $ZTRAP with GOTO vs XECUTE semantics:
        - If $ZTRAP matches GOTO pattern (G/GOTO prefix or bare label ref),
          use GOTO semantics — execute as GOTO command
        - Otherwise, use XECUTE semantics — execute as inline code

        GOTO patterns: "G ERR", "GOTO ERR^ROUTINE", "ERR", "ERR+2^RTN"
        XECUTE patterns: 'W "error",!', 'S $EC="" Q'

        Args:
            _scope: Current variable scope

        Raises:
            Exception: If $ZTRAP execution fails
        """
        if not self._ztrap:
            return

        ztrap = self._ztrap.strip()

        # Check for explicit GOTO syntax: "G label" or "GOTO label"
        if self._ZTRAP_GOTO_RE.match(ztrap):
            # GOTO semantics — execute the full GOTO command
            self.execute_mumps(ztrap, _scope)
        elif self._ZTRAP_LABEL_RE.match(ztrap):
            # Bare label reference — implicit GOTO semantics
            self.execute_mumps(f"G {ztrap}", _scope)
        else:
            # XECUTE semantics — execute as inline MUMPS code
            self.execute_mumps(ztrap, _scope)

    def _extract_error_code(self, ecode: str) -> str:
        """Extract the primary error code from $ECODE format.

        Args:
            ecode: $ECODE format string like ",M6," or ",M6,Z150373850,"

        Returns:
            Primary error code (e.g., "M6", "150373850")
        """
        if not ecode:
            return "150373210"  # Generic error
        # Remove surrounding commas and split
        parts = ecode.strip(",").split(",")
        if parts:
            code = parts[0]
            # If it's an M code, convert to numeric for $ZSTATUS
            if code.startswith("M"):
                # Map common M codes to YDB numeric codes
                m_code_map = {
                    "M1": "150373218",  # NAKEDERR
                    "M4": "150373274",  # SELECTFALSE
                    "M6": "150373850",  # LVUNDEF
                    "M9": "150373210",  # DIVZERO
                    "M13": "150373834",  # LABELUNKNOWN
                    "M26": "150373266",  # INVSVN
                    "M28": "150373258",  # RANDARGNEG
                    "M44": "150373250",  # TCOMMITWITHOUTTSTART
                }
                return m_code_map.get(code, "150373210")
            elif code.startswith("Z"):
                return code[1:]  # Strip the Z prefix
            return code
        return "150373210"

    def _get_ydb_error_name(self, exc: Exception) -> str:
        """Get YDB error name for an exception.

        Args:
            exc: Python exception

        Returns:
            YDB error name like "LVUNDEF", "DIVZERO", etc.
        """
        from m2py.core.exceptions import LVUNDEFError

        if isinstance(exc, ZeroDivisionError):
            return "DIVZERO"
        elif isinstance(exc, (KeyError, LVUNDEFError)):
            return "LVUNDEF"
        elif isinstance(exc, RuntimeError):
            msg = str(exc)
            if "NAKEDERR" in msg or "naked" in msg.lower():
                return "NAKEDERR"
            elif "M44" in msg or "TCOMMIT" in msg:
                return "TCOMMIT"
        return "ERRNAME"

    def push_frame(self) -> None:
        """Push a new stack frame (for DO/extrinsic calls).

        Legacy compatibility wrapper — pushes a minimal DO frame.
        New code should use push_stack_frame() for full metadata.
        """
        self._stack_frames.append(StackFrame(frame_type="DO"))

    def pop_frame(self) -> None:
        """Pop a stack frame (for QUIT)."""
        if self._stack_frames:
            self._stack_frames.pop()

    def push_stack_frame(
        self,
        frame_type: str,
        routine: str = "",
        label: str = "",
        offset: int = 0,
        mcode: str = "",
    ) -> None:
        """Push a new frame onto the call stack with full metadata.

        Called at DO, XECUTE, and extrinsic function ($$) entry points.
        Replaces the simple _stack_level increment.

        Args:
            frame_type: One of "DO", "$$", "XECUTE", "ZINTR", "TRIGGER"
            routine: Routine name
            label: Entry label
            offset: Line offset
            mcode: Original MUMPS source line
        """
        self._stack_frames.append(
            StackFrame(
                frame_type=frame_type,
                routine=routine,
                label=label,
                offset=offset,
                mcode=mcode,
            )
        )

    def pop_stack_frame(self) -> None:
        """Pop the top frame from the call stack.

        Called at QUIT/return from DO, XECUTE, or extrinsic function.
        Replaces the simple _stack_level decrement.
        """
        if self._stack_frames:
            self._stack_frames.pop()

    def stack_function(
        self, level: int, info: str = "", *, use_snapshot: bool = False
    ) -> str:
        """Implement $STACK(level[,info]) intrinsic function.

        Returns information about the call stack.
        During error handling ($ECODE non-empty), automatically returns
        data from the frozen snapshot. Otherwise returns live stack.

        Args:
            level: Stack level to query. -1 for current depth.
            info: Optional info code: "PLACE", "MCODE", "ECODE", or ""
            use_snapshot: If True, force snapshot use even if $ECODE is empty

        Returns:
            For level=-1: current stack depth as string
            For level=0 with no info: implementation start info (empty)
            For level=n with no info: frame type string ("DO", "$$", etc.)
            For level=n with "PLACE": "LABEL+offset^ROUTINE"
            For level=n with "MCODE": MUMPS source line
            For level=n with "ECODE": error codes at that level
            For level > stack depth: ""
        """
        # Determine which stack to use
        # Auto-use snapshot when $ECODE is non-empty (error state)
        stack = self._stack_frames
        if (use_snapshot or self._ecode != "") and self._stack_snapshot:
            stack = self._stack_snapshot

        depth = len(stack)

        # $STACK(-1) returns current depth
        if level == -1:
            return str(depth)

        # $STACK(0) returns implementation info (typically empty for us)
        if level == 0:
            return ""

        # Level must be 1-based and within range
        if level < 1 or level > depth:
            return ""

        # Get the frame (level is 1-based, so level 1 = index 0)
        frame = stack[level - 1]

        # Normalize info code to uppercase
        info_upper = info.upper() if info else ""

        # No info code: return frame type
        if not info_upper:
            return frame.frame_type

        # Handle info codes
        if info_upper == "PLACE":
            return f"{frame.label}+{frame.offset}^{frame.routine}"
        elif info_upper == "MCODE":
            return frame.mcode
        elif info_upper == "ECODE":
            return frame.ecode
        else:
            # Unknown info code returns empty
            return ""

    def _freeze_stack_snapshot(self) -> None:
        """Freeze a deep copy of the call stack for $STACK intrinsic function.

        When $ECODE transitions from empty to non-empty (first error),
        freeze the current call stack so $STACK(n) queries return the state
        at the time of the error, not the current (possibly unwound) state.

        The snapshot is only taken once — subsequent errors that accumulate
        into $ECODE do NOT update the snapshot. The snapshot is cleared when
        $ECODE is reset to "" via SET $ECODE="".

        The snapshot includes:
        - Deep copy of all StackFrame objects
        - The depth (len) at time of freeze
        """
        import copy

        if self._stack_snapshot is None:
            self._stack_snapshot = copy.deepcopy(self._stack_frames)
            self._stack_snapshot_depth = len(self._stack_frames)

    def _format_zstatus(
        self,
        error_code: str,
        label: str = "",
        offset: int = 0,
        routine: str = "",
        ydb_code: str = "",
        message: str = "",
    ) -> str:
        """Format error information as $ZSTATUS string.

        $ZSTATUS format matches YDB convention:
        "errorcode,label+offset^routine,%YDB-E-ERRNAME, message"

        Examples:
            "150373850,TEST+3^test,%YDB-E-LVUNDEF, Undefined local variable: X"
            "150373210,FOO+1^bar,%YDB-E-DIVZERO, Attempt to divide by zero"

        When label and routine are empty, the location part is still included
        but with empty values: "150373850,+0^,%YDB-E-LVUNDEF, message"

        Args:
            error_code: Numeric error code (e.g., "150373850")
            label: Label name at error site
            offset: Line offset from label
            routine: Routine name
            ydb_code: YDB error mnemonic (e.g., "LVUNDEF", "DIVZERO")
            message: Human-readable error description

        Returns:
            Formatted $ZSTATUS string
        """
        # Build location part: "label+offset^routine"
        location = f"{label}+{offset}^{routine}"

        # Build YDB error tag: "%YDB-E-ERRNAME"
        ydb_tag = f"%YDB-E-{ydb_code}" if ydb_code else ""

        # Assemble: "errorcode,location,%YDB-E-ERRNAME, message"
        if ydb_tag:
            return f"{error_code},{location},{ydb_tag}, {message}"
        else:
            return f"{error_code},{location}, {message}"

    # =========================================================================
    # Device I/O Methods (OPEN/CLOSE/USE)
    # =========================================================================

    def open_device(
        self,
        device: str,
        parameters: Optional[List[str]] = None,
        timeout: Optional[float] = None,
    ) -> bool:
        """Open a device for I/O (MUMPS OPEN command).

        Opens a device/file for I/O operations using the FileDevice/TCPDevice
        abstraction, device table, per-device parameter parsing, DEVOPENFAIL,
        and timeout/$TEST.

        MUMPS OPEN semantics (YDB-validated):
        - File-not-found / permission errors → raise DEVOPENFAIL regardless of timeout.
        - timeout is for devices that exist but are unavailable (e.g., locked by another
          process). For files, OPEN is immediate — timeout always succeeds.
        - If timeout is present: success → $TEST=1 (return True).
        - If timeout absent: success → return True (does not affect $TEST).
        - Re-opening an already-open device is a no-op (succeeds silently).

        Device type detection:
            - CONNECT param present → TCP device (name = "host:port")
            - Otherwise → File device

        Device parameter keywords (case-insensitive):
            NEWVERSION / NEW / WN → mode "w"  (create/truncate)
            READONLY / R          → mode "r"  (read-only)
            APPEND / A            → mode "a"  (append)
            WRITE / RW            → mode "r+" (read-write, file must exist)
            STREAM                → disables record-size limits
            RECORDSIZE=n          → sets record size limit
            CONNECT               → TCP client connection

        Args:
            device: Device name (file path or "host:port")
            parameters: Device parameters (NEWVERSION, READONLY, CONNECT, etc.)
            timeout: Optional timeout in seconds

        Returns:
            True if device opened successfully, False if timeout
        """
        import socket as socket_mod

        from m2py.runtime.devices import FileDevice, TCPDevice
        from m2py.runtime.exceptions import DeviceOpenFailError

        params = parameters or []

        # If device is already open in device_table, re-OPEN is a no-op
        if device in self._device_table:
            return True

        # Parse device parameters (case-insensitive)
        upper_params = [p.upper() for p in params]

        # ---- TCP device detection ----
        if "CONNECT" in upper_params:
            # Parse host:port from device name
            try:
                if ":" in device:
                    host, port_str = device.rsplit(":", 1)
                    port = int(port_str)
                else:
                    raise DeviceOpenFailError(
                        device, "CONNECT requires host:port format"
                    )
            except ValueError:
                raise DeviceOpenFailError(device, "invalid port number")

            connect_timeout = timeout if timeout is not None else 10.0
            try:
                sock = socket_mod.create_connection(
                    (host, port), timeout=connect_timeout
                )
                sock.settimeout(None)  # Reset to blocking after connect
            except (socket_mod.timeout, TimeoutError):
                if timeout is not None:
                    return False  # $TEST=0
                raise DeviceOpenFailError(device, "connection timed out")
            except OSError as e:
                if timeout is not None:
                    return False  # $TEST=0
                raise DeviceOpenFailError(device, str(e))

            tcp_device = TCPDevice(device, sock)
            self._device_table[device] = tcp_device
            return True

        # ---- File device ----
        mode = "r"  # Default read
        if (
            "NEWVERSION" in upper_params
            or "NEW" in upper_params
            or "WN" in upper_params
        ):
            mode = "w"
        elif "APPEND" in upper_params or "A" in upper_params:
            mode = "a"
        elif "WRITE" in upper_params or "RW" in upper_params:
            mode = "r+"
        elif "READONLY" in upper_params or "R" in upper_params:
            mode = "r"

        # Parse STREAM and RECORDSIZE
        stream = "STREAM" in upper_params
        record_size: int | None = None
        for p in upper_params:
            if p.startswith("RECORDSIZE="):
                try:
                    record_size = int(p.split("=", 1)[1])
                except (ValueError, IndexError):
                    pass

        try:
            file_obj = open(device, mode)  # noqa: SIM115
        except FileNotFoundError:
            # DEVOPENFAIL regardless of timeout (YDB-validated behavior)
            raise DeviceOpenFailError(device, "file not found")
        except PermissionError:
            raise DeviceOpenFailError(device, "permission denied")
        except OSError as e:
            raise DeviceOpenFailError(device, str(e))

        # Create FileDevice and register
        file_device = FileDevice(device, file_obj, mode)
        file_device._stream = stream
        file_device._record_size = record_size
        self._device_table[device] = file_device

        return True

    def close_device(self, device: str, parameters: Optional[List[str]] = None) -> None:
        """Close a device (MUMPS CLOSE command).

        Closes a device/file using the device abstraction layer.

        Closing $PRINCIPAL is a no-op. Closing the current device reverts
        to $PRINCIPAL. $IO is set to "0" after close.

        Args:
            device: Device name to close
            parameters: Optional close parameters (usually ignored)
        """
        # $PRINCIPAL cannot be closed
        if device == "0" or device == self._principal:
            return

        # Close via device_table (preferred path — FileDevice.close() closes file handle)
        if device in self._device_table:
            dev = self._device_table[device]
            try:
                dev.close()
            except (OSError, IOError):
                pass
            del self._device_table[device]

        # If closing current device, switch back to principal device
        if self._current_device.name == device:
            self._current_device = self._principal_device

    def use_device(self, device: str, parameters: Optional[List[str]] = None) -> None:
        """Select current I/O device (MUMPS USE command).

        Switches the current I/O device.
        USE 0 and USE $P switch back to $PRINCIPAL.

        Args:
            device: Device name to make current
            parameters: Optional device parameters
        """
        # USE 0 or USE $PRINCIPAL → switch to principal device
        if device == "0" or device == self._principal:
            self._current_device = self._principal_device
            return

        # Check device_table first (new abstraction)
        if device in self._device_table:
            self._current_device = self._device_table[device]
            return

    # =========================================================================
    # JOB Command Runtime Support
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

        Always uses subprocess.Popen for real process isolation. Requires
        SQLiteGlobalStorage for cross-process global sharing. If
        InMemoryGlobalStorage is in use, creates a temporary SQLite database
        for the subprocess (globals won't be shared back to the parent).

        Timeout behavior per MUMPS spec 8.2.10:
        - No timeout: Returns True, does not affect $TEST
        - Timeout present: Returns True on success ($TEST=1), False on timeout ($TEST=0)

        Args:
            label: Entry point label name
            routine: Routine name (None = current routine)
            args: Arguments to pass to the entry point
            params: Process parameters (e.g., output file redirection)
            timeout: Optional timeout in seconds

        Returns:
            bool: True if job started successfully, False on timeout/failure
        """
        import os
        import tempfile as _tf

        routine_name = routine or self._current_routine

        # Check if we have SQLiteGlobalStorage (cross-process capable)
        db_path = getattr(self._globals, "_db_path", None)

        if db_path is None:
            # InMemoryGlobalStorage — create a temporary SQLite DB for the
            # subprocess. The child process won't share in-memory globals,
            # but this is the expected behavior: JOB requires cross-process
            # storage. Callers needing JOB should use SQLiteGlobalStorage.
            # Use workspace tmp/ if available, otherwise system temp
            _ws_tmp = os.path.join(
                os.path.dirname(
                    os.path.dirname(
                        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    )
                ),
                "tmp",
            )
            _tmp_dir = _ws_tmp if os.path.isdir(_ws_tmp) else None
            fd, db_path = _tf.mkstemp(suffix=".db", dir=_tmp_dir)
            os.close(fd)

        return self._start_job_subprocess(
            label, routine_name, args, params, timeout, db_path
        )

    def _start_job_subprocess(
        self,
        label: Optional[str],
        routine_name: Optional[str],
        args: List[Any],
        params: Optional[List[str]],
        timeout: Optional[float],
        db_path: str,
    ) -> bool:
        """Start JOB as a real subprocess using job_runner.py.

        Creates a real process with independent locals
        and shared globals via SQLite.
        """
        import json
        import os
        import subprocess
        import sys

        if not routine_name:
            self._zjob = "0"
            return timeout is None or False

        entry_label = label or routine_name

        # Build subprocess command
        cmd = [
            sys.executable,
            "-m",
            "m2py.runtime.job_runner",
            "--routine",
            routine_name,
            "--label",
            entry_label,
            "--db-path",
            db_path,
        ]

        if args:
            cmd.extend(["--args", json.dumps([str(a) for a in args])])

        # Process parameters: check for INPUT/OUTPUT/ERROR file redirection
        # YDB syntax: JOB LABEL:(INPUT="file":OUTPUT="file":ERROR="file")
        # Params arrive as strings like "OUTPUT=filename" or just "filename"
        # (legacy: bare string = OUTPUT)
        output_file = None
        input_file = None
        error_file = None
        if params:
            for p in params:
                if isinstance(p, str):
                    p_upper = p.upper()
                    if p_upper.startswith("OUTPUT="):
                        output_file = p[7:]
                    elif p_upper.startswith("INPUT="):
                        input_file = p[6:]
                    elif p_upper.startswith("ERROR="):
                        error_file = p[6:]
                    elif not output_file:
                        # Legacy: bare string = output file
                        output_file = p

        if output_file:
            cmd.extend(["--output", output_file])
        if input_file:
            cmd.extend(["--input", input_file])
        if error_file:
            cmd.extend(["--error", error_file])

        try:
            # Pass parent's sys.path as PYTHONPATH so child can find routines
            env = os.environ.copy()
            env["PYTHONPATH"] = os.pathsep.join(sys.path)

            # Open I/O redirection files for Popen
            # INPUT/OUTPUT/ERROR redirection for JOB'd processes
            stdin_arg = subprocess.DEVNULL
            stdout_arg = subprocess.DEVNULL
            stderr_arg = subprocess.DEVNULL
            opened_files: list = []

            if input_file:
                try:
                    f_in = open(input_file, "r")
                    stdin_arg = f_in
                    opened_files.append(f_in)
                except OSError:
                    pass  # Fall back to DEVNULL

            if output_file:
                try:
                    f_out = open(output_file, "w")
                    stdout_arg = f_out
                    opened_files.append(f_out)
                except OSError:
                    pass

            if error_file:
                try:
                    f_err = open(error_file, "w")
                    stderr_arg = f_err
                    opened_files.append(f_err)
                except OSError:
                    pass

            proc = subprocess.Popen(
                cmd,
                stdin=stdin_arg,
                stdout=stdout_arg,
                stderr=stderr_arg,
                env=env,
            )

            # Close file handles in parent process — child has inherited them
            for f in opened_files:
                f.close()

            # Set $ZJOB to child's real PID
            self._zjob = str(proc.pid)
            # Track child process for cleanup
            self._job_processes.append(proc)

            if timeout is not None:
                # Poll for process start within timeout
                import time

                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    rc = proc.poll()
                    if rc is not None:
                        # Process finished — check if it started successfully
                        # Exit code 1 = import/label error in job_runner
                        if rc != 0:
                            self._zjob = "0"
                            return False  # $TEST=0 — failed to start
                        break
                    time.sleep(0.01)
                return True  # $TEST=1 — process started successfully

            return True

        except OSError:
            self._zjob = "0"
            if timeout is not None:
                return False
            return True

    def kill_job_processes(self, timeout: float = 2.0) -> None:
        """Kill all tracked JOB'd child processes.

        Cleanup for test teardown. Terminates any running
        child processes spawned by JOB commands, then reaps them.

        Args:
            timeout: Seconds to wait for graceful termination before SIGKILL.
        """
        for proc in self._job_processes:
            if proc.poll() is None:
                try:
                    proc.terminate()
                except OSError:
                    pass
        # Brief wait for graceful termination
        import time

        deadline = time.monotonic() + timeout
        for proc in self._job_processes:
            remaining = max(0, deadline - time.monotonic())
            try:
                proc.wait(timeout=remaining)
            except Exception:
                try:
                    proc.kill()
                    proc.wait(timeout=1)
                except OSError:
                    pass
        self._job_processes.clear()

    def get_data(self, name: str, _scope: Dict[str, Any]) -> int:
        """Get $DATA value for variable by name (indirection support).

        Implements $DATA for indirected variables.

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

    def resolve_order_name(
        self,
        inner_value: str,
        _scope: Dict[str, Any],
        levels_remaining: int = 0,
        per_level_subscripts: Optional[List[List[Any]]] = None,
    ) -> str:
        """Resolve multi-level indirection to get the final NAME for $ORDER.

        Used when $ORDER has nested indirection like @@^V(0)@(12,456):
        1. Inner value from ^V(0) = "V(1)"
        2. Merge subscripts at level 0: "V(1)" + (12,456) → "V(1,12,456)"
        3. Dereference for remaining level: V(1,12,456) → "^V(2,3)"
        4. Return "^V(2,3)" as the name for $ORDER

        Args:
            inner_value: Value from innermost expression (e.g., ^V(0) → "V(1)")
            _scope: Current scope dictionary
            levels_remaining: Additional levels to dereference after the first
            per_level_subscripts: Subscripts to merge at each level.
                Level 0 = subscripts for the innermost @ (merged with inner_value).
                Level 1+ = subscripts for subsequent @ levels.

        Returns:
            Final resolved name string for $ORDER to operate on.
        """
        name = inner_value
        pls = per_level_subscripts or []

        # Apply subscripts for the innermost level (level 0)
        if pls and len(pls) > 0 and pls[0]:
            name = self._merge_name_subscripts(name, pls[0], _scope)

        # For each remaining level, look up the value then merge any subscripts
        for lvl in range(levels_remaining):
            # Dereference: look up the value at the current name
            value = self.get_var(name, _scope)
            name = str(value) if value is not None else ""

            # Apply subscripts for this level (if any)
            sub_idx = lvl + 1
            if sub_idx < len(pls) and pls[sub_idx]:
                name = self._merge_name_subscripts(name, pls[sub_idx], _scope)

        return name

    def _merge_name_subscripts(
        self,
        name: str,
        additional_subs: List[Any],
        _scope: Dict[str, Any],
    ) -> str:
        """Merge additional subscripts into a name string.

        E.g., "V(1)" + [12, 456] → "V(1,12,456)"
             "^G" + [1, 2] → "^G(1,2)"
             '^V("A")' + [1, 2] → '^V("A",1,2)'

        Args:
            name: Variable name possibly with subscripts
            additional_subs: Subscripts to append
            _scope: Current scope (for evaluating subscripts)

        Returns:
            Name with merged subscripts
        """
        if not name or not additional_subs:
            return name

        from m2py.core.indirection import IndirectionResolver

        base, existing_subs = _parse_subscripted_name(name)
        evaluated_existing = _evaluate_subscripts(existing_subs, _scope, runtime=self)
        all_subs = list(evaluated_existing or ()) + [str(s) for s in additional_subs]
        if all_subs:
            # Use _append_subscripts which properly quotes string subscripts
            return IndirectionResolver._append_subscripts(base, all_subs)
        return base

    def get_order(
        self,
        name: str,
        _scope: Dict[str, Any],
        direction: int = 1,
        additional_subscripts: Optional[Tuple[Any, ...]] = None,
    ) -> str:
        """Get $ORDER value for variable by name (indirection support).

        Args:
            name: Variable name with subscripts, e.g. "A(1)", "^G(sub)"
                  May also be a nested indirection like "@V1A(20)"
                  May also be a naked reference like "^(1)"
            _scope: Current scope dictionary
            direction: 1 for forward, -1 for reverse
            additional_subscripts: Extra subscripts to append (for @name@(subs) pattern)
                                  These are merged with any subscripts in name

        Returns:
            Next subscript in collation order, or "" if no more
        """
        from m2py.core.values import m_num as _m_num
        from m2py.runtime.helpers import m_order, m_order_global

        # Coerce direction to int - MUMPS $ORDER direction is always numeric
        # This handles cases where direction comes from a function returning a string
        # e.g., $O(ref, $O(V(""))) where $O(V("")) returns "1" as a string
        try:
            direction = int(_m_num(direction))
        except (ValueError, TypeError):
            direction = 1

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
        # Keep values in original form for proper canonicalization by m_order
        evaluated_subs = _evaluate_subscripts(subscripts, _scope, runtime=self)

        # Merge additional subscripts if provided (for @name@(subs) pattern)
        if additional_subscripts:
            if evaluated_subs:
                evaluated_subs = list(evaluated_subs) + list(additional_subscripts)
            else:
                evaluated_subs = list(additional_subscripts)

        subs = tuple(evaluated_subs) if evaluated_subs else ("",)

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

    def m_next_local(
        self,
        array: MArray | None,
        subscripts: tuple,
    ) -> str | int:
        """$NEXT for local variables.

        $NEXT is like $ORDER but:
        - Returns -1 instead of "" when no more subscripts
        - Treats -1 as "start from beginning" (like $ORDER treats "")

        Args:
            array: MArray instance
            subscripts: Tuple of subscript values

        Returns:
            Next subscript, or -1 if no more
        """
        from m2py.runtime.helpers import m_order

        if array is None or not subscripts:
            return -1

        # Convert -1 start marker to "" for $ORDER semantics
        # Keep subscripts in original form (Decimal, int, etc.) for proper canonicalization
        subs = list(subscripts)
        last_sub = str(subs[-1])
        if last_sub == "-1":
            subs[-1] = ""

        result = m_order(array, tuple(subs), 1)
        return -1 if result == "" else result

    def m_next_global(
        self,
        global_name: str,
        subscripts: tuple,
    ) -> str | int:
        """$NEXT for global variables.

        $NEXT is like $ORDER but:
        - Returns -1 instead of "" when no more subscripts
        - Treats -1 as "start from beginning" (like $ORDER treats "")

        Args:
            global_name: Global variable name (without ^)
            subscripts: Tuple of subscript values

        Returns:
            Next subscript, or -1 if no more
        """
        from m2py.runtime.helpers import m_order_global

        if not subscripts:
            return -1

        # Convert -1 start marker to "" for $ORDER semantics
        # Keep subscripts in original form (Decimal, int, etc.) for proper canonicalization
        subs = list(subscripts)
        last_sub = str(subs[-1])
        if last_sub == "-1":
            subs[-1] = ""

        result = m_order_global(self._globals, global_name, tuple(subs), 1)
        return -1 if result == "" else result

    def get_name(
        self,
        name: str,
        extra_subscripts: tuple,
        _scope: Dict[str, Any],
        depth: int | None = None,
    ) -> str:
        """Get $NAME value for variable by name (indirection support).

        For $NAME(@A) where A="X(1,2)", returns "X(1,2)".
        For $NAME(@A@(3)) where A="X(1,2)", returns "X(1,2,3)".
        For $NAME(@A,2) where A="X(1,2,3)", returns "X(1,2)".

        Args:
            name: Variable name (e.g., "X(1,2)", "^G")
            extra_subscripts: Additional subscripts to append
            _scope: Current scope dictionary
            depth: Optional depth parameter (None = all subscripts)

        Returns:
            Canonical name string
        """
        from m2py.runtime.helpers import m_name

        if not name:
            return ""

        # Handle nested indirection
        if name.startswith("@"):
            name = self.resolve_nested_indirection(name, _scope)
            if not name:
                return ""

        # Parse the name into base + subscripts
        base_name, name_subs = _parse_subscripted_name(name)
        evaluated_name_subs = _evaluate_subscripts(name_subs, _scope, runtime=self)

        # Combine with extra subscripts
        all_subs = (
            tuple(evaluated_name_subs) if evaluated_name_subs else ()
        ) + extra_subscripts

        # Check if global
        is_global = base_name.startswith("^")
        if is_global:
            base_name = base_name[1:]

        # Use m_name to build canonical form
        return m_name(base_name, all_subs, depth=depth, is_global=is_global)

    def _append_subscripts_to_name(
        self,
        name: str,
        per_level_subscripts: list[list],
    ) -> str:
        """Append subscripts to a variable name string.

        Used for $NAME(@func()@(subs)) where func() returns a name string
        and we need to append additional subscripts.

        Args:
            name: Variable name string (e.g., "A(1,2)")
            per_level_subscripts: List of subscript lists to append

        Returns:
            Name with all subscripts appended (e.g., "A(1,2,3,4)")
        """
        from m2py.core.indirection import IndirectionResolver

        # Use static method directly - no instance needed
        result = name
        for sub_list in per_level_subscripts:
            if sub_list:
                result = IndirectionResolver._append_subscripts(result, sub_list)
        return result

    def append_subscripts_to_name(
        self,
        name: str,
        subscripts: list,
    ) -> str:
        """Append subscripts to a variable name string.

        Public wrapper for _append_subscripts_to_name that takes a single
        subscript list (not a list of lists).

        Args:
            name: Variable name string (e.g., "A(1,2)")
            subscripts: List of subscripts to append

        Returns:
            Name with subscripts appended (e.g., "A(1,2,3,4)")
        """
        return self._append_subscripts_to_name(name, [subscripts])

    def get_query(self, name: str, subscripts: tuple, _scope: Dict[str, Any]) -> str:
        """Get $QUERY value for variable by name (indirection support).

        Args:
            name: Variable name (e.g., "A", "^G")
            subscripts: Starting subscripts for query
            _scope: Current scope dictionary

        Returns:
            Full variable reference of next valued node, or "" if none
        """
        from m2py.runtime.helpers import m_query, m_query_global

        if not name:
            return ""

        # Handle nested indirection: if name starts with @, resolve it first
        if name.startswith("@"):
            name = self.resolve_nested_indirection(name, _scope)
            if not name:
                return ""

        # Parse any subscripts that are part of the resolved name
        if "(" in name:
            base_name, name_subs = _parse_subscripted_name(name)
            # Combine name subscripts with additional subscripts
            evaluated_name_subs = _evaluate_subscripts(name_subs, _scope, runtime=self)
            all_subs = (
                tuple(str(s) for s in evaluated_name_subs) + subscripts
                if evaluated_name_subs is not None
                else subscripts
            )
        else:
            base_name = name
            all_subs = subscripts

        # Handle global variables
        if base_name.startswith("^"):
            key = base_name[1:]
            if not key:
                # Naked reference
                resolved_name, full_subs = self._globals.resolve_naked(all_subs)
                return m_query_global(self._globals, resolved_name, full_subs)
            return m_query_global(self._globals, key, all_subs)

        # Handle local variables
        arr = _scope.get(base_name, MArray())
        if not isinstance(arr, MArray):
            return ""
        return m_query(arr, base_name, all_subs)

    # Variable access by name string - used AFTER indirection resolution.
    # Codegen calls this when the variable name is dynamically computed (e.g., FOR @A loops).
    # Note: This is NOT deprecated - it's the intended way to access a variable by name string.
    def get_var(self, name: str, _scope: Dict[str, Any]) -> Any:
        """Get variable value by name (name indirection).

        Implements reading a variable by dynamic name.

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
        # Pass self as runtime to handle complex indirection like @@@@@@@@X
        eval_subs = _evaluate_subscripts(subscripts, _scope, runtime=self)

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
        # Pass self as runtime to handle complex indirection like @@@@@@@@X
        eval_subs = _evaluate_subscripts(subscripts, _scope, runtime=self)

        # Use the GlobalStorageBackend interface
        subs = () if eval_subs is None else tuple(str(s) for s in eval_subs)
        result = self._globals.get(key, subs)
        return result if result is not None else ""

    # Variable write by name string - used AFTER indirection resolution.
    # Codegen calls this when the variable name is dynamically computed (e.g., FOR @A loops).
    # Note: This is NOT deprecated - it's the intended way to write a variable by name string.
    def set_var(self, name: str, value: Any, _scope: Dict[str, Any]) -> None:
        """Set variable value by name (name indirection).

        Implements writing a variable by dynamic name.

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

            # Evaluate any variable references in subscripts
            # For example, "^V1A(I)" where I=1 should become "^V1A(1)"
            if "(" in target and (target[0].isalpha() or target[0] in "%^"):
                target = resolver._evaluate_subscripts_in_name(target)

            # Append any per_level_subscripts to the target
            # For @"A(1)"@(2), source="A(1)", per_level_subscripts=[[2]]
            # Target should be "A(1,2)"
            if per_level_subscripts:
                # Get all subscripts from all levels
                all_subs = []
                for level_subs in per_level_subscripts:
                    if level_subs:
                        all_subs.extend(level_subs)
                if all_subs:
                    # Parse existing subscripts from source
                    base_name, existing_subs = _parse_subscripted_name(target)
                    # Combine and build new target (existing_subs may be None)
                    combined_subs = list(existing_subs or []) + [
                        str(s) for s in all_subs
                    ]
                    target = f"{base_name}({','.join(str(s) for s in combined_subs)})"
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
        allow_undefined: bool = False,
    ) -> Any:
        """Get variable value via indirection using unified components.

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
            allow_undefined: If True, return "" for undefined target (for $GET)
                If False, raise IndirectionError for undefined (default, MUMPS UNDEF)

        Returns:
            Value at the resolved variable, or "" if undefined (when allow_undefined=True)

        Raises:
            IndirectionError: If target is undefined and allow_undefined=False

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

            # levels=0 with subscripts (NakedGlobal case):
            # @^(naked)@(subs) where naked resolves to "NAME" → get_var("NAME(subs)")
            get_indirected("NAME", scope, levels=0, per_level_subscripts=[[subs]])
            # Returns value at NAME(subs)

            # $GET(@X, default) - allow undefined target
            get_indirected("X", scope, levels=1, allow_undefined=True)
            # Returns "" if target undefined (caller applies default)
        """
        # Handle levels=0: source is already the resolved target name
        # This is used for NakedGlobal expressions where the target name
        # was computed during code generation
        if levels == 0:
            # If we have per_level_subscripts, append them to the source name
            # This handles @^(naked)@(subs) where naked evaluates to "NAME"
            if per_level_subscripts and any(per_level_subscripts):
                from m2py.core.indirection import IndirectionResolver
                from m2py.core.scope import CurrentScope

                cs = CurrentScope.from_generated_context(_scope)
                resolver = IndirectionResolver(self, cs)

                # Append all subscripts to the source name
                target_name = source
                for sub_list in per_level_subscripts:
                    if sub_list:
                        target_name = resolver._append_subscripts(target_name, sub_list)

                return self.get_var(target_name, _scope)
            else:
                return self.get_var(source, _scope)

        # Use unified IndirectionResolver for all cases
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
        # Skip validation if allow_undefined=True (for $GET)
        if not allow_undefined and not target_name.startswith("^"):
            # Parse subscripted names properly
            from m2py.core.names import NameTranslator

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

    def increment_indirected(
        self,
        source: str,
        _scope: Dict[str, Any],
        increment: str = "1",
        levels: int = 1,
        per_level_subscripts: Optional[List[List[Any]]] = None,
    ) -> str:
        """$INCREMENT via indirection using unified components.

        Resolves the indirection target, then atomically increments it.

        Args:
            source: Source variable name for indirection (e.g., "X" for @X)
            _scope: Current scope dictionary
            increment: Amount to increment by (default "1")
            levels: Number of indirection levels
            per_level_subscripts: Subscripts per level for @X@(s1) form

        Returns:
            New value after increment (as canonical MUMPS string)
        """
        from m2py.core.scope import CurrentScope
        from m2py.core.indirection import IndirectionResolver
        from m2py.runtime.helpers import m_increment, m_increment_global

        # Create unified scope and resolver
        cs = CurrentScope.from_generated_context(_scope)
        resolver = IndirectionResolver(self, cs)

        # Resolve to get target variable NAME
        target = resolver.resolve_to_name(
            source, levels=levels, per_level_subscripts=per_level_subscripts
        )

        # Handle global variables
        if target.startswith("^"):
            base_name, subscripts = _parse_subscripted_name(target)
            subs = tuple(str(s) for s in subscripts) if subscripts else ()
            key = base_name[1:]  # Remove ^ prefix
            return m_increment_global(self.globals, key, subs, increment)

        # Local variable — parse name and any subscripts
        base_name, subscripts = _parse_subscripted_name(target)
        subs = tuple(str(s) for s in subscripts) if subscripts else ()
        from m2py.core.names import NameTranslator

        python_name = NameTranslator.to_python(base_name)
        array = _scope.get(python_name)
        return m_increment(array, subs, increment, _scope, python_name)

    def lock_indirected(
        self,
        source: str,
        _scope: Dict[str, Any],
        lockop: str = "+",
        timeout: Optional[float] = None,
        levels: int = 1,
        per_level_subscripts: Optional[List[List[Any]]] = None,
    ) -> None:
        """Resolve an indirected lock name and acquire/release the lock.

        Parses the name expression (may contain subscripts), resolves
        through multiple indirection levels if needed, and delegates to
        the existing lock()/unlock() methods in globals.

        Args:
            source: Source variable name for indirection (e.g., "X" for @X)
            _scope: Current scope dictionary
            lockop: Lock operation - "" (exclusive), "+" (incremental), "-" (release)
            timeout: Optional timeout in seconds. Sets $TEST on timeout.
            levels: Number of indirection levels (1 for @X, 2 for @@X, etc.)
            per_level_subscripts: Subscripts per level for @X@(s1)@(s2) form

        Behavior:
            - lockop="": Exclusive lock - releases all existing locks first,
              then acquires the new lock
            - lockop="+": Incremental lock - adds to existing locks
            - lockop="-": Release - decrements lock count

            Timeout handling:
            - If timeout is specified, $TEST is set to 1 on success, 0 on timeout
            - If no timeout, $TEST is not modified
            - LOCK - with timeout always sets $TEST=1 (unlock never fails)
        """
        from m2py.core.scope import CurrentScope
        from m2py.core.indirection import IndirectionResolver

        # Create unified scope and resolver
        cs = CurrentScope.from_generated_context(_scope)
        resolver = IndirectionResolver(self, cs)

        # Resolve to get target variable NAME (the lock target)
        target = resolver.resolve_to_name(
            source, levels=levels, per_level_subscripts=per_level_subscripts
        )

        # Parse the target to get name and subscripts
        # Target can be: "GLO", "^GLO", "^GLO(1,2)", "A(1,2)"
        if target.startswith("^"):
            # Global name - strip the caret for lock table
            name_part = target[1:]
        else:
            name_part = target

        # Parse subscripts from name_part
        base_name, subscripts = _parse_subscripted_name(name_part)
        subs = tuple(str(s) for s in subscripts) if subscripts else ()

        # For exclusive lock (no + or -), release all locks first
        if lockop == "":
            self.globals.unlock_all()
            # After releasing all, we acquire with "+"
            effective_lockop = "+"
        else:
            effective_lockop = lockop

        # Perform the lock operation
        if effective_lockop == "-":
            # Release lock
            self.globals.lock(base_name, subs, lock_type="-")
            # LOCK - with timeout always succeeds
            if timeout is not None:
                self._test = True
        else:
            # Acquire lock
            if timeout is not None:
                # Timed lock - sets $TEST
                result = self.globals.lock(
                    base_name, subs, timeout=timeout, lock_type=effective_lockop
                )
                self._test = result
            else:
                # Untimed lock - does NOT modify $TEST
                self.globals.lock(base_name, subs, lock_type=effective_lockop)

    # =========================================================================
    # Transaction Restart Variable Snapshots
    # =========================================================================

    def snapshot_locals(
        self,
        _scope: Dict[str, Any],
        var_names: Optional[list[str]] = None,
        all_vars: bool = False,
    ) -> None:
        """Snapshot local variables at TSTART time for potential TRESTART.

        Stores deep copies of specified (or all) local variables. Per YDB
        semantics, snapshots are discarded (not restored) on TCOMMIT and
        TROLLBACK. Only TRESTART restores from snapshots.

        Args:
            _scope: Current scope dictionary containing local variables
            var_names: List of MUMPS variable names to snapshot, or None
            all_vars: If True, snapshot all locals (TSTART *)
        """
        snapshot = TransactionLocalSnapshot(
            restart_vars=[NameTranslator.to_python(n) for n in var_names]
            if var_names
            else None,
            restart_all=all_vars,
            saved_test=self._test,
        )

        if all_vars:
            # TSTART * — snapshot all local variables
            for name, value in _scope.items():
                snapshot.snapshot[name] = copy.deepcopy(value)
        elif var_names:
            # TSTART (X,Y) — snapshot named variables only
            for mumps_name in var_names:
                py_name = NameTranslator.to_python(mumps_name)
                if py_name in _scope:
                    snapshot.snapshot[py_name] = copy.deepcopy(_scope[py_name])
                # If var is undefined at TSTART time, don't record it
                # (TRESTART would KILL it)

        self._transaction_snapshots.append(snapshot)

    def discard_local_snapshot(self) -> None:
        """Discard the most recent transaction local snapshot.

        Called on TCOMMIT and TROLLBACK. Per YDB semantics, local variable
        snapshots are NOT restored on TROLLBACK (only globals are restored).
        Snapshots exist solely for TRESTART support.
        """
        if self._transaction_snapshots:
            self._transaction_snapshots.pop()

    def discard_all_local_snapshots(self) -> None:
        """Discard all transaction local snapshots.

        Called on TROLLBACK which resets $TLEVEL to 0, clearing all
        nested transaction snapshots at once.
        """
        self._transaction_snapshots.clear()

    def restore_locals_from_snapshot(self, _scope: Dict[str, Any]) -> None:
        """Restore local variables from the most recent transaction snapshot.

        Called on TRESTART. Pops the snapshot and restores each variable
        to its saved state. Variables not in the snapshot are left unchanged.
        Variables that were undefined at TSTART time are KILLed.

        Args:
            _scope: Current scope dictionary to restore into
        """
        if not self._transaction_snapshots:
            return

        snapshot = self._transaction_snapshots[-1]  # Don't pop — TRESTART re-uses

        if snapshot.restart_all:
            # Restore all — clear scope and repopulate from snapshot
            _scope.clear()
            for name, value in snapshot.snapshot.items():
                _scope[name] = copy.deepcopy(value)
        elif snapshot.restart_vars:
            # Restore named variables only
            for py_name in snapshot.restart_vars:
                if py_name in snapshot.snapshot:
                    _scope[py_name] = copy.deepcopy(snapshot.snapshot[py_name])
                elif py_name in _scope:
                    # Variable was undefined at TSTART — KILL it
                    del _scope[py_name]

        # Restore $TEST
        if snapshot.saved_test is not None:
            self._test = snapshot.saved_test

    def get_indirected_marray(
        self,
        source: str,
        _scope: Dict[str, Any],
        levels: int = 1,
        per_level_subscripts: Optional[List[List[Any]]] = None,
    ) -> Any:
        """Resolve indirection and return MArray for call-by-reference aliasing.

        Used for indirected by-reference parameters
        like .@IX where IX contains a variable name. Instead of returning the
        VALUE (like get_indirected), this returns the MArray OBJECT so the
        callee can share the same variable tree.

        Example:
            S IX="X", X="hello", X(1)="world"
            D SUB(.@IX)   ; .@IX means by-ref the variable named by IX = "X"
            ; Formal param A gets the MArray for X, so A(1) = X(1) = "world"

        Args:
            source: Source variable name for indirection
            _scope: Current scope dictionary
            levels: Number of indirection levels
            per_level_subscripts: Subscripts per level

        Returns:
            MArray object for the resolved variable (for by-ref aliasing)
        """
        from m2py.core.scope import CurrentScope
        from m2py.core.indirection import IndirectionResolver
        from m2py.core.exceptions import LVUNDEFError

        cs = CurrentScope.from_generated_context(_scope)
        resolver = IndirectionResolver(self, cs)

        try:
            target_name = resolver.resolve_to_name(
                source,
                levels=levels,
                per_level_subscripts=per_level_subscripts,
            )
        except LVUNDEFError as e:
            raise IndirectionError(
                source,
                f"undefined variable in indirection chain: {e.name}",
                variable_name=e.name,
            )

        # Get the MArray object from scope (not the value)
        from m2py.core.names import NameTranslator

        base_name = target_name.split("(")[0] if "(" in target_name else target_name
        scope_key = NameTranslator.to_python(base_name)
        return _scope.get(scope_key, MArray())

    def get_subscript_indirected(
        self,
        source: str,
        _scope: Dict[str, Any],
        levels: int = 1,
        per_level_subscripts: Optional[List[List[Any]]] = None,
    ) -> Any:
        """Get VALUE via indirection for use in subscript context.

        Unlike get_indirected() which resolves to NAME and validates the result,
        this method uses IndirectionResolver with SUBSCRIPT context to get
        the value for use as a subscript without name validation.

        Example 1: A(@X) where X="Y" and Y=5
        - Source is "X", levels=1
        - Loop: get X's value = "Y"
        - After loop: "Y" is valid var name, get Y's value = 5
        - Returns 5 for use as subscript

        Example 2: ^V1A(@^(4)) where ^(4)="^V1A(5)" and ^V1A(5)=55
        - Source is "^V1A(5)" (value of naked global ^(4))
        - Loop: get ^V1A(5)'s value = 55
        - After loop: "55" is not valid var name, return "55" as-is
        - Returns 55 for use as the subscript

        The key difference from get_indirected():
        - get_indirected() validates final result is a valid variable NAME
        - get_subscript_indirected() returns the VALUE for use as subscript

        Args:
            source: Source expression value (e.g., "X" for @X)
            _scope: Current scope dictionary
            levels: Number of indirection levels (1 for @X, 2 for @@X, etc.)
            per_level_subscripts: Subscripts per level for @X@(s1)@(s2) form

        Returns:
            Value for use as subscript
        """
        from m2py.core.scope import CurrentScope
        from m2py.core.indirection import IndirectionContext, IndirectionResolver

        # Create unified scope and resolver
        cs = CurrentScope.from_generated_context(_scope)
        resolver = IndirectionResolver(self, cs)

        # Use SUBSCRIPT context for value resolution without name validation
        return resolver.resolve(
            source,
            levels=levels,
            context=IndirectionContext.SUBSCRIPT,
            per_level_subscripts=per_level_subscripts,
        )

    def kill_indirected(
        self,
        source: str,
        _scope: Dict[str, Any],
        levels: int = 1,
        per_level_subscripts: Optional[List[List[Any]]] = None,
    ) -> None:
        """Kill variable via indirection using unified components.

        Replaces scattered kill_var + resolve calls with unified approach.

        Uses IndirectionResolver.resolve_to_name() to determine the target,
        then kills the variable/global appropriately.

        Handles exclusive KILL syntax: K @A where A="(B),D,E" means:
        - Kill all except B (exclusive KILL)
        - Then also kill D and E explicitly

        Args:
            source: Source variable name for indirection (e.g., "X" for @X),
                OR the literal kill list for complex expressions (levels=0)
            _scope: Current scope dictionary
            levels: Number of indirection levels (1 for @X, 2 for @@X, etc.)
                levels=0 means source is already the kill list (complex expression result)
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

            # K @X where X="E,F" (argument list)
            kill_indirected("X", scope, levels=1)
            # Kills both E and F

            # K @X where X="A(1,2),B" (subscripted vars in list)
            kill_indirected("X", scope, levels=1)
            # Kills A(1,2) and B

            # K @X where X="(B),D,E" (exclusive + explicit kills)
            kill_indirected("X", scope, levels=1)
            # Kills all except B, then also kills D and E

            # K @(A_","_B) where result is "D,E,F" (complex expression)
            kill_indirected("D,E,F", scope, levels=0)
            # Source IS the kill list, no resolution needed
        """
        from m2py.core.scope import CurrentScope
        from m2py.core.indirection import IndirectionResolver

        # Create unified scope and resolver
        cs = CurrentScope.from_generated_context(_scope)
        resolver = IndirectionResolver(self, cs)

        # levels=0 means source is already the kill list (from complex expression)
        # No resolution needed - source IS the target
        if levels == 0:
            raw_value = source
        else:
            # First resolve to get the raw string value (not validated as var names)
            # validate=False because KILL may have exclusive patterns like "(B),D,E"
            raw_value = resolver.resolve_to_name(
                source,
                levels=levels,
                per_level_subscripts=per_level_subscripts,
                validate=False,
            )

        # Split by commas respecting parentheses
        args = _split_argument_list(raw_value)

        # Process each argument
        for arg in args:
            arg = arg.strip()
            if not arg:
                continue

            # If argument starts with @, it's nested indirection that needs resolution
            # For example, @A(1) where A(1)="B(2),B(3)" should resolve to kill B(2) and B(3)
            if arg.startswith("@"):
                # Recursively resolve the indirection
                inner = arg[1:]  # Strip the @

                # Handle multi-level @ (@@X etc)
                levels = 1
                while inner.startswith("@"):
                    levels += 1
                    inner = inner[1:]

                # Parse the variable name and any subscripts
                # e.g., "B(1)" → variable "B" with subscript 1
                paren_pos = inner.find("(")
                if paren_pos > 0:
                    var_name = inner[:paren_pos]
                    # Get subscripts
                    close_pos = inner.rfind(")")
                    if close_pos > paren_pos:
                        subs_str = inner[paren_pos + 1 : close_pos]
                        subs = resolver._parse_subscript_list(subs_str)
                        # Build the full name with subscripts
                        full_name = f"{var_name}({','.join(str(s) for s in subs)})"
                    else:
                        full_name = inner
                else:
                    full_name = inner

                # Resolve to get the target name(s)
                try:
                    resolved = resolver.resolve_to_name(
                        full_name, levels=levels, validate=False
                    )
                    # The resolved value might itself be a comma-separated list
                    # Recursively process by adding to our args
                    sub_args = _split_argument_list(resolved)
                    for sub_arg in sub_args:
                        sub_arg = sub_arg.strip()
                        if sub_arg:
                            # Recursively handle this argument (may contain more @)
                            if sub_arg.startswith("@"):
                                args.append(
                                    sub_arg
                                )  # Will be processed in a later iteration
                            else:
                                # Kill the resolved target
                                self._kill_single_target(sub_arg, _scope, cs, resolver)
                except Exception:
                    # If resolution fails, try to kill it as a literal name
                    pass
                continue

            # Check for exclusive KILL pattern: (var1,var2,...)
            if arg.startswith("(") and arg.endswith(")"):
                # Exclusive KILL - kill all locals except those in the parens
                except_list_str = arg[1:-1]  # Remove outer parens
                except_vars = set(
                    v.strip() for v in except_list_str.split(",") if v.strip()
                )
                # Kill all local variables except those in except_vars
                for var_name in list(_scope.keys()):
                    if var_name not in except_vars:
                        _scope.pop(var_name, None)
                continue

            # Regular variable kill
            self._kill_single_target(arg, _scope, cs, resolver)

    def _kill_single_target(
        self,
        target: str,
        _scope: Dict[str, Any],
        cs: Any,
        resolver: Any,
    ) -> None:
        """Kill a single variable target.

        Helper method for kill_indirected to handle individual targets.

        Args:
            target: Variable name to kill (may include subscripts)
            _scope: Current scope dictionary
            cs: CurrentScope wrapper
            resolver: IndirectionResolver for subscript evaluation
        """
        # Evaluate subscripts in the target if it contains indirections or variable refs
        # This handles cases like "^V1A(A1)" where A1 is a variable reference
        # or "^V1A(@B(1))" where @B(1) needs resolution
        if "(" in target and (target[0].isalpha() or target[0] in "%^"):
            target = resolver._evaluate_subscripts_in_name(target)

        # Handle naked global reference patterns like ^(@A,B)
        if target.startswith("^("):
            # This is a naked reference - expand using naked indicator
            target = resolver._expand_naked_reference_string(target)

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

    @staticmethod
    def _split_argument_list(arg_str: str) -> List[str]:
        """Split comma-separated argument list respecting parentheses.

        Exposed as staticmethod for use in generated code.

        See module-level _split_argument_list for details.
        """
        return _split_argument_list(arg_str)

    def execute_new_indirection(
        self, resolved_str: str, new_mgr: Any, scope: Dict[str, Any]
    ) -> None:
        """Execute NEW with runtime-resolved argument string.

        Handles the full MUMPS NEW argument syntax dynamically:
        - Simple variable names: "A,B,C" → new_var("A"), new_var("B"), new_var("C")
        - Exclusive groups: "(A,B)" → new_exclusive({"A","B"})
        - Mixed: "A,(B,C)" → new_var("A"), then new_exclusive({"B","C"})
        - Nested indirection: "@X" → resolve X value and recurse

        Args:
            resolved_str: The resolved string from the indirection expression
            new_mgr: NewScopeManager instance for proper save/restore
            scope: Current variable scope dict for resolving nested indirection
        """
        if not resolved_str or not resolved_str.strip():
            return

        parts = _split_argument_list(resolved_str.strip())
        for part in parts:
            part = part.strip()
            if not part:
                continue

            if part.startswith("(") and part.endswith(")"):
                # Exclusive NEW: (A,B,C) — keep these vars, NEW everything else
                inner = part[1:-1]
                keep_list = _split_argument_list(inner)
                resolved_keep: set = set()
                for k in keep_list:
                    k = k.strip()
                    if k.startswith("@"):
                        # Resolve indirection in keep list, recursing for nested @
                        val = str(self._resolve_new_indirection_value(k[1:], scope))
                        while val.startswith("@"):
                            val = str(
                                self._resolve_new_indirection_value(val[1:], scope)
                            )
                        resolved_keep.add(val)
                    else:
                        resolved_keep.add(k)
                new_mgr.new_exclusive(resolved_keep)
            elif part.startswith("@"):
                # Further indirection — resolve and recurse
                inner_name = part[1:]
                val = self._resolve_new_indirection_value(inner_name, scope)
                self.execute_new_indirection(str(val), new_mgr, scope)
            else:
                # Simple variable name
                new_mgr.new_var(part)

    def _resolve_new_indirection_value(
        self, expr_str: str, scope: Dict[str, Any]
    ) -> str:
        """Resolve a variable reference to its value for NEW indirection.

        Args:
            expr_str: Variable name like "X", "X(1,2)", "^VAR",
                or intrinsic function like "$C(66)", "$P(...)" etc.
            scope: Current variable scope

        Returns:
            The string value of the variable or expression result
        """
        from m2py.runtime.helpers import m_var_value

        expr_str = expr_str.strip()

        # Intrinsic function call: $C(66), $CHAR(66), $P(...), $E(...), etc.
        # Delegate to the IndirectionResolver which handles all functions
        if expr_str.startswith("$"):
            try:
                from m2py.core.scope import CurrentScope
                from m2py.core.indirection import IndirectionResolver

                cs = CurrentScope.from_generated_context(scope)
                resolver = IndirectionResolver(self, cs)
                return str(resolver.evaluate_expression(expr_str))
            except Exception:
                return ""

        if expr_str.startswith("^"):
            # Global variable reference
            global_name = expr_str[1:]
            # Check for subscripts
            if "(" in global_name:
                base = global_name[: global_name.index("(")]
                subs_str = global_name[global_name.index("(") + 1 : -1]
                subs = _split_argument_list(subs_str)
                # Evaluate subscript values
                eval_subs = tuple(
                    self._eval_simple_expr(s.strip(), scope) for s in subs
                )
                return str(self.globals.get(base, eval_subs) or "")
            else:
                return str(self.globals.get(global_name, ()) or "")

        # Local variable reference
        if "(" in expr_str:
            base = expr_str[: expr_str.index("(")]
            subs_str = expr_str[expr_str.index("(") + 1 : -1]
            subs = _split_argument_list(subs_str)
            arr = scope.get(base)
            if arr is None:
                return ""
            arr_obj = arr if hasattr(arr, "get") else None
            if arr_obj is None:
                return ""
            eval_subs = tuple(
                str(self._eval_simple_expr(s.strip(), scope)) for s in subs
            )
            return str(arr_obj.get(*eval_subs) or "")
        else:
            val = scope.get(expr_str)
            return str(m_var_value(val) if val is not None else "")

    def _eval_simple_expr(self, expr: str, scope: Dict[str, Any]) -> str:
        """Evaluate a simple MUMPS expression for subscript resolution.

        Handles: numeric literals, string literals, variable names,
        $D(var)/DATA(var) intrinsic, and basic arithmetic (+, -, *, /, \\, #).
        """
        from m2py.runtime.helpers import m_var_value

        expr = expr.strip()
        # String literal
        if expr.startswith('"') and expr.endswith('"'):
            return expr[1:-1].replace('""', '"')

        # $D(var) / $DATA(var) — evaluate data function
        import re

        m = re.match(r"^\$[Dd](?:[Aa][Tt][Aa])?\((.+)\)(.*)$", expr)
        if m:
            var_ref = m.group(1).strip()
            remainder = m.group(2).strip()
            # Evaluate $DATA on the variable
            val = scope.get(var_ref)
            if val is None:
                data_val = 0
            elif hasattr(val, "_children"):
                has_value = val.value is not None
                has_children = bool(val._children)
                data_val = (1 if has_value else 0) + (10 if has_children else 0)
            else:
                data_val = 1
            # Handle arithmetic remainder like +2, *3, etc.
            if remainder:
                arith_m = re.match(r"^([+\-*/#\\])\s*(.+)$", remainder)
                if arith_m:
                    op = arith_m.group(1)
                    right = self._eval_simple_expr(arith_m.group(2), scope)
                    try:
                        right_num = int(right) if "." not in right else float(right)
                    except (ValueError, TypeError):
                        right_num = 0
                    if op == "+":
                        data_val = data_val + right_num
                    elif op == "-":
                        data_val = data_val - right_num
                    elif op == "*":
                        data_val = data_val * right_num
                    elif op == "/":
                        data_val = data_val / right_num if right_num else 0
                    elif op == "\\":
                        data_val = data_val // right_num if right_num else 0
                    elif op == "#":
                        data_val = data_val % right_num if right_num else 0
            return str(int(data_val))

        # Numeric literal
        try:
            n = int(expr)
            return str(n)
        except ValueError:
            pass
        try:
            n = float(expr)
            return str(n)
        except ValueError:
            pass
        # Variable reference
        val = scope.get(expr)
        return str(m_var_value(val) if val is not None else "")

    def resolve_for_target(
        self,
        source: str,
        _scope: Dict[str, Any],
        levels: int = 1,
        per_level_subscripts: Optional[List[List[Any]]] = None,
    ) -> str:
        """Resolve FOR loop indirection target using unified components.

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
            treat_empty_as_truthy: If True, empty string resolves to 1 (for IF)
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

            # I @A where A=""
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

    def evaluate_mumps_expression(
        self,
        expr: str,
        _scope: Dict[str, Any],
        treat_empty_as_truthy: bool = False,
    ) -> Any:
        """Evaluate a MUMPS expression string directly.

        This is used for @$P(...) style indirection where the function
        result IS the expression to evaluate (no intermediate lookups).

        For example: W @$P("ABC","B",2) where $P returns "C"
        - We want to evaluate "C" as a MUMPS expression
        - This gets the value of variable C

        Args:
            expr: MUMPS expression string to evaluate
            _scope: Current scope dictionary
            treat_empty_as_truthy: If True, empty string → 1 (for IF contexts)

        Returns:
            Evaluated result of the expression
        """
        from m2py.core.scope import CurrentScope
        from m2py.core.indirection import IndirectionResolver

        # Create unified scope and resolver
        cs = CurrentScope.from_generated_context(_scope)
        resolver = IndirectionResolver(self, cs)

        # Evaluate the expression directly
        return resolver.evaluate_expression(
            expr, treat_empty_as_truthy=treat_empty_as_truthy
        )

    def write_indirection(
        self,
        source: str,
        _scope: Dict[str, Any],
        levels: int = 1,
        per_level_subscripts: Optional[List[List[Any]]] = None,
    ) -> None:
        """Execute WRITE argument indirection.

        Handles W @A where A contains WRITE arguments including format controls.
        Unlike evaluate_argument_indirection, this parses and executes the
        resolved value AS WRITE ARGUMENTS, not as an expression.

        The resolved value is passed directly to execute_mumps which handles
        any @-expressions, format controls, nested indirections, etc.

        Example: W @A where A='!?3,"AB"'
        - Resolves @A to: !?3,"AB"
        - Executes: W !?3,"AB" via execute_mumps

        Example: W @A where A='@B+1' and B='C', C=100
        - Resolves @A to: @B+1 (raw value, NOT recursively resolved)
        - Executes: W @B+1 via execute_mumps → outputs 101

        Example: W @''10 (expression indirection)
        - levels=0: Expression already evaluated at compile time to "1"
        - Just execute "1" as WRITE argument → outputs 1

        Args:
            source: Source variable name for indirection (e.g., "A" for @A)
                   OR for levels=0, the already-evaluated expression result string
            _scope: Current scope dictionary
            levels: Number of indirection levels (1 for @A, 2 for @@A)
                   0 means source is already the final value (expression indirection)
            per_level_subscripts: Subscripts per level for @A@(s1)@(s2) form

        Raises:
            LVUNDEFError: If source variable is undefined
            VarExpectedError: If resolved value is empty
        """
        from m2py.core.scope import CurrentScope
        from m2py.core.indirection import IndirectionResolver
        from m2py.core.exceptions import VarExpectedError

        # For levels=0, source is already the final value (expression indirection)
        # Example: @''10 → ''10 evaluates to "1" at compile time, levels=0
        if levels == 0:
            raw_value = source
        else:
            # Create unified scope and resolver
            cs = CurrentScope.from_generated_context(_scope)
            resolver = IndirectionResolver(self, cs)

            # Resolve to get the raw WRITE arguments string
            # Use resolve_to_raw_value which does NOT recursively resolve @-expressions
            # The raw value is passed to execute_mumps which handles @-expressions
            raw_value = resolver.resolve_to_raw_value(
                source,
                levels=levels,
                per_level_subscripts=per_level_subscripts,
                strict_undef=True,  # Undefined source should error
            )

        # Empty string value should raise error in WRITE context
        if not raw_value:
            raise VarExpectedError(
                source, f"Empty indirection value in WRITE context: {source}"
            )

        # Execute as WRITE command arguments
        self._execute_write_args(raw_value, _scope)

    def _execute_write_args(self, write_args: str, _scope: Dict[str, Any]) -> None:
        """Execute a string as WRITE arguments.

        Parses and executes the string as MUMPS WRITE arguments, including
        format controls (!, #, ?n, *n) and expressions.

        Args:
            write_args: WRITE argument string (e.g., '!?3,"AB"')
            _scope: Current scope dictionary

        Raises:
            VarExpectedError: If indirection string contains extra trailing chars
        """
        from m2py.core.exceptions import VarExpectedError

        # Check for INDEXTRACHARS-like pattern: number immediately followed by letter
        # This catches cases like "123INVALID" which YDB rejects
        import re

        if re.match(r"^\d+\.?\d*[A-Za-z%]", write_args):
            raise VarExpectedError(
                write_args,
                f"Indirection string contains extra trailing characters: '{write_args}'",
            )

        # Wrap in WRITE command and execute as MUMPS
        mumps_code = f"W {write_args}"
        self.execute_mumps(mumps_code, _scope)

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

        Implements KILL with indirection.

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

        Implements MERGE with indirection destination.

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

        Implements MERGE with indirection source.

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
        """Check if name looks like a valid MUMPS variable name.

        Now delegates to core.names.is_valid_varname() for unified validation.

        Args:
            name: Variable name to validate (may include subscripts)

        Returns:
            True if valid MUMPS variable name
        """
        return _core_is_valid_varname(name, allow_subscripts=True)

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
            # Also: if base_expr starts with ^ (global ref), the first ^ is NOT the separator
            # E.g., ^V1A^@(%_1) has label=^V1A (global lookup), routine=@(%_1)
            # Walk through finding unbracketed ^
            paren_depth = 0
            caret_pos = -1
            in_string = False
            i = 0
            # If starts with ^, skip past the global name to find the separator ^
            starts_with_global = base_expr.startswith("^")
            found_first_caret = False
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
                        if starts_with_global and not found_first_caret:
                            # Skip the first ^ which is part of the global reference
                            found_first_caret = True
                        else:
                            caret_pos = i
                            break
                i += 1

            # Only treat as label^routine if caret_pos > 0 (there's a label before ^)
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
                if label_part.startswith("^"):
                    # Global variable reference - look up in globals
                    global_name = label_part[1:]
                    global_base, global_subs = _parse_subscripted_name(global_name)
                    evaluated_global_subs = _evaluate_subscripts(
                        global_subs, scope, self
                    )
                    if evaluated_global_subs:
                        resolved_label = str(
                            self.globals.get(global_base, evaluated_global_subs) or ""
                        )
                    else:
                        resolved_label = str(self.globals.get(global_base, ()) or "")
                elif label_part and not label_part[0].isdigit():
                    # It's a local variable name, look it up
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
            # BUT handle @VAR+OFFSET case: offset is NOT part of the variable
            if target.startswith("@"):
                # Check if there's an offset (+) or routine-separator (^) after the @ portion
                # Find where the @-indirection part ends
                # The @ part continues until we hit + or ^ROUTINE separator (outside parens)
                # BUT: @^GLOBAL is a global reference, not label^routine - ^ is part of the name
                at_end = len(target)
                depth = 0
                in_str = False
                i = 1  # Start after the first @
                # Track consecutive @ characters (for @@VAR, @@@VAR, etc.)
                while i < len(target) and target[i] == "@":
                    i += 1
                # Now i points to first non-@ character after the @ prefix
                # If next char is ^, it's a global reference like @^GLO - include it
                if i < len(target) and target[i] == "^":
                    i += 1  # Skip the ^ (part of global name)

                while i < len(target):
                    c = target[i]
                    if c == '"':
                        in_str = not in_str
                    elif not in_str:
                        if c == "(":
                            depth += 1
                        elif c == ")":
                            depth -= 1
                        elif depth == 0 and c == "+":
                            # Found offset separator
                            at_end = i
                            break
                        elif depth == 0 and c == "^":
                            # Found routine separator (^ROUTINE)
                            # This is NOT part of the @ expression
                            at_end = i
                            break
                    i += 1

                at_part = target[
                    :at_end
                ]  # e.g., "@CMD" from "@CMD+1" or "@^GLO" from "@^GLO^RTN"
                rest_part = target[at_end:]  # e.g., "+1" from "@CMD+1"

                resolved = self.resolve_nested_indirection(at_part, scope)
                # The resolved result may itself contain multiple comma-separated targets
                if contains_unparenthesized_comma(resolved):
                    # Re-split and queue for processing (with the rest_part appended)
                    if rest_part:
                        # Append rest_part to each comma-separated target
                        # This is tricky - we need to re-process the whole thing
                        sub_targets = self.resolve_do_targets(resolved, scope)
                        for st in sub_targets:
                            # Add offset/routine back if present
                            new_target = f"{st.label or ''}"
                            if st.offset is not None:
                                new_target += f"+{st.offset}"
                            if st.routine:
                                new_target += f"^{st.routine}"
                            # Now append our rest_part
                            new_target += rest_part
                            targets_to_process.append(new_target)
                    else:
                        sub_targets = self.resolve_do_targets(resolved, scope)
                        result.extend(sub_targets)
                    continue

                # The resolved result might contain a postcondition (e.g., @A where A="1+3:0")
                # Strip it here and merge with any outer postcondition
                resolved_target, resolved_postcond = strip_postcondition(resolved)
                if resolved_postcond:
                    # Combine postconditions: resolved takes precedence (inner overrides outer)
                    # Actually, the outer postcondition should already be evaluated before
                    # we got here, so we just use the resolved one
                    postcondition = resolved_postcond
                target = resolved_target + rest_part  # e.g., "SUB+1"

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
                            from m2py.core.values import m_num

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

            # Parse the target and include postcondition for lazy evaluation
            # The caller will evaluate the postcondition just before executing each target
            call_target = self.parse_call_target(target, postcondition=postcondition)
            result.append(call_target)

        return result

    def parse_call_target(
        self, target_str: str, postcondition: Optional[str] = None
    ) -> CallTarget:
        """Parse indirect DO/GOTO target into components.

        Parses target strings for indirect DO/GOTO.

        Formats supported:
        - "LABEL" → local label
        - "^ROUTINE" → entry label of external routine
        - "LABEL^ROUTINE" → specific label in external routine
        - "LABEL+N" → label with offset (N is integer)
        - "LABEL+N^ROUTINE" → external with offset

        Args:
            target_str: Target string from indirection resolution (will be
                converted to string if numeric, per MUMPS semantics)
            postcondition: Optional postcondition expression to evaluate
                before executing this target (for lazy evaluation)

        Returns:
            CallTarget(label, routine, offset, postcondition)

        Raises:
            IndirectionError: If format is invalid

        Examples:
            >>> rt.parse_call_target("LABEL")
            CallTarget(label="LABEL", routine=None, offset=None, postcondition=None)
            >>> rt.parse_call_target("LABEL^ROUTINE")
            CallTarget(label="LABEL", routine="ROUTINE", offset=None, postcondition=None)
            >>> rt.parse_call_target("LABEL+5^ROUTINE")
            CallTarget(label="LABEL", routine="ROUTINE", offset=5, postcondition=None)
            >>> rt.parse_call_target(1)  # numeric label
            CallTarget(label="1", routine=None, offset=None, postcondition=None)
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
            return CallTarget(
                label=None, routine=routine, offset=None, postcondition=postcondition
            )

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

        return CallTarget(
            label=label, routine=routine, offset=offset, postcondition=postcondition
        )

    def execute_mumps(
        self,
        mumps_code: str,
        _scope: Dict[str, Any],
        caller_globals: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute MUMPS code string at runtime (XECUTE).

        Implements dynamic MUMPS code execution.

        Behavior:
        - Parses code as MUMPS using m2py parser
        - Generates Python via m2py codegen
        - Executes with exec() in shared _scope context
        - $TEST is NOT stacked (mutations visible to caller)
        - Supports all MUMPS constructs (depends on Specs 004-011)

        Note: Named execute_mumps() to distinguish from existing execute()
        which runs Python code. The contract specifies execute() but we
        need a different name to avoid shadowing the existing method.

        When caller_globals is provided, include it in the execution
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
        # Use codegen callback to compile MUMPS → Python
        generate_python = self._get_codegen_callback()
        from m2py.core.values import m_compare, m_num, m_truth

        # Handle MArray objects (from TRAMPOLINE scope sync)
        if hasattr(mumps_code, "value"):
            mumps_code = str(mumps_code.value or "")  # type: ignore[union-attr]

        # Ensure mumps_code is a string
        mumps_code = str(mumps_code)

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
            # Wrap in a temporary routine with label.
            # The safety QUIT goes on a NEW LINE so it doesn't merge with the
            # last command.  `Q Q` on one line means QUIT-returning-variable-Q.
            wrapped_code = "XECUTE " + mumps_code.strip() + "\n Q"
        else:
            # Already has structure, use as-is
            wrapped_code = mumps_code

        # Generate Python code
        try:
            python_code = generate_python(wrapped_code, routine_name="XECUTE")
        except Exception as e:
            # Provide useful context in XECUTE syntax error message
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
        # Update scope BEFORE adding callables so labels take precedence
        # In MUMPS, D A always refers to label A, not variable A
        namespace.update(_scope)

        # Include caller's globals so XECUTE can access module labels
        # This allows DO/GOTO to labels in the calling routine
        # Add callables AFTER scope so labels override variables
        if caller_globals:
            # Only include callable items (functions) to avoid polluting namespace
            for name, value in caller_globals.items():
                if callable(value) and not name.startswith("_"):
                    namespace[name] = value

        try:
            # Execute the generated code
            exec(python_code, namespace)

            # The generated code defines a function, we need to call it
            if "XECUTE" in namespace and callable(namespace["XECUTE"]):
                # Push XECUTE stack frame with MUMPS source as mcode
                self.push_stack_frame("XECUTE", mcode=mumps_code)
                try:
                    result = namespace["XECUTE"](self, _scope=_scope)
                finally:
                    # Pop XECUTE stack frame
                    self.pop_stack_frame()
            else:
                result = None

            # Sync $TEST back - store in both _scope and self._test
            # XECUTE does NOT stack $TEST
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

    def execute_mumps_indirected(
        self,
        source: str,
        _scope: Dict[str, Any],
        levels: int = 1,
        per_level_subscripts: Optional[List[List[Any]]] = None,
        caller_globals: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute MUMPS code via indirection (X @X argument indirection).

        Handles XECUTE argument indirection where the resolved value may be
        a comma-separated list of variable names, each containing code to execute.

        For X @X where X="Y,Z", Y="S A=1", Z="S B=2":
        1. Resolve @X → "Y,Z"
        2. Split into ["Y", "Z"]
        3. For each: resolve @Y → "S A=1", @Z → "S B=2"
        4. Execute each code string in order

        Args:
            source: Source variable name for indirection (e.g., "X" for @X)
            _scope: Scope dictionary shared with caller
            levels: Number of indirection levels (1 for @X, 2 for @@X, etc.)
            per_level_subscripts: Subscripts per level for @X@(s1)@(s2) form
            caller_globals: Optional caller's globals() for label access

        Returns:
            Last return value (if any code contains QUIT with value), else None
        """
        from m2py.core.scope import CurrentScope
        from m2py.core.indirection import IndirectionResolver

        # Create unified scope and resolver
        cs = CurrentScope.from_generated_context(_scope)
        resolver = IndirectionResolver(self, cs)

        # Resolve to get the argument list (may be comma-separated var names)
        # Use validate=False because the resolved string may contain var names
        raw_value = resolver.resolve_to_name(
            source,
            levels=levels,
            per_level_subscripts=per_level_subscripts,
            validate=False,
        )

        # Split by commas to get individual argument names (or expressions)
        # _split_argument_list respects quotes and parens, so:
        # - "S VCOMP=1",H → ['"S VCOMP=1"', 'H']  (two args)
        # - "A"_$E("B",1)_"C" → ['"A"_$E("B",1)_"C"'] (one arg, expression)
        args = _split_argument_list(raw_value)

        result = None
        for arg in args:
            arg = arg.strip()
            if not arg:
                continue

            # T091c-postcond: Each argument may have a postcondition (VAR:cond)
            # Parse out the variable name and postcondition
            # Must find colon at top level (not inside quotes or parens)
            var_name = arg
            postcond = None
            colon_pos = _find_toplevel_colon(arg)
            if colon_pos >= 0:
                var_name = arg[:colon_pos].strip()
                postcond = arg[colon_pos + 1 :].strip()

            # Evaluate postcondition if present
            if postcond:
                # Evaluate the postcondition as a MUMPS expression
                postcond_result = resolver.evaluate_expression(postcond)
                # MUMPS truth: non-zero or non-empty string starting with digit is true
                from m2py.core.values import m_truth

                if not m_truth(postcond_result):
                    # Postcondition false, skip this argument
                    continue

            # T091c-expr: Determine if arg is a variable name or an expression
            # Expressions to evaluate directly:
            # - Starts with " → quoted string or concatenation
            # - Starts with $ → intrinsic function ($SELECT, $EXTRACT, etc.)
            # - Contains operators at top level (_, +, -, etc.) → expression
            # Otherwise → variable name, look up its value
            arg_stripped = var_name.strip()
            is_expression = (
                arg_stripped.startswith('"')  # Quoted string
                or arg_stripped.startswith("$")  # Intrinsic function
            )

            if is_expression:
                # It's an expression - evaluate it to get the code
                code = resolver.evaluate_expression(arg_stripped)
            else:
                # It's a variable name - get the code from its value
                code = resolver._get_value(var_name)
                if isinstance(code, str) and code:
                    # T091c-expr: If the VALUE is an expression, evaluate it
                    code_stripped = code.strip()
                    if code_stripped.startswith('"') or code_stripped.startswith("$"):
                        code = resolver.evaluate_expression(code)

            # Execute the code if we have a valid string
            if isinstance(code, str) and code:
                result = self.execute_mumps(code, _scope, caller_globals)

        return result

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
        from m2py.core.values import m_str, m_compare, m_num, m_truth

        namespace["m_str"] = m_str
        namespace["m_num"] = m_num
        namespace["m_truth"] = m_truth
        namespace["m_compare"] = m_compare

        try:
            # Execute the module code (defines functions)
            exec(python_code, namespace)

            # Re-inject runtime after module execution
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
            # Entry point functions require _rt as first parameter
            # Use run_with_goto_support to handle external GOTOs
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
            # HALT command raises SystemExit(0)
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
    "resolve_goto_target",
    "call_external_with_offset",
    # Data structures
    "StackFrame",
    "TransactionLocalSnapshot",
    # Global storage and helpers
    "GlobalStorageBackend",
    "InMemoryGlobalStorage",
    "get_global_storage",
    "m_set_piece",
    "m_set_extract",
    "m_data",
    "m_data_global",
    # Runtime exceptions
    "MRuntimeError",
    # $ORDER and $QUERY helpers
    "m_order",
    "m_order_global",
    "m_query",
    "m_query_global",
    # $SELECT helper
    "_raise_select_false",
    # $PIECE and $EXTRACT helpers
    "m_piece",
    "m_extract",
    # $GET helpers
    "m_get",
    "m_get_global",
    # $FIND helper
    "m_find",
    # String comparison and pattern match helpers
    # Contains ([) and Follows (]) are inlined; only sorts-after needs runtime
    "m_sorts_after",
    "m_pattern_match",
    # Indirection & XECUTE
    "IndirectionError",
    "CallTarget",
    # SubscriptVarRef for subscript variable references
    "SubscriptVarRef",
    "VarRef",  # Backward compatibility alias for SubscriptVarRef
    # Argument list parsing for indirection
    "_split_argument_list",
    "_evaluate_subscript",
    "_evaluate_subscripts",
    "_convert_subscript",
    "_parse_subscripted_name",
]
