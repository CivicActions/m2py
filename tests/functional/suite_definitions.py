"""Static definitions of test suites for functional tests.

This module contains hardcoded lists of routines for each YDB test suite.
Using static definitions instead of parsing driver scripts provides:
- Simpler, faster test collection
- Explicit documentation of what's tested
- No runtime dependencies on driver script formats
- Version control for any future changes

Source: YDBTest suite driver scripts (u_inref/*.csh)
MUMPS language stability: These definitions are stable since MUMPS
has not changed significantly since the 1995 standard.

Each suite defines routines as tuples of (label, routine, args):
- label: The label printed in output (for matching against outref)
- routine: The routine name (for loading .m file)
- args: Optional arguments to pass when calling the routine
"""

from __future__ import annotations

from typing import NamedTuple


class RoutineDefinition(NamedTuple):
    """Definition of a routine to test.

    Attributes:
        label: Label printed in output (used for outref matching)
        routine: Routine name (filename without .m extension)
        args: Optional arguments for routines that take parameters
        skip_reason: If set, skip this test with the given reason
        expected_passes: Expected number of PASS markers (for pattern validation)
        expected_visual: Expected number of visual "should be identical" checks
        expected_fails: Expected number of "** FAIL" markers (known failures)
    """

    label: str
    routine: str
    args: str | None = None
    skip_reason: str | None = None
    expected_passes: int | None = None
    expected_visual: int | None = None
    expected_fails: int | None = None


# =============================================================================
# MUGJ Suite (MUMPS User Group Japan)
# =============================================================================
# Source: mugj/u_inref/mugj.csh
# 72 routines testing core MUMPS language features
# Format in driver: W !!,"LABEL" D ^ROUTINE
#
# Pattern-based validation:
# - expected_passes: Count of "PASS" markers expected
# - expected_visual: Count of "should be identical" visual checks expected
# - expected_fails: Count of "** FAIL" markers expected (known collation failures)

