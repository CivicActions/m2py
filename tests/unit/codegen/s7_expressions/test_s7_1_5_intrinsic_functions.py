"""Tests for Intrinsic Functions code generation (§7.1.5).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.5
"""

import pytest


@pytest.mark.codegen
class TestIntrinsicFunctionsCodegen:
    """Codegen-level tests for intrinsic functions code generation (§7.1.5)."""

    def test_function_ascii(self, execute_mumps):
        """$ASCII generates ord() equivalent (§7.1.5).

        Spec 010 Phase 7 (T053): $ASCII returns ASCII code of character at position.
        Returns -1 for out of range or empty string.
        """
        # Test 1: First character (default position)
        result = execute_mumps('TEST W $A("ABC") Q')
        assert result.output == "65"

        # Test 2: Character at position 2
        result = execute_mumps('TEST W $A("ABC",2) Q')
        assert result.output == "66"

        # Test 3: Character at position 3
        result = execute_mumps('TEST W $A("ABC",3) Q')
        assert result.output == "67"

        # Test 4: Out of range position returns -1
        result = execute_mumps('TEST W $A("ABC",4) Q')
        assert result.output == "-1"

        # Test 5: Position 0 returns -1
        result = execute_mumps('TEST W $A("ABC",0) Q')
        assert result.output == "-1"

        # Test 6: Empty string returns -1
        result = execute_mumps('TEST W $A("") Q')
        assert result.output == "-1"

        # Test 7: Full form abbreviation
        result = execute_mumps('TEST W $ASCII("XYZ") Q')
        assert result.output == "88"

    def test_function_char(self, execute_mumps):
        """$CHAR generates chr() equivalent (§7.1.5).

        Spec 010 Phase 7 (T054): $CHAR converts ASCII codes to characters.
        Multiple arguments produce concatenated result. Negative codes produce empty.
        """
        # Test 1: Single character
        result = execute_mumps("TEST W $C(65) Q")
        assert result.output == "A"

        # Test 2: Multiple characters
        result = execute_mumps("TEST W $C(65,66,67) Q")
        assert result.output == "ABC"

        # Test 3: Negative code produces empty
        result = execute_mumps('TEST W "[" W $C(-1) W "]" Q')
        assert result.output == "[]"

        # Test 4: Unicode support (code > 127)
        result = execute_mumps("TEST W $C(256) Q")
        assert result.output == "Ā"

        # Test 5: Full form abbreviation
        result = execute_mumps("TEST W $CHAR(90) Q")
        assert result.output == "Z"

    def test_function_data(self, execute_mumps):
        """$DATA generates data check (§7.1.5).

        Spec 010 Phase 6 (T035-T037): $DATA returns variable existence status.
        - 0: Undefined, no descendants
        - 1: Has value only
        - 10: Has descendants only
        - 11: Has both value and descendants
        """
        # Test 1: Undefined variable
        result = execute_mumps("TEST K Y W $D(Y) Q")
        assert result.output == "0"

        # Test 2: Defined simple variable
        result = execute_mumps("TEST S X=1 W $D(X) Q")
        assert result.output == "1"

        # Test 3: Array with children only
        result = execute_mumps("TEST S A(1)=1,A(2)=2 W $D(A) Q")
        assert result.output == "10"

        # Test 4: Variable with both value and children
        result = execute_mumps("TEST S A=1,A(1)=2 W $D(A) Q")
        assert result.output == "11"

        # Test 5: Subscripted variable that exists
        result = execute_mumps("TEST S A(1)=1 W $D(A(1)) Q")
        assert result.output == "1"

        # Test 6: Subscripted variable that doesn't exist
        result = execute_mumps("TEST S A(1)=1 W $D(A(2)) Q")
        assert result.output == "0"

        # Test 7: Full form abbreviation
        result = execute_mumps("TEST S X=1 W $DATA(X) Q")
        assert result.output == "1"

    def test_function_extract(self, execute_mumps):
        """$EXTRACT generates string slice (§7.1.5).

        Spec 010 Phase 5 (T031-T034): $EXTRACT extracts substrings by position.
        Uses 1-based indexing with inclusive range.
        """
        # Test 1: Default - first character
        result = execute_mumps('TEST W $E("HELLO") Q')
        assert result.output == "H"

        # Test 2: Single position
        result = execute_mumps('TEST W $E("HELLO",2) Q')
        assert result.output == "E"

        # Test 3: Range extraction
        result = execute_mumps('TEST W $E("HELLO",2,4) Q')
        assert result.output == "ELL"

        # Test 4: Out of range returns empty
        result = execute_mumps('TEST W $E("HELLO",6) Q')
        assert result.output == ""

        # Test 5: Position 0 returns empty
        result = execute_mumps('TEST W $E("HELLO",0) Q')
        assert result.output == ""

        # Test 6: Reverse range (start > end) returns empty
        result = execute_mumps('TEST W $E("HELLO",4,2) Q')
        assert result.output == ""

        # Test 7: Full form abbreviation
        result = execute_mumps('TEST W $EXTRACT("ABC",1,2) Q')
        assert result.output == "AB"

    def test_function_find(self, execute_mumps):
        """$FIND generates string find (§7.1.5).

        Spec 010 Phase 7 (T046): $FIND locates substring and returns position
        AFTER the match. Returns 0 if not found.
        """
        # Test 1: Find substring - returns position after match
        result = execute_mumps('TEST W $F("HELLO","LL") Q')
        assert result.output == "5"

        # Test 2: Find first occurrence of character
        result = execute_mumps('TEST W $F("HELLO","L") Q')
        assert result.output == "4"

        # Test 3: Not found returns 0
        result = execute_mumps('TEST W $F("HELLO","X") Q')
        assert result.output == "0"

        # Test 4: Search with starting position
        result = execute_mumps('TEST W $F("HELLO","L",4) Q')
        assert result.output == "5"

        # Test 5: Empty target returns start position
        result = execute_mumps('TEST W $F("ABC","") Q')
        assert result.output == "1"

        # Test 6: Full form abbreviation
        result = execute_mumps('TEST W $FIND("HELLO","LL") Q')
        assert result.output == "5"

    def test_function_get(self, execute_mumps):
        """$GET generates safe variable retrieval (§7.1.5).

        Spec 010 Phase 6 (T038-T042): $GET returns value if defined, else default.
        Distinguished undefined from defined-as-empty-string.
        """
        # Test 1: Undefined variable with default
        result = execute_mumps('TEST K X W $G(X,"DEFAULT") Q')
        assert result.output == "DEFAULT"

        # Test 2: Undefined variable without default (returns empty)
        result = execute_mumps('TEST K X W "[" W $G(X) W "]" Q')
        assert result.output == "[]"

        # Test 3: Defined variable (returns value, not default)
        result = execute_mumps('TEST S X="VALUE" W $G(X,"DEFAULT") Q')
        assert result.output == "VALUE"

        # Test 4: Defined as empty string (returns empty, not default)
        result = execute_mumps('TEST S X="" W "[" W $G(X,"DEFAULT") W "]" Q')
        assert result.output == "[]"

        # Test 5: Subscripted variable - defined
        result = execute_mumps('TEST S X(1)="A" W $G(X(1),"DEF") Q')
        assert result.output == "A"

        # Test 6: Subscripted variable - undefined
        result = execute_mumps('TEST S X(1)="A" W $G(X(2),"DEF") Q')
        assert result.output == "DEF"

        # Test 7: Full form abbreviation
        result = execute_mumps('TEST K Y W $GET(Y,"FULL") Q')
        assert result.output == "FULL"

    def test_function_length(self, execute_mumps):
        """$LENGTH generates len() equivalent (§7.1.5).

        Spec 010 Phase 5 (T024-T026): $LENGTH has two forms:
        1. $L(string) - character count
        2. $L(string, delimiter) - piece count
        """
        # Test 1: Character count
        result = execute_mumps('TEST W $L("HELLO") Q')
        assert result.output == "5"

        # Test 2: Empty string length
        result = execute_mumps('TEST W $L("") Q')
        assert result.output == "0"

        # Test 3: Piece count
        result = execute_mumps('TEST W $L("A^B^C","^") Q')
        assert result.output == "3"

        # Test 4: Empty string has 1 piece
        result = execute_mumps('TEST W $L("","^") Q')
        assert result.output == "1"

        # Test 5: Leading/trailing delimiters count as pieces
        result = execute_mumps('TEST W $L("^A^B^","^") Q')
        assert result.output == "4"

        # Test 6: Full form abbreviation
        result = execute_mumps('TEST W $LENGTH("ABC") Q')
        assert result.output == "3"

    def test_function_order(self, execute_mumps):
        """$ORDER generates next key retrieval (§7.1.5).

        Tests:
        - Forward iteration from empty string
        - Forward iteration from existing key
        - Reverse iteration
        - Global variable support
        - MUMPS collation order (negatives < 0 < positives < strings)
        """
        # Test 1: Forward iteration from empty string - gets first key
        result = execute_mumps(
            'TEST\n S A(1)=1,A(2)=2,A(3)=3\n S X=$O(A(""))\n W X\n Q'
        )
        assert result.output == "1"

        # Test 2: Forward iteration from existing key
        result = execute_mumps("TEST\n S A(1)=1,A(2)=2,A(3)=3\n S X=$O(A(1))\n W X\n Q")
        assert result.output == "2"

        # Test 3: Reverse iteration - gets last key
        result = execute_mumps(
            'TEST\n S A(1)=1,A(2)=2,A(3)=3\n S X=$O(A(""),-1)\n W X\n Q'
        )
        assert result.output == "3"

        # Test 4: Collation order - negatives before positives
        result = execute_mumps(
            'TEST\n S A(-1)=1,A(0)=2,A(1)=3\n S X=$O(A(""))\n W X\n Q'
        )
        assert result.output == "-1"

        # Test 5: Collation order - strings after numbers
        result = execute_mumps('TEST\n S A(1)=1,A("Z")=2\n S X=$O(A(1))\n W X\n Q')
        assert result.output == "Z"

    def test_function_piece(self, execute_mumps):
        """$PIECE generates string split (§7.1.5).

        Spec 010 Phase 5 (T027-T030): $PIECE extracts delimited pieces.
        Uses 1-based indexing.
        """
        # Test 1: Single piece extraction
        result = execute_mumps('TEST W $P("A^B^C","^",2) Q')
        assert result.output == "B"

        # Test 2: Range extraction
        result = execute_mumps('TEST W $P("A^B^C","^",2,3) Q')
        assert result.output == "B^C"

        # Test 3: Out of range returns empty
        result = execute_mumps('TEST W $P("A^B^C","^",4) Q')
        assert result.output == ""

        # Test 4: First piece
        result = execute_mumps('TEST W $P("A^B^C","^",1) Q')
        assert result.output == "A"

        # Test 5: Multi-character delimiter
        result = execute_mumps('TEST W $P("A::B::C","::",2) Q')
        assert result.output == "B"

        # Test 6: Full form abbreviation
        result = execute_mumps('TEST W $PIECE("X-Y-Z","-",2) Q')
        assert result.output == "Y"

    def test_function_query(self, execute_mumps):
        """$QUERY generates tree traversal (§7.1.5).

        Tests:
        - Start from empty string to get first valued node
        - Continue traversal to next valued node
        - Multi-level subscript traversal (depth-first order)
        - End of traversal returns empty string
        """
        # Test 1: Start traversal - gets first valued node
        result = execute_mumps(
            'TEST\n S A(1,1)=1,A(1,2)=2,A(2,1)=3\n S X=$Q(A(""))\n W X\n Q'
        )
        assert result.output == "A(1,1)"

        # Test 2: Continue traversal to sibling
        result = execute_mumps(
            "TEST\n S A(1,1)=1,A(1,2)=2,A(2,1)=3\n S X=$Q(A(1,1))\n W X\n Q"
        )
        assert result.output == "A(1,2)"

        # Test 3: Cross branch boundary
        result = execute_mumps(
            "TEST\n S A(1,1)=1,A(1,2)=2,A(2,1)=3\n S X=$Q(A(1,2))\n W X\n Q"
        )
        assert result.output == "A(2,1)"

        # Test 4: End of traversal returns empty string
        result = execute_mumps("TEST\n S A(1)=1,A(2)=2\n S X=$Q(A(2))\n W X\n Q")
        assert result.output == ""

    def test_function_random(self, execute_mumps):
        """$RANDOM generates random.randint (§7.1.5).

        Spec 010 Phase 8 (T057): $RANDOM generates random integers.
        $R(limit) returns integer from 0 to limit-1.
        $R(1) always returns 0.
        """
        # Test 1: $R(1) always returns 0
        result = execute_mumps("TEST W $R(1) Q")
        assert result.output == "0"

        # Test 2: $R(10) returns something (we just verify it runs)
        result = execute_mumps("TEST W $R(10) Q")
        assert result.output.isdigit()
        assert 0 <= int(result.output) <= 9

        # Test 3: $R(100) returns 0-99
        result = execute_mumps("TEST W $R(100) Q")
        assert result.output.isdigit()
        assert 0 <= int(result.output) <= 99

        # Test 4: Full form abbreviation
        result = execute_mumps("TEST W $RANDOM(1) Q")
        assert result.output == "0"

    def test_function_random_randargneg_error(self, generate_python):
        """$RANDOM raises RANDARGNEG for limit <= 0 (§7.1.5).

        Spec 010 Phase 8 (T058): $RANDOM with 0 or negative argument
        must raise MRuntimeError with RANDARGNEG code.
        """
        from m2py.runtime import MUMPSRuntime

        # Test 1: $R(0) raises RANDARGNEG
        code = generate_python("TEST W $R(0) Q")
        runtime = MUMPSRuntime()
        result = runtime.execute(code)
        assert result.success is False
        assert "RANDARGNEG" in result.error

        # Test 2: $R(-1) raises RANDARGNEG
        code = generate_python("TEST W $R(-1) Q")
        runtime = MUMPSRuntime()
        result = runtime.execute(code)
        assert result.success is False
        assert "RANDARGNEG" in result.error

    def test_function_select(self, execute_mumps):
        """$SELECT generates conditional expression (§7.1.5).

        Spec 010 Phase 3: $SELECT evaluates conditions left-to-right
        and returns the value for the first true condition.
        """
        # Test 1: Basic $SELECT with first condition true
        result = execute_mumps('TEST S X=$S(1=1:"YES",1:"NO") W X Q')
        assert result.output == "YES"

        # Test 2: $SELECT with multiple conditions - second matches
        result = execute_mumps('TEST S X=2 S Y=$S(X=1:"ONE",X=2:"TWO",1:"OTHER") W Y Q')
        assert result.output == "TWO"

        # Test 3: $SELECT with all false except final catch-all
        result = execute_mumps('TEST S Y=$S(0:"A",0:"B",1:"C") W Y Q')
        assert result.output == "C"

        # Test 4: $SELECT with comparison operators
        result = execute_mumps('TEST S A=5,B=3 S Y=$S(A>B:"FIRST",B>A:"SECOND") W Y Q')
        assert result.output == "FIRST"

        # Test 5: $SELECT using abbreviation $S
        result = execute_mumps('TEST S Y=$S(1:"ONLY") W Y Q')
        assert result.output == "ONLY"

    def test_function_select_abbreviation(self, generate_python):
        """$SELECT abbreviation $S generates same code (§7.1.5)."""
        # Both $SELECT and $S should generate the same pattern
        code_full = generate_python('TEST S X=$SELECT(1:"YES") Q')
        code_abbrev = generate_python('TEST S X=$S(1:"YES") Q')

        # Both should contain m_truth for condition check
        assert "m_truth" in code_full
        assert "m_truth" in code_abbrev

    def test_function_select_selectfalse_error(self, generate_python):
        """$SELECT raises SELECTFALSE when no condition is true (§7.1.5).

        Spec 010 Phase 3 T019: $SELECT with no true conditions must raise
        MRuntimeError with SELECTFALSE code.
        """
        from m2py.runtime import MUMPSRuntime

        # Generate code for $SELECT with all false conditions
        code = generate_python('TEST S X=$S(0:"A",0:"B") W X Q')

        # Execute - runtime captures exception as result error
        runtime = MUMPSRuntime()
        result = runtime.execute(code)

        # Check execution failed with SELECTFALSE error
        assert result.success is False
        assert "SELECTFALSE" in result.error

    def test_function_text(self, generate_python):
        """$TEXT generates source retrieval (§7.1.5).

        $TEXT returns source code lines from the routine.
        Implemented in Spec 008 with _rt.get_text() runtime method.
        """
        # Test $T(+N) generates get_text() with offset
        code = generate_python("TEST W $T(+1) Q")
        assert "_rt.get_text(offset=1)" in code

        # Test $T(LABEL) generates get_text() with label
        code = generate_python("TEST W $T(END) Q\nEND Q")
        assert "_rt.get_text(" in code and 'label="END"' in code

        # Test $T(+0) returns routine name
        code = generate_python("TEST W $T(+0) Q")
        assert "_rt.get_text(offset=0)" in code

    def test_function_translate(self, execute_mumps):
        """$TRANSLATE generates str.translate (§7.1.5).

        Spec 010 Phase 7 (T049): $TRANSLATE performs character-by-character
        replacement or deletion.
        """
        # Test 1: Delete characters (no 'to' argument)
        result = execute_mumps('TEST W $TR("HELLO","L") Q')
        assert result.output == "HEO"

        # Test 2: Replace characters (same length)
        result = execute_mumps('TEST W $TR("HELLO","LO","XY") Q')
        assert result.output == "HEXXY"

        # Test 3: Replace with different length 'to' (shorter deletes extra)
        result = execute_mumps('TEST W $TR("HELLO","HEL","A") Q')
        assert result.output == "AO"

        # Test 4: Replace all occurrences
        result = execute_mumps('TEST W $TR("HELLO","HEL","ABC") Q')
        assert result.output == "ABCCO"

        # Test 5: Empty string input
        result = execute_mumps('TEST W "[" W $TR("","A","B") W "]" Q')
        assert result.output == "[]"

        # Test 6: Full form abbreviation
        result = execute_mumps('TEST W $TRANSLATE("ABC","A","X") Q')
        assert result.output == "XBC"

    def test_function_name(self, execute_mumps):
        """$NAME/$NA function generates canonical name strings (§7.1.5).

        Spec 010 Phase 9: $NAME converts variable references to name strings.
        """
        # Test 1: Basic array reference
        result = execute_mumps("TEST S A(1,2,3)=1 W $NA(A(1,2,3)) Q")
        assert result.output == "A(1,2,3)"

        # Test 2: With depth parameter
        result = execute_mumps("TEST S A(1,2,3)=1 W $NA(A(1,2,3),2) Q")
        assert result.output == "A(1,2)"

        # Test 3: Depth 0 returns name only
        result = execute_mumps("TEST S A(1,2,3)=1 W $NA(A(1,2,3),0) Q")
        assert result.output == "A"

        # Test 4: String subscripts are quoted
        result = execute_mumps('TEST S A("foo","bar")=1 W $NA(A("foo","bar")) Q')
        assert result.output == 'A("foo","bar")'

        # Test 5: Variable with no subscripts
        result = execute_mumps("TEST S A=1 W $NA(A) Q")
        assert result.output == "A"

        # Test 6: Full form
        result = execute_mumps("TEST S A(1,2)=1 W $NAME(A(1,2)) Q")
        assert result.output == "A(1,2)"

    def test_function_qlength(self, execute_mumps):
        """$QLENGTH/$QL function counts subscripts in name string (§7.1.5).

        Spec 010 Phase 9: $QLENGTH returns the number of subscripts.
        """
        # Test 1: Basic count
        result = execute_mumps('TEST W $QL("A(1,2,3)") Q')
        assert result.output == "3"

        # Test 2: No subscripts
        result = execute_mumps('TEST W $QL("A") Q')
        assert result.output == "0"

        # Test 3: Global with subscripts
        result = execute_mumps('TEST W $QL("^GLO(1,2)") Q')
        assert result.output == "2"

        # Test 4: String subscripts
        result = execute_mumps('TEST W $QL("A(""hello"",""world"")") Q')
        assert result.output == "2"

        # Test 5: Full form
        result = execute_mumps('TEST W $QLENGTH("A(1,2,3,4,5)") Q')
        assert result.output == "5"

    def test_function_qsubscript(self, execute_mumps):
        """$QSUBSCRIPT/$QS function extracts subscripts from name string (§7.1.5).

        Spec 010 Phase 9: $QSUBSCRIPT extracts subscript at position from name.
        """
        # Test 1: Position 0 returns name
        result = execute_mumps('TEST W $QS("A(1,2,3)",0) Q')
        assert result.output == "A"

        # Test 2: Position 1 returns first subscript
        result = execute_mumps('TEST W $QS("A(1,2,3)",1) Q')
        assert result.output == "1"

        # Test 3: Position 2 returns second subscript
        result = execute_mumps('TEST W $QS("A(1,2,3)",2) Q')
        assert result.output == "2"

        # Test 4: Position 3 returns third subscript
        result = execute_mumps('TEST W $QS("A(1,2,3)",3) Q')
        assert result.output == "3"

        # Test 5: Out of range returns empty
        result = execute_mumps('TEST W "[" W $QS("A(1,2,3)",5) W "]" Q')
        assert result.output == "[]"

        # Test 6: Global name at position 0
        result = execute_mumps('TEST W $QS("^GLO(1,2)",0) Q')
        assert result.output == "^GLO"

        # Test 7: Negative position returns empty
        result = execute_mumps('TEST W "[" W $QS("A(1,2,3)",-1) W "]" Q')
        assert result.output == "[]"

        # Test 8: String subscript extraction (unquoted)
        result = execute_mumps('TEST W $QS("A(""hello"",2)",1) Q')
        assert result.output == "hello"

        # Test 9: Full form
        result = execute_mumps('TEST W $QSUBSCRIPT("A(1,2)",1) Q')
        assert result.output == "1"

    def test_function_justify(self, execute_mumps):
        """$JUSTIFY/$J right-justifies values in field width (§7.1.5).

        Spec 010 Phase 10 (T067): $JUSTIFY right-justifies strings or numbers.
        Two-argument form: simple right-justify.
        Three-argument form: numeric formatting with decimal places.
        """
        # Test 1: Simple right-justify string
        result = execute_mumps('TEST W $J("ABC",6) Q')
        assert result.output == "   ABC"

        # Test 2: Simple right-justify number
        result = execute_mumps("TEST W $J(12,5) Q")
        assert result.output == "   12"

        # Test 3: Number with decimal places
        result = execute_mumps("TEST W $J(3.14159,10,2) Q")
        assert result.output == "      3.14"

        # Test 4: Width smaller than string (no truncation)
        result = execute_mumps('TEST W $J("HELLO",3) Q')
        assert result.output == "HELLO"

        # Test 5: Full form abbreviation
        result = execute_mumps("TEST W $JUSTIFY(42,6) Q")
        assert result.output == "    42"

    def test_function_reverse(self, execute_mumps):
        """$REVERSE/$RE reverses a string (§7.1.5).

        Spec 010 Phase 10 (T068): $REVERSE returns string with characters in reverse order.
        """
        # Test 1: Simple reverse
        result = execute_mumps('TEST W $RE("HELLO") Q')
        assert result.output == "OLLEH"

        # Test 2: Reverse number (treated as string)
        result = execute_mumps("TEST W $RE(12345) Q")
        assert result.output == "54321"

        # Test 3: Empty string
        result = execute_mumps('TEST W "[" W $RE("") W "]" Q')
        assert result.output == "[]"

        # Test 4: Single character
        result = execute_mumps('TEST W $RE("X") Q')
        assert result.output == "X"

        # Test 5: Full form abbreviation
        result = execute_mumps('TEST W $REVERSE("ABC") Q')
        assert result.output == "CBA"

    def test_function_fnumber(self, execute_mumps):
        """$FNUMBER/$FN formats numbers with specified codes (§7.1.5).

        Spec 010 Phase 10 (T069-T070): $FNUMBER formats numbers with codes:
        - "," = add comma separators
        - "+" = force plus sign for positive
        - "-" = suppress minus sign on negative
        - "P" = parentheses for negative
        - "T" = trailing sign
        """
        # Test 1: Comma separators
        result = execute_mumps('TEST W $FN(12345.67,",") Q')
        assert result.output == "12,345.67"

        # Test 2: Plus sign for positive
        result = execute_mumps('TEST W $FN(42,"+") Q')
        assert result.output == "+42"

        # Test 3: Suppress minus on negative
        result = execute_mumps('TEST W $FN(-42,"-") Q')
        assert result.output == "42"

        # Test 4: Parentheses for negative
        result = execute_mumps('TEST W $FN(-42,"P") Q')
        assert result.output == "(42)"

        # Test 5: Trailing minus for negative
        result = execute_mumps('TEST W $FN(-100,"T") Q')
        assert result.output == "100-"

        # Test 6: Trailing space for positive
        # Note: trailing space may be stripped by test harness
        result = execute_mumps('TEST W "|" W $FN(42,"T") W "|" Q')
        assert result.output == "|42 |"

        # Test 7: Full form abbreviation
        result = execute_mumps('TEST W $FNUMBER(1000,",") Q')
        assert result.output == "1,000"

    @pytest.mark.pre1995
    def test_function_next(self, execute_mumps):
        """$NEXT function generates $ORDER equivalent (§7.1.5, pre-1995).

        Spec 010: $NEXT is deprecated but still supported by YottaDB.
        It maps directly to $ORDER for forward iteration.
        """
        # Test 1: Forward iteration from empty string - gets first key
        result = execute_mumps(
            'TEST\n S A(1)=1,A(2)=2,A(3)=3\n S X=$N(A(""))\n W X\n Q'
        )
        assert result.output == "1"

        # Test 2: Forward iteration from existing key
        result = execute_mumps("TEST\n S A(1)=1,A(2)=2,A(3)=3\n S X=$N(A(1))\n W X\n Q")
        assert result.output == "2"

        # Test 3: Full form
        result = execute_mumps('TEST\n S A(1)=1,A(2)=2\n S X=$NEXT(A(""))\n W X\n Q')
        assert result.output == "1"

    @pytest.mark.pre1995
    def test_function_next_returns_minus_one(self, execute_mumps):
        """$NEXT returns -1 when no next subscript exists (§7.1.5, pre-1995).

        Unlike $ORDER (returns empty string), $NEXT returns -1 when there
        is no next subscript. This is a key difference from $ORDER.
        """
        # Test: $NEXT at end of array returns -1
        result = execute_mumps("TEST\n S A(1)=1,A(3)=3\n W $NEXT(A(3))\n Q")
        assert result.output == "-1"

        # Contrast with $ORDER which returns empty string
        result = execute_mumps("TEST\n S A(1)=1,A(3)=3\n W $ORDER(A(3))\n Q")
        assert result.output == ""

    def test_function_case_insensitivity(self, execute_mumps):
        """Function names are case-insensitive per FR-027 (§7.1.5).

        Spec 010 FR-027: System MUST be case-insensitive for function names.
        $l = $L = $LENGTH, $p = $P = $PIECE, etc.
        """
        # Test lowercase $l
        result = execute_mumps('TEST W $l("HELLO") Q')
        assert result.output == "5"

        # Test lowercase $p
        result = execute_mumps('TEST W $p("A^B^C","^",2) Q')
        assert result.output == "B"

        # Test lowercase $e
        result = execute_mumps('TEST W $e("HELLO",1,3) Q')
        assert result.output == "HEL"

        # Test mixed case $Length
        result = execute_mumps('TEST W $Length("ABC") Q')
        assert result.output == "3"

        # Test mixed case $Piece
        result = execute_mumps('TEST W $Piece("X-Y","-",2) Q')
        assert result.output == "Y"

    def test_function_get_global_undefined(self, execute_mumps):
        """$GET with undefined global returns empty or default (§7.1.5).

        Spec 010 Edge Case: $G(^UNDEFINED) returns empty string.
        """
        # Test 1: Undefined global without default
        result = execute_mumps('TEST W "[" W $G(^UNDEFINED12345) W "]" Q')
        assert result.output == "[]"

        # Test 2: Undefined global with default
        result = execute_mumps('TEST W $G(^UNDEFINED12345,"DEFAULT") Q')
        assert result.output == "DEFAULT"

        # Test 3: Undefined subscripted global
        result = execute_mumps('TEST W $G(^UNDEFINED12345(1,2),"DEF") Q')
        assert result.output == "DEF"


