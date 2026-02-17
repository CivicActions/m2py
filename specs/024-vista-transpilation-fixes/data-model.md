# Data Model: VistA-VEHU-M Transpilation Fixes

**Feature**: 024-vista-transpilation-fixes | **Date**: 2026-02-17

This feature primarily extends existing entities rather than creating new ones. The "data model" here catalogs the new runtime functions, special variables, and codegen dispatch entries.

---

## New Runtime Functions

### m_replace(string, search, replace, start=1, count=-1, case=0) → str

IRIS `$REPLACE` implementation. String-for-string replacement.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| string | str | required | Source string |
| search | str | required | Substring to find (empty → return string unchanged) |
| replace | str | required | Replacement string |
| start | int | 1 | Start position (1-based). Returns only from this position onward. |
| count | int | -1 | Max replacements (-1 = replace all) |
| case | int | 0 | 0 = case-sensitive, 1 = case-insensitive |

**Returns**: Modified string (from `start` position onward if start > 1)

---

### m_zboolean(arg1, arg2, op) → int | str

IRIS `$ZBOOLEAN` implementation. 16 bitwise Boolean operations.

| Parameter | Type | Description |
|-----------|------|-------------|
| arg1 | int or str | First operand |
| arg2 | int or str | Second operand |
| op | int | Operation code 0–15 |

**Operation Table** (integer mode):

| op | Name | Formula |
|----|------|---------|
| 0 | FALSE | 0 |
| 1 | AND | arg1 & arg2 |
| 2 | arg1 AND NOT arg2 | arg1 & ~arg2 |
| 3 | arg1 | arg1 |
| 4 | NOT arg1 AND arg2 | ~arg1 & arg2 |
| 5 | arg2 | arg2 |
| 6 | XOR | arg1 ^ arg2 |
| 7 | OR | arg1 \| arg2 |
| 8 | NOR | ~(arg1 \| arg2) |
| 9 | XNOR | ~(arg1 ^ arg2) |
| 10 | NOT arg2 | ~arg2 |
| 11 | arg1 OR NOT arg2 | arg1 \| ~arg2 |
| 12 | NOT arg1 | ~arg1 |
| 13 | NOT arg1 OR arg2 | ~arg1 \| arg2 |
| 14 | NAND | ~(arg1 & arg2) |
| 15 | TRUE | -1 (all bits set) |

**String mode**: When either argument is a non-numeric string, apply per-character bitwise ops on ASCII/byte values. Shorter string is right-padded with NUL bytes.

**Returns**: Integer result (for numeric args) or string result (for string args)

---

### m_zu(code, *args) → str | int

IRIS `$ZU` utility function dispatcher.

| Code | Args | Returns | Maps To |
|------|------|---------|---------|
| 0 | none | str | `$NAMESPACE` value |
| 5 | none | str | `$NAMESPACE` value |
| 5 | ns:str | str | SET `$NAMESPACE`, returns previous |
| 12 | none | str | Config directory path / `os.getcwd()` |
| 53 | none | str | `$IO` value |
| 56 | 2 | int | 0 (collation info) |
| 68 | 15,1 | int | 0 (no-op) |
| 68 | 28,0/1 | int | 0 (no-op) |
| 68 | 40,1 | int | 0 (no-op) |
| 140 | 4,file | int | 1 if file exists, 0 otherwise |
| 168 | none | str | `os.getcwd()` |
| 190 | 17 | int | 0 (block collision stub) |

**Error**: Unrecognized codes raise `NotImplementedError(f"$ZU({code}) not implemented")`

---

### m_zf(code, *args) → int | str

IRIS `$ZF` external function family.

| Variant | Behavior | Returns |
|---------|----------|---------|
| `$ZF(-1, cmd)` | `subprocess.run(cmd, shell=True)` | Exit code (int) |
| `$ZF(-2, cmd)` | `subprocess.Popen(cmd, shell=True)` | 0 (launched) |
| `$ZF(-100, flags, cmd, *args)` | `subprocess.run([cmd] + args)` with flag parsing | Exit code |
| `$ZF("GETSYM", ...)` | VMS stub | "" |
| `$ZF("GETJPI", ...)` | VMS stub | "" |
| `$ZF("TRNLNM", ...)` | VMS stub | "" |

---

## New Special Variables

