"""Tests for naked reference evaluation order in SET, SET $PIECE, and SET $EXTRACT.

In MUMPS/YDB, the evaluation order for SET with naked references is:
  1. Evaluate ALL expressions (subscripts, delimiter, from, to, RHS value)
  2. THEN resolve the naked reference for the LHS target
  3. Perform the assignment

This means global references in the RHS can change the naked indicator,
and the LHS naked reference resolves using the UPDATED indicator.

Example (verified against YDB):
  S X=^A(1,2,3)     ; naked = ^A(1,2)
  S ^(0)=^B(1)       ; naked changes to ^B() from RHS, so LHS ^(0)=^B(0)

Verified against YDB via tmp/NAKEDSP.m and tmp/NAKEDS.m test routines.
"""

from __future__ import annotations

import pytest


@pytest.mark.codegen
class TestNakedSetEvalOrder:
    """Verify evaluation order: RHS evaluated before LHS naked resolution."""

    def test_set_naked_rhs_changes_naked(self, execute_mumps):
        """S ^(0)=^B(1) — RHS global ref changes naked before LHS resolves.

        After reading ^A(1,2,3), naked = ^A(1,2).
        RHS ^B(1) changes naked to ^B().
        So ^(0) resolves to ^B(0), NOT ^A(1,2,0).

        Verified against YDB (tmp/NAKEDS.m).
        """
        result = execute_mumps(
            "TEST\n"
            ' S ^A(1,2,3)="OLD"\n'
            ' S ^B(1)="VALUE"\n'
            " S X=^A(1,2,3)\n"
            " S ^(0)=^B(1)\n"
            ' W $G(^B(0),"undef"),"/",$G(^A(1,2,0),"undef")\n'
            " Q\n",
        )
        assert result.output == "VALUE/undef"

    def test_set_piece_naked_rhs_changes_naked(self, execute_mumps):
        """S $P(^(0),U,2)=^B(1) — naked from RHS affects LHS in SET $PIECE.

        After reading ^A(1,2,3), naked = ^A(1,2).
        RHS ^B(1) changes naked to ^B().
        LHS ^(0) resolves to ^B(0).

        Verified against YDB (tmp/NAKEDSP.m).
        """
        result = execute_mumps(
            "TEST\n"
            ' S U="^"\n'
            ' S ^A(1,2,3)="X^Y^Z"\n'
            ' S ^B(1)="NEW"\n'
            ' S ^B(0)="P1^P2^P3"\n'
            " S X=^A(1,2,3)\n"
            " S $P(^(0),U,2)=^B(1)\n"
            ' W ^B(0),"/",$G(^A(1,2,0),"undef")\n'
            " Q\n",
        )
        assert result.output == "P1^NEW^P3/undef"

    def test_set_piece_naked_range_rhs_global(self, execute_mumps):
        """S $P(^(0),U,3,4)=rhs_with_global — DMUFINIT line 24 pattern.

        After SET ^ZDD(N,0,"VR"), naked = ^ZDD(N,0).
        RHS evaluates $P(^ZDIC(0),U,4), changing naked to ^ZDIC().
        So ^(0) resolves to ^ZDIC(0), NOT ^ZDD(N,0,0).

        This is the exact pattern from DMUFINIT line 24.
        Verified against YDB (tmp/DMUFINIT_DBG.m).
        Uses ^ZDD/^ZDIC instead of ^DD/^DIC to avoid IRIS system globals.
        """
        result = execute_mumps(
            "TEST\n"
            ' S U="^"\n'
            ' S ^ZDD(100,0,"VR")="0.1"\n'
            ' S ^ZDIC(0)="FILE^1^100^2706"\n'
            ' S X=^ZDD(100,0,"VR")\n'
            ' S DIFQN="2^100"\n'
            " S $P(^(0),U,3,4)=$P(DIFQN,U,2)_U_($P(^ZDIC(0),U,4)+DIFQN)\n"
            " K DIFQN\n"
            " ; ^ZDIC(0) should be modified, not ^ZDD(100,0,0)\n"
            ' W ^ZDIC(0),"/",$G(^ZDD(100,0,0),"undef")\n'
            " Q\n",
        )
        assert result.output == "FILE^1^100^2708/undef"

    def test_set_piece_naked_no_rhs_global(self, execute_mumps):
        """S $P(^(0),U,2)="static" — no global in RHS, naked unchanged.

        When the RHS has no global references, naked stays from the last
        global access, so ^(0) resolves normally.
        """
        result = execute_mumps(
            "TEST\n"
            ' S U="^"\n'
            ' S ^A(1,2,3)="X^Y^Z"\n'
            " S X=^A(1,2,3)\n"
            ' S $P(^(0),U,2)="NEW"\n'
            " W ^A(1,2,0)\n"
            " Q\n",
        )
        assert result.output == "^NEW"

    def test_set_piece_naked_range_no_rhs_global(self, execute_mumps):
        """S $P(^(0),U,3,4)=local_expr — no global in RHS, naked unchanged."""
        result = execute_mumps(
            "TEST\n"
            ' S U="^"\n'
            ' S ^DD(100,0,"VR")="0.1"\n'
            ' S ^DIC(0)="FILE^1^100^2706"\n'
            ' S X=^DD(100,0,"VR")\n'
            ' S $P(^(0),U,3,4)="100"_U_(2706+2)\n'
            " W ^DD(100,0,0)\n"
            " Q\n",
        )
        # RHS is purely local, naked stays ^DD(100,0), ^(0) = ^DD(100,0,0)
        assert result.output == "^^100^2708"

    def test_set_extract_naked_rhs_changes_naked(self, execute_mumps):
        """S $E(^(0),2,3)=^B(1) — naked from RHS affects LHS in SET $EXTRACT."""
        result = execute_mumps(
            "TEST\n"
            ' S ^A(1,2,3)="ABCDEF"\n'
            ' S ^B(1)="XY"\n'
            ' S ^B(0)="123456"\n'
            " S X=^A(1,2,3)\n"
            " S $E(^(0),2,3)=^B(1)\n"
            ' W ^B(0),"/",$G(^A(1,2,0),"undef")\n'
            " Q\n",
        )
        assert result.output == "1XY456/undef"

    def test_set_naked_multiple_rhs_globals(self, execute_mumps):
        """Multiple global refs in RHS — last one determines naked.

        ^B(1) then ^C(5,6) in RHS → last ref is ^C(5,6), naked = ^C(5).
        So ^(0) = ^C(5,0).
        """
        result = execute_mumps(
            "TEST\n"
            ' S ^A(1,2,3)="val"\n'
            ' S ^B(1)="b1"\n'
            ' S ^C(5,6)="c56"\n'
            " S X=^A(1,2,3)\n"
            " S ^(0)=^B(1)_^C(5,6)\n"
            ' W $G(^C(5,0),"undef")\n'
            " Q\n",
        )
        assert result.output == "b1c56"
