"""Tests for READ command code generation (§8.2.17).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.17

Note: These stub tests were consolidated into test_s8_2_20_read.py which contains
comprehensive tests for READ command code generation (Spec 013 Phase 10).
- test_read_to_input -> test_basic_read_generates_input_call
- test_read_with_prompt -> test_read_with_prompt_generates_print_and_input
- test_read_timeout -> test_timeout_read_generates_correct_code
- test_read_single_char -> test_char_read_generates_m_read_char
"""