@pytest.mark.codegen
class TestDeprecatedFunctionsCodegen:
    """Codegen tests for deprecated functions (LIM-004).

    $DEXTRACT and $DPIECE were proposed but never standardized. They parse
    as valid intrinsic function syntax but have no defined semantics.
    Codegen should raise NotImplementedError.

    Reference: MUMPS 1995 ANSI Standard, Section 7.1.5
    Limitation: docs/limitations.md - LIM-004: Deprecated Functions
    """

    def test_lim004_dextract_raises_error(self, generate_python):
        """$DEXTRACT should raise NotImplementedError (LIM-004).

        $DEXTRACT was proposed but never standardized. Codegen must fail.
        """
        with pytest.raises(NotImplementedError, match="DEXTRACT"):
            generate_python('TEST S X=$DEXTRACT("abc") Q')

    def test_lim004_dpiece_raises_error(self, generate_python):
        """$DPIECE should raise NotImplementedError (LIM-004).

        $DPIECE was proposed but never standardized. Codegen must fail.
        """
        with pytest.raises(NotImplementedError, match="DPIECE"):
            generate_python('TEST S X=$DPIECE("a:b",":",1) Q')


# =============================================================================
# $DATA Function Tests (consolidated from test_spec_009_data.py)
# =============================================================================


