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
    """

    label: str
    routine: str
    args: str | None = None
    skip_reason: str | None = None


# =============================================================================
# MUGJ Suite (MUMPS User Group Japan)
# =============================================================================
# Source: mugj/u_inref/mugj.csh
# 72 routines testing core MUMPS language features
# Format in driver: W !!,"LABEL" D ^ROUTINE

MUGJ_ROUTINES: list[RoutineDefinition] = [
    # V1* routines - Part 77 MUMPS Standard tests
    RoutineDefinition("V1WR", "V1WR"),
    RoutineDefinition("V1CMT", "V1CMT"),
    RoutineDefinition("V1LL1", "V1LL1"),
    RoutineDefinition("V1LL2", "V1LL2"),
    RoutineDefinition("V1PRGD", "V1PRGD"),
    RoutineDefinition("V1RN", "V1RN"),
    RoutineDefinition("V1PRSET", "V1PRSET"),
    RoutineDefinition("V1PRIE", "V1PRIE"),
    RoutineDefinition("V1PRFOR", "V1PRFOR"),
    RoutineDefinition("V1NUM", "V1NUM"),
    RoutineDefinition("V1FC", "V1FC"),
    RoutineDefinition("V1UO", "V1UO"),
    RoutineDefinition("V1BOA", "V1BOA"),
    RoutineDefinition("V1BOB", "V1BOB"),
    RoutineDefinition("V1BOC", "V1BOC"),
    RoutineDefinition("V1FN", "V1FN"),
    RoutineDefinition("V1AC", "V1AC"),
    RoutineDefinition("V1LVN", "V1LVN"),
    RoutineDefinition("V1GVN", "V1GVN"),
    RoutineDefinition("V1DLA", "V1DLA"),
    RoutineDefinition("V1DLB", "V1DLB"),
    RoutineDefinition("V1DLC", "V1DLC"),
    RoutineDefinition("V1DGA", "V1DGA"),
    RoutineDefinition("V1DGB", "V1DGB"),
    RoutineDefinition("V1NR", "V1NR"),
    RoutineDefinition("V1NX", "V1NX"),
    RoutineDefinition("V1SET", "V1SET"),
    RoutineDefinition("V1GO", "V1GO"),
    RoutineDefinition("V1OV", "V1OV"),
    RoutineDefinition("V1DO", "V1DO"),
    RoutineDefinition("V1CALL", "V1CALL"),
    RoutineDefinition("V1IE", "V1IE"),
    RoutineDefinition("V1PC", "V1PC"),
    RoutineDefinition("V1FORA", "V1FORA"),
    RoutineDefinition("V1FORB", "V1FORB"),
    RoutineDefinition("V1FORC", "V1FORC"),
    RoutineDefinition("V1IDNM", "V1IDNM"),
    RoutineDefinition("V1IDGO", "V1IDGO"),
    RoutineDefinition("V1IDDO", "V1IDDO"),
    RoutineDefinition("V1IDARG", "V1IDARG"),
    RoutineDefinition("V1XECA", "V1XECA"),
    RoutineDefinition("V1XECB", "V1XECB"),
    RoutineDefinition("V1SEQ", "V1SEQ"),
    RoutineDefinition("V1PAT", "V1PAT"),
    RoutineDefinition("V1NST1", "V1NST1"),
    RoutineDefinition("V1NST2", "V1NST2"),
    RoutineDefinition("V1NST3", "V1NST3"),
    RoutineDefinition("V1JST", "V1JST"),
    RoutineDefinition("V1SVH", "V1SVH"),
    RoutineDefinition("V1SVS", "V1SVS"),
    RoutineDefinition("V1MAX", "V1MAX"),
    RoutineDefinition("V1BR", "V1BR"),
    # VV2* routines - Part 84 extended tests
    RoutineDefinition("VV2CS", "VV2CS"),
    RoutineDefinition("VV2LCC1", "VV2LCC1"),
    RoutineDefinition("VV2LCC2", "VV2LCC2"),
    RoutineDefinition("VV2LCF1", "VV2LCF1"),
    RoutineDefinition("VV2LCF2", "VV2LCF2"),
    RoutineDefinition("VV2FN1", "VV2FN1"),
    RoutineDefinition("VV2FN2", "VV2FN2"),
    RoutineDefinition("VV2LHP1", "VV2LHP1"),
    RoutineDefinition("VV2LHP2", "VV2LHP2"),
    RoutineDefinition("VV2VNIA", "VV2VNIA"),
    RoutineDefinition("VV2VNIB", "VV2VNIB"),
    RoutineDefinition("VV2VNIC", "VV2VNIC"),
    RoutineDefinition("VV2NR", "VV2NR"),
    RoutineDefinition(
        "VV2READ",
        "VV2READ",
        skip_reason="READ timeouts cannot be automated",
    ),
    RoutineDefinition("VV2PAT1", "VV2PAT1"),
    RoutineDefinition("VV2PAT2", "VV2PAT2"),
    RoutineDefinition("VV2PAT3", "VV2PAT3"),
    RoutineDefinition("VV2NO", "VV2NO"),
    RoutineDefinition("VV2SS1", "VV2SS1"),
    RoutineDefinition("VV2SS2", "VV2SS2"),
]


# =============================================================================
# BASIC Suite
# =============================================================================
# Source: basic/u_inref/basic.csh
# 56 routines testing fundamental MUMPS features
# Format in driver: w "d ^routine(args)",! d ^routine(args)
# Note: Label includes the full command string for outref matching

BASIC_ROUTINES: list[RoutineDefinition] = [
    # Core arithmetic and expression tests
    RoutineDefinition("d ^fact(18)", "fact", "18"),
    RoutineDefinition("d ^arith(18)", "arith", "18"),
    RoutineDefinition("d ^ebmuldiv(0)", "ebmuldiv", "0"),
    RoutineDefinition("d ^barith", "barith"),
    RoutineDefinition("d ^bool", "bool"),
    RoutineDefinition("d ^relation", "relation"),
    RoutineDefinition("d ^pattst", "pattst"),
    RoutineDefinition("d ^sortsaft", "sortsaft"),
    RoutineDefinition("d ^text4", "text4"),
    RoutineDefinition("d ^per02457", "per02457"),
    # String functions
    RoutineDefinition("d ^ascii", "ascii"),
    RoutineDefinition("d ^char", "char"),
    RoutineDefinition("d ^fnextr", "fnextr"),
    RoutineDefinition("d ^length", "length"),
    RoutineDefinition("d ^piece", "piece"),
    RoutineDefinition("d ^setpiece", "setpiece"),
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
    RoutineDefinition("d ^new", "new"),
    RoutineDefinition("d ^select", "select"),
    RoutineDefinition("d ^xecute", "xecute"),
    RoutineDefinition("d ^larray", "larray"),
    # VIEW command tests (YDB-specific)
    RoutineDefinition("d ^view", "view"),
    RoutineDefinition("d ^view2(0)", "view2", "0"),
    # Z-extension tests
    RoutineDefinition("d ^zbits", "zbits"),
    # Regression tests
    RoutineDefinition("d ^per2586a(0)", "per2586a", "0"),
    RoutineDefinition("d ^per2586b(0)", "per2586b", "0"),
    RoutineDefinition("d ^per2586c(0)", "per2586c", "0"),
    RoutineDefinition("d ^per2968", "per2968"),
    RoutineDefinition("d ^tstp", "tstp"),
    RoutineDefinition("d ^zlfix", "zlfix"),
    RoutineDefinition("d ^largeexp1", "largeexp1"),
    RoutineDefinition("d ^largeexp2", "largeexp2"),
    RoutineDefinition("d ^largeexp3", "largeexp3"),
    RoutineDefinition("d ^order", "order"),
    # Z-debugging tests
    RoutineDefinition("d ^zbrk", "zbrk"),
    RoutineDefinition("d ^ztrp", "ztrp"),
    RoutineDefinition("d ^zstep", "zstep"),
    RoutineDefinition("d ^zstep1", "zstep1"),
    # Database operations
    RoutineDefinition("d ^kill1", "kill1"),
    RoutineDefinition("d ^set", "set"),
    RoutineDefinition("d ^globals", "globals"),
    RoutineDefinition("d ^zprev", "zprev"),
    # More regression tests
    RoutineDefinition("d ^per02397", "per02397"),
    RoutineDefinition("d ^miscdb", "miscdb"),
    RoutineDefinition("d ^per02276", "per02276"),
    RoutineDefinition("d ^stpfail", "stpfail"),
    # I/O tests
    RoutineDefinition("d ^putfail", "putfail"),
    RoutineDefinition("d ^fifo", "fifo"),
    RoutineDefinition("d ^stream", "stream"),
    RoutineDefinition("d ^iowrite", "iowrite"),
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
MVTS_VV1_ROUTINES: list[RoutineDefinition] = [
    RoutineDefinition("1---V1WR", "V1WR"),
    RoutineDefinition("2---V1CMT", "V1CMT"),
    RoutineDefinition("3---V1LL0", "V1LL0"),
    RoutineDefinition("4---V1LL1", "V1LL1"),
    RoutineDefinition("5---V1LL2", "V1LL2"),
    RoutineDefinition("6---V1LL3", "V1LL3"),
    RoutineDefinition("7---V1PRGD", "V1PRGD"),
    RoutineDefinition("8---V1RN", "V1RN"),
    RoutineDefinition("9---V1PRSET", "V1PRSET"),
    RoutineDefinition("10---V1PRIE", "V1PRIE"),
    RoutineDefinition("11---V1PRFOR", "V1PRFOR"),
    RoutineDefinition("11.1---V1NUM", "V1NUM"),
    RoutineDefinition("17.1---V1FC", "V1FC"),
    RoutineDefinition("20.1---V1UO", "V1UO"),
    RoutineDefinition("35.1---V1BOA", "V1BOA"),
    RoutineDefinition("47.1---V1BOR", "V1BOR"),
    RoutineDefinition("84.1---V1BOL", "V1BOL"),
    RoutineDefinition("91---V1BOC", "V1BOC"),
    RoutineDefinition("91.1---V1FN", "V1FN"),
    RoutineDefinition("103.1---V1AC", "V1AC"),
    RoutineDefinition("107---V1LVN", "V1LVN"),
    RoutineDefinition("108---V1GVN", "V1GVN"),
    RoutineDefinition("109---V1DLA", "V1DLA"),
    RoutineDefinition("109.1---V1DLB", "V1DLB"),
    RoutineDefinition("112---V1DLC", "V1DLC"),
    RoutineDefinition("113---V1DGA", "V1DGA"),
    RoutineDefinition("113.1---V1DGB", "V1DGB"),
    RoutineDefinition("115.1---V1NR", "V1NR"),
    RoutineDefinition("118.1---V1NX", "V1NX"),
    RoutineDefinition("120.1---V1SET", "V1SET"),
    RoutineDefinition("122.1---V1GO", "V1GO"),
    RoutineDefinition("125.1---V1OV", "V1OV"),
    RoutineDefinition("127.1---V1DO", "V1DO"),
    RoutineDefinition("131.1---V1CALL", "V1CALL"),
    RoutineDefinition("133.1---V1IE", "V1IE"),
    RoutineDefinition("135.1---V1PC", "V1PC"),
    RoutineDefinition("138.1---V1FORA", "V1FORA"),
    RoutineDefinition("141.1---V1FORB", "V1FORB"),
    RoutineDefinition("143.1---V1FORC", "V1FORC"),
    RoutineDefinition("145.1---V1IDNM", "V1IDNM"),
    RoutineDefinition("149.1---V1IDGO", "V1IDGO"),
    RoutineDefinition("150.1---V1IDDO", "V1IDDO"),
    RoutineDefinition("152.1---V1IDARG", "V1IDARG"),
    RoutineDefinition("158.1---V1XECA", "V1XECA"),
    RoutineDefinition("161---V1XECB", "V1XECB"),
    RoutineDefinition("162---V1SEQ", "V1SEQ"),
    RoutineDefinition("162.1---V1PAT", "V1PAT"),
    RoutineDefinition("167---V1NST1", "V1NST1"),
    RoutineDefinition("168---V1NST2", "V1NST2"),
    RoutineDefinition("169---V1NST3", "V1NST3"),
    RoutineDefinition("169.1---V1JST", "V1JST"),
    RoutineDefinition("176---V1SVH", "V1SVH"),
    RoutineDefinition("177---V1SVS", "V1SVS"),
    RoutineDefinition("177.1---V1MAX", "V1MAX"),
    RoutineDefinition("181---V1BR", "V1BR"),
    RoutineDefinition("188.1---V1HANG", "V1HANG"),
    RoutineDefinition("191---V1PO", "V1PO"),
    RoutineDefinition("192---V1RANDA", "V1RANDA"),
    RoutineDefinition("193---V1RANDB", "V1RANDB"),
]

# VV2 sub-drivers (Part 84 - Extended tests)
MVTS_VV2_ROUTINES: list[RoutineDefinition] = [
    RoutineDefinition("1---V2CS", "V2CS"),
    RoutineDefinition("2---V2LCC1", "V2LCC1"),
    RoutineDefinition("3---V2LCC2", "V2LCC2"),
    RoutineDefinition("4---V2LCF1", "V2LCF1"),
    RoutineDefinition("5---V2LCF2", "V2LCF2"),
    RoutineDefinition("6---V2LCF3", "V2LCF3"),
    RoutineDefinition("7---V2LCF4", "V2LCF4"),
    RoutineDefinition("8---V2FN1", "V2FN1"),
    RoutineDefinition("9---V2FN2", "V2FN2"),
    RoutineDefinition("10---V2LHP1", "V2LHP1"),
    RoutineDefinition("11---V2LHP2", "V2LHP2"),
    RoutineDefinition("12---V2LHP3", "V2LHP3"),
    RoutineDefinition("13---V2LHP4", "V2LHP4"),
    RoutineDefinition("14---V2VNIA", "V2VNIA"),
    RoutineDefinition("15---V2VNIB", "V2VNIB"),
    RoutineDefinition("16---V2VNIC", "V2VNIC"),
    RoutineDefinition("17---V2NR", "V2NR"),
    RoutineDefinition("19---V2PAT1", "V2PAT1"),
    RoutineDefinition("20---V2PAT2", "V2PAT2"),
    RoutineDefinition("21---V2PAT3", "V2PAT3"),
    RoutineDefinition("22---V2PAT4", "V2PAT4"),
    RoutineDefinition("23---V2NO1", "V2NO1"),
    RoutineDefinition("24---V2NO2", "V2NO2"),
    RoutineDefinition("25---V2SSUB1", "V2SSUB1"),
    RoutineDefinition("26---V2SSUB2", "V2SSUB2"),
]

# VV3 sub-drivers (Part 95 - Extended tests)
MVTS_VV3_ROUTINES: list[RoutineDefinition] = [
    RoutineDefinition("0.1---V3GET", "V3GET"),
    RoutineDefinition("6.1---V3TR", "V3TR"),
    RoutineDefinition("17.1---V3TEXT", "V3TEXT"),
    RoutineDefinition("20.1---V3FOR", "V3FOR"),
    RoutineDefinition("22.1---V3HANG", "V3HANG"),
    RoutineDefinition("25.1---V3MAX", "V3MAX"),
    RoutineDefinition("28---V3NST1", "V3NST1"),
    RoutineDefinition("29---V3NST2", "V3NST2"),
    RoutineDefinition("30---V3NST3", "V3NST3"),
    RoutineDefinition("31---V3SVS", "V3SVS"),
    RoutineDefinition("31.1---V3SSUB", "V3SSUB"),
    RoutineDefinition("34---V3JOB", "V3JOB"),
    RoutineDefinition("34.1---V3LOCK", "V3LOCK"),
    RoutineDefinition("37---V3INDNM", "V3INDNM"),
    RoutineDefinition("37.1---V3QUERY", "V3QUERY"),
    RoutineDefinition("43.1---V3FN2", "V3FN2"),
    RoutineDefinition("65.1---V3FN3", "V3FN3"),
    RoutineDefinition("70.1---V3NEW", "V3NEW"),
    RoutineDefinition("136---V3FP", "V3FP"),
    RoutineDefinition("137---V3DWP", "V3DWP"),
    RoutineDefinition("138---V3ESV", "V3ESV"),
    RoutineDefinition("139---V3EF", "V3EF"),
    RoutineDefinition("139.1---V3CBR", "V3CBR"),
]

# VV4 sub-drivers (Part 95 continued)
MVTS_VV4_ROUTINES: list[RoutineDefinition] = [
    RoutineDefinition("0.1---V4SORT", "V4SORT"),
    RoutineDefinition("10.1---V4FNUM", "V4FNUM"),
    RoutineDefinition("18.1---V4REV", "V4REV"),
    RoutineDefinition("22.1---V4GET2", "V4GET2"),
    RoutineDefinition("31.1---V4NAME", "V4NAME"),
    RoutineDefinition("45.1---V4QLEN", "V4QLEN"),
    RoutineDefinition("53.1---V4QSUB", "V4QSUB"),
    RoutineDefinition("68.1---V4SVQ", "V4SVQ"),
    RoutineDefinition("74.1---V4MERGE", "V4MERGE"),
    RoutineDefinition("97---V4KEY", "V4KEY"),
    RoutineDefinition("98---V4SYSTEM", "V4SYSTEM"),
    RoutineDefinition("98.1---V4POWER", "V4POWER"),
    RoutineDefinition("107---V4RAND", "V4RAND"),
    RoutineDefinition("107.1---V4ORDER", "V4ORDER"),
    RoutineDefinition("118---V4QUERY", "V4QUERY"),
    RoutineDefinition("119---V4PRIN", "V4PRIN"),
    RoutineDefinition("120---V4QUIT", "V4QUIT"),
    RoutineDefinition("120.1---V4MAX", "V4MAX"),
    RoutineDefinition("122.1---V4SSUB", "V4SSUB"),
    RoutineDefinition("125---V4JOB", "V4JOB"),
    RoutineDefinition("125.1---V4PAT", "V4PAT"),
    RoutineDefinition("135---V4NST1", "V4NST1"),
    RoutineDefinition("136---V4NST2", "V4NST2"),
    RoutineDefinition("137---V4NST3", "V4NST3"),
    RoutineDefinition("138---V4NST4", "V4NST4"),
    RoutineDefinition("139---V4NST5", "V4NST5"),
    RoutineDefinition("140---V4NST6", "V4NST6"),
    RoutineDefinition("141---V4MDC", "V4MDC"),
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

# Sub-test definitions with their primary test routines
MERGE_SUBTESTS: list[RoutineDefinition] = [
    # Basic merge operations
    RoutineDefinition("gbl2gbl", "mbyexam"),
    RoutineDefinition("gbl2lcl", "mbyexam"),
    RoutineDefinition("lcl2gbl", "mbyexam"),
    RoutineDefinition("lcl2lcl", "mbyexam"),
    # Error handling
    RoutineDefinition("errors", "errors"),
    # Extended global tests
    RoutineDefinition("extgbl1", "extgbl1"),
    RoutineDefinition("extgbl2", "extgbl2"),
    # Collation tests
    RoutineDefinition("gblcol", "gblcol"),
    RoutineDefinition("lclcol", "lclcol"),
    RoutineDefinition("polgblcol", "gblcol"),
    RoutineDefinition("pollclcol", "lclcol"),
    # Indirection tests
    RoutineDefinition("indirection", "MINDR1"),
    # Miscellaneous
    RoutineDefinition("falsedsc", "falsedsc"),
    RoutineDefinition("misclv", "mergelv"),
    RoutineDefinition("mrgclnup", "mrgclnup"),
    RoutineDefinition("nullsubs", "nullfill"),
    # MVTS merge tests
    RoutineDefinition("MVTS_MERGE", "V4MERGE"),
    # Transaction processing tests
    RoutineDefinition("tp_simple", "MRGITP"),
    RoutineDefinition("tp_stress", "mrgstp"),
    # Unicode merge tests
    RoutineDefinition("ugbl2gbl", "mbyexam"),
    RoutineDefinition("ugbl2lcl", "mbyexam"),
    RoutineDefinition("ulcl2gbl", "mbyexam"),
    RoutineDefinition("ulcl2lcl", "mbyexam"),
    # ZSHOW tests
    RoutineDefinition("zshowgbl", "list"),
    RoutineDefinition("zshowlcl", "list"),
]

# Individual merge routines (for direct testing if needed)
MERGE_ROUTINES: list[RoutineDefinition] = [
    RoutineDefinition("mbyexam", "mbyexam"),  # Basic merge examples
    RoutineDefinition("errors", "errors"),  # Error condition tests
    RoutineDefinition("extgbl1", "extgbl1"),  # Extended global 1
    RoutineDefinition("extgbl2", "extgbl2"),  # Extended global 2
    RoutineDefinition("falsedsc", "falsedsc"),  # False descriptor tests
    RoutineDefinition("gblcol", "gblcol"),  # Global collation
    RoutineDefinition("lclcol", "lclcol"),  # Local collation
    RoutineDefinition("mergelv", "mergelv"),  # Merge local variable
    RoutineDefinition("mrgclnup", "mrgclnup"),  # Merge cleanup
    RoutineDefinition("MRGITP", "MRGITP"),  # Merge in TP
    RoutineDefinition("mrgstp", "mrgstp"),  # Merge stress TP
    RoutineDefinition("MINDR1", "MINDR1"),  # Merge indirection 1
    RoutineDefinition("MINDR2", "MINDR2"),  # Merge indirection 2
    RoutineDefinition("MINDR3", "MINDR3"),  # Merge indirection 3
    RoutineDefinition("MINDR4", "MINDR4"),  # Merge indirection 4
    RoutineDefinition("MINDMISC", "MINDMISC"),  # Merge indirection misc
    RoutineDefinition("V4MERGE", "V4MERGE"),  # MVTS merge tests
    RoutineDefinition("list", "list"),  # List routine for ZSHOW
    RoutineDefinition("nullfill", "nullfill"),  # Null subscript fill
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
