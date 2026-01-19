# Intrinsic Functions Contract

**Spec**: 013-test-consolidation  
**Scope**: String and numeric intrinsic functions (FR-013, FR-014, FR-017, FR-020-021, FR-025, FR-027, FR-031)

## $ASCII Function (FR-013)

**MUMPS**: `$ASCII(string, position?)`

**Behavior**:
- Returns ASCII code of character at position (1-indexed, default 1)
- Returns -1 if string is empty or position out of bounds
- Position defaults to 1

**Examples**:
```mumps
W $A("ABC")      ; 65 (A)
W $A("ABC",2)    ; 66 (B)
W $A("")         ; -1
W $A("A",5)      ; -1
```

**Python Implementation**:
```python
def _ascii(s: str, pos: int = 1) -> int:
    if not s or pos < 1 or pos > len(s):
        return -1
    return ord(s[pos - 1])
```

---

## $CHAR Function (FR-014)

**MUMPS**: `$CHAR(code, ...)`

**Behavior**:
- Returns string of characters for given ASCII codes
- Multiple arguments concatenate results
- Invalid codes (< 0 or > 255) produce empty string for that position

**Examples**:
```mumps
W $C(65)         ; "A"
W $C(65,66,67)   ; "ABC"
W $C(72,73)      ; "HI"
```

**Python Implementation**:
```python
def _char(*codes: int) -> str:
    result = []
    for code in codes:
        if 0 <= code <= 255:
            result.append(chr(code))
    return "".join(result)
```

---

## $JUSTIFY Function (FR-017)

**MUMPS**: `$JUSTIFY(string, width, decimals?)`

**Behavior**:
- Right-justifies string/number in field of given width
- With decimals, formats as fixed-point number
- Pads with spaces on left if needed

**Examples**:
```mumps
W $J("A",5)      ; "    A"
W $J(3.14159,8,2); "    3.14"
W $J(123,3)      ; "123"
```

**Python Implementation**:
```python
def _justify(value: str, width: int, decimals: int | None = None) -> str:
    if decimals is not None:
        num = m_num(value)
        formatted = f"{num:.{decimals}f}"
        return formatted.rjust(width)
    return str(value).rjust(width)
```

---

## $TRANSLATE Function (FR-020)

**MUMPS**: `$TRANSLATE(string, from, to?)`

**Behavior**:
- Replaces characters in `from` with corresponding characters in `to`
- Characters in `from` without `to` counterpart are deleted
- Two-argument form deletes all `from` characters

**Examples**:
```mumps
W $TR("MUMPS","MP","mp")  ; "MuMpS" → wait, case-sensitive
W $TR("HELLO","LO","lo")  ; "HEllo"
W $TR("A1B2C3","123")     ; "ABC" (deletes 1,2,3)
```

**Python Implementation**:
```python
def _translate(s: str, from_chars: str, to_chars: str = "") -> str:
    result = []
    for c in s:
        idx = from_chars.find(c)
        if idx == -1:
            result.append(c)  # Not in from_chars, keep
        elif idx < len(to_chars):
            result.append(to_chars[idx])  # Replace
        # else: delete (no counterpart in to_chars)
    return "".join(result)
```

---

## $TEXT Function (FR-021)

**MUMPS**: `$TEXT(label+offset)`

**Behavior**:
- Returns source line text for label
- Offset adds to label's line number
- Returns empty string if line doesn't exist

**Examples**:
```mumps
; Given:
; HELLO
;  W "Hello"
;  Q

W $T(HELLO)      ; "HELLO"
W $T(HELLO+1)    ; " W ""Hello"""
W $T(HELLO+99)   ; ""
```

**Python Implementation**:
```python
def _text(label: str, offset: int = 0) -> str:
    line_num = _label_lines.get(label, -1)
    if line_num < 0:
        return ""
    target = line_num + offset
    if 0 <= target < len(_source_lines):
        return _source_lines[target]
    return ""
```

**Dependencies**: Requires `_source_lines` and `_label_lines` from Spec 007.

---

## $FNUMBER Function (FR-025)

**MUMPS**: `$FNUMBER(number, format, decimals?)`

**Behavior**:
- Formats number according to format codes
- Format codes: "+" (plus sign), "-" (no sign), "," (comma separators), "T"/"P" (trailing/paren negative)

**Examples**:
```mumps
W $FN(1234.5,"",2)      ; "1234.50"
W $FN(-1234.5,"P",2)    ; "(1234.50)"
W $FN(1234567,",")      ; "1,234,567"
W $FN(123.456,"+",2)    ; "+123.46"
```

**Python Implementation**:
```python
def _fnumber(num: str, format_code: str = "", decimals: int | None = None) -> str:
    n = m_num(num)
    # Implementation details depend on format codes
    # "," = add thousands separators
    # "+" = always show sign
    # "-" = never show minus sign
    # "P" = parentheses for negative
    # "T" = trailing sign
    ...
```

---

## $REVERSE Function (FR-027)

**MUMPS**: `$REVERSE(string)`

**Behavior**:
- Returns string with characters in reverse order

**Examples**:
```mumps
W $RE("HELLO")   ; "OLLEH"
W $RE("")        ; ""
W $RE("A")       ; "A"
```

**Python Implementation**:
```python
def _reverse(s: str) -> str:
    return s[::-1]
```

---

## $NEXT Function (FR-031) - Deprecated

**MUMPS**: `$NEXT(subscript)`

**Behavior**:
- Returns next subscript at same level
- Deprecated in favor of $ORDER
- Returns -1 when no more subscripts (unlike $ORDER which returns "")

**Examples**:
```mumps
S ^A(1)=1,^A(3)=3,^A(5)=5
W $N(^A(""))     ; "1"
W $N(^A(1))      ; "3"
W $N(^A(5))      ; -1
```

**Python Implementation**:
```python
def _next(subscript_ref) -> str:
    # Similar to $ORDER but returns "-1" instead of ""
    result = _order(subscript_ref)
    return "-1" if result == "" else result
```

**Note**: May emit deprecation warning per spec.