@pytest.mark.codegen
@pytest.mark.spec009
class TestDataLocalVariables:
    """Tests for $DATA with local variables."""

    def test_data_undefined_variable(self, execute_mumps):
        """Scenario 1: $DATA of undefined variable returns 0.

        W $D(UNDEF) → "0"
        """
        result = execute_mumps("TEST W $D(UNDEF) Q")
        assert result.output == "0"

    def test_data_value_only(self, execute_mumps):
        """Scenario 2: $DATA of variable with value only returns 1.

        S X=1 W $D(X) → "1"
        """
        result = execute_mumps("TEST S X=1 W $D(X) Q")
        assert result.output == "1"

    def test_data_children_only(self, execute_mumps):
        """Scenario 3: $DATA of variable with children only returns 10.

        S X(1)=1 W $D(X) → "10"
        X has a child X(1) but no value at X itself.
        """
        result = execute_mumps("TEST S X(1)=1 W $D(X) Q")
        assert result.output == "10"

    def test_data_value_and_children(self, execute_mumps):
        """Scenario 4: $DATA of variable with value AND children returns 11.

        S X=1 S X(1)=2 W $D(X) → "11"
        X has both a value and children.
        """
        result = execute_mumps("TEST S X=1 S X(1)=2 W $D(X) Q")
        assert result.output == "11"