MUGJ_ROUTINES: list[RoutineDefinition] = [
    # V1* routines - Part 77 MUMPS Standard tests
    # fmt: off
    RoutineDefinition("V1WR", "V1WR", expected_passes=0, expected_visual=4),
    RoutineDefinition("V1CMT", "V1CMT", expected_passes=5),
    RoutineDefinition("V1LL1", "V1LL1", expected_passes=13),
    RoutineDefinition("V1LL2", "V1LL2", expected_passes=21),
    RoutineDefinition("V1PRGD", "V1PRGD", expected_passes=9),
    RoutineDefinition("V1RN", "V1RN", expected_passes=5),
    RoutineDefinition("V1PRSET", "V1PRSET", expected_passes=0, expected_visual=4),
    RoutineDefinition("V1PRIE", "V1PRIE", expected_passes=9),
    RoutineDefinition("V1PRFOR", "V1PRFOR", expected_passes=4),
    RoutineDefinition("V1NUM", "V1NUM", expected_passes=103),
    RoutineDefinition("V1FC", "V1FC", expected_passes=0, expected_visual=13),
    RoutineDefinition("V1UO", "V1UO", expected_passes=241),
    RoutineDefinition("V1BOA", "V1BOA", expected_passes=184),
    RoutineDefinition("V1BOB", "V1BOB", expected_passes=365),
    RoutineDefinition("V1BOC", "V1BOC", expected_passes=67),
    RoutineDefinition("V1FN", "V1FN", expected_passes=171),
    RoutineDefinition(
        "V1AC",
        "V1AC",
        expected_passes=28,
        skip_reason="LIM-015: Uses $ZVERSION (YDB Z-function)",
    ),
    RoutineDefinition("V1LVN", "V1LVN", expected_passes=16),
    RoutineDefinition("V1GVN", "V1GVN", expected_passes=17),
    RoutineDefinition("V1DLA", "V1DLA", expected_passes=8),
    RoutineDefinition("V1DLB", "V1DLB", expected_passes=11),
    RoutineDefinition("V1DLC", "V1DLC", expected_passes=5),
    RoutineDefinition("V1DGA", "V1DGA", expected_passes=9),
    RoutineDefinition("V1DGB", "V1DGB", expected_passes=11),
    RoutineDefinition("V1NR", "V1NR", expected_passes=17),
    RoutineDefinition("V1NX", "V1NX", expected_passes=7),
    RoutineDefinition("V1SET", "V1SET", expected_passes=8),
    RoutineDefinition("V1GO", "V1GO", expected_passes=40),
    RoutineDefinition("V1OV", "V1OV", expected_passes=20),
    RoutineDefinition("V1DO", "V1DO", expected_passes=43),
    RoutineDefinition("V1CALL", "V1CALL", expected_passes=17),
    RoutineDefinition("V1IE", "V1IE", expected_passes=25),
    RoutineDefinition("V1PC", "V1PC", expected_passes=20),
    RoutineDefinition("V1FORA", "V1FORA", expected_passes=28),
    RoutineDefinition("V1FORB", "V1FORB", expected_passes=15),
    RoutineDefinition("V1FORC", "V1FORC", expected_passes=17),
    RoutineDefinition("V1IDNM", "V1IDNM", expected_passes=29),
    RoutineDefinition("V1IDGO", "V1IDGO", expected_passes=14),
    RoutineDefinition("V1IDDO", "V1IDDO", expected_passes=14),
    RoutineDefinition("V1IDARG", "V1IDARG", expected_passes=35, expected_visual=9),
    RoutineDefinition("V1XECA", "V1XECA", expected_passes=22),
    RoutineDefinition("V1XECB", "V1XECB", expected_passes=7),
    RoutineDefinition("V1SEQ", "V1SEQ", expected_passes=7),
    RoutineDefinition("V1PAT", "V1PAT", expected_passes=24),
    RoutineDefinition("V1NST1", "V1NST1", expected_passes=6),
    RoutineDefinition("V1NST2", "V1NST2", expected_passes=3),
    RoutineDefinition("V1NST3", "V1NST3", expected_passes=3),
    RoutineDefinition("V1JST", "V1JST", expected_passes=60),
    RoutineDefinition("V1SVH", "V1SVH", expected_passes=1),
    RoutineDefinition("V1SVS", "V1SVS", expected_passes=5),
    RoutineDefinition("V1MAX", "V1MAX", expected_passes=10),
    RoutineDefinition(
        "V1BR", "V1BR", expected_passes=7, skip_reason="BREAK command enters debugger"
    ),
    # VV2* routines - Part 84 extended tests
    RoutineDefinition("VV2CS", "VV2CS", expected_passes=8),
    RoutineDefinition("VV2LCC1", "VV2LCC1", expected_passes=10),
    RoutineDefinition("VV2LCC2", "VV2LCC2", expected_passes=10),
    RoutineDefinition("VV2LCF1", "VV2LCF1", expected_passes=18),
    RoutineDefinition("VV2LCF2", "VV2LCF2", expected_passes=18),
    RoutineDefinition("VV2FN1", "VV2FN1", expected_passes=14),
    RoutineDefinition("VV2FN2", "VV2FN2", expected_passes=14),
    RoutineDefinition("VV2LHP1", "VV2LHP1", expected_passes=21),
    RoutineDefinition("VV2LHP2", "VV2LHP2", expected_passes=13),
    RoutineDefinition("VV2VNIA", "VV2VNIA", expected_passes=10),
    RoutineDefinition("VV2VNIB", "VV2VNIB", expected_passes=7),
    RoutineDefinition("VV2VNIC", "VV2VNIC", expected_passes=3),
    RoutineDefinition("VV2NR", "VV2NR", expected_passes=10, expected_fails=2),
    RoutineDefinition(
        "VV2READ", "VV2READ", skip_reason="READ commands wait for user input"
    ),
    RoutineDefinition("VV2PAT1", "VV2PAT1", expected_passes=7),
    RoutineDefinition("VV2PAT2", "VV2PAT2", expected_passes=11),
    RoutineDefinition("VV2PAT3", "VV2PAT3", expected_passes=15),
    RoutineDefinition("VV2NO", "VV2NO", expected_passes=8, expected_fails=2),
    RoutineDefinition("VV2SS1", "VV2SS1", expected_passes=6, expected_fails=1),
    RoutineDefinition("VV2SS2", "VV2SS2", expected_passes=5),
    # fmt: on
]


# =============================================================================
# BASIC Suite
# =============================================================================
# Source: basic/u_inref/basic.csh
# 57 routines testing fundamental MUMPS features
# Format in driver: w "d ^routine(args)",! d ^routine(args)
# Note: Label includes the full command string for outref matching
#
# Limitation codes:
# - LIM-005: VIEW command (implementation-defined keywords)
# - LIM-015: Zero-VistA-usage YDB Z-commands
# - LIM-019: Arithmetic precision edge cases

