#!/usr/bin/env python3
"""
Extract stub test file paths from tasks.md (Phases 1-7).

This utility parses the tasks.md file and extracts all test file paths
that should exist according to the spec-002 unit test organization plan.
"""

from pathlib import Path


# All stub test files from Phases 1-7 of tasks.md
# These are the canonical paths that MUST exist for spec compliance
REQUIRED_STUB_TEST_FILES: list[str] = [
    # Phase 2: Foundational files
    "tests/unit/STUB_TEMPLATE.py",
    "tests/unit/parser/conftest.py",
    "tests/unit/asg/conftest.py",
    "tests/unit/analysis/conftest.py",
    "tests/unit/codegen/conftest.py",
    # Phase 4: Parser Test Stubs (US1)
    # §5 Metalanguage (parser)
    "tests/unit/parser/s5_metalanguage/test_s5_1_bnf_notation.py",
    # §6 Routine Structure (parser)
    "tests/unit/parser/s6_routine/test_s6_1_routine_head.py",
    "tests/unit/parser/s6_routine/test_s6_2_routine_body.py",
    "tests/unit/parser/s6_routine/test_s6_3_1_indirection.py",
    "tests/unit/parser/s6_routine/test_s6_3_1_transaction.py",
    "tests/unit/parser/s6_routine/test_s6_3_2_error_processing.py",
    "tests/unit/parser/s6_routine/test_s6_3_4_event_processing.py",
    "tests/unit/parser/s6_routine/test_s6_4_embedded_programs.py",
    # §7 Expressions (parser)
    "tests/unit/parser/s7_expressions/test_s7_1_1_values.py",
    "tests/unit/parser/s7_expressions/test_s7_1_2_variables.py",
    "tests/unit/parser/s7_expressions/test_s7_1_3_ssvns.py",
    "tests/unit/parser/s7_expressions/test_s7_1_4_literals.py",
    "tests/unit/parser/s7_expressions/test_s7_1_5_intrinsic_functions.py",
    "tests/unit/parser/s7_expressions/test_s7_1_6_extrinsic_functions.py",
    "tests/unit/parser/s7_expressions/test_s7_1_7_special_variables.py",
    "tests/unit/parser/s7_expressions/test_s7_2_operators.py",
    "tests/unit/parser/s7_expressions/test_s7_2_5_pattern_match.py",
    "tests/unit/parser/s7_expressions/test_s7_3_indirection.py",
    # §8 Commands (parser)
    "tests/unit/parser/s8_commands/test_s8_1_general_rules.py",
    "tests/unit/parser/s8_commands/test_s8_2_01_break.py",
    "tests/unit/parser/s8_commands/test_s8_2_02_close.py",
    "tests/unit/parser/s8_commands/test_s8_2_03_do.py",
    "tests/unit/parser/s8_commands/test_s8_2_04_else.py",
    "tests/unit/parser/s8_commands/test_s8_2_05_for.py",
    "tests/unit/parser/s8_commands/test_s8_2_06_goto.py",
    "tests/unit/parser/s8_commands/test_s8_2_07_halt.py",
    "tests/unit/parser/s8_commands/test_s8_2_08_hang.py",
    "tests/unit/parser/s8_commands/test_s8_2_09_if.py",
    "tests/unit/parser/s8_commands/test_s8_2_10_job.py",
    "tests/unit/parser/s8_commands/test_s8_2_11_kill.py",
    "tests/unit/parser/s8_commands/test_s8_2_12_lock.py",
    "tests/unit/parser/s8_commands/test_s8_2_13_merge.py",
    "tests/unit/parser/s8_commands/test_s8_2_14_new.py",
    "tests/unit/parser/s8_commands/test_s8_2_15_open.py",
    "tests/unit/parser/s8_commands/test_s8_2_16_quit.py",
    "tests/unit/parser/s8_commands/test_s8_2_17_read.py",
    "tests/unit/parser/s8_commands/test_s8_2_18_set.py",
    "tests/unit/parser/s8_commands/test_s8_2_19_tcommit.py",
    "tests/unit/parser/s8_commands/test_s8_2_20_trestart.py",
    "tests/unit/parser/s8_commands/test_s8_ksubscripts.py",
    "tests/unit/parser/s8_commands/test_s8_2_21_trollback.py",
    "tests/unit/parser/s8_commands/test_s8_kvalue.py",
    "tests/unit/parser/s8_commands/test_s8_2_22_tstart.py",
    "tests/unit/parser/s8_commands/test_s8_2_23_use.py",
    "tests/unit/parser/s8_commands/test_s8_2_24_view.py",
    "tests/unit/parser/s8_commands/test_s8_2_25_write.py",
    "tests/unit/parser/s8_commands/test_s8_2_26_xecute.py",
    "tests/unit/parser/s8_commands/test_s8_2_27_zcommand.py",
    "tests/unit/parser/s8_commands/test_s8_3_device_params.py",
    "tests/unit/parser/s8_commands/test_s8_event_processing.py",
    "tests/unit/parser/s8_commands/test_s8_then_command.py",
    "tests/unit/parser/s8_commands/test_s8_assign.py",
    "tests/unit/parser/s8_commands/test_s8_2_28_rload.py",
    "tests/unit/parser/s8_commands/test_s8_2_29_rsave.py",
    # §9 Character Set (parser)
    "tests/unit/parser/s9_charset/test_s9_1_definitions.py",
    # Phase 5: ASG Test Stubs (US2)
    # §5 Metalanguage (ASG)
    "tests/unit/asg/s5_metalanguage/test_s5_1_bnf_notation.py",
    # §6 Routine Structure (ASG)
    "tests/unit/asg/s6_routine/test_s6_1_routine_head.py",
    "tests/unit/asg/s6_routine/test_s6_2_routine_body.py",
    "tests/unit/asg/s6_routine/test_s6_3_1_indirection.py",
    "tests/unit/asg/s6_routine/test_s6_3_1_transaction.py",
    "tests/unit/asg/s6_routine/test_s6_3_2_error_processing.py",
    "tests/unit/asg/s6_routine/test_s6_3_4_event_processing.py",
    "tests/unit/asg/s6_routine/test_s6_4_embedded_programs.py",
    # §7 Expressions (ASG)
    "tests/unit/asg/s7_expressions/test_s7_1_1_values.py",
    "tests/unit/asg/s7_expressions/test_s7_1_2_variables.py",
    "tests/unit/asg/s7_expressions/test_s7_1_3_ssvns.py",
    "tests/unit/asg/s7_expressions/test_s7_1_4_literals.py",
    "tests/unit/asg/s7_expressions/test_s7_1_5_intrinsic_functions.py",
    "tests/unit/asg/s7_expressions/test_s7_1_6_extrinsic_functions.py",
    "tests/unit/asg/s7_expressions/test_s7_1_7_special_variables.py",
    "tests/unit/asg/s7_expressions/test_s7_2_operators.py",
    "tests/unit/asg/s7_expressions/test_s7_2_5_pattern_match.py",
    "tests/unit/asg/s7_expressions/test_s7_3_indirection.py",
    # §8 Commands (ASG)
    "tests/unit/asg/s8_commands/test_s8_1_general_rules.py",
    "tests/unit/asg/s8_commands/test_s8_2_01_break.py",
    "tests/unit/asg/s8_commands/test_s8_2_02_close.py",
    "tests/unit/asg/s8_commands/test_s8_2_03_do.py",
    "tests/unit/asg/s8_commands/test_s8_2_04_else.py",
    "tests/unit/asg/s8_commands/test_s8_2_05_for.py",
    "tests/unit/asg/s8_commands/test_s8_2_06_goto.py",
    "tests/unit/asg/s8_commands/test_s8_2_07_halt.py",
    "tests/unit/asg/s8_commands/test_s8_2_08_hang.py",
    "tests/unit/asg/s8_commands/test_s8_2_09_if.py",
    "tests/unit/asg/s8_commands/test_s8_2_10_job.py",
    "tests/unit/asg/s8_commands/test_s8_2_11_kill.py",
    "tests/unit/asg/s8_commands/test_s8_2_12_lock.py",
    "tests/unit/asg/s8_commands/test_s8_2_13_merge.py",
    "tests/unit/asg/s8_commands/test_s8_2_14_new.py",
    "tests/unit/asg/s8_commands/test_s8_2_15_open.py",
    "tests/unit/asg/s8_commands/test_s8_2_16_quit.py",
    "tests/unit/asg/s8_commands/test_s8_2_17_read.py",
    "tests/unit/asg/s8_commands/test_s8_2_18_set.py",
    "tests/unit/asg/s8_commands/test_s8_2_19_tcommit.py",
    "tests/unit/asg/s8_commands/test_s8_2_20_trestart.py",
    "tests/unit/asg/s8_commands/test_s8_ksubscripts.py",
    "tests/unit/asg/s8_commands/test_s8_2_21_trollback.py",
    "tests/unit/asg/s8_commands/test_s8_kvalue.py",
    "tests/unit/asg/s8_commands/test_s8_2_22_tstart.py",
    "tests/unit/asg/s8_commands/test_s8_2_23_use.py",
    "tests/unit/asg/s8_commands/test_s8_2_24_view.py",
    "tests/unit/asg/s8_commands/test_s8_2_25_write.py",
    "tests/unit/asg/s8_commands/test_s8_2_26_xecute.py",
    "tests/unit/asg/s8_commands/test_s8_2_27_zcommand.py",
    "tests/unit/asg/s8_commands/test_s8_3_device_params.py",
    "tests/unit/asg/s8_commands/test_s8_event_processing.py",
    "tests/unit/asg/s8_commands/test_s8_then_command.py",
    "tests/unit/asg/s8_commands/test_s8_assign.py",
    "tests/unit/asg/s8_commands/test_s8_rload.py",
    "tests/unit/asg/s8_commands/test_s8_rsave.py",
    # §9 Character Set (ASG)
    "tests/unit/asg/s9_charset/test_s9_1_definitions.py",
    # Phase 6: Codegen Test Stubs (US7)
    # §5 Metalanguage (Codegen)
    "tests/unit/codegen/s5_metalanguage/test_s5_1_bnf_notation.py",
    # §6 Routine Structure (Codegen)
    "tests/unit/codegen/s6_routine/test_s6_1_routine_head.py",
    "tests/unit/codegen/s6_routine/test_s6_2_routine_body.py",
    "tests/unit/codegen/s6_routine/test_s6_3_1_indirection.py",
    "tests/unit/codegen/s6_routine/test_s6_3_1_transaction.py",
    "tests/unit/codegen/s6_routine/test_s6_3_2_error_processing.py",
    "tests/unit/codegen/s6_routine/test_s6_3_4_event_processing.py",
    "tests/unit/codegen/s6_routine/test_s6_4_embedded_programs.py",
    # §7 Expressions (Codegen)
    "tests/unit/codegen/s7_expressions/test_s7_1_1_values.py",
    "tests/unit/codegen/s7_expressions/test_s7_1_2_variables.py",
    "tests/unit/codegen/s7_expressions/test_s7_1_3_ssvns.py",
    "tests/unit/codegen/s7_expressions/test_s7_1_4_literals.py",
    "tests/unit/codegen/s7_expressions/test_s7_1_5_intrinsic_functions.py",
    "tests/unit/codegen/s7_expressions/test_s7_1_6_extrinsic_functions.py",
    "tests/unit/codegen/s7_expressions/test_s7_1_7_special_variables.py",
    "tests/unit/codegen/s7_expressions/test_s7_2_operators.py",
    "tests/unit/codegen/s7_expressions/test_s7_2_5_pattern_match.py",
    "tests/unit/codegen/s7_expressions/test_s7_3_indirection.py",
    # §8 Commands (Codegen)
    "tests/unit/codegen/s8_commands/test_s8_1_general_rules.py",
    "tests/unit/codegen/s8_commands/test_s8_2_01_break.py",
    "tests/unit/codegen/s8_commands/test_s8_2_02_close.py",
    "tests/unit/codegen/s8_commands/test_s8_2_03_do.py",
    "tests/unit/codegen/s8_commands/test_s8_2_04_else.py",
    "tests/unit/codegen/s8_commands/test_s8_2_05_for.py",
    "tests/unit/codegen/s8_commands/test_s8_2_06_goto.py",
    "tests/unit/codegen/s8_commands/test_s8_2_07_halt.py",
    "tests/unit/codegen/s8_commands/test_s8_2_08_hang.py",
    "tests/unit/codegen/s8_commands/test_s8_2_09_if.py",
    "tests/unit/codegen/s8_commands/test_s8_2_10_job.py",
    "tests/unit/codegen/s8_commands/test_s8_2_11_kill.py",
    "tests/unit/codegen/s8_commands/test_s8_2_12_lock.py",
    "tests/unit/codegen/s8_commands/test_s8_2_13_merge.py",
    "tests/unit/codegen/s8_commands/test_s8_2_14_new.py",
    "tests/unit/codegen/s8_commands/test_s8_2_15_open.py",
    "tests/unit/codegen/s8_commands/test_s8_2_16_quit.py",
    "tests/unit/codegen/s8_commands/test_s8_2_17_read.py",
    "tests/unit/codegen/s8_commands/test_s8_2_18_set.py",
    "tests/unit/codegen/s8_commands/test_s8_2_19_tcommit.py",
    "tests/unit/codegen/s8_commands/test_s8_2_20_trestart.py",
    "tests/unit/codegen/s8_commands/test_s8_ksubscripts.py",
    "tests/unit/codegen/s8_commands/test_s8_2_21_trollback.py",
    "tests/unit/codegen/s8_commands/test_s8_kvalue.py",
    "tests/unit/codegen/s8_commands/test_s8_2_22_tstart.py",
    "tests/unit/codegen/s8_commands/test_s8_2_23_use.py",
    "tests/unit/codegen/s8_commands/test_s8_2_24_view.py",
    "tests/unit/codegen/s8_commands/test_s8_2_25_write.py",
    "tests/unit/codegen/s8_commands/test_s8_2_26_xecute.py",
    "tests/unit/codegen/s8_commands/test_s8_2_27_zcommand.py",
    "tests/unit/codegen/s8_commands/test_s8_3_device_params.py",
    "tests/unit/codegen/s8_commands/test_s8_event_processing.py",
    "tests/unit/codegen/s8_commands/test_s8_then_command.py",
    "tests/unit/codegen/s8_commands/test_s8_assign.py",
    "tests/unit/codegen/s8_commands/test_s8_2_28_rload.py",
    "tests/unit/codegen/s8_commands/test_s8_2_29_rsave.py",
    # §9 Character Set (Codegen)
    "tests/unit/codegen/s9_charset/test_s9_1_definitions.py",
    # Phase 7: YottaDB Z-Command Stubs (US5)
    # Z-Command Parser Stubs
    "tests/unit/parser/extensions/ydb/test_zbreak.py",
    "tests/unit/parser/extensions/ydb/test_zcompile.py",
    "tests/unit/parser/extensions/ydb/test_zcontinue.py",
    "tests/unit/parser/extensions/ydb/test_zgoto.py",
    "tests/unit/parser/extensions/ydb/test_zlink.py",
    "tests/unit/parser/extensions/ydb/test_zmessage.py",
    "tests/unit/parser/extensions/ydb/test_zprint.py",
    "tests/unit/parser/extensions/ydb/test_zshow.py",
    "tests/unit/parser/extensions/ydb/test_zstep.py",
    "tests/unit/parser/extensions/ydb/test_zsystem.py",
    "tests/unit/parser/extensions/ydb/test_zwrite.py",
    "tests/unit/parser/extensions/ydb/test_zhelp.py",
    "tests/unit/parser/extensions/ydb/test_zkill.py",
    "tests/unit/parser/extensions/ydb/test_zhalt.py",
    "tests/unit/parser/extensions/ydb/test_zallocate.py",
    "tests/unit/parser/extensions/ydb/test_ztrigger.py",
    "tests/unit/parser/extensions/ydb/test_zedit.py",
    "tests/unit/parser/extensions/ydb/test_zfunctions.py",
    # Z-Command ASG Stubs
    "tests/unit/asg/extensions/ydb/test_zbreak.py",
    "tests/unit/asg/extensions/ydb/test_zgoto.py",
    "tests/unit/asg/extensions/ydb/test_zlink.py",
    "tests/unit/asg/extensions/ydb/test_zwrite.py",
    "tests/unit/asg/extensions/ydb/test_zkill.py",
    "tests/unit/asg/extensions/ydb/test_zhalt.py",
    "tests/unit/asg/extensions/ydb/test_zallocate.py",
    "tests/unit/asg/extensions/ydb/test_ztrigger.py",
    "tests/unit/asg/extensions/ydb/test_zedit.py",
    "tests/unit/asg/extensions/ydb/test_zhelp.py",
    "tests/unit/asg/extensions/ydb/test_zfunctions.py",
    # Z-Command Codegen Stubs
    "tests/unit/codegen/extensions/ydb/test_zbreak.py",
    "tests/unit/codegen/extensions/ydb/test_zgoto.py",
    "tests/unit/codegen/extensions/ydb/test_zlink.py",
    "tests/unit/codegen/extensions/ydb/test_zsystem.py",
    "tests/unit/codegen/extensions/ydb/test_zwrite.py",
    "tests/unit/codegen/extensions/ydb/test_zhelp.py",
    "tests/unit/codegen/extensions/ydb/test_zkill.py",
    "tests/unit/codegen/extensions/ydb/test_zhalt.py",
    "tests/unit/codegen/extensions/ydb/test_zallocate.py",
    "tests/unit/codegen/extensions/ydb/test_ztrigger.py",
    "tests/unit/codegen/extensions/ydb/test_zedit.py",
    "tests/unit/codegen/extensions/ydb/test_zcompile.py",
    "tests/unit/codegen/extensions/ydb/test_zcontinue.py",
    "tests/unit/codegen/extensions/ydb/test_zmessage.py",
    "tests/unit/codegen/extensions/ydb/test_zprint.py",
    "tests/unit/codegen/extensions/ydb/test_zshow.py",
    "tests/unit/codegen/extensions/ydb/test_zstep.py",
    "tests/unit/codegen/extensions/ydb/test_zfunctions.py",
]


def get_project_root() -> Path:
    """Get the project root directory."""
    # Start from this file's directory and go up until we find pyproject.toml
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find project root (no pyproject.toml found)")


def check_stub_files_exist(
    project_root: Path | None = None,
) -> tuple[list[str], list[str]]:
    """
    Check which stub test files exist.

    Returns:
        Tuple of (existing_files, missing_files) as relative paths
    """
    if project_root is None:
        project_root = get_project_root()

    existing = []
    missing = []

    for rel_path in REQUIRED_STUB_TEST_FILES:
        full_path = project_root / rel_path
        if full_path.exists():
            existing.append(rel_path)
        else:
            missing.append(rel_path)

    return existing, missing


def main() -> int:
    """Main entry point for the utility."""

    project_root = get_project_root()
    existing, missing = check_stub_files_exist(project_root)

    print(f"Project root: {project_root}")
    print(f"Total required stub files: {len(REQUIRED_STUB_TEST_FILES)}")
    print(f"Existing: {len(existing)}")
    print(f"Missing: {len(missing)}")

    if missing:
        print("\n❌ Missing stub test files:")
        for path in sorted(missing):
            print(f"  - {path}")
        return 1
    else:
        print("\n✅ All stub test files are present!")
        return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