| Variable | Read | SET | NEW | Default | Backing |
|----------|------|-----|-----|---------|---------|
| `$X` | ✅ (exists) | ✅ (new) | ❌ | 0 | `_current_device.x_pos` |
| `$Y` | ✅ (exists) | ✅ (new) | ❌ | 0 | `_current_device.y_pos` |
| `$ZA` | ✅ (new) | ❌ | ❌ | 0 | `self._za` |
| `$ZR`/`$ZREFERENCE` | ✅ (new) | ✅ (new) | ❌ | "" | `self._zreference` |
| `$ZV`/`$ZVERSION` | ✅ (new) | ❌ | ❌ | "M2PY for Python 1.0..." | computed |
| `$NAMESPACE` | ✅ (new) | ✅ (new) | ✅ (new) | "VISTA" | `self._namespace` |
| `$DEVICE` | ✅ (new) | ❌ | ❌ | "" | `self._device_status` |
| `$REFERENCE` | ✅ (new) | ❌ | ❌ | "" | alias for `$ZR` |
| `$ZGBLDIR` | ✅ (new) | ❌ | ❌ | "" | config string |
| `$ZINTERRUPT` | ❌ | ✅ (new) | ❌ | "" | `self._zinterrupt` |
| `$ZERR` | ❌ | ✅ (new) | ❌ | "" | alias for `$ZERROR` |
| `$ZSOURCE` | ❌ | ✅ (new) | ❌ | "" | `self._zsource` |

---

## New Codegen Dispatch Entries

### Expression Dispatcher (`generate_expr`)

| ASG Type | Handler | Notes |
|----------|---------|-------|
| `ParenExpr` (textX) | Recurse into `.expr` | Defensive fallback |
| `UnaryPrefixedExpr` (textX) | Recurse into operand | Defensive fallback |

### Binary Operator Dispatcher (`_generate_binary_op`)

| Operator | Generated Code | Equivalent |
|----------|---------------|------------|
| `>=` | `int(not m_compare(left, "<", right))` | Same as `'<` |
| `<=` | `int(not m_compare(left, ">", right))` | Same as `'>` |

### SET Special Variable Dispatcher

| Variable | Generated Code |
|----------|---------------|
| `$X` | `_rt.set_x(value)` |
| `$Y` | `_rt.set_y(value)` |
| `$NAMESPACE` | `_rt.set_namespace(value)` |
| `$ZINTERRUPT` | `_rt.set_zinterrupt(value)` |
| `$ZERR` | `_rt.set_zerror(value)` |
| `$ZSOURCE` | `_rt.set_zsource(value)` |

### Intrinsic Function Dispatcher

| Function | Runtime Call |
|----------|-------------|
| `$REPLACE` | `m_replace(string, search, replace, ...)` |
| `$ZBOOLEAN`/`$ZB` | `m_zboolean(arg1, arg2, op)` |
| `$ZU` | `m_zu(code, *args)` |
| `$ZF` | `m_zf(code, *args)` |
| `$ZC`/`$ZCALL` | `m_zcall_stub(*args)` → "" + warning |
| `$VIEW`/`$V` (function) | `m_view_func_stub(*args)` → "" + warning |

### Statement Dispatcher

| Statement Type | Handler |
|----------------|---------|
| `MZLoadStatement` | `_generate_zlink()` (reuse existing) |

---

## Limitations Model Update

### New Entry: LIM-017 — Partial IRIS/Caché Support

**Type**: Parses OK

M2PY implements partial support for InterSystems Caché/IRIS vendor-specific functions
as used by VA VistA. This covers the subset of IRIS features actually used in VistA-VEHU-M
routines.

| Category | Functions | Status |
|----------|-----------|--------|
| Fully Implemented | `$REPLACE`, `$ZBOOLEAN`, `$ZF(-1/-2/-100)` | Full IRIS-compatible semantics |
| Read-only SVN | `$ZV`/`$ZVERSION`, `$ZA`, `$ZR`/`$ZREFERENCE`, `$NAMESPACE` | Returns appropriate values |
| Settable SVN | `$NAMESPACE`, `$ZR` | SET and NEW supported |
| Dispatch Table | `$ZU(0,5,12,53,56,68,140,168,190)` | VistA-used codes only |
| Stubs (warning) | `$ZC`/`$ZCALL`, `$VIEW`/`$V` (function form) | Returns "" + log warning |
| Not Implemented | Other `$ZU` codes, `$ZF("GETSYM"/etc.)` VMS | Error on unrecognized |