BASIC_ROUTINES: list[RoutineDefinition] = [
    # fmt: off
    # Core arithmetic and expression tests
    RoutineDefinition("d ^fact(18)", "fact", "18"),
    RoutineDefinition(
        "d ^arith(18)",
        "arith",
        "18",
        skip_reason="LIM-019: Arithmetic precision edge cases at 18-digit boundary",
    ),
    RoutineDefinition(
        "d ^ebmuldiv(0)",
        "ebmuldiv",
        "0",
        skip_reason="LIM-015: Uses YDB %HD utility (hex-to-decimal conversion)",
    ),
    RoutineDefinition("d ^barith", "barith"),
    RoutineDefinition("d ^bool", "bool"),
    RoutineDefinition("d ^relation", "relation"),
    RoutineDefinition("d ^pattst", "pattst"),
    RoutineDefinition("d ^sortsaft", "sortsaft"),
    RoutineDefinition(
        "d ^text4",
        "text4",
        skip_reason="LIM-015: $TEXT with external routine references requires source lookup",
    ),
    RoutineDefinition(
        "d ^per02457",
        "per02457",
        skip_reason="LIM-015: $TEXT with external routine references requires source lookup",
    ),
    # String functions
    RoutineDefinition("d ^ascii", "ascii"),
    RoutineDefinition(
        "d ^char", "char", skip_reason="LIM-015: Uses $ZVERSION (YDB Z-function)"
    ),
    RoutineDefinition("d ^fnextr", "fnextr"),
    RoutineDefinition("d ^length", "length"),
    RoutineDefinition("d ^piece", "piece"),
    RoutineDefinition(
        "d ^setpiece",
        "setpiece",
        skip_reason="LIM-015: Uses $ZTRAP (YDB error handling)",
    ),
    RoutineDefinition("d ^query", "query"),
    # Routine calls and variables
    RoutineDefinition("d ^extcall", "extcall"),
    RoutineDefinition("d ^locals", "locals"),
    RoutineDefinition("d ^cmptst", "cmptst"),
    RoutineDefinition("d ^expr2", "expr2"),
    # Control flow
    RoutineDefinition("d ^for", "for"),
    RoutineDefinition("d ^forloop", "forloop"),
    RoutineDefinition("d ^log", "log"),
    RoutineDefinition(
        "d ^new", "new", skip_reason="LIM-015: Uses $ZPOSITION (YDB special variable)"
    ),
    RoutineDefinition("d ^select", "select"),
    RoutineDefinition("d ^xecute", "xecute"),
    RoutineDefinition("d ^larray", "larray"),
    # VIEW command tests (YDB-specific)
    RoutineDefinition(
        "d ^view",
        "view",
        skip_reason="LIM-005: VIEW command (implementation-defined keywords)",
    ),
    RoutineDefinition(
        "d ^view2(0)",
        "view2",
        "0",
        skip_reason="LIM-005: VIEW command (implementation-defined keywords)",
    ),
    # Z-extension tests
    RoutineDefinition(
        "d ^zbits", "zbits", skip_reason="LIM-015: Uses $ZTRAP (YDB error handling)"
    ),
    # Regression tests
    RoutineDefinition(
        "d ^per2586a(0)",
        "per2586a",
        "0",
        skip_reason="LIM-015: Uses $ZTRAP (YDB error handling)",
    ),
    RoutineDefinition(
        "d ^per2586b(0)",
        "per2586b",
        "0",
        skip_reason="LIM-015: Uses $ZTRAP (YDB error handling)",
    ),
    RoutineDefinition(
        "d ^per2586c(0)",
        "per2586c",
        "0",
        skip_reason="LIM-015: Uses $ZTRAP (YDB error handling)",
    ),
    RoutineDefinition(
        "d ^per2968",
        "per2968",
        skip_reason="LIM-015: Uses ZSYSTEM command (shell execution)",
    ),
    RoutineDefinition("d ^tstp", "tstp"),
    RoutineDefinition(
        "d ^zlfix",
        "zlfix",
        skip_reason="LIM-015: Uses ZSYSTEM command (shell execution)",
    ),
    RoutineDefinition("d ^largeexp1", "largeexp1"),
    RoutineDefinition(
        "d ^largeexp2",
        "largeexp2",
        skip_reason="LIM-015: Tests YDB error handling for numbers >1E47",
    ),
    RoutineDefinition(
        "d ^largeexp3",
        "largeexp3",
        skip_reason="LIM-015: Tests YDB error handling for numbers >1E47",
    ),
    RoutineDefinition(
        "d ^order",
        "order",
        skip_reason="LIM-015: Outref requires ZTRAP external routines (ztvref*, zticmd*)",
    ),
    # Z-debugging tests
    RoutineDefinition(
        "d ^zbrk",
        "zbrk",
        skip_reason="LIM-015: ZBREAK debugging command requires YDB debugger",
    ),
    RoutineDefinition(
        "d ^ztrp", "ztrp", skip_reason="LIM-015: Uses $ZTRAP (YDB error handling)"
    ),
    RoutineDefinition(
        "d ^zstep",
        "zstep",
        skip_reason="LIM-015: ZSTEP debugging command requires YDB debugger",
    ),
    RoutineDefinition(
        "d ^zstep1",
        "zstep1",
        skip_reason="LIM-015: ZSTEP debugging command requires YDB debugger",
    ),
    # Database operations
    RoutineDefinition(
        "d ^kill1",
        "kill1",
        skip_reason="LIM-015: Uses $ZPOSITION (YDB special variable)",
    ),
    RoutineDefinition(
        "d ^set", "set", skip_reason="LIM-015: Uses $ZTRAP (YDB error handling)"
    ),
    RoutineDefinition("d ^globals", "globals"),
    RoutineDefinition(
        "d ^zprev", "zprev", skip_reason="LIM-015: Uses $ZPREVIOUS (YDB Z-function)"
    ),
    # More regression tests
    RoutineDefinition(
        "d ^per02397",
        "per02397",
        skip_reason="LIM-015: Requires ^ASW database pre-populated",
    ),
    RoutineDefinition(
        "d ^miscdb",
        "miscdb",
        skip_reason="LIM-015: Outref includes YDB mupip integ/file creation infrastructure output",
    ),
    RoutineDefinition("d ^per02276", "per02276"),
    RoutineDefinition(
        "d ^stpfail",
        "stpfail",
        skip_reason="LIM-015: Requires YDB JOBLABOFF / test harness",
    ),
    # I/O tests
    RoutineDefinition(
        "d ^putfail",
        "putfail",
        skip_reason="LIM-015: Uses NEW $ZTRAP (YDB error handling)",
    ),
    RoutineDefinition(
        "d ^fifo", "fifo", skip_reason="LIM-015: Uses $ZVERSION (YDB Z-function)"
    ),
    RoutineDefinition(
        "d ^stream",
        "stream",
        skip_reason="LIM-015: Uses ZSYSTEM command (shell execution)",
    ),
    RoutineDefinition(
        "d ^iowrite",
        "iowrite",
        skip_reason="LIM-015: OPEN with YDB-specific device parameters",
    ),
    # fmt: on
]


