# Internal API Contracts: Codegen Refactoring (Phase 2)

This is an internal refactoring — no external/public APIs change. These contracts
define the interfaces of new internal helper functions and modules.

## codegen/var_access.py

```python
def var_read_expr(var_name: str, ctx: "GeneratorContext") -> str:
    """Generate Python expression that reads a local variable's value.

    Returns the appropriate expression based on the codegen strategy:
    - TRAMPOLINE + dynamic_locals: state._locals.get({name!r}, MArray())
    - TRAMPOLINE + state_vars: state.{python_name}
    - SIMPLE_FUNCTIONS: _scope.get({name!r}, MArray())

    Args:
        var_name: MUMPS variable name (e.g., "X", "RESULT")
        ctx: Current generator context

    Returns:
        Python expression string for reading the variable
    """

def var_write_stmt(var_name: str, value_expr: str, ctx: "GeneratorContext") -> str:
    """Generate Python statement that writes a value to a local variable.

    Args:
        var_name: MUMPS variable name
        value_expr: Python expression for the value to write
        ctx: Current generator context

    Returns:
        Python statement string for writing the variable
    """

def var_base_expr(var_name: str, ctx: "GeneratorContext") -> str:
    """Generate Python expression for the base MArray of a local variable.

    Used when the caller needs the MArray object itself (for subscripted access).

    Args:
        var_name: MUMPS variable name
        ctx: Current generator context

    Returns:
        Python expression string for the MArray base object
    """
```

## codegen/statements.py — Extracted Helpers

```python
def gen_subscripts_tuple(subscripts: list, ctx: "GeneratorContext") -> str:
    """Generate Python tuple expression from ASG subscript node list.

    Args:
        subscripts: List of ASG expression nodes representing subscripts
        ctx: Current generator context

    Returns:
        Python tuple string, e.g., "(expr1, expr2,)" or "()"
    """

def _build_lhs_getter_setter(
    target: "MExpr", ctx: "GeneratorContext"
) -> tuple[str, str]:
    """Build getter/setter lambda expressions for LHS variable access.

    Handles all variable types: GlobalVariable, NakedGlobal, MIndirection, MVariable.
    3-way strategy dispatch for MVariable.

    Args:
        target: ASG expression node for the LHS target
        ctx: Current generator context

    Returns:
        (getter_expr, setter_expr) tuple of Python lambda expression strings
    """

def emit_state_to_scope_sync(ctx: "GeneratorContext") -> None:
    """Emit state._locals → _scope synchronization code.

    Only emits if ctx.uses_dynamic_locals is True.
    """

def emit_scope_to_state_sync(ctx: "GeneratorContext") -> None:
    """Emit _scope → state._locals synchronization code.

    Only emits if ctx.uses_dynamic_locals is True.
    Wraps non-MArray values in MArray containers.
    """

def _emit_goto_external_handler(ctx: "GeneratorContext") -> None:
    """Emit standard 'except GotoExternal' handler block.

    Includes scope sync and re-raise.
    """
```

## parser/ — compile_mumps_line

```python
def compile_mumps_line(
    code_str: str,
    context: Optional["AnalysisContext"] = None
) -> list["MStatement"]:
    """Run full parse→analyze→structure pipeline for a MUMPS code string.

    Used by XECUTE and any other inline compilation needs.

    Args:
        code_str: MUMPS source code string (single line)
        context: Optional analysis context for variable resolution

    Returns:
        List of analyzed MStatement ASG nodes
    """
```

## runtime/__init__.py — Extended ZWRITE

```python
def zwrite_local(
    self,
    name: str,
    subscripts: tuple,
    scope: dict,
    *,
    range_start: Optional[Any] = None,
    range_end: Optional[Any] = None,
) -> None:
    """ZWRITE a local variable with optional subscript range filtering.

    Range filtering uses MUMPS collation ordering via _mumps_collation_key.

    Args:
        name: Variable name
        subscripts: Concrete subscript prefix
        scope: Current scope dict
        range_start: Optional lower bound (inclusive, MUMPS collation)
        range_end: Optional upper bound (inclusive, MUMPS collation)
    """

def zwrite_global(
    self,
    name: str,
    subscripts: tuple,
    *,
    range_start: Optional[Any] = None,
    range_end: Optional[Any] = None,
) -> None:
    """ZWRITE a global variable with optional subscript range filtering."""
```

## runtime/__init__.py — Consolidated offset_wrapper

```python
def _create_offset_entry_wrapper(
    self,
    base_fn: Callable,
    offset: int,
    strategy: "GotoStrategy",
    *,
    handle_goto_external: bool = False,
) -> Callable:
    """Factory for offset entry point wrappers.

    Consolidates the two near-identical offset_wrapper closures into
    a single parameterized factory.

    Args:
        base_fn: The base routine function
        offset: Line offset to skip to
        strategy: Codegen strategy used
        handle_goto_external: Whether to include GotoExternal handling
    """
```

## ASG Changes — MLockTarget

```python
@dataclass
class MLockTarget(ASGElement):
    """A single lock target in a LOCK statement.

    Replaces the untyped dict previously used in MLockStatement.targets.
    """
    name: Optional[str] = None
    subscripts: List["MExpr"] = field(default_factory=list)
    is_global: bool = False
    lockop: str = ""                          # "", "+", "-"
    timeout: Optional["MExpr"] = None
    postcondition: Optional["MExpr"] = None
    is_indirect: bool = False
    indirection: Optional["MExpr"] = None
    indirection_levels: int = 0
```
