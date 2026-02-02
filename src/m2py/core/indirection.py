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

from m2py.core.exceptions import VarExpectedError, LVUNDEFError
from m2py.core.names import is_valid_varname as _core_is_valid_varname
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
        treat_empty_as_truthy: bool = False,
    ) -> Any:
        """Resolve indirection and return final value.

        Args:
            source: Initial variable name or expression string, OR
                a naked reference string like "^(5)" that needs expansion
            levels: Number of @ levels (1 for @X, 2 for @@X, etc.)
            context: How to use final resolved value
            direct_subscripts: Subscripts for @X(subs) form
            per_level_subscripts: Subscripts per resolution level for @X@(s1)@(s2)
            treat_empty_as_truthy: T052 - if True, empty string in ARGUMENT context
                                   returns 1 (TRUE). Used by IF indirection.

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
        # MUMPS semantics: get value first, then apply subscripts
        # For @VV@(12,456) where VV="V": get VV → "V", apply (12,456) → "V(12,456)"
        for i in range(levels):
            # Check if current is a naked reference string that needs expansion
            # rather than value lookup (e.g., "^(5)" should expand to "^V(5)")
            if self._is_naked_reference_string(current):
                # Expand the naked reference to full global name
                value = self._expand_naked_reference_string(current)
            else:
                # T065: Check if source variable is defined before getting value
                # This raises LVUNDEF for @UNDEF (undefined source variable)
                if self._is_valid_var_name(current) and not self._scope.exists(current):
                    # Global variables - check via _state
                    if current.startswith("^"):
                        # Globals don't raise LVUNDEF, they just return ""
                        pass
                    else:
                        # Local variable is undefined
                        raise LVUNDEFError(current)

                # Get value at current name
                value = self._get_value(current)

            # Convert to string for processing
            if not isinstance(value, str):
                value = str(value)

            # Handle recursive @-expression (value contains @)
            while value.startswith("@"):
                value = self._resolve_recursive_at(value)

            # Apply per-level subscripts AFTER value lookup
            if per_level_subscripts and i < len(per_level_subscripts):
                value = self._append_subscripts(value, per_level_subscripts[i])

            current = value

        # If final result is a naked reference string, expand it to full name
        # This handles cases like @@^(1)@(1) where the resolution produces "^(3)"
        # which needs to be expanded to "^V(5,3)" using the current naked indicator
        if self._is_naked_reference_string(current):
            current = self._expand_naked_reference_string(current)

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
            return self.evaluate_expression(
                current, treat_empty_as_truthy=treat_empty_as_truthy
            )

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

    def _is_naked_reference_string(self, s: str) -> bool:
        """Check if string is a naked reference like "^(5)" or "^(1,2)".

        A naked reference string is a string representation of a MUMPS naked
        global reference that needs to be expanded using the naked indicator.

        Args:
            s: String to check

        Returns:
            True if string is a naked reference pattern

        Examples:
            "^(5)" → True  (naked reference)
            "^(1,2)" → True  (naked reference with multiple subs)
            "^V(5)" → False  (regular global, not naked)
            "X" → False  (local variable)
            "^V" → False  (unsubscripted global)
        """
        # Pattern: starts with ^(, contains subscripts, ends with )
        # Must be "^(" not "^V(" etc.
        return s.startswith("^(") and s.endswith(")")

    def _expand_naked_reference_string(self, naked_ref: str) -> str:
        """Expand a naked reference string to full global name.

        Takes a naked reference string like "^(5)" and uses the current
        naked indicator to expand it to the full name like "^V(5)".

        Args:
            naked_ref: Naked reference string like "^(5)" or "^(1,2)"

        Returns:
            Full global name like "^V(5)" or "^V(1,2)"

        Raises:
            RuntimeError: If naked indicator is not set

        Examples:
            With naked indicator ("V", ()):
            "^(5)" → "^V(5)"
            "^(1,2)" → "^V(1,2)"

            With naked indicator ("V", ("3",)):
            "^(5)" → "^V(3,5)"
        """
        # Parse subscripts from the naked ref string
        # "^(5)" → subscripts = ["5"]
        # "^(1,2)" → subscripts = ["1", "2"]
        inner = naked_ref[2:-1]  # Strip "^(" and ")"
        subscripts = self._parse_subscript_list(inner)

        # Convert to tuple for resolve_naked
        subs_tuple = tuple(str(s) for s in subscripts)

        # Use the globals storage to resolve the naked reference
        resolved_name, full_subs = self._state._globals.resolve_naked(subs_tuple)

        # Build the full name string
        if full_subs:
            subs_str = ",".join(str(s) for s in full_subs)
            return f"^{resolved_name}({subs_str})"
        else:
            return f"^{resolved_name}"

    def resolve_to_name(
        self,
        source: str,
        levels: int = 1,
        per_level_subscripts: Optional[List[List[Any]]] = None,
        validate: bool = True,
    ) -> str:
        """Resolve indirection to get TARGET VARIABLE NAME (not value).

        Used for SET operations where we need the name to assign to,
        not the value at that location.

        For SET @X=5 where X="Y": resolve_to_name("X", 1) → "Y"
        For SET @@X=5 where X="Y", Y="Z": resolve_to_name("X", 2) → "Z"

        Args:
            source: Initial variable name (source of @source), OR
                a naked reference string like "^(5)" that needs expansion
            levels: Number of @ levels (1 for @X, 2 for @@X, etc.)
            per_level_subscripts: Subscripts per resolution level for @X@(s1)@(s2)
            validate: If True (default), validate result is a valid variable name.
                Set to False for KILL indirection which may contain exclusive
                KILL syntax like "(B),D,E".

        Returns:
            Target variable name as string

        Raises:
            VarExpectedError: If resolved name is not a valid variable name (when validate=True)
            ValueError: If levels < 1

        Examples:
            # @X where X="Y" → "Y" (the name to SET)
            resolve_to_name("X", 1) → "Y"

            # @@X where X="Y", Y="Z" → "Z" (the name to SET)
            resolve_to_name("X", 2) → "Z"

            # @X@(1,2) where X="A" → "A(1,2)" (the name to SET)
            resolve_to_name("X", 1, per_level_subscripts=[[1,2]]) → "A(1,2)"

            # @"^(5)"@(1) where naked=("V",()), ^V(5,1)="^(3)"
            # → expand "^(5)" to "^V(5)", append (1) → "^V(5,1)"
            # → lookup "^V(5,1)" → "^(3)", expand → "^V(5,3)"
            resolve_to_name("^(5)", 2, per_level_subscripts=[["1"], []]) → "^V(5,3)"
        """
        if levels < 1:
            raise ValueError(f"Indirection levels must be >= 1, got {levels}")

        current = source

        # Resolve each level to get the target variable name
        # MUMPS semantics: get value first, then apply subscripts
        # For @VV@(12,456) where VV="V": get VV → "V", apply (12,456) → "V(12,456)"
        # For @@C@(1,2) where C="X", X(1,2)="Y": get C → "X", apply (1,2) → "X(1,2)", get X(1,2) → "Y"
        for i in range(levels):
            # Check if current is a naked reference string that needs expansion
            # rather than value lookup (e.g., "^(5)" should expand to "^V(5)")
            if self._is_naked_reference_string(current):
                # Expand the naked reference to full global name
                value = self._expand_naked_reference_string(current)
            else:
                # Get value at current name (this gives us the next name)
                value = self._get_value(current)

            # Convert to string for processing
            if not isinstance(value, str):
                value = str(value)

            # Handle recursive @-expression (value contains @)
            while value.startswith("@"):
                value = self._resolve_recursive_at(value)

            # Apply per-level subscripts AFTER value lookup
            # This handles @VV@(subs) where VV's value becomes the base name
            if per_level_subscripts and i < len(per_level_subscripts):
                value = self._append_subscripts(value, per_level_subscripts[i])

            current = value

        # If final result is a naked reference string, expand it to full name
        # This handles cases like @@^(1)@(1) where the resolution produces "^(3)"
        # which needs to be expanded to "^V(5,3)" using the current naked indicator
        if self._is_naked_reference_string(current):
            current = self._expand_naked_reference_string(current)

        # Validate that result is a valid variable name (unless disabled for KILL)
        if validate and not self._is_valid_var_name(current):
            raise VarExpectedError(current)

        return current

    def resolve_to_argument_list(
        self,
        source: str,
        levels: int = 1,
        per_level_subscripts: Optional[List[List[Any]]] = None,
    ) -> List[str]:
        """Resolve indirection to get a list of TARGET VARIABLE NAMES.

        Feature: 017 T088 - Argument Indirection Command Lists
        Used for KILL @X, NEW @X where the resolved value may be a
        comma-separated list of variable names.

        For KILL @X where X="E,F": returns ["E", "F"]
        For KILL @X where X="A(1,2),B": returns ["A(1,2)", "B"]

        Each individual variable name is validated; if any is invalid,
        raises VarExpectedError.

        Args:
            source: Initial variable name (source of @source)
            levels: Number of @ levels (1 for @X, 2 for @@X, etc.)
            per_level_subscripts: Subscripts per resolution level for @X@(s1)@(s2)

        Returns:
            List of target variable names (may be single-element list)

        Raises:
            VarExpectedError: If any resolved name is not a valid variable name
            ValueError: If levels < 1

        Examples:
            # @X where X="E,F" → ["E", "F"]
            resolve_to_argument_list("X", 1) → ["E", "F"]

            # @X where X="A(1,2),B" → ["A(1,2)", "B"]
            resolve_to_argument_list("X", 1) → ["A(1,2)", "B"]

            # @X where X="Y" → ["Y"] (single element)
            resolve_to_argument_list("X", 1) → ["Y"]
        """
        if levels < 1:
            raise ValueError(f"Indirection levels must be >= 1, got {levels}")

        current = source

        # Resolve each level to get the target variable name(s)
        # MUMPS semantics: get value first, then apply subscripts
        for i in range(levels):
            # Check if current is a naked reference string that needs expansion
            if self._is_naked_reference_string(current):
                value = self._expand_naked_reference_string(current)
            else:
                value = self._get_value(current)

            # Convert to string for processing
            if not isinstance(value, str):
                value = str(value)

            # Handle recursive @-expression (value contains @)
            while value.startswith("@"):
                value = self._resolve_recursive_at(value)

            # Apply per-level subscripts AFTER value lookup
            if per_level_subscripts and i < len(per_level_subscripts):
                value = self._append_subscripts(value, per_level_subscripts[i])

            current = value

        # If final result is a naked reference string, expand it
        if self._is_naked_reference_string(current):
            current = self._expand_naked_reference_string(current)

        # Split by commas respecting parentheses (for subscripted variables)
        # Use existing _split_argument_list method (already handles quotes/parens)
        args = self._split_argument_list(current)

        # Validate each argument is a valid variable name
        for arg in args:
            arg = arg.strip()
            if arg and not self._is_valid_var_name(arg):
                raise VarExpectedError(arg)

        # Filter out empty args and strip whitespace
        return [arg.strip() for arg in args if arg.strip()]

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

    def evaluate_expression(
        self, expr_string: str, treat_empty_as_truthy: bool = False
    ) -> Any:
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
            treat_empty_as_truthy: T052 - if True, empty string returns 1 (TRUE)
                                   Used by IF indirection. Other contexts (WRITE, SET)
                                   should pass False to get error on empty.

        Returns:
            Evaluated result (number, string, etc.)

        Raises:
            VarExpectedError: If expr_string is empty and treat_empty_as_truthy=False

        Examples:
            evaluate_expression("1=0") → 0  # False
            evaluate_expression("X>5") → 1  # True if X=10
            evaluate_expression("$E(\"ABC\",2)") → "B"
            evaluate_expression("", treat_empty_as_truthy=True) → 1  # T052
            evaluate_expression("", treat_empty_as_truthy=False) → VarExpectedError
            evaluate_expression("00.1,2") → 1  # Both 0.1 and 2 are truthy → TRUE
            evaluate_expression("1=1,0") → 0  # 1=1 is TRUE but 0 is FALSE → FALSE
        """
        # Handle empty string based on context
        if not expr_string or not expr_string.strip():
            if treat_empty_as_truthy:
                # T052: Empty string in IF argument indirection is TRUE (YDB-specific)
                # This handles I @A where A="" → TRUE
                # Note: This differs from I "" → FALSE (direct empty string check)
                return 1
            else:
                # For WRITE, SET, etc. - empty string is an error
                raise VarExpectedError("", "Empty expression in indirection")

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
            Evaluated result (the actual value, not Boolean-converted)
        """
        stripped = expr_string.strip()

        # Empty after stripping - raise error for invalid expression
        if not stripped:
            raise VarExpectedError("", "Empty expression in indirection")

        # Numeric literal check
        if self._is_numeric_literal(stripped):
            return self._parse_numeric(stripped)

        # String literal (quoted)
        if stripped.startswith('"') and stripped.endswith('"'):
            return stripped[1:-1]

        # Simple variable reference - just get its value
        # Return the actual value, not Boolean conversion - let caller handle Boolean
        # if needed (e.g., IF uses m_truth() on the result)
        if self._is_valid_var_name(stripped) and not any(
            op in stripped for op in ["=", "<", ">", "+", "-", "*", "/", "_", "[", "#"]
        ):
            return self._get_value(stripped)

        # Complex expression - use execute_mumps to evaluate
        return self._evaluate_complex_expression(stripped)

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

            # Check if the variable was set - if not, the expression was invalid
            # (parser silently drops invalid expressions)
            if python_temp_var not in scope_dict:
                raise VarExpectedError(
                    expr_string, f"Invalid expression in indirection: '{expr_string}'"
                )

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

        except Exception as e:
            # If evaluation fails, raise a VarExpectedError with the invalid expression
            # YDB raises "INDEXTRACHARS: Indirection string contains extra trailing characters"
            # for invalid expressions in indirection
            raise VarExpectedError(
                expr_string, f"Invalid expression in indirection: '{expr_string}' - {e}"
            )

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

            # Evaluate subscripts as MUMPS expressions (handles variable refs)
            evaluated_subs = self._evaluate_subscripts(subscripts)

            # Handle global references
            if base_name.startswith("^"):
                return self._get_global_value(base_name, evaluated_subs)

            return self._scope.get_subscripted(base_name, evaluated_subs)

        # Handle global references
        if name.startswith("^"):
            return self._get_global_value(name, [])

        return self._scope.get(name)

    def _evaluate_subscripts(self, subscripts: List[str]) -> List[Any]:
        """Evaluate subscripts as MUMPS expressions.

        When subscripts come from an indirection string like "A(AA)",
        each subscript may be a variable reference that needs evaluation.

        Args:
            subscripts: List of subscript strings from parsing

        Returns:
            List of evaluated subscript values

        Examples:
            ["1", "2"] → [1, 2]  (numeric literals)
            ["AA", "BB"] → [11, 22]  (variable values if AA=11, BB=22)
            ["@X", "5"] → [value_of_X, 5]  (indirection + literal)
            ['"key"'] → ["key"]  (quoted string literal)
        """
        result = []
        for sub in subscripts:
            # Skip empty subscripts
            if not sub:
                result.append("")
                continue

            # Quoted string literal - treat as literal, not variable
            if sub.startswith('"') and sub.endswith('"'):
                # Strip quotes and unescape doubled quotes
                result.append(self._strip_mumps_quotes(sub))
                continue

            # Numeric literal
            if self._is_numeric_literal(sub):
                result.append(self._parse_numeric(sub))
            elif sub.startswith("@"):
                # Subscript indirection - resolve
                var_name = sub[1:]
                result.append(self._get_value(var_name))
            elif sub.startswith("$"):
                # Function call - evaluate as expression
                result.append(self.evaluate_expression(sub))
            elif self._is_valid_subscript_literal(sub):
                # Could be a variable reference - try to evaluate
                # But first check if it's just a simple identifier (variable)
                if sub.isidentifier() or (sub[0] == "%" and sub[1:].isidentifier()):
                    # This is a variable name - get its value
                    result.append(self._scope.get(sub))
                else:
                    # Complex expression - use evaluate_expression
                    result.append(self.evaluate_expression(sub))
            else:
                # String literal that doesn't look like a variable
                result.append(sub)

        return result

    def _is_valid_subscript_literal(self, s: str) -> bool:
        """Check if string could be a subscript expression to evaluate.

        Args:
            s: String to check

        Returns:
            True if it looks like it needs evaluation
        """
        if not s:
            return False
        # Variable names start with letter or %
        if s[0].isalpha() or s[0] == "%":
            return True
        # Expressions with operators
        if any(
            op in s
            for op in ["+", "-", "*", "/", "_", "#", "\\", "=", "<", ">", "&", "!", "'"]
        ):
            return True
        return False

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

        Handles patterns like:
        - @VAR → get value of VAR
        - @VAR@(subs) → get value of VAR, append subs → return NAME (let caller get value)
        - @@VAR@(subs) → resolve @VAR first, then append subs → return NAME
        - @$E(...) → evaluate MUMPS function

        Args:
            value: String starting with @

        Returns:
            For @VAR: the VALUE at VAR
            For @VAR@(subs): the NAME with subs appended (so caller's while loop can continue)
        """
        # Strip the @ and recursively resolve
        inner = value[1:]

        # If inner itself starts with @, recursively resolve it first
        # This handles @@VAR, @@@VAR, etc. in VALUE strings
        # Use while loop to handle cases where the resolved value also starts with @
        while inner.startswith("@"):
            inner = self._resolve_recursive_at(inner)
            # If the result is empty or not a valid continuation, return it
            if not inner:
                return inner

        # If it's @$E(...) or other function, evaluate it
        if inner.startswith("$"):
            # Use evaluate_expression to handle function calls
            return str(self.evaluate_expression(inner))

        # Handle parenthesized expressions: @(expr)@(subs) or just @(expr)
        # A leading ( indicates a parenthesized expression, not a subscripted variable
        if inner.startswith("("):
            # Find the matching close paren for the expression
            close_pos = self._find_matching_paren(inner, 0)
            if close_pos > 0:
                expr_content = inner[1:close_pos]  # Contents inside (...)
                trailing = inner[close_pos + 1 :]  # e.g., "@(5,6)" or ""

                # Evaluate the expression to get a variable name
                result = str(self.evaluate_expression(expr_content))

                # If there are trailing @(subs), append them
                while trailing.startswith("@("):
                    sub_close = self._find_matching_paren(trailing, 1)
                    if sub_close < 0:
                        break
                    subs_str = trailing[2:sub_close]
                    subs = self._parse_subscript_list(subs_str)
                    result = self._append_subscripts(result, subs)
                    trailing = trailing[sub_close + 1 :]

                return result

        # Check for name indirection subscripts pattern: VAR@(subs)
        # This is different from VAR(subs) - the @() means "append these subscripts
        # to whatever VAR resolves to"
        # IMPORTANT: We need to distinguish:
        #   - VAR@(subs) = name-indirection subscripts (@ after variable name)
        #   - VAR(@X) = subscript indirection (@ inside subscripts)
        # Only look for @( that appears BEFORE any opening parenthesis
        paren_pos = inner.find("(")
        at_paren_pos = inner.find("@(")

        # Only treat as name-indirection subscripts if @( appears before (
        # Example: X@(1) has @( at 1, no ( before it → name-indirection subscripts
        # Example: ^V1A(@Y) has @( at 5, but ( at 4 → subscript indirection, not name-indirection
        if at_paren_pos > 0 and (paren_pos < 0 or at_paren_pos < paren_pos):
            # Pattern: VAR@(subs) or VAR@(subs)@(more_subs)
            var_name = inner[:at_paren_pos]
            subscript_part = inner[at_paren_pos:]

            # Get value of VAR (which should be a variable name)
            resolved_name = str(self._get_value(var_name))

            # If the resolved_name itself contains @, recursively resolve it FIRST
            # before appending our subscripts. This handles cases like:
            # @VV@(B,"C") where VV="@^VV(\"A\")" and ^VV("A")="^VV(\"a\")"
            # We need to resolve @^VV("A") → ^VV("a") THEN append (B,"C")
            while resolved_name.startswith("@"):
                resolved_name = self._resolve_recursive_at(resolved_name)

            # Parse and append all @(subs) groups
            remaining = subscript_part
            while remaining.startswith("@("):
                # Find matching close paren
                close_pos = self._find_matching_paren(remaining, 1)
                if close_pos < 0:
                    # Malformed - just return what we have
                    return resolved_name + remaining

                subs_str = remaining[2:close_pos]  # Contents inside @(...)
                subs = self._parse_subscript_list(subs_str)

                # Append subscripts to resolved name
                resolved_name = self._append_subscripts(resolved_name, subs)

                remaining = remaining[close_pos + 1 :]

            # Return the NAME (with subscripts appended), not the value
            # The outer while loop will call _get_value on the next iteration
            # if the value at this name starts with @
            return resolved_name

        # Otherwise it's a variable reference (possibly with subscript indirection)
        # Handle subscript indirection: ^V1A(@Y) means ^V1A with Y's value as subscript
        # Also handle trailing @(subs) after the variable reference
        if paren_pos > 0:
            # Has subscripts - need to resolve any @VAR in subscripts
            base_name = inner[:paren_pos]

            # Find the matching close paren for the subscript list
            close_pos = self._find_matching_paren(inner, paren_pos)
            if close_pos < 0:
                # Malformed - try to handle gracefully
                subs_part = inner[paren_pos:]
                trailing_subs = ""
            else:
                subs_part = inner[paren_pos : close_pos + 1]
                trailing_subs = inner[close_pos + 1 :]  # e.g., "@(@X)" or ""

            # Parse and resolve subscripts (handles @VAR inside subscripts)
            resolved_subs = self._resolve_subscript_string(subs_part)

            # Get value at the fully resolved variable reference
            full_ref = base_name + resolved_subs
            value = str(self._get_value(full_ref))

            # If there are trailing @(subs), this is name-indirection subscripts
            # that should be appended to the resolved value
            if trailing_subs:
                # If value itself starts with @, resolve it first
                while value.startswith("@"):
                    value = self._resolve_recursive_at(value)

                # Now append the trailing subscripts
                remaining = trailing_subs
                while remaining.startswith("@("):
                    close_pos = self._find_matching_paren(remaining, 1)
                    if close_pos < 0:
                        break
                    subs_str = remaining[2:close_pos]
                    subs = self._parse_subscript_list(subs_str)
                    value = self._append_subscripts(value, subs)
                    remaining = remaining[close_pos + 1 :]

            return value

        # Simple variable reference - get and return VALUE
        return str(self._get_value(inner))

    def _find_matching_paren(self, s: str, start_pos: int) -> int:
        """Find the position of the closing paren matching the one at start_pos.

        Args:
            s: String to search
            start_pos: Position of the opening '('

        Returns:
            Position of matching ')' or -1 if not found
        """
        depth = 1
        i = start_pos + 1
        in_quotes = False
        while i < len(s):
            c = s[i]
            if c == '"' and (i == 0 or s[i - 1] != "\\"):
                in_quotes = not in_quotes
            elif not in_quotes:
                if c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
                    if depth == 0:
                        return i
            i += 1
        return -1

    def _resolve_subscript_string(self, subs_part: str) -> str:
        """Resolve subscript indirection within a subscript string.

        Handles patterns like (1,@Y,3) where @Y is subscript indirection.
        Returns the subscript string with all @VAR resolved to values.

        Args:
            subs_part: Subscript string like "(1,@Y,3)" or "(@X)"

        Returns:
            Subscript string with indirections resolved, e.g. "(1,3,3)"
        """
        if not subs_part or not subs_part.startswith("("):
            return subs_part

        # Remove outer parens for processing
        inner = subs_part[1:-1] if subs_part.endswith(")") else subs_part[1:]

        # Parse each subscript, resolving @VAR references
        resolved_subs = self._parse_subscript_list(inner)

        # Rebuild the subscript string
        subs_strs = []
        for sub in resolved_subs:
            if isinstance(sub, str):
                # Quote strings that need quoting
                if sub and not sub.replace(".", "").replace("-", "").isdigit():
                    subs_strs.append(f'"{sub}"' if '"' not in sub else str(sub))
                else:
                    subs_strs.append(str(sub))
            else:
                subs_strs.append(str(sub))

        return "(" + ",".join(subs_strs) + ")"

    def _parse_subscript_list(self, subs_str: str) -> List[Any]:
        """Parse a comma-separated subscript list.

        Args:
            subs_str: String like "1,2" or "1,@B,3"

        Returns:
            List of subscript values (resolving any @VAR references)
        """
        if not subs_str:
            return []

        result = []
        current = ""
        depth = 0
        in_quotes = False

        for char in subs_str:
            if char == '"' and (not current or current[-1] != "\\"):
                in_quotes = not in_quotes
                current += char
            elif char == "(" and not in_quotes:
                depth += 1
                current += char
            elif char == ")" and not in_quotes:
                depth -= 1
                current += char
            elif char == "," and depth == 0 and not in_quotes:
                result.append(self._evaluate_subscript_value(current.strip()))
                current = ""
            else:
                current += char

        if current:
            result.append(self._evaluate_subscript_value(current.strip()))

        return result

    def _evaluate_subscript_value(self, value: str) -> Any:
        """Evaluate a single subscript value, handling @VAR references.

        In MUMPS, @VAR in a subscript position means:
        1. Get the value of VAR
        2. Evaluate that value as an expression

        So ^V1A(@Y) where Y="Z" and Z=3 means ^V1A(3), not ^V1A("Z").

        Multiple @ levels like @@Y mean:
        1. @Y → get value of Y → "Z"
        2. @@Y → @(@Y) → @"Z" → evaluate "Z" as variable → Z=Q → "Q"
        3. But then we also evaluate that: Q=3 → 3

        Args:
            value: Subscript value string, may be "@VAR", "@@VAR", a quoted string,
                   a numeric literal, or a variable name

        Returns:
            Evaluated subscript value
        """
        if value.startswith("@"):
            # Count how many @ levels
            at_count = 0
            while at_count < len(value) and value[at_count] == "@":
                at_count += 1

            var_name = value[at_count:]

            # Resolve through @ levels: @@Y means @(@Y)
            # So we need to dereference at_count times
            current_value = self._get_value(var_name)

            for _ in range(at_count - 1):
                # Each additional @ means another dereference
                if isinstance(current_value, str) and current_value:
                    current_value = self._get_value(current_value)
                else:
                    break

            # Now evaluate the final value as an expression
            # If it's a variable name, look it up
            if isinstance(current_value, str) and current_value:
                return self.evaluate_expression(current_value)
            return current_value

        # Check if it's a quoted string - remove quotes
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1].replace('""', '"')

        # Check if it's a numeric literal
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # Bare identifier - evaluate as MUMPS expression (variable reference)
        # In MUMPS, A(X) where X=5 means A(5), not A("X")
        if value and self._is_valid_var_name(value):
            return self.evaluate_expression(value)

        # Check if it looks like an arithmetic expression (has operators)
        # This handles cases like "1+2", "8/2", "A*B" etc.
        if value and any(op in value for op in ["+", "-", "*", "/", "\\", "#", "_"]):
            try:
                return self.evaluate_expression(value)
            except Exception:
                pass  # Fall through to return as-is

        # Return as-is for anything else
        return value

    @staticmethod
    def _append_subscripts(name: str, subscripts: List[Any]) -> str:
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
            This method preserves quotes to distinguish literals from variables.
            Quote stripping is handled in _evaluate_subscripts().
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
                    # Don't strip quotes here - let _evaluate_subscripts handle it
                    subscripts.append(current.strip())
                    current = ""
                else:
                    current += char
            if current:
                # Don't strip quotes here - let _evaluate_subscripts handle it
                subscripts.append(current.strip())

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

        Feature: 018-unified-variable-system
        Now delegates to core.names.is_valid_varname() for unified validation.

        Args:
            name: String to check (may include subscripts)

        Returns:
            True if valid variable name
        """
        return _core_is_valid_varname(name, allow_subscripts=True)

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