# =============================================================================
# MVTS Suite (M Validation Test Suite)
# =============================================================================
# Source: mvts/inref/VV1.m, VV2.m, VV3.m, VV4.m (main driver routines)
# MVTS is a comprehensive validation suite with sub-driver routines that
# call individual test routines. Each sub-driver tests a specific feature area.
#
# The MVTS framework consists of pure MUMPS routines:
# - V1PRESET: Sets up test state (^ABSN, ^ITEM, ^NEXT)
# - VEXAMINE: Compares ^VCOMP vs ^VCORR, reports PASS/FAIL
# - VENVIRON: Environment setup and configuration
#
# All framework routines are in mvts/inref/ and can be transpiled along
# with the test routines. Tests will fail naturally if m2py doesn't support
# the MUMPS constructs used.
#
# Format in drivers: V1WR W !!,"1---V1WR" D ^V1WR

# VV1 sub-drivers (Part 77 - MUMPS Standard tests)
# expected_passes: Count of D ^VEXAMINE calls (automated tests)
# expected_fails: Count of D MANPF*^VEXAMINE calls (operator tests produce *FAILO*)
# Counts include sub-routines (e.g., V1NUM includes V1NUM1-V1NUM6)
MVTS_VV1_ROUTINES: list[RoutineDefinition] = [
    # fmt: off
    RoutineDefinition("1---V1WR", "V1WR", expected_passes=0, expected_fails=4),
    RoutineDefinition("2---V1CMT", "V1CMT", expected_passes=5),
    RoutineDefinition("3---V1LL0", "V1LL0", expected_passes=1),
    RoutineDefinition("4---V1LL1", "V1LL1", expected_passes=13),
    RoutineDefinition("5---V1LL2", "V1LL2", expected_passes=9),
    RoutineDefinition("6---V1LL3", "V1LL3", expected_passes=14),
    RoutineDefinition("7---V1PRGD", "V1PRGD", expected_passes=9),
    RoutineDefinition("8---V1RN", "V1RN", expected_passes=5),
    RoutineDefinition("9---V1PRSET", "V1PRSET", expected_passes=0, expected_fails=4),
    RoutineDefinition("10---V1PRIE", "V1PRIE", expected_passes=9),
    RoutineDefinition("11---V1PRFOR", "V1PRFOR", expected_passes=4),
    RoutineDefinition("11.1---V1NUM", "V1NUM", expected_passes=103),
    RoutineDefinition("17.1---V1FC", "V1FC", expected_passes=0, expected_fails=15),
    RoutineDefinition("20.1---V1UO", "V1UO"),
    RoutineDefinition("35.1---V1BOA", "V1BOA", expected_passes=184),
    RoutineDefinition("47.1---V1BOR", "V1BOR"),
    RoutineDefinition("84.1---V1BOL", "V1BOL"),
    RoutineDefinition("91---V1BOC", "V1BOC", expected_passes=15),
    RoutineDefinition("91.1---V1FN", "V1FN"),
    RoutineDefinition("103.1---V1AC", "V1AC", expected_passes=28),
    RoutineDefinition("107---V1LVN", "V1LVN", expected_passes=16),
    RoutineDefinition("108---V1GVN", "V1GVN", expected_passes=17),
    RoutineDefinition("109---V1DLA", "V1DLA", expected_passes=8),
    RoutineDefinition("109.1---V1DLB", "V1DLB", expected_passes=13),
    RoutineDefinition("112---V1DLC", "V1DLC", expected_passes=5),
    RoutineDefinition("113---V1DGA", "V1DGA", expected_passes=9),
    RoutineDefinition("113.1---V1DGB", "V1DGB", expected_passes=13),
    RoutineDefinition("115.1---V1NR", "V1NR", expected_passes=21),
    RoutineDefinition("118.1---V1NX", "V1NX"),
    RoutineDefinition("120.1---V1SET", "V1SET", expected_passes=8),
    RoutineDefinition("122.1---V1GO", "V1GO", expected_passes=40),
    RoutineDefinition("125.1---V1OV", "V1OV"),
    RoutineDefinition("127.1---V1DO", "V1DO", expected_passes=43),
    RoutineDefinition("131.1---V1CALL", "V1CALL", expected_passes=17),
    RoutineDefinition("133.1---V1IE", "V1IE", expected_passes=25),
    RoutineDefinition("135.1---V1PC", "V1PC"),
    RoutineDefinition("138.1---V1FORA", "V1FORA", expected_passes=28),
    RoutineDefinition("141.1---V1FORB", "V1FORB", expected_passes=15),
    RoutineDefinition("143.1---V1FORC", "V1FORC", expected_passes=17),
    RoutineDefinition("145.1---V1IDNM", "V1IDNM", expected_passes=24),
    RoutineDefinition("149.1---V1IDGO", "V1IDGO", expected_passes=1),
    RoutineDefinition("150.1---V1IDDO", "V1IDDO"),
    RoutineDefinition(
        "152.1---V1IDARG",
        "V1IDARG",
        expected_passes=37,
        expected_fails=9,
        skip_reason="LIM-ARG-INDIR: WRITE argument indirection requires runtime parsing",
    ),
    RoutineDefinition("158.1---V1XECA", "V1XECA", expected_passes=22),
    RoutineDefinition("161---V1XECB", "V1XECB", expected_passes=7),
    RoutineDefinition("162---V1SEQ", "V1SEQ", expected_passes=7),
    RoutineDefinition("162.1---V1PAT", "V1PAT", expected_passes=26),
    RoutineDefinition("167---V1NST1", "V1NST1"),
    RoutineDefinition("168---V1NST2", "V1NST2"),
    RoutineDefinition("169---V1NST3", "V1NST3"),
    RoutineDefinition("169.1---V1JST", "V1JST", expected_passes=60),
    RoutineDefinition("176---V1SVH", "V1SVH", expected_passes=1, expected_fails=1),
    RoutineDefinition("177---V1SVS", "V1SVS", expected_passes=5),
    RoutineDefinition("177.1---V1MAX", "V1MAX", expected_passes=3, expected_fails=1),
    RoutineDefinition(
        "181---V1BR",
        "V1BR",
        expected_passes=7,
        skip_reason="BREAK command enters debugger",
    ),
    RoutineDefinition(
        "188.1---V1HANG", "V1HANG", skip_reason="HANG command causes test to sleep"
    ),
    RoutineDefinition("191---V1PO", "V1PO", expected_passes=10),
    RoutineDefinition("192---V1RANDA", "V1RANDA", expected_passes=2),
    RoutineDefinition("193---V1RANDB", "V1RANDB"),
    # fmt: on
]

