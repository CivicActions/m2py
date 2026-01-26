"""Indirection Resolution for @-expressions.

This module provides the IndirectionResolver class for resolving MUMPS
@-expressions at runtime. It supports single-level, multi-level,
per-level subscripts, recursive @-expressions, and context-aware
finalization (NAME vs ARGUMENT).

Constitution VII: Used ONLY for truly dynamic cases where codegen
cannot statically resolve the indirection.

Feature: 018-unified-variable-system
Requirements: FR-010 through FR-022
"""

from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from m2py.core.exceptions import VarExpectedError
from m2py.core.subscripts import SubscriptCanonicalizer

if TYPE_CHECKING:
    from m2py.core.scope import CurrentScope


class IndirectionContext(Enum):
    """Context for indirection final step.

    NAME: Result used as variable identifier
          SET @X=, WRITE @X, KILL @X, $DATA(@X)
          Error if result is not valid variable name

    ARGUMENT: Result evaluated as MUMPS expression
              IF @A, FOR args, XECUTE @A, postconditions
              Empty string allowed (evaluates to false)

    SUBSCRIPT: Result used as subscript value
               A(1,@B,3) - indirection within subscript
               Returns the resolved VALUE, not a variable reference

    PATTERN: Result used as pattern for pattern match
             X?@P - pattern indirection
    """

    NAME = "name"
    ARGUMENT = "argument"
    SUBSCRIPT = "subscript"
    PATTERN = "pattern"


