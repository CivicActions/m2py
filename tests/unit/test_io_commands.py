# MIGRATED: Phase 8 test organization - 2025-07
#
# All tests from this file have been migrated to spec-aligned locations:
#
# OPEN command tests (test_open_*, TestOpenStatementASG):
#   → tests/unit/asg/s8_commands/test_s8_2_15_open.py
#
# CLOSE command tests (test_close_*, TestCloseStatementASG):
#   → tests/unit/asg/s8_commands/test_s8_2_02_close.py
#
# USE command tests (test_use_*, TestUseStatementASG):
#   → tests/unit/asg/s8_commands/test_s8_2_23_use.py
#
# JOB command tests (test_job_*, TestJobIndirection, TestJobTimeoutAndProcessParameters):
#   → tests/unit/asg/s8_commands/test_s8_2_10_job.py
#
# MERGE command tests (TestMergeCommand, TestMergeStatementASG):
#   → tests/unit/asg/s8_commands/test_s8_2_13_merge.py
#
# VIEW command tests (TestViewCommand, TestViewStatementASG):
#   → tests/unit/asg/s8_commands/test_s8_2_24_view.py
#
# LOCK command tests (TestLockCommand, TestLockStatementASG):
#   → tests/unit/asg/s8_commands/test_s8_2_12_lock.py
#
# test_io_commands_with_postconditions:
#   → tests/unit/asg/s8_commands/test_s8_2_15_open.py (TestOpenStatementASG.test_open_command_with_postcondition)
#   (postconditions are tested per-command in each destination file)
