#!/usr/bin/env python3
"""Analyze failing functional tests and categorize by root cause."""

import json
import subprocess
import sys


def run_single_test(test_name: str, suite: str) -> dict:
    """Run a single test and capture its error."""
    test_path = f"tests/functional/test_{suite}.py::Test{suite.title()}Suite::test_routine[{test_name}]"
    result = subprocess.run(
        ["uv", "run", "pytest", test_path, "-v", "--tb=short", "-x"],
        capture_output=True,
        text=True,
        timeout=120,
    )

    output = result.stdout + result.stderr

    # Categorize by error type
    error_info = {
        "test": test_name,
        "suite": suite,
        "category": "UNKNOWN",
        "error": None,
        "details": None,
    }

    # Check for specific error patterns
    if "NotImplementedError: Special variable $ZPOSITION" in output:
        error_info["category"] = "Z_EXTENSION"
        error_info["error"] = "$ZPOSITION not supported"
    elif "NotImplementedError: Special variable $i not yet supported" in output:
        error_info["category"] = "Z_EXTENSION"
        error_info["error"] = "$I (for-loop index) not supported"
    elif "NotImplementedError: Unsupported expression type: MGlobal" in output:
        error_info["category"] = "MGLOBAL_EXPR"
        error_info["error"] = "MGlobal as expression not supported"
    elif "UnsupportedFeatureError: UNRESOLVED GOTO" in output:
        error_info["category"] = "UNRESOLVED_GOTO"
        error_info["error"] = "Unresolved GOTO target"
    elif "Execution timed out" in output:
        error_info["category"] = "TIMEOUT"
        error_info["error"] = "Execution timed out"
    elif "failed to execute: None" in output:
        error_info["category"] = "EXECUTION_ERROR"
        error_info["error"] = "Execution failed with no error message"
    elif "Output mismatch" in output:
        # Look for specific patterns in the diff
        if "@@ -0,0 +1 @@" in output and any(
            f"+{test_name}" in output or f"+{test_name[:-1]}1" in output for _ in [1]
        ):
            # Output is just the driver name - means helper routine not found
            error_info["category"] = "HELPER_ROUTINE"
            error_info["error"] = "External routine call failed (helper not loaded)"
        elif "0.001" in output and ".001" in output:
            error_info["category"] = "SUBSCRIPT_FORMAT"
            error_info["error"] = "Subscript/number formatting (0.001 vs .001)"
        elif (
            "$FNUMBER" in output.upper()
            or "+1234567.89" in output
            or "1234568+" in output
        ):
            error_info["category"] = "FUNCTION_BUG"
            error_info["error"] = "$FNUMBER trailing sign issue"
        elif "** FAIL" in output:
            # Check for specific function bugs
            if "0.8900" in output and ".89" in output:
                error_info["category"] = "SUBSCRIPT_FORMAT"
                error_info["error"] = "Trailing zeros on decimals"
            elif "COMPUTED" in output and "CORRECT" in output:
                error_info["category"] = "OUTPUT_MISMATCH"
                error_info["error"] = "Value computation mismatch"
        elif "-END OF" in output or "No errors detected" in output:
            # Missing parts of output at the end
            error_info["category"] = "INCOMPLETE_OUTPUT"
            error_info["error"] = "Output incomplete (external calls or IO)"
        else:
            error_info["category"] = "OUTPUT_MISMATCH"
            error_info["error"] = "Output differs from expected"

    # Extract more details
    if "Diff:" in output:
        diff_start = output.find("Diff:")
        diff_end = output.find("=======", diff_start)
        if diff_end > diff_start:
            error_info["details"] = output[diff_start:diff_end][:500]

    return error_info


def main():
    # List of failing tests from basic suite
    basic_tests = [
        "new",
        "kill1",
        "xecute",
        "globals",
        "text4",
        "ebmuldiv",
        "per02457",
        "extcall",
        "expr2",
        "locals",
        "cmptst",
        "largeexp2",
        "largeexp3",
        "miscdb",
        "stpfail",
        "putfail",
        "per02397",
        "iowrite",
        "larray",
    ]

    # List of failing tests from mugj suite
    mugj_tests = [
        "V1LL1",
        "V1LL2",
        "V1PRGD",
        "V1RN",
        "V1OV",
        "V1BOB",
        "V1NUM",
        "V1DO",
        "V1BOC",
        "V1SEQ",
        "V1FC",
        "V1CALL",
        "V1FN",
        "V1UO",
        "VV2LCF2",
        "V1IE",
        "V1PAT",
        "V1BOA",
        "V1PC",
        "V1LVN",
        "VV2FN1",
        "V1NST1",
        "V1FORA",
        "VV2FN2",
        "V1NST2",
        "V1FORB",
        "V1DLA",
        "VV2LHP1",
        "V1NST3",
        "V1FORC",
        "V1DLB",
        "VV2LHP2",
        "V1IDNM",
        "V1JST",
        "V1IDGO",
        "V1SVH",
        "VV2VNIA",
        "V1IDDO",
        "V1DGA",
        "V1IDARG",
        "V1DGB",
        "V1MAX",
        "VV2VNIB",
        "V1XECA",
        "V1NR",
        "V1BR",
        "VV2VNIC",
        "V1NX",
        "V1XECB",
        "VV2NR",
        "V1SET",
        "VV2PAT1",
        "V1GO",
        "VV2PAT3",
        "VV2LCC1",
        "VV2LCC2",
        "VV2LCF1",
        "VV2NO",
        "VV2SS1",
        "VV2SS2",
    ]

    results = []

    print("Analyzing basic suite tests...", file=sys.stderr)
    for test in basic_tests:
        print(f"  {test}...", file=sys.stderr)
        try:
            result = run_single_test(test, "basic")
            results.append(result)
        except Exception as e:
            results.append(
                {
                    "test": test,
                    "suite": "basic",
                    "category": "ERROR",
                    "error": str(e),
                }
            )

    print("Analyzing mugj suite tests...", file=sys.stderr)
    for test in mugj_tests:
        print(f"  {test}...", file=sys.stderr)
        try:
            result = run_single_test(test, "mugj")
            results.append(result)
        except Exception as e:
            results.append(
                {
                    "test": test,
                    "suite": "mugj",
                    "category": "ERROR",
                    "error": str(e),
                }
            )

    # Categorize results
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(
            {
                "test": r["test"],
                "suite": r["suite"],
                "error": r["error"],
            }
        )

    # Output as JSON
    output = {
        "total_failures": len(results),
        "categories": {
            cat: {
                "count": len(tests),
                "tests": tests,
            }
            for cat, tests in sorted(categories.items())
        },
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