# VV2 sub-drivers (Part 84 - Extended tests)
MVTS_VV2_ROUTINES: list[RoutineDefinition] = [
    # fmt: off
    RoutineDefinition("1---V2CS", "V2CS", expected_passes=8),
    RoutineDefinition("2---V2LCC1", "V2LCC1", expected_passes=8, expected_fails=2),
    RoutineDefinition("3---V2LCC2", "V2LCC2", expected_passes=12),
    RoutineDefinition("4---V2LCF1", "V2LCF1", expected_passes=10),
    RoutineDefinition("5---V2LCF2", "V2LCF2", expected_passes=6),
    RoutineDefinition("6---V2LCF3", "V2LCF3", expected_passes=10),
    RoutineDefinition("7---V2LCF4", "V2LCF4", expected_passes=8),
    RoutineDefinition("8---V2FN1", "V2FN1", expected_passes=14),
    RoutineDefinition("9---V2FN2", "V2FN2", expected_passes=15),
    RoutineDefinition("10---V2LHP1", "V2LHP1", expected_passes=12),
    RoutineDefinition("11---V2LHP2", "V2LHP2", expected_passes=7),
    RoutineDefinition("12---V2LHP3", "V2LHP3", expected_passes=3),
    RoutineDefinition("13---V2LHP4", "V2LHP4", expected_passes=8),
    RoutineDefinition("14---V2VNIA", "V2VNIA", expected_passes=10),
    RoutineDefinition("15---V2VNIB", "V2VNIB", expected_passes=7),
    RoutineDefinition("16---V2VNIC", "V2VNIC", expected_passes=3),
    RoutineDefinition("17---V2NR", "V2NR", expected_passes=4),
    RoutineDefinition("19---V2PAT1", "V2PAT1", expected_passes=8),
    RoutineDefinition("20---V2PAT2", "V2PAT2", expected_passes=11),
    RoutineDefinition("21---V2PAT3", "V2PAT3", expected_passes=9),
    RoutineDefinition("22---V2PAT4", "V2PAT4", expected_passes=6),
    RoutineDefinition("23---V2NO1", "V2NO1"),
    RoutineDefinition("24---V2NO2", "V2NO2", expected_passes=8),
    RoutineDefinition("25---V2SSUB1", "V2SSUB1", expected_passes=2),
    RoutineDefinition("26---V2SSUB2", "V2SSUB2"),
    # fmt: on
]

