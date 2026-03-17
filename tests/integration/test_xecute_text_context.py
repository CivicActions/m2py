"""Test that XECUTE preserves the caller's $TEXT context.

When a routine reads its own source via $TEXT and also uses XECUTE in a
loop, the XECUTE'd code temporarily overwrites the runtime's
``_current_source_lines`` and ``_current_label_lines``.  After the
XECUTE returns, the caller's context must be restored so that subsequent
$TEXT reads still work.

This was a bug where the DMUFI data-loader pattern::

    F I=1:2 S X=$T(Q+I) Q:X=""  ... X NO E  S @X=Y

would only process the first iteration because ``X NO`` (XECUTE "I 0")
clobbered the source line context, making ``$T(Q+I)`` return "" on the
next iteration, triggering the ``Q:X=""`` exit.
"""

from __future__ import annotations

from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime


class TestXecutePreservesTextContext:
    """XECUTE must not clobber the caller's $TEXT source lines."""

    ROUTINE = (
        "TEST\n"
        " ; Read $TEXT lines in a loop, XECUTE in between\n"
        ' F I=1:1:3 S X=$T(DATA+I) X "S $EC=""""" S Y(I)=X\n'
        " Q\n"
        "DATA\n"
        " ;;LINE ONE\n"
        " ;;LINE TWO\n"
        " ;;LINE THREE\n"
    )

    def test_text_works_after_xecute(self):
        """$TEXT still works after an XECUTE in the same loop iteration.

        The routine reads DATA+1, DATA+2, DATA+3 via $TEXT, with an
        XECUTE between each read.  All three lines must be captured.
        """
        code = generate_python(self.ROUTINE)

        rt = MUMPSRuntime()
        scope: dict = {}
        namespace: dict = {}
        exec(code, namespace)
        namespace["TEST"](rt, _scope=scope)

        # Y(1), Y(2), Y(3) should contain the ;;-prefixed DATA lines
        y = scope["Y"]
        assert "LINE ONE" in str(y.get("1"))
        assert "LINE TWO" in str(y.get("2"))
        assert "LINE THREE" in str(y.get("3"))

    def test_text_loop_with_xecute_i_zero(self):
        """Reproduce the exact DMUFI pattern: X "I 0" then $TEXT.

        The DMUFI data loaders use ``X NO`` where NO="I 0" (always
        sets $TEST=0) followed by ELSE to unconditionally execute the
        SET @X=Y.  The critical thing is that $TEXT on the next FOR
        iteration still reads the right source line.
        """
        routine = (
            "TEST\n"
            ' S NO="I 0"\n'
            ' F I=1:2 S X=$T(Q+I) Q:X=""  S Y=$E($T(Q+I+1),4,999),X=$E(X,4,999) X NO E  S @X=Y\n'
            " Q\n"
            "Q Q\n"
            ' ;;^TST("A")\n'
            " ;;ALPHA\n"
            ' ;;^TST("B")\n'
            " ;;BETA\n"
            ' ;;^TST("C")\n'
            " ;;GAMMA\n"
        )
        code = generate_python(routine)

        rt = MUMPSRuntime()
        scope: dict = {}
        namespace: dict = {}
        exec(code, namespace)
        namespace["TEST"](rt, _scope=scope)

        # All three global pairs should be set.
        # Values don't have leading "=" since we simplified the data format
        # (the real DMUFI routine uses S:$A(Y)=61 to strip the "=" prefix).
        assert rt.globals.get("TST", ("A",), update_naked=False) == "ALPHA"
        assert rt.globals.get("TST", ("B",), update_naked=False) == "BETA"
        assert rt.globals.get("TST", ("C",), update_naked=False) == "GAMMA"