@pytest.mark.codegen
@pytest.mark.spec009
class TestDataGlobalVariables:
    """Tests for $DATA with global variables."""

    def test_data_global_value_and_children(self, execute_mumps):
        """Scenario 5: $DATA works on globals with value AND children.

        S ^G=1 S ^G(1)=2 W $D(^G) → "11"
        """
        result = execute_mumps("TEST S ^G=1 S ^G(1)=2 W $D(^G) Q")
        assert result.output == "11"

    def test_data_global_undefined(self, execute_mumps):
        """$DATA of undefined global returns 0."""
        result = execute_mumps("TEST W $D(^UNDEFINED) Q")
        assert result.output == "0"

    def test_data_global_value_only(self, execute_mumps):
        """$DATA of global with value only returns 1."""
        result = execute_mumps("TEST S ^H=1 W $D(^H) Q")
        assert result.output == "1"

    def test_data_global_children_only(self, execute_mumps):
        """$DATA of global with children only returns 10."""
        result = execute_mumps("TEST S ^I(1)=1 W $D(^I) Q")
        assert result.output == "10"


@pytest.mark.codegen
@pytest.mark.spec009
class TestDataSubscriptedAccess:
    """Tests for $DATA with subscripted variable access."""

    def test_data_subscripted_local(self, execute_mumps):
        """$DATA of subscripted local variable."""
        result = execute_mumps("TEST S X(1)=1 S X(1,2)=2 W $D(X(1)) Q")
        # X(1) has value=1 and child X(1,2), so $D(X(1))=11
        assert result.output == "11"

    def test_data_subscripted_local_value_only(self, execute_mumps):
        """$DATA of leaf subscripted local variable."""
        result = execute_mumps("TEST S X(1,2)=2 W $D(X(1,2)) Q")
        # X(1,2) has value only, no children
        assert result.output == "1"

    def test_data_subscripted_global(self, execute_mumps):
        """$DATA of subscripted global variable."""
        result = execute_mumps("TEST S ^J(1)=1 S ^J(1,2)=2 W $D(^J(1)) Q")
        # ^J(1) has value=1 and child ^J(1,2), so $D(^J(1))=11
        assert result.output == "11"

    def test_data_undefined_subscript(self, execute_mumps):
        """$DATA of undefined subscript returns 0."""
        result = execute_mumps("TEST S X(1)=1 W $D(X(99)) Q")
        assert result.output == "0"