# VV3 sub-drivers (Part 95 - Extended tests)
MVTS_VV3_ROUTINES: list[RoutineDefinition] = [
    # fmt: off
    RoutineDefinition("0.1---V3GET", "V3GET", expected_passes=86),
    RoutineDefinition("6.1---V3TR", "V3TR", expected_passes=165),
    RoutineDefinition("17.1---V3TEXT", "V3TEXT", expected_passes=46),
    RoutineDefinition("20.1---V3FOR", "V3FOR", expected_passes=15),
    RoutineDefinition(
        "22.1---V3HANG",
        "V3HANG",
        expected_passes=15,
        skip_reason="HANG command causes test to sleep",
    ),
    RoutineDefinition("25.1---V3MAX", "V3MAX", expected_passes=7),
    RoutineDefinition("28---V3NST1", "V3NST1", expected_passes=6),
    RoutineDefinition("29---V3NST2", "V3NST2", expected_passes=3),
    RoutineDefinition("30---V3NST3", "V3NST3", expected_passes=3),
    RoutineDefinition("31---V3SVS", "V3SVS", expected_passes=1),
    RoutineDefinition("31.1---V3SSUB", "V3SSUB", expected_passes=9),
    RoutineDefinition(
        "34---V3JOB",
        "V3JOB",
        expected_passes=4,
        skip_reason="JOB command requires process spawning",
    ),
    RoutineDefinition(
        "34.1---V3LOCK",
        "V3LOCK",
        expected_passes=16,
        skip_reason="LOCK command can hang",
    ),
    RoutineDefinition("37---V3INDNM", "V3INDNM", expected_passes=5),
    RoutineDefinition(
        "37.1---V3QUERY",
        "V3QUERY",
        skip_reason="LIM-SUB-CANON: Subscript canonicalization collapses numeric-looking strings",
    ),
    RoutineDefinition("43.1---V3FN2", "V3FN2", expected_passes=407),
    RoutineDefinition("65.1---V3FN3", "V3FN3", expected_passes=49),
    RoutineDefinition("70.1---V3NEW", "V3NEW", expected_passes=36),
    RoutineDefinition("136---V3FP", "V3FP", expected_passes=4),
    RoutineDefinition("137---V3DWP", "V3DWP", expected_passes=6),
    RoutineDefinition("138---V3ESV", "V3ESV", expected_passes=4),
    RoutineDefinition("139---V3EF", "V3EF", expected_passes=6),
    RoutineDefinition("139.1---V3CBR", "V3CBR", expected_passes=14),
    # fmt: on
]

