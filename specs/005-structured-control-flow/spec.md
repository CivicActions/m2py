# Feature Specification: Structured Control Flow

**Feature Branch**: `005-structured-control-flow`  
**Created**: 2026-01-09  
**Status**: Draft  
**Input**: Spec 005 from codegen-plan.md - Structured Control Flow

## Overview

This specification extends the code generation infrastructure from Spec 004 to handle common structured control flow patterns that map to Python constructs. The focus is on:

1. **$TEST tracking with stack semantics** - Correct save/restore behavior for argumentless DO and extrinsics
2. **FOR loop variations** - All loop types based on analysis flags
3. **Intra-label GOTO** - Restructuring within a single label
4. **Loop exits** - break patterns and multi-loop exits
5. **QUIT context awareness** - Using ASG-provided exit flags
6. **Variable scope strategies** - Generating Python based on ScopeStrategy classification
7. **By-reference parameters** - Return-tuple pattern for modified params

This spec handles control flow that stays within structured patterns. Cross-label GOTO requiring state machines or trampolines is deferred to Spec 006.

## Pre-requisites from Spec 004

The following infrastructure is now available:

- Module-level `_test` variable with `global _test` declarations in each function
- `m_truth()` helper for condition evaluation in IF statements
- Labels as Python functions callable via `LABEL()` / `return LABEL()`
- `NameTranslator` for variable/label name translation (handles %, numeric, reserved words)
- `MUMPSRuntime.execute()` with isolated namespace injection
- `CodeEmitter` class for indent-aware code generation
- Basic FOR loop generation (`F I=1:1:10` -> `for` loop, `F I="A","B"` -> list iteration)
- Basic GOTO as function call + return (no restructuring)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - $TEST Stack Semantics for Argumentless DO (Priority: P1)

As a developer, when I generate Python from MUMPS code with argumentless DO calls, the `$TEST` special variable is correctly saved before the call and restored after QUIT, so that subsequent ELSE statements see the correct condition value.

**Why this priority**: $TEST semantics are fundamental to correct IF/ELSE behavior across subroutine boundaries. Getting this wrong breaks any code that checks ELSE after a DO call. This is the highest risk area because many real M programs depend on this behavior.

**Independent Test**: Can be tested by generating and executing code with IF/DO/ELSE sequences that rely on $TEST restoration.

**Acceptance Scenarios**:

1. **Given** `TEST I 1 D SUB E W "BAD" Q SUB I 0 Q`, **When** generated and executed, **Then** output is empty (ELSE should NOT execute because $TEST was 1 before DO, restored after)
2. **Given** `TEST I 0 D SUB E W "GOOD" Q SUB I 0 Q`, **When** generated and executed, **Then** output is "GOOD" (ELSE executes because $TEST was 0 before DO, restored after)
3. **Given** nested calls `TEST I 1 D A E W "OUTER" Q A D B Q B I 0 Q`, **When** generated, **Then** outer ELSE sees restored $TEST=1 (not B's $TEST=0)

---

### User Story 2 - $TEST NOT Stacked for DO with Arguments (Priority: P1)

As a developer, when I generate Python from MUMPS code with DO calls that pass arguments, the `$TEST` changes made by the callee are visible to the caller, following MUMPS semantics.

**Why this priority**: This is the critical distinction from argumentless DO. Many VistA patterns use DO with arguments specifically to communicate $TEST state back to the caller. Getting this wrong inverts the expected behavior.

**Independent Test**: Can be tested by generating and executing code where the called routine sets $TEST and the caller uses ELSE afterward.

**Acceptance Scenarios**:

1. **Given** `TEST I 1 D SUB(1) E W "ELSE" Q SUB(X) I 0 Q`, **When** generated and executed, **Then** output is "ELSE" ($TEST=0 from callee IS visible to caller)
2. **Given** `TEST I 0 D SUB(1) E W "ELSE" Q SUB(X) I 1 Q`, **When** generated and executed, **Then** output is empty ($TEST=1 from callee, ELSE doesn't execute)

---

### User Story 3 - FOR Loop Variations Based on Analysis (Priority: P1)

As a developer, the code generator correctly handles all FOR loop types by consulting the analysis flags (`loop_type`, `loop_var_modified_in_body`, `has_internal_quit`) and generating the appropriate Python pattern.

**Why this priority**: FOR loops are ubiquitous in MUMPS code. The basic bounded loop from Spec 004 only covers simple cases. Real code uses open-ended loops, argumentless loops, mixed parameters, and modifies loop variables. Incorrect generation causes infinite loops or wrong iteration counts.

**Independent Test**: Can be tested by executing generated code for each loop type and verifying iteration behavior.

**Acceptance Scenarios**:

1. **Given** `TEST F I=1:1 W I Q:I=5`, **When** generated and executed, **Then** output is "12345" (open-ended with QUIT)
2. **Given** `TEST S X=3 F D Q:X=0 . S X=X-1 . W X`, **When** generated and executed, **Then** output is "210" (argumentless with DO block)
3. **Given** `TEST F I=1:1:3,"X",10:2:14 W I`, **When** generated and executed, **Then** output is "123X101214" (mixed parameters)
4. **Given** `TEST F I=1:1:10 S I=I+2 W I Q:I>8`, **When** generated and executed, **Then** output is "369" (loop var modified -> while loop)

---

### User Story 4 - Intra-Label GOTO Restructuring (Priority: P2)

As a developer, when I generate Python from MUMPS code containing GOTO statements within the same label, the code generator restructures them to if/else chains or continue statements rather than using function calls.

**Why this priority**: Intra-label GOTOs are common for early exit and skip patterns. Using function calls for these adds unnecessary overhead and prevents local Python optimizations. Restructuring to native control flow produces cleaner, faster Python.

**Independent Test**: Can be tested by verifying generated Python uses if/elif/else instead of function calls for same-label jumps.

**Acceptance Scenarios**:

1. **Given** `TEST S X=1 I X=1 G SKIP . W "A" SKIP W "B" Q` (forward jump within label), **When** generated, **Then** Python uses if/else structure (not function call)
2. **Given** `TEST F I=1:1:10 I I=5 G LOOP . W I LOOP Q` (continue to loop start), **When** generated and executed, **Then** output is "1234678910" (5 skipped via continue)

---

### User Story 5 - Loop Exit Translation (Priority: P2)

As a developer, when I generate Python from MUMPS GOTO statements that exit FOR loops, the code generator uses `break` for single loop exits and an exception pattern for multi-loop exits.

**Why this priority**: Many MUMPS programs use GOTO to exit loops when errors occur or conditions are met. Direct translation to break/exception patterns produces idiomatic Python and correct behavior.

**Independent Test**: Can be tested by executing generated code with loop-exiting GOTOs and verifying correct exit behavior.

**Acceptance Scenarios**:

1. **Given** `TEST F I=1:1:100 I I=5 G DONE . W I DONE W "!" Q`, **When** generated and executed, **Then** output is "1234!" (single loop exit -> break)
2. **Given** nested `TEST F I=1:1:3 F J=1:1:3 I I=2,J=2 G OUT . W I,J OUT W "X" Q`, **When** generated and executed, **Then** output is "1112X" (multi-loop exit -> exception pattern)

---

### User Story 6 - QUIT Context Awareness (Priority: P2)

As a developer, the code generator correctly interprets QUIT statements based on ASG context flags (`exits_for`, `exits_do_block`, `return_value`) to generate appropriate Python code.

**Why this priority**: QUIT has different meanings depending on context: break from FOR, return from DO block, or return value from extrinsic. The ASG already provides classification; codegen must use it correctly.

**Independent Test**: Can be tested by verifying QUIT generates break vs return based on context.

**Acceptance Scenarios**:

1. **Given** `TEST F I=1:1:10 Q:I=3 W I Q`, **When** generated and executed, **Then** output is "12" (QUIT with exits_for=True -> break)
2. **Given** `TEST D . W "A" . Q . W "B" W "C" Q`, **When** generated and executed, **Then** output is "AC" (QUIT with exits_do_block=True -> return from nested scope)
3. **Given** `TEST S R=$$ADD(2,3) W R Q ADD(A,B) Q A+B`, **When** generated and executed, **Then** output is "5" (QUIT with return_value -> return expression)

**Note**: This tests basic extrinsic return mechanics. Full extrinsic function support ($$label^routine, external calls) is Spec 008.

---

### User Story 7 - Variable Scope Strategy Code Generation (Priority: P2)

As a developer, the code generator uses `FunctionSignature.scope_strategy` to determine how to translate labels to Python functions, using appropriate patterns for PURE_FUNCTION, FUNCTION_WITH_OUTPUTS, and SUBROUTINE.

**Why this priority**: Different MUMPS patterns require different Python function signatures. Pure functions can be simple; functions with side effects need to return modified variables. This enables clean, Rope-refactorable Python output.

**Independent Test**: Can be tested by examining generated function signatures and return statements.

**Acceptance Scenarios**:

1. **Given** a label with `scope_strategy=PURE_FUNCTION` that returns a value, **When** generated, **Then** Python function returns the value directly
2. **Given** a label with `scope_strategy=SUBROUTINE` that modifies caller variables, **When** generated, **Then** Python function returns None (modifications handled separately)
3. **Given** a label with `scope_strategy=FUNCTION_WITH_OUTPUTS`, **When** generated, **Then** Python function returns tuple of (return_value, modified_outputs)

---

### User Story 8 - By-Reference Parameter Handling (Priority: P3)

As a developer, when I generate Python from MUMPS code that passes variables by reference (`.X`), the code generator uses a return-tuple pattern so that modifications made by the callee are visible to the caller.

**Why this priority**: Call-by-reference is common in MUMPS for output parameters. Without proper handling, modifications are lost. The return-tuple pattern enables this without runtime scope access.

**Independent Test**: Can be tested by passing variables by reference and verifying caller sees modifications.

**Acceptance Scenarios**:

1. **Given** `TEST S A=1,B=2 D SWAP(.A,.B) W A,B Q SWAP(X,Y) N T S T=X,X=Y,Y=T Q`, **When** generated and executed, **Then** output is "21" (A and B swapped)
2. **Given** `TEST S X=5 D INCR(.X) W X Q INCR(N) S N=N+1 Q`, **When** generated and executed, **Then** output is "6" (X incremented via by-ref)
3. **Given** `TEST S X=0 D CNT(.X) D CNT(.X) W X Q CNT(N) S N=N+1 Q`, **When** generated and executed, **Then** output is "2" (multiple by-ref calls accumulate)

---

### Edge Cases

- **Postconditions do NOT update $TEST**: `I X=1 S:Y=2 Z=1 E W "NO"` - the postcondition Y=2 is evaluated but doesn't change $TEST; ELSE sees original IF result
- **Argumentless IF uses prior $TEST**: `I X I W "YES"` - second IF has no condition, uses $TEST from first IF
- **Zero step FOR**: `F I=1:0` creates infinite loop - must use `while True` (no increment)
- **Negative step bounds**: `F I=10:-1:1` should iterate 10,9,8,...,1 (inclusive)
- **Empty FOR body**: `F I=1:1:3 W I` vs `F I=1:1:3 D . W I` - both valid, different scoping
- **QUIT without FOR context**: `Q` in label body returns from label, not break
- **Multiple by-ref to same variable**: `D FOO(.A,.A)` - aliasing edge case (may require REQUIRES_RUNTIME)

**Edge cases explicitly deferred to later specs**:
- $TEST behavior with XECUTE -> Spec 007
- Cross-label GOTO requiring state machine -> Spec 006
- REQUIRES_RUNTIME scope strategy -> Spec 006/007
- Extrinsic functions ($$label) with full semantics -> Spec 008

## Requirements *(mandatory)*

### Functional Requirements

#### $TEST Tracking

- **FR-001**: System MUST save $TEST value before argumentless DO calls and restore it after QUIT
- **FR-002**: System MUST NOT save/restore $TEST for DO calls with arguments (mutations visible to caller)
- **FR-003**: System MUST save/restore $TEST for extrinsic function calls ($$label) - stacked per ANSI spec
- **FR-004**: Postconditions MUST NOT update $TEST - only IF command conditions update $TEST
- **FR-005**: Argumentless IF (`I `) MUST use the existing $TEST value as its condition

#### FOR Loop Translation

- **FR-006**: System MUST generate `while True` loop for `ForLoopType.OPEN_ENDED` with explicit step increment
- **FR-007**: System MUST generate `while True` loop for `ForLoopType.ARGUMENTLESS`
- **FR-008**: System MUST generate `for x in [...]` loop for `ForLoopType.STRING_LIST`
- **FR-009**: System MUST generate `itertools.chain` or unrolled loop for `ForLoopType.MIXED` parameters
- **FR-010**: System MUST use `while` loop (not `for`) when `loop_var_modified_in_body=True`
- **FR-011**: System MUST emit `break` capability when `has_internal_quit=True`
- **FR-012**: System MUST use inclusive end bound for MUMPS ranges (1:1:10 includes 10)

#### Intra-Label GOTO

- **FR-013**: System MUST restructure **forward** jumps within same label (`is_cross_label=False`, `goto_type=FORWARD_JUMP`) to if/else chains
- **FR-014**: System MUST translate `is_loop_continue=True` GOTO to Python `continue` statement
- **FR-014b**: System MUST raise UnsupportedFeatureError for backward intra-label GOTO (`goto_type=BACKWARD_JUMP`, `is_cross_label=False`) - deferred to Spec 006
- **FR-015**: Intra-label restructuring MUST preserve execution order of intermediate statements

#### Loop Exits

- **FR-016**: System MUST translate `GotoType.LOOP_EXIT` to Python `break` statement
- **FR-017**: System MUST translate `GotoType.MULTI_LOOP_EXIT` to exception-based exit pattern
- **FR-018**: System MUST set flag/execute target code after multi-loop exit

#### QUIT Context

- **FR-019**: System MUST generate `break` when `MQuitStatement.exits_for=True`
- **FR-020**: System MUST generate appropriate return when `MQuitStatement.exits_do_block=True`
- **FR-021**: System MUST generate `return <value>` when `MQuitStatement.return_value` is present
- **FR-022**: System MUST recognize postconditioned QUIT (`Q:cond`) syntax but MAY defer codegen to Spec 008 (postconditions)

#### Variable Scope Strategies

- **FR-023**: System MUST generate simple return for `ScopeStrategy.PURE_FUNCTION`
- **FR-024**: System MUST generate return-tuple for `ScopeStrategy.FUNCTION_WITH_OUTPUTS`
- **FR-025**: System MUST generate return None (implicit) for `ScopeStrategy.SUBROUTINE`
- **FR-026**: System MUST defer to Spec 006/007 for `ScopeStrategy.REQUIRES_RUNTIME`

#### By-Reference Parameters

- **FR-027**: System MUST track formal parameters in `byref_outputs` that are modified by callee
- **FR-028**: System MUST generate return-tuple pattern for labels with non-empty `byref_outputs`
- **FR-029**: Caller code MUST destructure returned tuple to update by-ref variables
- **FR-030**: System MUST handle mixed by-ref and by-value parameters in same call

### Key Entities

- **MIfStatement.conditions**: List of conditions with AND semantics for comma-separated
- **MQuitStatement.exits_for**: Boolean - True if this QUIT exits a FOR loop
- **MQuitStatement.exits_do_block**: Boolean - True if this QUIT exits a DO block
- **MQuitStatement.return_value**: Optional expression for extrinsic return
- **MForStatement.loop_type**: ForLoopType enum - classification of loop structure
- **MForStatement.loop_var_modified_in_body**: Boolean - requires while loop
- **MForStatement.has_internal_quit**: Boolean - needs break support
- **MForStatement.has_internal_goto**: Boolean - GOTO exits this loop
- **MForStatement.exit_points**: List of MGotoStatements that exit this loop
- **MGotoStatement.goto_type**: GotoType enum - classification of jump
- **MGotoStatement.is_cross_label**: Boolean - True if target in different label
- **MGotoStatement.is_loop_continue**: Boolean - True for continue semantics
- **MGotoStatement.exits_loops**: List of MForStatements exited by this GOTO
- **FunctionSignature.scope_strategy**: ScopeStrategy enum
- **FunctionSignature.byref_outputs**: Set of formal params actually modified
- **FunctionSignature.transitive_inputs/outputs**: Including callee dependencies

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of $TEST stack semantics test cases match YDB reference output
- **SC-002**: All FOR loop types (open-ended, argumentless, string-list, mixed, modified-var) execute with correct iteration count
- **SC-003**: Intra-label GOTO restructuring produces Python that does NOT use function calls for same-label jumps
- **SC-004**: Loop exit patterns (break, exception) produce same control flow as YDB
- **SC-005**: QUIT in FOR context generates break; QUIT in DO context generates return
- **SC-006**: By-reference parameter modifications are visible to caller in 100% of test cases
- **SC-007**: Generated Python passes `ast.parse()` validation for all inputs
- **SC-008**: Test suite achieves at least 85% code coverage on new codegen additions

## Assumptions

- Spec 004 infrastructure is complete and functioning (labels as functions, _test variable, m_truth())
- Analysis passes (for_analysis, goto_analysis, variables analysis) have been run and populated all classification fields
- `is_cross_label=False` for all GOTOs handled in this spec (cross-label deferred to Spec 006)
- `ScopeStrategy.REQUIRES_RUNTIME` labels will raise UnsupportedFeatureError (deferred to Spec 006/007)
- Extrinsic function syntax (`$$label`) parsing is complete; this spec handles $TEST stack only
- Postcondition parsing exists in ASG; this spec tests that postconditions do NOT update $TEST but defers postcondition codegen to Spec 008

## Explicitly Deferred

The following are explicitly **out of scope** for Spec 005:

- **Cross-label GOTO** (`is_cross_label=True`) -> Spec 006
- **Backward intra-label GOTO** (creates implicit loops within label) -> Spec 006
- **State machine or trampoline patterns** -> Spec 006
- **Line-based dispatch for computed offsets** (`G LABEL+expr`) -> Spec 006/008
- **REQUIRES_RUNTIME scope strategy** (indirection/XECUTE defeats analysis) -> Spec 006/007
- **XECUTE command** -> Spec 007
- **Indirection** (`@VAR`) -> Spec 007
- **Global variables** (`^name`) -> Spec 008
- **Intrinsic functions** ($PIECE, $LENGTH, etc.) -> Spec 008
- **Full extrinsic function support** ($$label^routine, parameter semantics) -> Spec 008
- **External routine calls** (D LABEL^ROUTINE) -> Spec 009
- **NEW / KILL commands** -> Spec 008
- **Postconditions** (S:cond X=1) - parsing exists, codegen deferred -> Spec 008

## Research Phase

Review before implementing:

- **Docs**: `docs/analysis/for_analysis.md`, `docs/analysis/goto_analysis.md`, `docs/codegen/for_loops.md`, `docs/analysis/variable_analysis.md`
- **FOR analysis**: `analysis/for_analysis.py` -> `ForLoopType`, `loop_var_modified_in_body`, `has_internal_quit`
- **GOTO analysis**: `analysis/goto_analysis.py` -> `GotoType`, `is_cross_label`, `is_loop_continue`
- **Scope**: `analysis/variables.py` -> `FunctionSignature`, `ScopeStrategy`, `input_variables`, `output_variables`, `byref_outputs`
- **QUIT**: `asg/statements.py` -> `MQuitStatement.exits_for`, `.exits_do_block`, `.return_value`
- **Current $TEST**: `codegen/statements.py` and `codegen/routine.py` -> current `_test` handling
- **ASG dump**: `uv run python utils/validate_asg.py --compact tests/functional/mugj/inref/V1FOR*.m`

### Key Implementation Questions (To Answer in Research Phase)

1. **$TEST stacking mechanism**: Current `_test` is module-level. Options:
   - Pass `_test` as hidden parameter, restore on return
   - Thread-local stack for $TEST values  
   - Context manager pattern: `with _test_context(): DO_LABEL()`
   - Return tuple including saved $TEST

2. **By-reference pattern**: How to handle return-tuple at call sites:
   - Single return: `A, B = SWAP(A, B)`
   - Mixed returns: `result, A = FUNC(X, .A, Z)` - positional mapping

3. **FOR variable visibility**: After FOR loop, is loop variable visible?
   - Answer: Yes, MUMPS loop var survives loop exit with final value

### Spike: $TEST Elimination

**Hypothesis**: Many IF/ELSE chains can be restructured to eliminate explicit `_test` tracking.

**Test**: Create minimal IF/ELSE/argumentless-IF test case, translate with explicit `_test`, then attempt restructuring. Measure:
- How many `_test` references remain?
- Is restructured code clearer?

**Decision**: If >80% eliminable, make restructuring the default. Otherwise, always use `_test`.
