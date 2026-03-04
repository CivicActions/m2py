"""IRIS backend implementation for GlobalStorageBackend protocol.

Uses the intersystems-irispython SDK to connect to an InterSystems IRIS
database over TCP. The IRIS container runs via Docker; our code runs locally.

Features:
    - Lazy connection initialization (deferred until first use)
    - Thread-safe via threading.Lock
    - Naked reference tracking (Python-side, matching InMemoryGlobalStorage)
    - MUMPS subscript canonicalization via SubscriptCanonicalizer
    - SDK exception translation to m2py BackendError types
    - Connection parameter reading from environment variables
    - Namespace support for extended global references
"""

# All methods call _ensure_connected() which guarantees self._iris is set,
# but type checkers cannot track this narrowing across method boundaries.

from __future__ import annotations

import builtins
import os
import threading
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

from m2py.core.subscripts import SubscriptCanonicalizer
from m2py.runtime.helpers import (
    _format_subscript,
    m_format_output,
)

if TYPE_CHECKING:
    from m2py.runtime import MArray


class IRISGlobalStorage:
    """IRIS backend implementation using intersystems-irispython SDK.

    Connects to an IRIS server over TCP to persist globals. Supports
    namespace switching via extended reference syntax ^|"NS"|Global.

    Thread safety: A threading.Lock serializes all IRIS API calls.
    The IRIS connection is not inherently thread-safe.
    """

    # Class-level tracking of all live instances for cleanup in test fixtures.
    _all_instances: builtins.set[IRISGlobalStorage] = set()

    def __init__(self) -> None:
        """Initialize IRIS backend (lazy — no connection yet)."""
        self._iris_module = None  # Lazy import of iris module
        self._conn = None  # IRIS connection object
        self._iris = None  # iris.IRIS instance
        self._lock = threading.Lock()

        # Naked indicator (Python-side, same as InMemoryGlobalStorage)
        self._naked_indicator_value: tuple[str, tuple[str, ...]] | None = None

        # Lock tracking: {(name, subscripts): count}
        self._lock_table: dict[tuple[str, tuple[str, ...]], int] = {}

        # Transaction state
        self._tlevel: int = 0
        # Lock snapshot for TROLLBACK — per spec §6.3.2, ROLLBACK removes
        # any nrefs from the Lock-LIST not present when the TRANSACTION started
        self._lock_snapshot: dict[tuple[str, tuple[str, ...]], int] | None = None

        # $ZREFERENCE
        self._last_global_ref: str = ""

        # Track known global names for kill_all()
        self._known_globals: set[str] = set()

    # Class-level set tracking all global names written by ANY instance.
    # IRIS shares a single database so kill_all() on any instance must
    # be able to clean up globals created by other instances.
    _all_known_globals: builtins.set[str] = set()

    @property
    def _naked_indicator(self) -> tuple[str, tuple[str, ...]] | None:
        """Naked indicator for global reference resolution."""
        return self._naked_indicator_value

    @_naked_indicator.setter
    def _naked_indicator(self, value: tuple[str, tuple[str, ...]] | None) -> None:
        self._naked_indicator_value = value

    def _resolve_ns_name(
        self, name: str, subscripts: tuple[str, ...]
    ) -> tuple[str, tuple[str, ...]]:
        """Resolve namespace-prefixed names like ``"NS:X"`` into (name, subs).

        Codegen may emit ``set("NS:X", subs, val)`` using the ``NS:name``
        convention from the InMemory backend.  IRIS global names cannot
        contain ``:``, so we translate:

            ("NS:X", ("a",)) → ("X", ("~NS:NS", "a"))

        Plain names (no ``:``) pass through unchanged.
        """
        if ":" in name:
            ns, real_name = name.split(":", 1)
            return real_name, (f"~NS:{ns}", *subscripts)
        return name, subscripts

    def _ensure_connected(self) -> None:
        """Lazily connect to IRIS on first use."""
        if self._conn is not None:
            return

        try:
            import iris as iris_module

            self._iris_module = iris_module
        except ImportError as e:
            from m2py.runtime.backend_exceptions import BackendConnectionError

            raise BackendConnectionError(
                "IRIS Python SDK not available. "
                "Install with: uv add intersystems-irispython --optional backend"
            ) from e

        from m2py.runtime.backend_config import IRISConfig

        config = IRISConfig.from_env()

        try:
            self._conn = iris_module.connect(
                config.host,
                config.port,
                config.namespace,
                config.username,
                config.password,
            )
            self._iris = iris_module.createIRIS(self._conn)
            # Track this instance so test fixtures can close all connections.
            IRISGlobalStorage._all_instances.add(self)
        except Exception as e:
            from m2py.runtime.backend_exceptions import BackendConnectionError

            raise BackendConnectionError(
                f"Cannot connect to IRIS at {config.host}:{config.port}: {e}"
            ) from e

    def _make_global_name(self, name: str) -> str:
        """Construct IRIS global name with caret.

        Args:
            name: Global name without caret (e.g., "PATIENT")

        Returns:
            Global name with caret (e.g., "^PATIENT")
        """
        return f"^{name}"

    def _canonicalize_subscript(self, subscript: str | int | float) -> str:
        """Convert subscript to MUMPS canonical string form."""
        return SubscriptCanonicalizer.canonicalize(subscript)

    def _canonicalize_subscripts(
        self, subscripts: tuple[str | int | float, ...]
    ) -> tuple[str, ...]:
        """Convert all subscripts to canonical string form."""
        return tuple(self._canonicalize_subscript(s) for s in subscripts)

    def _update_naked_indicator(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Update naked indicator after global access."""
        if subscripts:
            subs_str = ",".join(_format_subscript(s) for s in subscripts)
            self._last_global_ref = f"^{name}({subs_str})"
        else:
            self._last_global_ref = f"^{name}"

        if subscripts:
            self._naked_indicator_value = (name, subscripts[:-1])
        else:
            self._naked_indicator_value = None

    def _translate_exception(self, e: Exception) -> Exception:
        """Translate IRIS exceptions to m2py backend exceptions."""
        from m2py.runtime.backend_exceptions import (
            BackendConnectionError,
            BackendTimeoutError,
            BackendError,
        )

        msg = str(e)
        if "timeout" in msg.lower() or "LOCKTIME" in msg:
            err = BackendTimeoutError(msg)
            err.__cause__ = e
            return err
        elif "connect" in msg.lower() or "connection" in msg.lower():
            err = BackendConnectionError(msg)
            err.__cause__ = e
            return err
        else:
            err = BackendError("IRISERR", msg)
            err.__cause__ = e
            return err

    # =========================================================================
    # Null Subscript Support (IRIS SDK workaround)
    # =========================================================================
    # The IRIS Python SDK raises <SUBSCRIPT> for empty-string subscripts,
    # even when the IRIS server allows them (Config.Miscellaneous.NullSubscripts=1).
    # VistA MUMPS code uses empty-string subscripts (e.g., ^TMP("MXMLPRSE",$J,"ELE","")).
    #
    # Workaround: detect empty-string subscripts and delegate those operations
    # to a server-side ObjectScript class (M2PY.Helper) which uses indirection
    # to handle null subscripts natively.

    _helper_class_installed: bool = False

    @staticmethod
    def _has_null_subscript(subscripts: tuple[str, ...]) -> bool:
        """Check if any subscript is an empty string (null subscript)."""
        return any(s == "" for s in subscripts)

    def _build_gref(self, name: str, subscripts: tuple[str, ...]) -> str:
        """Build MUMPS global reference string for use with indirection.

        Examples:
            _build_gref("TMP", ("a", "", "c")) -> '^TMP("a","","c")'
        """
        gname = self._make_global_name(name)
        if not subscripts:
            return gname
        parts = []
        for s in subscripts:
            escaped = str(s).replace('"', '""')
            parts.append(f'"{escaped}"')
        return f"{gname}({','.join(parts)})"

    @staticmethod
    def _parse_gref(ref: str) -> tuple[str, tuple[str, ...]] | None:
        """Parse a MUMPS global reference string into (name, subscripts).

        Handles quoted strings with doubled internal quotes.

        Examples:
            _parse_gref('^TMP("a","","c")') -> ("TMP", ("a", "", "c"))
            _parse_gref('^X') -> ("X", ())
            _parse_gref('') -> None
        """
        if not ref:
            return None
        if ref.startswith("^"):
            ref = ref[1:]
        paren = ref.find("(")
        if paren == -1:
            return (ref, ())
        name = ref[:paren]
        inner = ref[paren + 1 : -1]  # Remove outer parens
        subs: list[str] = []
        i = 0
        while i < len(inner):
            if inner[i] == '"':
                # Quoted string subscript
                i += 1
                chars: list[str] = []
                while i < len(inner):
                    if inner[i] == '"':
                        if i + 1 < len(inner) and inner[i + 1] == '"':
                            chars.append('"')
                            i += 2
                        else:
                            i += 1  # closing quote
                            break
                    else:
                        chars.append(inner[i])
                        i += 1
                subs.append("".join(chars))
            elif inner[i] == ",":
                i += 1
            else:
                # Unquoted (numeric) subscript
                j = i
                while j < len(inner) and inner[j] != ",":
                    j += 1
                subs.append(inner[i:j])
                i = j
        return (name, tuple(subs))

    def _ensure_helper_class(self) -> None:
        """Install the M2PY.Helper class in IRIS if not already present.

        Creates an ObjectScript class with class methods that use indirection
        to perform global operations, bypassing the SDK's null subscript
        restriction. The class is compiled once and persists in the IRIS
        database for the lifetime of the container.
        """
        if IRISGlobalStorage._helper_class_installed:
            return

        assert self._iris is not None

        try:
            exists = self._iris.classMethodValue(
                "%Dictionary.ClassDefinition", "%ExistsId", "M2PY.Helper"
            )
            if exists:
                IRISGlobalStorage._helper_class_installed = True
                return
        except Exception:
            pass

        # Create the helper class via the SDK object API
        cls = self._iris.classMethodObject(
            "%Dictionary.ClassDefinition", "%New", "M2PY.Helper"
        )
        cls.set("Super", "%RegisteredObject")

        # Define all helper methods
        _methods = {
            "GGet": {
                "spec": "gref:%String",
                "ret": "%String",
                "code": " Quit $Get(@gref)",
            },
            "GSet": {
                "spec": "val:%String,gref:%String",
                "ret": "%Integer",
                "code": " Set @gref=val Quit 1",
            },
            "GKill": {
                "spec": "gref:%String",
                "ret": "%Integer",
                "code": " Kill @gref Quit 1",
            },
            "GData": {
                "spec": "gref:%String",
                "ret": "%Integer",
                "code": " Quit $Data(@gref)",
            },
            "GOrder": {
                "spec": "gref:%String,dir:%Integer=1",
                "ret": "%String",
                "code": " Quit $Order(@gref,dir)",
            },
            "GQuery": {
                "spec": "gref:%String",
                "ret": "%String",
                "code": " Quit $Query(@gref)",
            },
        }

        for mname, info in _methods.items():
            m = self._iris.classMethodObject("%Dictionary.MethodDefinition", "%New")
            m.set("Name", mname)
            m.set("ClassMethod", True)
            m.set("FormalSpec", info["spec"])
            m.set("ReturnType", info["ret"])
            impl = m.getObject("Implementation")
            impl.invokeVoid("WriteLine", info["code"])
            m.set("parent", cls)

        cls.invoke("%Save")
        self._iris.classMethodValue("%SYSTEM.OBJ", "Compile", "M2PY.Helper", "ck")
        IRISGlobalStorage._helper_class_installed = True

    def _helper_get(self, name: str, subscripts: tuple[str, ...]) -> str | None:
        """Get global value via M2PY.Helper (null subscript safe)."""
        self._ensure_helper_class()
        assert self._iris is not None
        gref = self._build_gref(name, subscripts)
        # $DATA check needed because $GET returns "" for both undefined
        # and empty-string values
        d = int(self._iris.classMethodValue("M2PY.Helper", "GData", gref))
        if d in (0, 10):
            return None
        result = self._iris.classMethodString("M2PY.Helper", "GGet", gref)
        return str(result) if result is not None else None

    def _helper_set(self, name: str, subscripts: tuple[str, ...], value: str) -> None:
        """Set global value via M2PY.Helper (null subscript safe)."""
        self._ensure_helper_class()
        assert self._iris is not None
        gref = self._build_gref(name, subscripts)
        self._iris.classMethodValue("M2PY.Helper", "GSet", str(value), gref)

    def _helper_kill(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Kill global node via M2PY.Helper (null subscript safe)."""
        self._ensure_helper_class()
        assert self._iris is not None
        gref = self._build_gref(name, subscripts)
        self._iris.classMethodValue("M2PY.Helper", "GKill", gref)

    def _helper_data(self, name: str, subscripts: tuple[str, ...]) -> int:
        """$DATA via M2PY.Helper (null subscript safe)."""
        self._ensure_helper_class()
        assert self._iris is not None
        gref = self._build_gref(name, subscripts)
        return int(self._iris.classMethodValue("M2PY.Helper", "GData", gref))

    def _helper_order(
        self, name: str, subscripts: tuple[str, ...], direction: int = 1
    ) -> str:
        """$ORDER via M2PY.Helper (null subscript safe)."""
        self._ensure_helper_class()
        assert self._iris is not None
        gref = self._build_gref(name, subscripts)
        result = self._iris.classMethodString("M2PY.Helper", "GOrder", gref, direction)
        if result is None:
            return ""
        return m_format_output(str(result))

    def _helper_query(self, name: str, subscripts: tuple[str, ...]) -> str:
        """$QUERY via M2PY.Helper (null subscript safe).

        Returns the full global reference of the next node with data,
        using the server-side $QUERY function directly.
        """
        self._ensure_helper_class()
        assert self._iris is not None
        gref = self._build_gref(name, subscripts)
        result = self._iris.classMethodString("M2PY.Helper", "GQuery", gref)
        if result is None or result == "":
            return ""
        return str(result)

    # =========================================================================
    # Basic CRUD Operations
    # =========================================================================

    def get(
        self, name: str, subscripts: tuple[str, ...], update_naked: bool = True
    ) -> str | None:
        """Get value at ^NAME(subscripts)."""
        name, subscripts = self._resolve_ns_name(name, subscripts)
        subscripts = self._canonicalize_subscripts(subscripts)
        if update_naked:
            self._update_naked_indicator(name, subscripts)

        with self._lock:
            self._ensure_connected()
            try:
                # Use helper for null subscript workaround
                if subscripts and self._has_null_subscript(subscripts):
                    return self._helper_get(name, subscripts)

                gname = self._make_global_name(name)
                if subscripts:
                    val = self._iris.get(gname, *subscripts)
                else:
                    val = self._iris.get(gname)
                if val is None:
                    return None
                # IRIS SDK may return int/float Python types.
                # Canonicalize numeric values so str(5.0) becomes "5"
                # (MUMPS canonical) rather than "5.0".
                if isinstance(val, float):
                    if val == int(val):
                        return str(int(val))
                    # Remove trailing zeros, no leading zero before decimal
                    s = f"{val:.15g}"
                    if "." in s:
                        s = s.rstrip("0").rstrip(".")
                    if s.startswith("0."):
                        s = s[1:]
                    elif s.startswith("-0."):
                        s = "-" + s[2:]
                    return s
                if isinstance(val, int):
                    return str(val)
                return str(val)
            except Exception as e:
                # IRIS raises exception for <UNDEFINED>
                msg = str(e)
                if "UNDEFINED" in msg or "does not exist" in msg.lower():
                    return None
                raise self._translate_exception(e)

    def set(self, name: str, subscripts: tuple[str, ...], value: str) -> None:
        """Set value at ^NAME(subscripts)."""
        name, subscripts = self._resolve_ns_name(name, subscripts)
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)
        self._known_globals.add(name)
        IRISGlobalStorage._all_known_globals.add(name)
        value = str(value)  # MUMPS canonical: all values are strings

        with self._lock:
            self._ensure_connected()
            try:
                # Use helper for null subscript workaround
                if subscripts and self._has_null_subscript(subscripts):
                    self._helper_set(name, subscripts, value)
                    return

                gname = self._make_global_name(name)
                if subscripts:
                    self._iris.set(value, gname, *subscripts)
                else:
                    self._iris.set(value, gname)
            except Exception as e:
                raise self._translate_exception(e)

    def kill(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Kill node and all descendants at ^NAME(subscripts)."""
        name, subscripts = self._resolve_ns_name(name, subscripts)
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        with self._lock:
            self._ensure_connected()
            try:
                # Use helper for null subscript workaround
                if subscripts and self._has_null_subscript(subscripts):
                    self._helper_kill(name, subscripts)
                    return

                gname = self._make_global_name(name)
                if subscripts:
                    self._iris.kill(gname, *subscripts)
                else:
                    self._iris.kill(gname)
            except Exception as e:
                # Ignore errors on nonexistent nodes
                msg = str(e)
                if "UNDEFINED" in msg:
                    return
                raise self._translate_exception(e)

    # Globals that belong to the IRIS platform and must not be killed.
    # Includes HealthShare/Ensemble package globals (contain dots) and
    # well-known IRIS internals.  Checked by kill_all().
    _IRIS_SYSTEM_GLOBALS: frozenset[str] = frozenset(
        {"ZOSF", "DD", "DIC", "DMU", "DST", "CFG"}
    )

    def kill_all(self) -> None:
        """Kill all globals in the database. Used for testing/reset.

        Enumerates all globals via the ``%SYS.GlobalQuery`` SQL class so
        that globals created in child processes (e.g. multiprocessing
        workers) are also cleaned up, not just those tracked in
        ``_known_globals``.  System/package globals (names containing
        dots or in the ``_IRIS_SYSTEM_GLOBALS`` set) are preserved.
        """
        with self._lock:
            self._ensure_connected()
            # Enumerate all globals from the IRIS global directory
            try:
                rs = self._iris.classMethodValue(
                    "%SYSTEM.SQL",
                    "Execute",
                    "SELECT Name FROM %SYS.GlobalQuery_NameSpaceList()",
                )
                while rs.invokeBoolean("%Next"):
                    raw_name = str(rs.get("Name"))
                    # Skip package globals (contain dots) and known IRIS internals
                    if "." in raw_name or raw_name in self._IRIS_SYSTEM_GLOBALS:
                        continue
                    # Skip names with special SQL notation (subscript refs)
                    if "(" in raw_name:
                        continue
                    try:
                        self._iris.kill(f"^{raw_name}")
                    except Exception:
                        pass
            except Exception:
                # Fallback: kill only tracked globals
                all_names = self._known_globals | IRISGlobalStorage._all_known_globals
                for gname in list(all_names):
                    try:
                        self._iris.kill(f"^{gname}")
                    except Exception:
                        pass

            self._known_globals.clear()
            IRISGlobalStorage._all_known_globals.clear()

        self._naked_indicator_value = None
        self._last_global_ref = ""

    def data(self, name: str, subscripts: tuple[str, ...]) -> int:
        """Return $DATA value for ^NAME(subscripts)."""
        name, subscripts = self._resolve_ns_name(name, subscripts)
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        with self._lock:
            self._ensure_connected()
            try:
                # Use helper for null subscript workaround
                if subscripts and self._has_null_subscript(subscripts):
                    return self._helper_data(name, subscripts)

                gname = self._make_global_name(name)
                if subscripts:
                    return self._iris.isDefined(gname, *subscripts)
                else:
                    return self._iris.isDefined(gname)
            except Exception as e:
                msg = str(e)
                if "UNDEFINED" in msg:
                    return 0
                raise self._translate_exception(e)

    # =========================================================================
    # Naked Reference Support
    # =========================================================================

    def get_naked_indicator(self) -> tuple[str, tuple[str, ...]] | None:
        """Get current naked indicator."""
        return self._naked_indicator_value

    def set_naked_indicator(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Set naked indicator explicitly."""
        self._naked_indicator_value = (name, self._canonicalize_subscripts(subscripts))

    @property
    def last_global_ref(self) -> str:
        """Return the last global reference string ($ZREFERENCE)."""
        return self._last_global_ref

    def set_order_naked(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Pre-set naked indicator for $ORDER evaluation ordering."""
        subs = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subs)

    def resolve_naked(self, subscripts: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
        """Resolve naked reference ^(subscripts) to full global reference."""
        if self._naked_indicator_value is None:
            raise RuntimeError("NAKEDERR: Naked reference without prior global access")
        name, base_subscripts = self._naked_indicator_value
        subscripts = self._canonicalize_subscripts(subscripts)
        full_subscripts = base_subscripts + subscripts
        return (name, full_subscripts)

    # =========================================================================
    # Traversal Operations
    # =========================================================================

    def order(
        self,
        name: str,
        subscripts: tuple[str, ...],
        direction: int = 1,
        update_naked: bool = True,
    ) -> str:
        """Return next/previous subscript in MUMPS collation order."""
        name, subscripts = self._resolve_ns_name(name, subscripts)
        subscripts = self._canonicalize_subscripts(subscripts)
        if update_naked:
            self._update_naked_indicator(name, subscripts)

        if not subscripts:
            return ""

        with self._lock:
            self._ensure_connected()
            try:
                # Use helper for null subscript workaround
                # Check parent subscripts (not the last one, which is the
                # $ORDER start position — "" is valid there as "from beginning")
                parent_subs = subscripts[:-1]
                if parent_subs and self._has_null_subscript(parent_subs):
                    return self._helper_order(name, subscripts, direction)

                gname = self._make_global_name(name)
                parent_subs = subscripts[:-1]
                start_sub = subscripts[-1]

                reversed_flag = direction != 1
                if parent_subs:
                    result = self._iris.nextSubscript(
                        reversed_flag, gname, *parent_subs, start_sub
                    )
                else:
                    result = self._iris.nextSubscript(reversed_flag, gname, start_sub)

                if result is None or result == "":
                    return ""

                return m_format_output(str(result))
            except Exception as e:
                msg = str(e)
                if "UNDEFINED" in msg:
                    return ""
                raise self._translate_exception(e)

    def query(self, name: str, subscripts: tuple[str, ...]) -> str:
        """Return full reference of next node with data ($QUERY).

        Uses the M2PY.Helper class for server-side $QUERY when null subscripts
        are involved (IRIS SDK workaround), otherwise falls back to manual
        tree traversal since IRIS Native API doesn't expose $QUERY.
        """
        name, subscripts = self._resolve_ns_name(name, subscripts)
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        with self._lock:
            self._ensure_connected()
            try:
                # Use server-side $QUERY via helper when null subscripts
                # could be encountered in the tree
                if subscripts and self._has_null_subscript(subscripts):
                    ref = self._helper_query(name, subscripts)
                    if ref:
                        parsed = self._parse_gref(ref)
                        if parsed:
                            _, result_subs = parsed
                            self._update_naked_indicator(name, result_subs)
                    return ref

                result = self._query_next(name, subscripts)
                if result is None:
                    return ""

                result_subs = result
                formatted_subs = [_format_subscript(sub) for sub in result_subs]
                ref = f"^{name}({','.join(formatted_subs)})"

                # Update naked indicator
                self._update_naked_indicator(name, result_subs)

                return ref
            except Exception as e:
                msg = str(e)
                if "UNDEFINED" in msg or "SUBSCRIPT" in msg:
                    # Fall back to helper on SUBSCRIPT errors (null subscripts
                    # encountered during tree traversal)
                    try:
                        ref = self._helper_query(name, subscripts)
                        if ref:
                            parsed = self._parse_gref(ref)
                            if parsed:
                                _, result_subs = parsed
                                self._update_naked_indicator(name, result_subs)
                        return ref
                    except Exception:
                        pass
                    return ""
                raise self._translate_exception(e)

    def _query_next(
        self, name: str, subscripts: tuple[str, ...]
    ) -> tuple[str, ...] | None:
        """Find next valued node after given subscripts (manual $QUERY).

        Implements depth-first traversal to find the next node with a value.
        Handles empty-string subscripts (meaning "from the beginning").
        """
        gname = self._make_global_name(name)

        if not subscripts:
            return None

        # Check if the last subscript is "" (meaning "start from beginning")
        last_sub = subscripts[-1]
        parent_subs = subscripts[:-1]

        if last_sub == "":
            # $QUERY from beginning: find first subscript at this level
            if parent_subs:
                first = self._iris.nextSubscript(False, gname, *parent_subs, "")
            else:
                first = self._iris.nextSubscript(False, gname, "")

            if first is None or first == "":
                return None

            first_subs = parent_subs + (str(first),)
            d = self._iris.isDefined(gname, *first_subs)
            if d in (1, 11):
                return first_subs
            # Has children but no value — descend
            return self._query_next(name, first_subs)

        # Normal case: current subscript is not empty
        # Try to descend into children first
        d = self._iris.isDefined(gname, *subscripts)

        if d in (10, 11):
            # Try to find first child
            if subscripts:
                first_child = self._iris.nextSubscript(False, gname, *subscripts, "")
            else:
                first_child = self._iris.nextSubscript(False, gname, "")

            if first_child is not None and first_child != "":
                child_subs = subscripts + (str(first_child),)
                child_d = self._iris.isDefined(gname, *child_subs)
                if child_d in (1, 11):
                    return child_subs
                # Recurse into this child
                result = self._query_next(name, child_subs)
                if result is not None:
                    return result

        # Try to move to next sibling
        current = subscripts[-1]

        if parent_subs:
            next_sib = self._iris.nextSubscript(False, gname, *parent_subs, current)
        else:
            next_sib = self._iris.nextSubscript(False, gname, current)

        if next_sib is not None and next_sib != "":
            sib_subs = parent_subs + (str(next_sib),)
            sib_d = self._iris.isDefined(gname, *sib_subs)
            if sib_d in (1, 11):
                return sib_subs
            # Recurse into sibling
            result = self._query_next(name, sib_subs)
            if result is not None:
                return result

            # Continue to next siblings
            while True:
                if parent_subs:
                    next_next = self._iris.nextSubscript(
                        False, gname, *parent_subs, str(next_sib)
                    )
                else:
                    next_next = self._iris.nextSubscript(False, gname, str(next_sib))

                if next_next is None or next_next == "":
                    break

                next_sib = next_next
                sib_subs = parent_subs + (str(next_sib),)
                sib_d = self._iris.isDefined(gname, *sib_subs)
                if sib_d in (1, 11):
                    return sib_subs
                result = self._query_next(name, sib_subs)
                if result is not None:
                    return result

        # Move up to parent level and try next
        if parent_subs:
            return self._query_up(name, parent_subs)

        return None

    def _query_up(
        self, name: str, subscripts: tuple[str, ...]
    ) -> tuple[str, ...] | None:
        """Walk up the tree and look for next sibling at each level."""
        gname = self._make_global_name(name)

        parent_subs = subscripts[:-1]
        current = subscripts[-1]

        if parent_subs:
            next_sib = self._iris.nextSubscript(False, gname, *parent_subs, current)
        else:
            next_sib = self._iris.nextSubscript(False, gname, current)

        if next_sib is not None and next_sib != "":
            sib_subs = parent_subs + (str(next_sib),)
            sib_d = self._iris.isDefined(gname, *sib_subs)
            if sib_d in (1, 11):
                return sib_subs
            result = self._query_next(name, sib_subs)
            if result is not None:
                return result

        # Continue up
        if parent_subs:
            return self._query_up(name, parent_subs)

        return None

    # =========================================================================
    # Kill Node (value only)
    # =========================================================================

    def kill_node(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Kill only the value at node, preserving descendants.

        IRIS doesn't have a native kill-node-only operation, so we:
        1. Save all children
        2. Kill the node (which kills children too)
        3. Restore children
        """
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        with self._lock:
            self._ensure_connected()
            try:
                gname = self._make_global_name(name)
                if subscripts:
                    d = self._iris.isDefined(gname, *subscripts)
                else:
                    d = self._iris.isDefined(gname)

                if d in (0, 10):
                    # No value to kill
                    return

                if d == 1:
                    # Value only, no children — just kill
                    if subscripts:
                        self._iris.kill(gname, *subscripts)
                    else:
                        self._iris.kill(gname)
                    return

                # d == 11: Has value AND children
                # Save the tree, remove value, restore children
                # Actually, we can use the IRIS execute method to run
                # ZKILL which kills only the node value
                # Try using classMethodValue to call $ZKILL or similar
                # For now: save children, kill all, restore children
                children = self._save_children(name, subscripts)
                if subscripts:
                    self._iris.kill(gname, *subscripts)
                else:
                    self._iris.kill(gname)
                self._restore_children(name, subscripts, children)
            except Exception as e:
                msg = str(e)
                if "UNDEFINED" in msg:
                    return
                raise self._translate_exception(e)

    def _save_children(
        self, name: str, subscripts: tuple[str, ...]
    ) -> list[tuple[tuple[str, ...], str]]:
        """Save all descendant nodes under the given path."""
        result = []
        self._collect_children(name, subscripts, result)
        return result

    def _collect_children(
        self,
        name: str,
        subscripts: tuple[str, ...],
        result: list[tuple[tuple[str, ...], str]],
    ) -> None:
        """Recursively collect all children with values."""
        gname = self._make_global_name(name)
        current = ""
        while True:
            if subscripts:
                next_child = self._iris.nextSubscript(
                    False, gname, *subscripts, current
                )
            else:
                next_child = self._iris.nextSubscript(False, gname, current)

            if next_child is None or next_child == "":
                break

            child_subs = subscripts + (str(next_child),)
            child_d = self._iris.isDefined(gname, *child_subs)

            if child_d in (1, 11):
                val = self._iris.get(gname, *child_subs)
                result.append((child_subs, str(val)))

            if child_d in (10, 11):
                self._collect_children(name, child_subs, result)

            current = str(next_child)

    def _restore_children(
        self,
        name: str,
        parent_subs: tuple[str, ...],
        children: list[tuple[tuple[str, ...], str]],
    ) -> None:
        """Restore saved child nodes."""
        gname = self._make_global_name(name)
        for child_subs, value in children:
            self._iris.set(value, gname, *child_subs)

    # =========================================================================
    # Bulk Operations
    # =========================================================================

    def get_tree(self, name: str, subscripts: tuple[str, ...]) -> "MArray | None":
        """Get subtree as MArray for MERGE source."""
        from m2py.runtime import MArray

        name, subscripts = self._resolve_ns_name(name, subscripts)
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        with self._lock:
            self._ensure_connected()
            try:
                gname = self._make_global_name(name)
                if subscripts:
                    d = self._iris.isDefined(gname, *subscripts)
                else:
                    d = self._iris.isDefined(gname)

                if d == 0:
                    return None

                root = MArray()
                if d in (1, 11):
                    if subscripts:
                        val = self._iris.get(gname, *subscripts)
                    else:
                        val = self._iris.get(gname)
                    if val is not None:
                        root._value = str(val)

                if d in (10, 11):
                    self._build_tree_iris(name, subscripts, root)

                return root
            except Exception as e:
                msg = str(e)
                if "UNDEFINED" in msg:
                    return None
                raise self._translate_exception(e)

    def _build_tree_iris(
        self,
        name: str,
        subscripts: tuple[str, ...],
        parent_marray: "MArray",
    ) -> None:
        """Recursively build MArray from IRIS global using order traversal."""
        from m2py.runtime import MArray

        gname = self._make_global_name(name)
        current = ""
        while True:
            if subscripts:
                next_child = self._iris.nextSubscript(
                    False, gname, *subscripts, current
                )
            else:
                next_child = self._iris.nextSubscript(False, gname, current)

            if next_child is None or next_child == "":
                break

            sub_str = str(next_child)
            child = MArray()
            child_subs = subscripts + (sub_str,)

            d = self._iris.isDefined(gname, *child_subs)
            if d in (1, 11):
                val = self._iris.get(gname, *child_subs)
                if val is not None:
                    child._value = str(val)

            if d in (10, 11):
                self._build_tree_iris(name, child_subs, child)

            if child._value is not None or child._children:
                parent_marray._children[sub_str] = child

            current = sub_str

    def merge_tree(
        self, name: str, subscripts: tuple[str, ...], source: "MArray"
    ) -> None:
        """Merge MArray tree into global at ^NAME(subscripts)."""
        name, subscripts = self._resolve_ns_name(name, subscripts)
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)
        self._known_globals.add(name)
        IRISGlobalStorage._all_known_globals.add(name)
        self._merge_tree_recursive(name, subscripts, source)

    def _merge_tree_recursive(
        self, name: str, subscripts: tuple[str, ...], node: "MArray"
    ) -> None:
        """Recursively merge MArray node into IRIS global."""
        if node._value is not None:
            self.set(name, subscripts, str(node._value))
        for key, child in node._children.items():
            child_sub = str(key)
            self._merge_tree_recursive(name, subscripts + (child_sub,), child)

    # =========================================================================
    # Atomic Increment
    # =========================================================================

    def incr(self, name: str, subscripts: tuple[str, ...], increment: str = "1") -> str:
        """Atomically increment value at ^NAME(subscripts)."""
        name, subscripts = self._resolve_ns_name(name, subscripts)
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)
        self._known_globals.add(name)
        IRISGlobalStorage._all_known_globals.add(name)

        with self._lock:
            self._ensure_connected()
            try:
                gname = self._make_global_name(name)
                # IRIS increment returns the new value
                inc_val = int(increment) if "." not in increment else float(increment)
                if subscripts:
                    result = self._iris.increment(inc_val, gname, *subscripts)
                else:
                    result = self._iris.increment(inc_val, gname)
                return m_format_output(str(result))
            except Exception as e:
                raise self._translate_exception(e)

    # =========================================================================
    # Lock Operations
    # =========================================================================

    def lock(
        self,
        name: str,
        subscripts: tuple[str, ...],
        timeout: float | None = None,
        lock_type: str = "+",
    ) -> bool:
        """Acquire or release a lock on ^NAME(subscripts)."""
        subscripts = self._canonicalize_subscripts(subscripts)
        lock_key = (name, subscripts)

        if lock_type == "-":
            # Decremental unlock
            if lock_key in self._lock_table:
                self._lock_table[lock_key] -= 1
                if self._lock_table[lock_key] <= 0:
                    del self._lock_table[lock_key]

            with self._lock:
                self._ensure_connected()
                try:
                    lock_name = f"^{name}"
                    if subscripts:
                        self._iris.unlock("", lock_name, *subscripts)
                    else:
                        self._iris.unlock("", lock_name)
                except Exception:
                    pass
            return True

        # Incremental lock (+)
        #
        # IRIS timeout semantics: timeout=0 means "try once, fail immediately".
        # MUMPS untimed LOCK waits indefinitely, so we retry in a loop with
        # 10-second per-attempt timeouts up to a 300-second safety limit.
        import time as _time

        _PER_ATTEMPT_SEC = 10
        _MAX_INDEFINITE = 300  # 5-minute safety limit

        with self._lock:
            self._ensure_connected()
            lock_name = f"^{name}"

            if timeout is not None:
                # Explicit timeout — single attempt
                timeout_sec = int(timeout)
                try:
                    if subscripts:
                        self._iris.lock("", timeout_sec, lock_name, *subscripts)
                    else:
                        self._iris.lock("", timeout_sec, lock_name)
                    self._lock_table[lock_key] = self._lock_table.get(lock_key, 0) + 1
                    return True
                except Exception as e:
                    msg = str(e)
                    if "TIMEOUT" in msg or "timeout" in msg.lower():
                        return False
                    raise self._translate_exception(e)
            else:
                # Indefinite wait — retry with per-attempt timeouts
                deadline = _time.monotonic() + _MAX_INDEFINITE
                while True:
                    remaining = deadline - _time.monotonic()
                    if remaining <= 0:
                        return False
                    attempt_sec = min(_PER_ATTEMPT_SEC, int(remaining) + 1)
                    try:
                        if subscripts:
                            self._iris.lock("", attempt_sec, lock_name, *subscripts)
                        else:
                            self._iris.lock("", attempt_sec, lock_name)
                        self._lock_table[lock_key] = (
                            self._lock_table.get(lock_key, 0) + 1
                        )
                        return True
                    except Exception as e:
                        msg = str(e)
                        if "TIMEOUT" in msg or "timeout" in msg.lower():
                            continue  # retry until deadline
                        raise self._translate_exception(e)

    def unlock(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Release a lock on ^NAME(subscripts)."""
        subscripts = self._canonicalize_subscripts(subscripts)
        lock_key = (name, subscripts)
        if lock_key in self._lock_table:
            self._lock_table[lock_key] -= 1
            if self._lock_table[lock_key] <= 0:
                del self._lock_table[lock_key]

        with self._lock:
            self._ensure_connected()
            try:
                lock_name = f"^{name}"
                if subscripts:
                    self._iris.unlock("", lock_name, *subscripts)
                else:
                    self._iris.unlock("", lock_name)
            except Exception:
                pass

    def unlock_all(self) -> None:
        """Release all locks held by current process."""
        with self._lock:
            self._ensure_connected()
            try:
                self._iris.releaseAllLocks()
            except Exception:
                pass
        self._lock_table.clear()

    def get_locks(self) -> list[tuple[str, str, int]]:
        """Return all locks held by the current process/thread."""
        import json

        result = []
        for (lock_name, lock_subs), count in self._lock_table.items():
            subs_json = json.dumps(list(lock_subs))
            result.append((lock_name, subs_json, count))
        return result

    # =========================================================================
    # Transaction Operations
    # =========================================================================

    def transaction_start(self) -> None:
        """Begin a transaction (TSTART).

        Per spec §6.3.2: snapshots Lock-LIST for TROLLBACK.
        """
        # Snapshot lock state at outermost TSTART only
        if self._tlevel == 0:
            self._lock_snapshot = dict(self._lock_table)

        self._tlevel += 1
        if self._tlevel == 1:
            with self._lock:
                self._ensure_connected()
                try:
                    self._iris.tStart()
                except Exception:
                    self._tlevel -= 1
                    self._lock_snapshot = None
                    raise

    def transaction_commit(self) -> None:
        """Commit current transaction (TCOMMIT)."""
        if self._tlevel == 0:
            raise RuntimeError(
                "M44: Cannot TCOMMIT outside of a transaction ($TLEVEL=0)"
            )
        self._tlevel -= 1
        if self._tlevel == 0:
            with self._lock:
                self._ensure_connected()
                self._iris.tCommit()
            # Clear lock snapshot on outermost commit
            self._lock_snapshot = None

    def transaction_rollback(self) -> None:
        """Rollback current transaction (TROLLBACK).

        Per spec §6.3.2: restores Lock-LIST to pre-TSTART state.
        """
        if self._tlevel == 0:
            raise RuntimeError(
                "M44: Cannot TROLLBACK outside of a transaction ($TLEVEL=0)"
            )
        self._tlevel = 0
        with self._lock:
            self._ensure_connected()
            self._iris.tRollback()

            # Restore lock state to what it was at outermost TSTART
            if self._lock_snapshot is not None:
                # Release native locks that were acquired during the transaction
                for lock_key, count in self._lock_table.items():
                    if lock_key not in self._lock_snapshot:
                        # This lock was acquired during the txn — release it
                        name, subs = lock_key
                        lock_name = f"^{name}"
                        for _ in range(count):
                            try:
                                if subs:
                                    self._iris.unlock("", lock_name, *subs)
                                else:
                                    self._iris.unlock("", lock_name)
                            except Exception:
                                pass
                    else:
                        # Lock existed before, but count may have grown
                        orig_count = self._lock_snapshot[lock_key]
                        extra = count - orig_count
                        if extra > 0:
                            name, subs = lock_key
                            lock_name = f"^{name}"
                            for _ in range(extra):
                                try:
                                    if subs:
                                        self._iris.unlock("", lock_name, *subs)
                                    else:
                                        self._iris.unlock("", lock_name)
                                except Exception:
                                    pass
                # Restore the Python-side lock tracking dict
                self._lock_table = dict(self._lock_snapshot)
                self._lock_snapshot = None

    def get_tlevel(self) -> int:
        """Return current transaction nesting level ($TLEVEL)."""
        return self._tlevel

    # =========================================================================
    # SSVN Operations
    # =========================================================================

    def ssvn_global(self, subscript: str) -> str:
        """Query ^$GLOBAL(name) for global existence."""
        with self._lock:
            self._ensure_connected()
            try:
                gname = self._make_global_name(subscript)
                d = self._iris.isDefined(gname)
                return "1" if d > 0 else ""
            except Exception:
                return ""

    def ssvn_job(self, subscript: str) -> str:
        """Query ^$JOB(pid) for job/process information."""
        try:
            pid = int(subscript)
            if pid <= 0:
                return ""  # PIDs must be positive
            try:
                os.kill(pid, 0)  # Signal 0 = check existence
                return "1"
            except ProcessLookupError:
                return ""  # Process does not exist
            except PermissionError:
                return "1"  # Process exists but we lack permission
        except (ValueError, OverflowError):
            return ""

    def ssvn_lock(self, subscript: str) -> str:
        """Query ^$LOCK(lockname) for lock information."""
        for (lock_name, _), count in self._lock_table.items():
            if lock_name == subscript:
                return str(count)
        return ""

    def ssvn_routine(self, subscript: str) -> str:
        """Query ^$ROUTINE(routinename) for routine metadata.

        Checks if a routine is importable as a Python module under the
        m2py.routines or m2py.runtime.routines namespace, or exists as a
        .m file in the current directory.
        """
        import importlib.util

        if not subscript:
            return ""

        for prefix in ("m2py.routines", "m2py.runtime.routines"):
            try:
                spec = importlib.util.find_spec(f"{prefix}.{subscript}")
                if spec is not None:
                    return "1"
            except (ModuleNotFoundError, ValueError):
                pass

        if os.path.isfile(f"{subscript}.m"):
            return "1"

        return ""

    # =========================================================================
    # Namespace (Extended Global References)
    # =========================================================================

    def _ns_subs(self, subscripts: tuple[str, ...], namespace: str) -> tuple[str, ...]:
        """Prepend namespace qualifier as first subscript.

        IRIS global names only allow alphanumeric chars, so we cannot
        embed the namespace in the name (e.g. ``NS:X`` is invalid).  Instead,
        we prepend a namespace tag as the first subscript:

            _ns_subs(("a",), "NS") → ("~NS:NS", "a")

        The ``~NS:`` prefix sorts after all normal subscripts and is never
        generated by user code, guaranteeing isolation.
        """
        if namespace:
            return (f"~NS:{namespace}", *subscripts)
        return subscripts

    def set_ns(
        self,
        name: str,
        subscripts: tuple[str, ...],
        value: str,
        namespace: str = "",
    ) -> None:
        """Set a global variable in a specific namespace."""
        self.set(name, self._ns_subs(subscripts, namespace), value)

    def get_ns(
        self,
        name: str,
        subscripts: tuple[str, ...],
        namespace: str = "",
    ) -> str | None:
        """Get a global variable from a specific namespace."""
        return self.get(name, self._ns_subs(subscripts, namespace))

    def data_ns(
        self, name: str, subscripts: tuple[str, ...], namespace: str = ""
    ) -> int:
        """$DATA for namespace-qualified global."""
        return self.data(name, self._ns_subs(subscripts, namespace))

    def order_ns(
        self,
        name: str,
        subscripts: tuple[str, ...],
        direction: int = 1,
        namespace: str = "",
    ) -> str:
        """$ORDER for namespace-qualified global."""
        return self.order(name, self._ns_subs(subscripts, namespace), direction)

    def kill_ns(
        self, name: str, subscripts: tuple[str, ...], namespace: str = ""
    ) -> None:
        """KILL for namespace-qualified global."""
        self.kill(name, self._ns_subs(subscripts, namespace))

    def query_ns(
        self,
        name: str,
        subscripts: tuple[str, ...],
        direction: int = 1,
        namespace: str = "",
    ) -> str:
        """$QUERY for namespace-qualified global."""
        return self.query(name, self._ns_subs(subscripts, namespace))

    def merge_tree_ns(
        self,
        name: str,
        subscripts: tuple[str, ...],
        source: "MArray",
        namespace: str = "",
    ) -> None:
        """MERGE for namespace-qualified global."""
        self.merge_tree(name, self._ns_subs(subscripts, namespace), source)

    def get_tree_ns(
        self,
        name: str,
        subscripts: tuple[str, ...],
        namespace: str = "",
    ) -> "MArray | None":
        """Get subtree for namespace-qualified global."""
        return self.get_tree(name, self._ns_subs(subscripts, namespace))

    # =========================================================================
    # ZWR Import
    # =========================================================================

    def import_zwr(self, source: Path | TextIO, batch_size: int = 10_000) -> int:
        """Import ZWR data with transaction batching for speed.

        Groups *batch_size* SET operations inside ``tStart()``/``tCommit()``
        transactions to reduce per-node TCP overhead.  Bypasses the
        high-level ``self.set()`` and calls ``_iris.set()`` directly.

        Falls back to line-by-line ``self.set()`` if the native path fails.
        """
        import logging

        from m2py.runtime.zwr import parse_zwr_stream

        log = logging.getLogger(__name__)

        try:
            return self._import_zwr_batched(source, batch_size)
        except Exception:
            log.warning(
                "IRIS batched import failed; falling back to line-by-line",
                exc_info=True,
            )

        # Fallback: line-by-line
        count = 0

        def _load(stream: TextIO) -> int:
            nonlocal count
            for name, subs, value in parse_zwr_stream(stream):
                bare_name = name[1:] if name.startswith("^") else name
                self.set(bare_name, tuple(subs), value)
                count += 1
            return count

        if isinstance(source, Path):
            with open(source, errors="replace") as f:
                return _load(f)
        return _load(source)

    def _import_zwr_batched(
        self, source: Path | TextIO, batch_size: int = 10_000
    ) -> int:
        """Core batched import via low-level ``_iris.set()``."""
        from m2py.runtime.zwr import parse_zwr_stream

        self._ensure_connected()
        iris_obj = self._iris
        assert iris_obj is not None  # guaranteed by _ensure_connected

        count = 0
        batch_count = 0

        def _do_set(name: str, subs: list[str], value: str) -> None:
            nonlocal count, batch_count
            bare_name = name[1:] if name.startswith("^") else name
            gname = f"^{bare_name}"
            self._known_globals.add(bare_name)
            IRISGlobalStorage._all_known_globals.add(bare_name)
            # Canonicalize subscripts before storing — the high-level
            # self.set() does this, but this fast-path bypasses it.
            canon_subs = [self._canonicalize_subscript(s) for s in subs]
            if canon_subs:
                iris_obj.set(value, gname, *canon_subs)
            else:
                iris_obj.set(value, gname)
            count += 1
            batch_count += 1

        def _process_stream(stream) -> None:
            nonlocal batch_count
            iris_obj.tStart()
            try:
                for name, subs, value in parse_zwr_stream(stream):
                    _do_set(name, subs, value)
                    if batch_count >= batch_size:
                        iris_obj.tCommit()
                        batch_count = 0
                        iris_obj.tStart()
                # Commit any remaining operations (or balance an empty tStart)
                iris_obj.tCommit()
                batch_count = 0
            except Exception:
                try:
                    iris_obj.tRollback()
                except Exception:
                    pass
                raise

        if isinstance(source, Path):
            with open(source, errors="replace") as f:
                _process_stream(f)
        else:
            _process_stream(source)

        return count

    # =========================================================================
    # Connection Management
    # =========================================================================

    def close(self) -> None:
        """Release all locks and close the IRIS connection."""
        IRISGlobalStorage._all_instances.discard(self)
        if self._conn is not None:
            try:
                self._iris.releaseAllLocks()
            except Exception:
                pass
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
            self._iris = None
            self._lock_table.clear()

    def __del__(self) -> None:
        """Close connection on garbage collection."""
        self.close()