# VV4 sub-drivers (Part 95 continued)
MVTS_VV4_ROUTINES: list[RoutineDefinition] = [
    # fmt: off
    RoutineDefinition("0.1---V4SORT", "V4SORT", expected_passes=87),
    RoutineDefinition("10.1---V4FNUM", "V4FNUM"),
    RoutineDefinition("18.1---V4REV", "V4REV", expected_passes=25),
    RoutineDefinition("22.1---V4GET2", "V4GET2", expected_passes=64),
    RoutineDefinition("31.1---V4NAME", "V4NAME", expected_passes=97),
    RoutineDefinition("45.1---V4QLEN", "V4QLEN", expected_passes=59),
    RoutineDefinition("53.1---V4QSUB", "V4QSUB", expected_passes=116),
    RoutineDefinition("68.1---V4SVQ", "V4SVQ", expected_passes=30),
    RoutineDefinition("74.1---V4MERGE", "V4MERGE", expected_passes=36),
    RoutineDefinition("97---V4KEY", "V4KEY", expected_passes=3),
    RoutineDefinition("98---V4SYSTEM", "V4SYSTEM", expected_passes=3),
    RoutineDefinition("98.1---V4POWER", "V4POWER"),
    RoutineDefinition("107---V4RAND", "V4RAND", expected_passes=1),
    RoutineDefinition("107.1---V4ORDER", "V4ORDER"),
    RoutineDefinition("118---V4QUERY", "V4QUERY", expected_passes=2),
    RoutineDefinition("119---V4PRIN", "V4PRIN", expected_passes=4),
    RoutineDefinition("120---V4QUIT", "V4QUIT", expected_passes=6),
    RoutineDefinition("120.1---V4MAX", "V4MAX", expected_passes=7),
    RoutineDefinition("122.1---V4SSUB", "V4SSUB", expected_passes=9),
    RoutineDefinition(
        "125---V4JOB",
        "V4JOB",
        expected_passes=3,
        skip_reason="JOB command requires process spawning",
    ),
    RoutineDefinition("125.1---V4PAT", "V4PAT", expected_passes=87),
    RoutineDefinition("135---V4NST1", "V4NST1", expected_passes=1),
    RoutineDefinition("136---V4NST2", "V4NST2", expected_passes=1),
    RoutineDefinition("137---V4NST3", "V4NST3", expected_passes=1),
    RoutineDefinition("138---V4NST4", "V4NST4", expected_passes=1),
    RoutineDefinition("139---V4NST5", "V4NST5", expected_passes=1),
    RoutineDefinition("140---V4NST6", "V4NST6", expected_passes=1),
    RoutineDefinition("141---V4MDC", "V4MDC", expected_passes=2),
    # fmt: on
]

# Combined MVTS routines (all sub-drivers from VV1-VV4)
MVTS_ROUTINES: list[RoutineDefinition] = (
    MVTS_VV1_ROUTINES + MVTS_VV2_ROUTINES + MVTS_VV3_ROUTINES + MVTS_VV4_ROUTINES
)


# =============================================================================
# MERGE Suite
# =============================================================================
# Source: merge/u_inref/*.csh driver scripts
# Each sub-test has its own driver and outref file
# Tests the MERGE command with various source/target combinations
#
# Structure:
# - 23 driver scripts in u_inref/ (shell scripts for YDB infrastructure)
# - 25 outref files (contain YDB prompts + actual MUMPS output)
# - 54 routines in inref/ (pure MUMPS)
#
# The outrefs include YDB infrastructure output (DB creation, replication)
# but the actual test output (STEP 1, ZWR results, etc.) can be extracted
# and compared. Use normalize_outref() to strip infrastructure markers.
#
# Limitation codes:
# - LIM-005: VIEW command (implementation-defined keywords)
# - LIM-015: Zero-VistA-usage YDB Z-commands

# Sub-test definitions with their primary test routines
MERGE_SUBTESTS: list[RoutineDefinition] = [
    # fmt: off
    # Basic merge operations
    RoutineDefinition("gbl2gbl", "mbyexam"),
    RoutineDefinition("gbl2lcl", "mbyexam"),
    RoutineDefinition("lcl2gbl", "mbyexam"),
    RoutineDefinition("lcl2lcl", "mbyexam"),
    # Error handling
    RoutineDefinition(
        "errors", "errors", skip_reason="LIM-015: Uses NEW $ZTRAP (YDB error handling)"
    ),
    # Extended global tests
    RoutineDefinition("extgbl1", "extgbl1"),
    RoutineDefinition("extgbl2", "extgbl2"),
    # Collation tests
    RoutineDefinition("gblcol", "gblcol"),
    RoutineDefinition("lclcol", "lclcol"),
    RoutineDefinition("polgblcol", "gblcol"),
    RoutineDefinition("pollclcol", "lclcol"),
    # Indirection tests
    RoutineDefinition(
        "indirection",
        "MINDR1",
        skip_reason="LIM-015: Uses NEW $ZTRAP (YDB error handling)",
    ),
    # Miscellaneous
    RoutineDefinition(
        "falsedsc",
        "falsedsc",
        skip_reason="LIM-015: Uses SET $ZTRAP (YDB error handling)",
    ),
    RoutineDefinition("misclv", "mergelv"),
    RoutineDefinition(
        "mrgclnup",
        "mrgclnup",
        skip_reason="LIM-015: Uses NEW $ZTRAP (YDB error handling)",
    ),
    RoutineDefinition(
        "nullsubs",
        "nullfill",
        skip_reason="LIM-015: Uses NEW $ZTRAP (YDB error handling)",
    ),
    # MVTS merge tests
    RoutineDefinition(
        "MVTS_MERGE",
        "V4MERGE",
        skip_reason="LIM-015: Uses NEW $ZTRAP (YDB error handling)",
    ),
    # Transaction processing tests
    RoutineDefinition(
        "tp_simple", "MRGITP", skip_reason="LIM-015: Uses SET $ZT (YDB error handling)"
    ),
    RoutineDefinition(
        "tp_stress", "mrgstp", skip_reason="LIM-015: Uses SET $ZT (YDB error handling)"
    ),
    # Unicode merge tests
    RoutineDefinition("ugbl2gbl", "mbyexam"),
    RoutineDefinition("ugbl2lcl", "mbyexam"),
    RoutineDefinition("ulcl2gbl", "mbyexam"),
    RoutineDefinition("ulcl2lcl", "mbyexam"),
    # ZSHOW tests
    RoutineDefinition(
        "zshowgbl",
        "list",
        skip_reason="LIM-015: Uses D ^%G (YDB global display utility)",
    ),
    RoutineDefinition(
        "zshowlcl",
        "list",
        skip_reason="LIM-015: Uses D ^%G (YDB global display utility)",
    ),
    # fmt: on
]