class IndirectionResolver:
    """Runtime resolver for @-expressions.

    Constitution VII: Used ONLY for truly dynamic cases where
    codegen cannot statically resolve the indirection.

    Supports:
    - Single level: @X
    - Multi-level: @@X, @@@X, etc.
    - Direct subscripts: @X(1,2)
    - Name indirection subscripts: @X@(1,2), @X@(1)@(2,3)
    - Recursive @-expressions: Value contains @, re-evaluated
    - Context-aware: NAME (variable lookup) vs ARGUMENT (expression eval)
    """

    def __init__(self, state: Any, scope: "CurrentScope"):
        """Initialize resolver with runtime state and scope.

        Args:
            state: MState/MUMPSRuntime instance for global state, naked indicator, etc.
            scope: CurrentScope instance for unified variable access
        """
        self._state = state
        self._scope = scope

    def resolve(
        self,
        source: str,
        levels: int = 1,
        context: IndirectionContext = IndirectionContext.NAME,
        direct_subscripts: Optional[List[Any]] = None,
        per_level_subscripts: Optional[List[List[Any]]] = None,
    ) -> Any:
        """Resolve indirection and return final value.

        Args:
            source: Initial variable name or expression string
            levels: Number of @ levels (1 for @X, 2 for @@X, etc.)
            context: How to use final resolved value
            direct_subscripts: Subscripts for @X(subs) form
            per_level_subscripts: Subscripts per resolution level for @X@(s1)@(s2)

        Returns:
            - NAME context: Variable value (string, MArray, etc.)
            - ARGUMENT context: Expression evaluation result

        Raises:
            VarExpectedError: NAME context and result not valid variable name
            ValueError: If levels < 1

        Examples:
            # @X where X="Y", Y=5
            resolve("X", 1, NAME) → 5

            # @@X where X="Y", Y="Z", Z=99
            resolve("X", 2, NAME) → 99

            # @X@(1,2) where X="A", A(1,2)="hello"
            resolve("X", 1, NAME, per_level_subscripts=[[1,2]]) → "hello"

            # @A where A="1=0" in IF context
            resolve("A", 1, ARGUMENT) → False
        """
        if levels < 1:
            raise ValueError(f"Indirection levels must be >= 1, got {levels}")

        current = source

        # 1. Resolve intermediate levels (NAME semantics)
        for i in range(levels):
            # Get value at current name
            value = self._get_value(current)

            # Convert to string for processing
            if not isinstance(value, str):
                value = str(value)

            # Handle recursive @-expression (value contains @)
            while value.startswith("@"):
                value = self._resolve_recursive_at(value)

            # Apply per-level subscripts if any
            if per_level_subscripts and i < len(per_level_subscripts):
                value = self._append_subscripts(value, per_level_subscripts[i])

            current = value

        # 2. Apply direct subscripts to final reference
        if direct_subscripts:
            current = self._append_subscripts(current, direct_subscripts)

        # 3. Final resolution based on context
        if context == IndirectionContext.NAME:
            # Validate that result is valid variable name
            if not self._is_valid_var_name(current):
                raise VarExpectedError(current)
            return self._get_value(current)

        elif context == IndirectionContext.ARGUMENT:
            # Evaluate as MUMPS expression
            # The current value IS the expression string to evaluate
            return self.evaluate_expression(current)

        elif context == IndirectionContext.SUBSCRIPT:
            # Return the actual value at the resolved variable
            # For subscript indirection like A(1,@B,3), we want the VALUE at B
            # to use as a subscript, not B's value treated as a variable name
            if self._is_valid_var_name(current):
                return self._get_value(current)
            # If not a valid variable name, return as-is (might be a literal)
            return current

        elif context == IndirectionContext.PATTERN:
            # Return the pattern string
            return current

        # Fallback - return as-is
        return current

    def resolve_name_indirection(
        self, name: str, subscripts: Optional[List[Any]] = None
    ) -> Any:
        """Convenience method for simple NAME indirection.

        Equivalent to resolve(name, 1, NAME, direct_subscripts=subscripts)

        Args:
            name: Variable name to resolve (source of @name)
            subscripts: Optional direct subscripts for @name(subs)

        Returns:
            Value at the indirected variable
        """
        return self.resolve(
            name,
            levels=1,
            context=IndirectionContext.NAME,
            direct_subscripts=subscripts,
        )

    def resolve_argument_indirection(self, name: str) -> Any:
        """Convenience method for ARGUMENT indirection.

        Equivalent to resolve(name, 1, ARGUMENT)

        This is the FIX for Challenge 6 bug. When A="1=0",
        @A in IF context evaluates "1=0" as expression → FALSE.

        Args:
            name: Variable name containing expression to evaluate

        Returns:
            Evaluated result of the expression
        """
        return self.resolve(name, levels=1, context=IndirectionContext.ARGUMENT)

    def resolve_to_name(
        self,
        source: str,
        levels: int = 1,
        per_level_subscripts: Optional[List[List[Any]]] = None,
    ) -> str:
        """Resolve indirection to get TARGET VARIABLE NAME (not value).

        Used for SET operations where we need the name to assign to,
        not the value at that location.

        For SET @X=5 where X="Y": resolve_to_name("X", 1) → "Y"
        For SET @@X=5 where X="Y", Y="Z": resolve_to_name("X", 2) → "Z"

        Args:
            source: Initial variable name (source of @source)
            levels: Number of @ levels (1 for @X, 2 for @@X, etc.)
            per_level_subscripts: Subscripts per resolution level for @X@(s1)@(s2)

        Returns:
            Target variable name as string

        Raises:
            VarExpectedError: If resolved name is not a valid variable name
            ValueError: If levels < 1

        Examples:
            # @X where X="Y" → "Y" (the name to SET)
            resolve_to_name("X", 1) → "Y"

            # @@X where X="Y", Y="Z" → "Z" (the name to SET)
            resolve_to_name("X", 2) → "Z"

            # @X@(1,2) where X="A" → "A(1,2)" (the name to SET)
            resolve_to_name("X", 1, per_level_subscripts=[[1,2]]) → "A(1,2)"
        """
        if levels < 1:
            raise ValueError(f"Indirection levels must be >= 1, got {levels}")

        current = source

        # Resolve each level to get the target variable name
        for i in range(levels):
            # Get value at current name (this gives us the next name)
            value = self._get_value(current)

            # Convert to string for processing
            if not isinstance(value, str):
                value = str(value)

            # Handle recursive @-expression (value contains @)
            while value.startswith("@"):
                value = self._resolve_recursive_at(value)

            # Apply per-level subscripts if any
            if per_level_subscripts and i < len(per_level_subscripts):
                value = self._append_subscripts(value, per_level_subscripts[i])

            current = value

        # Validate that result is a valid variable name
        if not self._is_valid_var_name(current):
            raise VarExpectedError(current)

        return current

    def resolve_subscript_indirection(self, name: str) -> Any:
        """Resolve indirection within a subscript position.

        Used for A(1,@B,3) patterns where @B appears within a subscript list.
        Gets the VALUE at B and returns it for use as a subscript.

        Unlike NAME indirection, this does NOT perform multi-level resolution.
        @B in a subscript simply means "get the value of B and use it as subscript".

        Args:
            name: Variable name to resolve (source of @name in subscript)

        Returns:
            Value at the variable, for use as subscript

        Example:
            S B=2
            W A(1,@B,3)  ; @B resolves to 2, accessing A(1,2,3)
        """
        # For subscript indirection, we simply get the value directly
        # No multi-level resolution, no variable name validation
        return self._get_value(name)

    def resolve_subscript_list(self, subscripts: List[Any]) -> List[Any]:
        """Resolve indirection within a list of subscripts.

        Processes subscripts that may contain @ indirection and returns
        a list with all indirections resolved to their values.

        Args:
            subscripts: List of subscript values, some may be "@VAR" strings

        Returns:
            List with indirections resolved to values

        Examples:
            ["1", "@B", "3"] where B=2 → ["1", 2, "3"]
            ["@X", "@Y"] where X="a", Y=5 → ["a", 5]
        """
        result = []
        for sub in subscripts:
            if isinstance(sub, str) and sub.startswith("@"):
                # Subscript indirection - resolve the variable
                var_name = sub[1:]  # Remove @
                resolved = self.resolve_subscript_indirection(var_name)
                result.append(resolved)
            else:
                result.append(sub)
        return result

    def evaluate_expression(self, expr_string: str) -> Any:
        """Evaluate MUMPS expression string and return result.

        This is the CRITICAL method for fixing Challenge 6 bug.
        Instead of returning the string to m_truth(), we parse and
        evaluate the actual MUMPS expression.

        T052 (Challenge 7): Empty string in argument context is TRUE in YDB.
        This is YDB-specific behavior where `I @A` where A="" returns TRUE,
        even though `I ""` returns FALSE. The distinction appears to be:
        - Successful indirection resolution (even to empty) → TRUE
        - Direct empty string evaluation → FALSE

        T053a: Argument list indirection - when @A contains comma-separated
        values like "00.1,2", it expands to multiple IF conditions ANDed.
        Example: I @B where B="00.1,2" → I 00.1,2 → (0.1 AND 2) → TRUE

        Args:
            expr_string: MUMPS expression like "1=0", "X>5", "$E(S,1,3)"
                        Can also be comma-separated list: "1=1,0" (AND of conditions)

        Returns:
            Evaluated result (number, string, etc.)

        Examples:
            evaluate_expression("1=0") → 0  # False
            evaluate_expression("X>5") → 1  # True if X=10
            evaluate_expression("$E(\"ABC\",2)") → "B"
            evaluate_expression("") → 1  # YDB-specific: empty argument indirection is TRUE
            evaluate_expression("00.1,2") → 1  # Both 0.1 and 2 are truthy → TRUE
            evaluate_expression("1=1,0") → 0  # 1=1 is TRUE but 0 is FALSE → FALSE
        """
        # T052: Empty string in argument context is TRUE (YDB-specific)
        # This handles I @A where A="" → TRUE
        # Note: This differs from I "" → FALSE (direct empty string check)
        if not expr_string or not expr_string.strip():
            return 1  # YDB treats empty argument indirection as TRUE

        stripped = expr_string.strip()

        # T053a: Check for comma-separated argument list (IF argument expansion)
        # In MUMPS, I @A where A="cond1,cond2" expands to I cond1,cond2
        # which means evaluate cond1 AND cond2 (all must be truthy)
        args = self._split_argument_list(stripped)
        if len(args) > 1:
            # Multiple conditions - evaluate each and AND them together
            for arg in args:
                result = self._evaluate_single_expression(arg.strip())
                if not self._to_mumps_bool(result):
                    return 0  # Short-circuit: any FALSE makes whole thing FALSE
            return 1  # All conditions were truthy

        # Single expression
        return self._evaluate_single_expression(stripped)

    def _split_argument_list(self, expr_string: str) -> List[str]:
        """Split expression on commas that are outside quotes and parentheses.

        T053a: For IF argument indirection, "00.1,2" should split into ["00.1", "2"].
        But "$P(X,Y)" should NOT split (comma inside parens).
        And '"A,B"' should NOT split (comma inside quotes).

        Args:
            expr_string: Expression string potentially containing comma-separated args

        Returns:
            List of argument strings (1 element if no splitting needed)
        """
        result = []
        current = ""
        depth = 0  # Parenthesis depth
        in_quotes = False

        for char in expr_string:
            if char == '"' and (not current or current[-1] != "\\"):
                in_quotes = not in_quotes
                current += char
            elif char == "(" and not in_quotes:
                depth += 1
                current += char
            elif char == ")" and not in_quotes:
                depth -= 1
                current += char
            elif char == "," and not in_quotes and depth == 0:
                # This is a top-level comma - split here
                if current.strip():
                    result.append(current)
                current = ""
            else:
                current += char

        # Don't forget the last segment
        if current.strip():
            result.append(current)

        return result if result else [expr_string]

    def _evaluate_single_expression(self, expr_string: str) -> Any:
        """Evaluate a single MUMPS expression (no comma-separated list).

        Args:
            expr_string: Single MUMPS expression

        Returns:
            Evaluated result
        """
        stripped = expr_string.strip()

        # Empty after stripping
        if not stripped:
            return 1  # YDB-specific: empty is TRUE in argument context

        # Numeric literal check
        if self._is_numeric_literal(stripped):
            return self._parse_numeric(stripped)

        # String literal (quoted)
        if stripped.startswith('"') and stripped.endswith('"'):
            return stripped[1:-1]

        # Simple variable reference - just get its value
        if self._is_valid_var_name(stripped) and not any(
            op in stripped for op in ["=", "<", ">", "+", "-", "*", "/", "_", "[", "#"]
        ):
            value = self._get_value(stripped)
            # Return the truthiness as MUMPS boolean (0 or 1)
            return self._to_mumps_bool(value)

        # Complex expression - use execute_mumps to evaluate
        return self._evaluate_complex_expression(expr_string)

    def _evaluate_complex_expression(self, expr_string: str) -> Any:
        """Evaluate complex MUMPS expression using full parser.

        Uses MState.execute_mumps to parse and evaluate the expression.

        Args:
            expr_string: MUMPS expression string

        Returns:
            Evaluated result
        """
        from m2py.runtime import MArray

        # Build MUMPS code that evaluates the expression and stores result
        # Use % prefix for valid MUMPS name, which becomes _pct_ in Python
        mumps_temp_var = "%ARGINDIRECT"
        python_temp_var = "_pct_ARGINDIRECT"

        # Build the SET command
        mumps_code = f"S {mumps_temp_var}={expr_string}"

        # Get scope dict from CurrentScope for execute_mumps
        scope_dict = self._get_scope_dict()

        try:
            # Execute the SET to evaluate the expression
            self._state.execute_mumps(mumps_code, scope_dict)

            # Get the result - it will be an MArray, need to extract .value
            result_raw = scope_dict.get(python_temp_var, 0)

            # Extract value from MArray if present
            if isinstance(result_raw, MArray):
                result = result_raw.value
            else:
                result = result_raw

            # Clean up temp variable
            if python_temp_var in scope_dict:
                del scope_dict[python_temp_var]

            return result if result is not None else 0

        except Exception:
            # If evaluation fails, return 0 (FALSE)
            # This matches MUMPS behavior for invalid expressions
            return 0

    def _get_scope_dict(self) -> Dict[str, Any]:
        """Get the underlying scope dictionary for execute_mumps.

        Returns:
            The primary scope dictionary
        """
        # Access the internal scope_dict from CurrentScope
        scope_dict = self._scope._scope_dict
        if scope_dict is None:
            return {}
        return scope_dict

    def _get_value(self, name: str) -> Any:
        """Get variable value using CurrentScope.

        Args:
            name: Variable name (may include subscripts)

        Returns:
            Variable value or empty string if undefined
        """
        # Handle subscripted names
        if "(" in name:
            base_name, subscripts = self._parse_subscripted_name(name)

            # Handle global references
            if base_name.startswith("^"):
                return self._get_global_value(base_name, subscripts)

            return self._scope.get_subscripted(base_name, subscripts)

        # Handle global references
        if name.startswith("^"):
            return self._get_global_value(name, [])

        return self._scope.get(name)

    def _get_global_value(self, base_name: str, subscripts: List[Any]) -> Any:
        """Get global variable value from MState.

        Args:
            base_name: Global name including ^ prefix
            subscripts: List of subscript values

        Returns:
            Global value or empty string if undefined
        """
        # Handle naked reference
        if base_name == "^":
            # Use state's naked indicator to resolve
            # For now, delegate to state's get_var
            full_name = base_name
            if subscripts:
                subs_str = ",".join(
                    str(SubscriptCanonicalizer.canonicalize(s)) for s in subscripts
                )
                full_name = f"^({subs_str})"
            # Use state's get_var which handles naked resolution
            scope_dict = self._get_scope_dict()
            return self._state.get_var(full_name, scope_dict)

        # Regular global
        key = base_name[1:]  # Remove ^ prefix
        canonical_subs = tuple(
            str(SubscriptCanonicalizer.canonicalize(s)) for s in subscripts
        )
        return self._state._globals.get(key, canonical_subs) or ""

    def _resolve_recursive_at(self, value: str) -> str:
        """Resolve recursive @-expression in value.

        When a resolved value itself starts with @, we need to
        evaluate that as an expression/variable reference.

        Args:
            value: String starting with @

        Returns:
            Resolved value after handling the @ prefix
        """
        # Strip the @ and recursively resolve
        inner = value[1:]

        # If it's @$E(...) or other function, evaluate it
        if inner.startswith("$"):
            # Use evaluate_expression to handle function calls
            return str(self.evaluate_expression(inner))

        # Otherwise it's another variable reference
        return str(self._get_value(inner))

    def _append_subscripts(self, name: str, subscripts: List[Any]) -> str:
        """Append subscripts to a variable name.

        Args:
            name: Base variable name (may already have subscripts)
            subscripts: Subscripts to append

        Returns:
            Variable name with appended subscripts

        Note:
            String subscripts must be quoted in MUMPS-style name syntax.
            B("key") + ["sub"] → B("key","sub")
        """
        if not subscripts:
            return name

        # Format subscripts for MUMPS name syntax
        # Numeric subscripts don't need quotes, strings do
        formatted_subs = []
        for s in subscripts:
            canonical = SubscriptCanonicalizer.canonicalize(s)
            # Check if it's a canonical numeric string
            if SubscriptCanonicalizer.is_canonical_numeric_string(canonical):
                formatted_subs.append(canonical)
            else:
                # String subscripts need quotes - escape internal quotes
                escaped = canonical.replace('"', '""')
                formatted_subs.append(f'"{escaped}"')
        subs_str = ",".join(formatted_subs)

        if "(" in name:
            # Already has subscripts - append
            # Remove trailing ) and add new subscripts
            return f"{name[:-1]},{subs_str})"
        else:
            # No subscripts yet
            return f"{name}({subs_str})"

    def _parse_subscripted_name(self, name: str) -> tuple[str, List[str]]:
        """Parse a subscripted variable name into base and subscripts.

        Args:
            name: Variable name like "A(1,2)" or "^GLO(x,y)"

        Returns:
            Tuple of (base_name, list_of_subscripts)

        Note:
            String subscripts in MUMPS-style name syntax are quoted (e.g. "key").
            This method strips those quotes to return raw subscript values.
        """
        if "(" not in name:
            return name, []

        paren_pos = name.index("(")
        base = name[:paren_pos]
        subs_str = name[paren_pos + 1 : -1]  # Remove ( and )

        # Parse subscripts (simple split for now - doesn't handle nested parens)
        subscripts = []
        if subs_str:
            # Handle nested expressions with parentheses
            depth = 0
            current = ""
            for char in subs_str:
                if char == "(" or char == "[":
                    depth += 1
                    current += char
                elif char == ")" or char == "]":
                    depth -= 1
                    current += char
                elif char == "," and depth == 0:
                    subscripts.append(self._strip_mumps_quotes(current.strip()))
                    current = ""
                else:
                    current += char
            if current:
                subscripts.append(self._strip_mumps_quotes(current.strip()))

        return base, subscripts

    def _strip_mumps_quotes(self, s: str) -> str:
        """Strip MUMPS-style quotes from a string subscript.

        Args:
            s: String that may be surrounded by double quotes

        Returns:
            String with surrounding quotes removed and escaped quotes unescaped

        Examples::

            "FOO" (in MUMPS) -> FOO
            5 -> 5  (unchanged)
        """
        if len(s) >= 2 and s.startswith('"') and s.endswith('"'):
            # Remove surrounding quotes and unescape doubled quotes
            return s[1:-1].replace('""', '"')
        return s

    def _is_valid_var_name(self, name: str) -> bool:
        """Check if name is a valid MUMPS variable name.

        Args:
            name: String to check

        Returns:
            True if valid variable name
        """
        if not name:
            return False

        # Strip subscripts for validation
        base = name.split("(")[0] if "(" in name else name

        # Naked reference like "^(3)"
        if base == "^":
            return True

        # Global: must start with ^
        if base.startswith("^"):
            rest = base[1:]
            if not rest:
                return False
            return rest[0].isalpha() or rest[0] == "%"

        # Local: must start with letter or %
        return base[0].isalpha() or base[0] == "%"

    def _is_numeric_literal(self, s: str) -> bool:
        """Check if string is a numeric literal.

        Args:
            s: String to check

        Returns:
            True if numeric literal
        """
        if not s:
            return False
        try:
            float(s)
            return True
        except ValueError:
            return False

    def _parse_numeric(self, s: str) -> Any:
        """Parse numeric string to number.

        Args:
            s: Numeric string

        Returns:
            int or float value
        """
        try:
            # Try int first
            if "." not in s and "e" not in s.lower():
                return int(s)
            return float(s)
        except ValueError:
            return 0

    def _to_mumps_bool(self, value: Any) -> int:
        """Convert value to MUMPS boolean (0 or 1).

        Args:
            value: Any value

        Returns:
            0 or 1
        """
        if value is None or value == "":
            return 0

        if isinstance(value, (int, float)):
            return 1 if value != 0 else 0

        if isinstance(value, str):
            # MUMPS: numeric-looking strings are truthy if non-zero
            try:
                return 1 if float(value) != 0 else 0
            except ValueError:
                # Non-numeric strings are truthy if non-empty
                return 1 if value else 0

        # Other values - check truthiness
        return 1 if value else 0