# Individual merge routines (for direct testing if needed)
MERGE_ROUTINES: list[RoutineDefinition] = [
    # fmt: off
    RoutineDefinition("mbyexam", "mbyexam"),  # Basic merge examples
    RoutineDefinition(
        "errors",
        "errors",  # Error condition tests
        skip_reason="LIM-015: Uses NEW $ZTRAP (YDB error handling)",
    ),
    RoutineDefinition("extgbl1", "extgbl1"),  # Extended global 1
    RoutineDefinition("extgbl2", "extgbl2"),  # Extended global 2
    RoutineDefinition(
        "falsedsc",
        "falsedsc",  # False descriptor tests
        skip_reason="LIM-015: Uses SET $ZTRAP (YDB error handling)",
    ),
    RoutineDefinition("gblcol", "gblcol"),  # Global collation
    RoutineDefinition("lclcol", "lclcol"),  # Local collation
    RoutineDefinition("mergelv", "mergelv"),  # Merge local variable
    RoutineDefinition(
        "mrgclnup",
        "mrgclnup",  # Merge cleanup
        skip_reason="LIM-015: Uses NEW $ZTRAP (YDB error handling)",
    ),
    RoutineDefinition(
        "MRGITP",
        "MRGITP",  # Merge in TP
        skip_reason="LIM-015: Uses SET $ZT (YDB error handling)",
    ),
    RoutineDefinition(
        "mrgstp",
        "mrgstp",  # Merge stress TP
        skip_reason="LIM-015: Uses SET $ZT (YDB error handling)",
    ),
    RoutineDefinition(
        "MINDR1",
        "MINDR1",  # Merge indirection 1
        skip_reason="LIM-015: Uses NEW $ZTRAP (YDB error handling)",
    ),
    RoutineDefinition(
        "MINDR2",
        "MINDR2",  # Merge indirection 2
        skip_reason="LIM-015: Uses NEW $ZTRAP (YDB error handling)",
    ),
    RoutineDefinition(
        "MINDR3",
        "MINDR3",  # Merge indirection 3
        skip_reason="LIM-015: Uses NEW $ZTRAP (YDB error handling)",
    ),
    RoutineDefinition(
        "MINDR4",
        "MINDR4",  # Merge indirection 4
        skip_reason="LIM-015: Uses NEW $ZTRAP (YDB error handling)",
    ),
    RoutineDefinition(
        "MINDMISC",
        "MINDMISC",  # Merge indirection misc
        skip_reason="LIM-015: Uses NEW $ZTRAP (YDB error handling)",
    ),
    RoutineDefinition(
        "V4MERGE",
        "V4MERGE",  # MVTS merge tests
        skip_reason="LIM-015: Uses NEW $ZTRAP (YDB error handling)",
    ),
    RoutineDefinition(
        "list",
        "list",  # List routine for ZSHOW
        skip_reason="LIM-015: Uses D ^%G (YDB global display utility)",
    ),
    RoutineDefinition(
        "nullfill",
        "nullfill",  # Null subscript fill
        skip_reason="LIM-015: Uses NEW $ZTRAP (YDB error handling)",
    ),
    # fmt: on
]


# =============================================================================
# Suite Registry
# =============================================================================
# Maps suite names to their routine definitions

SUITE_REGISTRY: dict[str, list[RoutineDefinition]] = {
    "mugj": MUGJ_ROUTINES,
    "basic": BASIC_ROUTINES,
    "mvts": MVTS_ROUTINES,
    "merge": MERGE_SUBTESTS,
}


def get_suite_routines(suite_name: str) -> list[RoutineDefinition]:
    """Get routine definitions for a test suite.

    Args:
        suite_name: Name of the suite (e.g., "mugj", "basic", "mvts", "merge")

    Returns:
        List of RoutineDefinition for the suite

    Raises:
        KeyError: If suite_name is not in the registry
    """
    return SUITE_REGISTRY[suite_name]
