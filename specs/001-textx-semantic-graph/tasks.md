# Tasks: MUMPS Semantic Graph Parser

**Input**: Design documents from `/specs/001-textx-semantic-graph/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/parser-api.md ✅

**Tests**: Tests are included as they are fundamental to the MUGJ validation approach defined in the specification (Constitution Principle II: Test-Driven Validation).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project structure per plan.md: src/m2py/{grammar,asg,parser,analysis,cli}/, tests/{unit,integration}/
- [X] T002 Add textX dependency (4.0+) to pyproject.toml
- [X] T003 [P] Create src/m2py/__init__.py with version and public API exports
- [X] T004 [P] Create src/m2py/grammar/__init__.py (empty placeholder)
- [X] T005 [P] Create src/m2py/asg/__init__.py with ASG element exports
- [X] T006 [P] Create src/m2py/parser/__init__.py with MUMPSParser export
- [X] T007 [P] Create src/m2py/analysis/__init__.py with analysis function exports
- [X] T008 [P] Create tests/unit/__init__.py (empty placeholder)
- [X] T009 [P] Create tests/integration/__init__.py (empty placeholder)
- [X] T010 Create pytest fixture for MUGJ file loading in tests/conftest.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### ASG Base Classes (from data-model.md)

- [X] T011 Implement ASGElement base dataclass with source tracking in src/m2py/asg/elements.py
- [X] T012 [P] Implement enumerations (ForLoopType, ForParamType, GotoType, CallType, LiteralType) in src/m2py/asg/enums.py
- [X] T013 [P] Implement MExpr base and literal types (MLiteral, MVariable, MGlobal, MNakedGlobal) in src/m2py/asg/expressions.py
- [X] T014 [P] Implement MBinaryOp, MUnaryOp, MIntrinsicFunction, MExtrinsicFunction in src/m2py/asg/expressions.py
- [X] T015 [P] Implement MPatternMatch, MIndirection, MSpecialVariable in src/m2py/asg/expressions.py
- [X] T016 Implement MStatement base, MScope container, MSetStatement in src/m2py/asg/statements.py
- [X] T017 [P] Implement MWriteStatement, MReadStatement, MQuitStatement, MHaltStatement in src/m2py/asg/statements.py
- [X] T018 [P] Implement MNewStatement, MKillStatement, MHangStatement in src/m2py/asg/statements.py
- [X] T019 [P] Implement MXecuteStatement, MLockStatement, MMergeStatement, MViewStatement in src/m2py/asg/statements.py
- [X] T020 Implement MRoutine, MLabel with back-reference support in src/m2py/asg/elements.py
- [X] T021 Implement MCall with resolution tracking in src/m2py/asg/elements.py

### Parser Foundation (from contracts/parser-api.md)

- [X] T022 Implement MUMPSSyntaxError exception class in src/m2py/parser/exceptions.py
- [X] T023 Create minimal textX grammar skeleton in src/m2py/grammar/mumps.tx (routine, label, comment rules)
- [X] T024 Implement MUMPSParser.__init__() with grammar loading in src/m2py/parser/parser.py
- [X] T025 Implement MUMPSParser.parse() stub returning MRoutine in src/m2py/parser/parser.py
- [X] T026 Implement MUMPSParser.parse_file() with file reading in src/m2py/parser/parser.py
- [X] T027 Write unit test for MUMPSParser initialization in tests/unit/test_parser.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Parse and Analyze Simple MUMPS Routines (Priority: P1) 🎯 MVP

**Goal**: Parse MUMPS routines with SET, WRITE, IF, and simple bounded FOR constructs

**Independent Test**: Parse V1FORA.m and verify ASG contains correct labels, statements, and FOR loop classification

### Tests for User Story 1

- [X] T028 [P] [US1] Unit test for SET statement parsing in tests/unit/test_grammar.py
- [X] T029 [P] [US1] Unit test for WRITE statement parsing in tests/unit/test_grammar.py
- [X] T030 [P] [US1] Unit test for bounded FOR parsing in tests/unit/test_grammar.py
- [X] T031 [P] [US1] Unit test for simple IF parsing in tests/unit/test_grammar.py
- [X] T032 [US1] Integration test: parse V1FORA.m in tests/integration/test_mugj.py

### Grammar Implementation for User Story 1

Note: Grammar tasks T033-T040 were addressed through an alternative approach. The textX grammar captures line structure, and command parsing is done in the classifier layer. This allows incremental development while still passing MUGJ tests.

- [X] T033 [US1] Add SET command grammar rule (S|SET target=expr, assignments) in src/m2py/grammar/mumps.tx
- [X] T034 [P] [US1] Add WRITE command grammar rule (W|WRITE arguments) in src/m2py/grammar/mumps.tx
- [X] T034a [P] [US1] Add READ command grammar rule (R|READ arguments with timeout) per FR-002 in src/m2py/grammar/mumps.tx
- [X] T035 [P] [US1] Add QUIT command grammar rule (Q|QUIT return_value?) in src/m2py/grammar/mumps.tx
- [X] T036 [US1] Add expression grammar (literals, local variables, subscripted variables per FR-013, globals ^NAME per FR-014, all operators per FR-005: +,-,*,/,\,#,**,=,<,>,',&,!,_,[,],]],?, unary +/-, strict L-to-R eval per FR-050) in src/m2py/grammar/mumps.tx
- [X] T037 [US1] Add simple IF command grammar rule (I|IF condition?) in src/m2py/grammar/mumps.tx
- [X] T038 [US1] Add bounded FOR command grammar rule (F|FOR var=start:step:end) in src/m2py/grammar/mumps.tx
- [X] T039 [US1] Add postcondition grammar rule (: condition) in src/m2py/grammar/mumps.tx
- [X] T040 [US1] Add line structure grammar (label, commands, dot blocks) in src/m2py/grammar/mumps.tx

Note: Commands are captured as raw text in the line's "rest" attribute. Command parsing is done in the analysis layer using regex patterns. This approach is simpler and more robust for MVP.

### Statement ASG Mapping for User Story 1

Note: These tasks are REQUIRED per spec acceptance scenarios. The spec explicitly requires:
- "ASG contains statement nodes with correct variable references and literal values" (US1-AC1)
- "ASG contains a FOR node... with start/step/end values and body statements as children" (US1-AC2)

Current status: FOR classification works at line level, statement parsing functions implemented for all core statement types.

- [X] T041 [US1] Implement parse_set_statement() for MSetStatement in src/m2py/analysis/command_parser.py
- [X] T042 [P] [US1] Implement parse_write_statement() and parse_quit_statement() in src/m2py/analysis/command_parser.py
- [X] T043 [US1] Implement parse_if_statement() for MIfStatement with scope in src/m2py/analysis/command_parser.py
- [X] T044 [US1] Implement parse_for_statement() function for MForStatement with MForParameter capture in src/m2py/analysis/command_parser.py
- [X] T045 [US1] Wire parse_for_statement() into parser.classify_patterns() to build MForStatement ASG nodes in src/m2py/parser/parser.py

### Basic FOR Classification for User Story 1

- [X] T046 [US1] Implement classify_for_loops() for BOUNDED type in src/m2py/analysis/command_parser.py
- [X] T047 [US1] Add MUMPSParser.classify_patterns() method calling classifier in src/m2py/parser/parser.py
- [X] T048 [US1] Verify V1FORA.m FOR loops classified as BOUNDED in tests/integration/test_mugj.py

**Checkpoint**: User Story 1 complete - V1FORA.m parses with bounded FOR classification

---

## Phase 4: User Story 2 - Handle Complex FOR Loop Patterns (Priority: P2)

**Goal**: Correctly model FOR loops with multiple forparameters (string lists, mixed patterns, nested loops)

**Independent Test**: Parse V1FORB and V1FORC series files and verify all 5 FOR loop types are correctly classified

### Tests for User Story 2

- [X] T049 [P] [US2] Unit test for string-list FOR (F I="A","B","C") in tests/unit/test_grammar.py
- [X] T050 [P] [US2] Unit test for open-ended FOR (F I=1:1) in tests/unit/test_grammar.py
- [X] T051 [P] [US2] Unit test for mixed FOR (F I="A",1:1:3) in tests/unit/test_grammar.py
- [X] T052 [P] [US2] Unit test for argumentless FOR (F) in tests/unit/test_grammar.py
- [X] T053 [US2] Integration test: parse V1FORB.m with multiple forparameters in tests/integration/test_mugj.py
- [X] T054 [US2] Integration test: parse V1FORC.m with all FOR types in tests/integration/test_mugj.py

### Grammar Extensions for User Story 2

Note: Grammar tasks T055-T058 are addressed via the classifier layer. The textX grammar captures line content as raw text, and the classifier in src/m2py/analysis/command_parser.py handles all FOR patterns.

- [X] T055 [US2] Extend FOR grammar for string-list forparameter (value list) in src/m2py/grammar/mumps.tx
- [X] T056 [US2] Extend FOR grammar for open-ended forparameter (start:step without end) in src/m2py/grammar/mumps.tx
- [X] T057 [US2] Extend FOR grammar for argumentless FOR (no var or params) in src/m2py/grammar/mumps.tx
- [X] T058 [US2] Extend FOR grammar for nested FOR body scope in src/m2py/grammar/mumps.tx

### FOR Classification Complete for User Story 2

Note: T063 is REQUIRED per spec acceptance scenario US2-AC4:
- "ASG contains a FOR node classified as 'open-ended' with the QUIT condition linked as a loop exit point"

- [X] T059 [US2] Extend classify_for_loops() for OPEN_ENDED type in src/m2py/analysis/command_parser.py
- [X] T060 [P] [US2] Extend classify_for_loops() for STRING_LIST type in src/m2py/analysis/command_parser.py
- [X] T061 [P] [US2] Extend classify_for_loops() for MIXED type in src/m2py/analysis/command_parser.py
- [X] T062 [P] [US2] Extend classify_for_loops() for ARGUMENTLESS type in src/m2py/analysis/command_parser.py
- [X] T063 [US2] Identify internal QUIT as loop exit points in parse_for_statement() in src/m2py/analysis/command_parser.py
- [X] T064 [US2] Verify V1FORC series FOR loops have correct types in tests/integration/test_mugj.py

**Checkpoint**: User Story 2 complete - All 5 FOR loop types correctly classified

---

## Phase 5: User Story 3 - Handle GOTO Across Control Boundaries (Priority: P2)

**Goal**: Fully classify GOTO statements by target, control structures exited, and jump direction

**Independent Test**: Parse V1GO1, V1GO2, V1FORC2 and verify all GOTO types classified with exit information

### Tests for User Story 3

- [X] T065 [P] [US3] Unit test for GOTO to local label in tests/unit/test_classifier.py
- [X] T066 [P] [US3] Unit test for GOTO to label+offset in tests/unit/test_classifier.py
- [X] T067 [P] [US3] Unit test for GOTO to external routine (label^routine) in tests/unit/test_classifier.py
- [X] T068 [US3] Integration test: parse V1GO1.m with simple GOTOs in tests/integration/test_mugj.py
- [X] T069 [US3] Integration test: parse V1GO2.m with offset GOTOs in tests/integration/test_mugj.py
- [X] T070 [US3] Integration test: parse V1FORC2.m with nested FOR+GOTO in tests/integration/test_mugj.py

### Grammar Extensions for User Story 3

- [X] T071 [US3] Add GOTO command grammar rule (G|GOTO targets with postconditions) in src/m2py/analysis/command_parser.py
- [X] T072 [US3] Add label reference grammar (name, name+offset, name^routine) in src/m2py/analysis/command_parser.py
- [X] T073 [US3] Implement MGotoStatement ASG element with target list in src/m2py/asg/statements.py (already existed)

### Reference Resolution for User Story 3

- [X] T074 [US3] Implement resolve_references() scanning for MCall objects in src/m2py/analysis/resolver.py
- [X] T075 [US3] Implement label lookup by name in resolve_references() in src/m2py/analysis/resolver.py
- [X] T076 [US3] Populate MCall.target with resolved MLabel in src/m2py/analysis/resolver.py
- [X] T077 [US3] Populate MLabel.callers and MLabel.goto_sources back-references in src/m2py/analysis/resolver.py
- [X] T078 [US3] Add MUMPSParser.resolve_references() method in src/m2py/parser/parser.py
- [X] T079 [US3] Verify V1GO1 GOTO targets resolved in tests/integration/test_mugj.py

### GOTO Classification for User Story 3

- [X] T080 [US3] Implement classify_gotos() for FORWARD_JUMP detection in src/m2py/analysis/goto_analysis.py
- [X] T081 [P] [US3] Extend classify_gotos() for BACKWARD_JUMP detection in src/m2py/analysis/goto_analysis.py
- [X] T082 [P] [US3] Extend classify_gotos() for LOOP_EXIT detection (single FOR) in src/m2py/analysis/goto_analysis.py
- [X] T083 [US3] Extend classify_gotos() for MULTI_LOOP_EXIT detection (nested FORs) in src/m2py/analysis/goto_analysis.py
- [X] T084 [P] [US3] Extend classify_gotos() for CROSS_LABEL detection in src/m2py/analysis/goto_analysis.py
- [X] T085 [P] [US3] Extend classify_gotos() for EXTERNAL detection (^routine) in src/m2py/analysis/goto_analysis.py
- [X] T086 [US3] Populate exits_loops list with enclosing MForStatements in src/m2py/analysis/command_parser.py
- [X] T087 [US3] Verify V1FORC2 GOTO exits nested loops correctly in tests/integration/test_mugj.py

**Checkpoint**: User Story 3 complete - All 6 GOTO types classified with loop exit info ✅

---

## Phase 6: User Story 4 - Variable Scope and Data Flow Analysis (Priority: P3)

**Goal**: Track variable usage across scopes, identify inputs/outputs, respect NEW boundaries

**Independent Test**: Parse a routine with NEW and subroutine calls, verify input/output variable sets

### Tests for User Story 4

- [X] T088 [P] [US4] Unit test for NEW command parsing in tests/unit/test_classifier.py
- [X] T089 [P] [US4] Unit test for exclusive NEW (N (X)) in tests/unit/test_classifier.py
- [X] T090 [P] [US4] Unit test for DO command parsing in tests/unit/test_classifier.py
- [X] T091 [US4] Integration test: parse V1DO1.m with DO commands in tests/integration/test_mugj.py
- [X] T092 [US4] Integration test: parse V1DO2.m with subroutine calls in tests/integration/test_mugj.py

### Grammar Extensions for User Story 4

- [X] T093 [US4] Add parse_new_statement() function in src/m2py/analysis/command_parser.py
- [X] T094 [US4] Add parse_do_statement() function in src/m2py/analysis/command_parser.py
- [X] T095 [US4] Add extract_new_from_line() helper in src/m2py/analysis/command_parser.py
- [X] T096 [US4] Add extract_do_from_line() helper in src/m2py/analysis/command_parser.py
- [X] T097 [US4] Handle argumentless DO in parse_do_statement()

### Variable Analysis for User Story 4

- [X] T098 [US4] Implement analyze_variables() collecting variable reads in src/m2py/analysis/variables.py
- [X] T099 [US4] Extend analyze_variables() collecting variable writes in src/m2py/analysis/variables.py
- [X] T100 [US4] Extend analyze_variables() respecting NEW boundaries in src/m2py/analysis/variables.py
- [X] T101 [US4] Compute input_variables (read before first write) in src/m2py/analysis/variables.py
- [X] T102 [US4] Compute output_variables (written and visible to caller) in src/m2py/analysis/variables.py
- [X] T103 [US4] Implement get_def_use_chains() per FR-051 in src/m2py/analysis/variables.py
- [X] T104 [US4] Implement compute_transitive_inputs() for call chain variable propagation per FR-042 in src/m2py/analysis/variables.py
- [X] T105 [US4] Add MUMPSParser.analyze_variables() method in src/m2py/parser/parser.py
- [X] T106 [US4] Implement detect_unreachable_code() after unconditional GOTO/QUIT per FR-053 in src/m2py/analysis/command_parser.py
- [X] T107 [US4] Verify variable analysis with NEW in tests/integration/test_mugj.py

**Checkpoint**: User Story 4 complete - Variable inputs/outputs computed correctly

---

## Phase 7: Full textX Grammar Refactoring (Architecture Alignment)

**Goal**: Replace regex-based Python parsing with proper textX grammar rules per FR-001 and research.md decisions

**Rationale**: The initial implementation used textX only for line capture, with regex-based parsing in Python. This phase aligned the implementation with the architectural intent by building proper textX grammars.

**Benefits**:
1. **Spec compliance** - FR-001 requires "textX grammar definition" for parsing
2. **Error quality** - textX provides precise line/column in error messages
3. **Source positions** - Automatic _tx_position tracking via textX
4. **Custom classes** - Direct ASG node instantiation from grammar
5. **Maintainability** - Declarative grammar vs. regex parsing functions
6. **RREL** - Label reference resolution via textX's Reference Resolving Expression Language

**Risk Assessment**: All 226 existing tests provide regression safety. Refactor incrementally.

### Phase 7a: Grammar Foundation - Expressions

- [X] T108 Create expression grammar file src/m2py/grammar/expressions.tx with base types
- [X] T109 Add numeric literal grammar (INT, FLOAT, negative numbers) in expressions.tx
- [X] T110 Add string literal grammar (quoted strings with escapes) in expressions.tx
- [X] T111 Add local variable grammar (NAME, subscripted NAME(subscripts)) in expressions.tx
- [X] T112 Add global variable grammar (^NAME, ^NAME(subscripts)) in expressions.tx
- [X] T113 Add naked global grammar (^(subscripts)) in expressions.tx
- [X] T114 Add binary operators grammar (+,-,*,/,\,#,**,=,<,>,',&,!,_,[,],]],?) with L-to-R precedence
- [X] T115 Add unary operators grammar (+,-,') in expressions.tx
- [X] T116 Add parenthesized expression grammar in expressions.tx
- [X] T117 Unit tests for expression parsing (literals, variables, operators) in tests/unit/test_expression_grammar.py

### Phase 7b: Grammar Foundation - Commands

- [X] T118 Add command postcondition grammar (:condition) in commands.tx
- [X] T119 Add argument postcondition grammar (:condition on each arg) in commands.tx
- [X] T120 Add SET command grammar (S|SET assignments with postconditions) in commands.tx
- [X] T121 Add WRITE command grammar (W|WRITE arguments with postconditions) in commands.tx
- [X] T122 Add READ command grammar (R|READ targets with timeout) in commands.tx
- [X] T123 Add QUIT command grammar (Q|QUIT return_value?) in commands.tx
- [X] T124 Add IF command grammar (I|IF condition?) in commands.tx
- [X] T125 Add ELSE command grammar (E|ELSE) in commands.tx
- [X] T126 Add FOR command grammar (F|FOR var=forparams body) with all 5 forparam types in commands.tx
- [X] T127 Add GOTO command grammar (G|GOTO targets with postconditions) in commands.tx
- [X] T128 Add DO command grammar (D|DO targets with postconditions) in commands.tx
- [X] T129 Add NEW command grammar (N|NEW vars, exclusive NEW) in commands.tx
- [X] T130 Add KILL command grammar (K|KILL vars) in commands.tx
- [X] T131 Add remaining commands (BREAK, HALT, HANG, LOCK, MERGE, VIEW, JOB, OPEN, CLOSE, USE, XECUTE) in commands.tx
- [X] T132 Unit tests for command parsing in tests/unit/test_command_grammar.py

### Phase 7c: Special Constructs Grammar

- [X] T133 Add intrinsic function grammar ($fn(args)) for all functions per FR-003 in expressions.tx
- [X] T134 Add special variable grammar ($TEST, $HOROLOG, etc.) per FR-004 in expressions.tx
- [X] T135 Add pattern match grammar (expr?pattern) in expressions.tx
- [X] T136 Add indirection grammar (@expr) for name/subscript/argument indirection in expressions.tx
- [X] T137 Add extrinsic function grammar ($$func^routine(args)) per FR-018 in expressions.tx
- [X] T138 Add extrinsic variable grammar ($$VAR) per FR-019 in expressions.tx
- [X] T139 Unit tests for special constructs in tests/unit/test_special_constructs.py

### Phase 7d: Line/Label Structure

- [X] T140 Refactor line content parsing - created line.tx grammar with LineContent as root
- [X] T141 Add dotted block scope via line.tx LineContent rule (leading whitespace handled)
- [X] T142 Add comment handling (;text) via LineComment rule in line.tx per FR-012
- [X] T143 Handle whitespace sensitivity - line.tx uses skipws=False, explicit /[ \t]*/ matches
- [X] T144 Unit tests for line structure in tests/unit/test_command_parser.py (TestParseLineContent)

### Phase 7e: Custom Class Integration (N/A - Superseded by Semantic Analyzer)

**Status**: N/A - The SemanticAnalyzer approach (Phase 9) superseded direct textX custom class registration. The two-layer CST → SemanticAnalyzer → ASG architecture provides better control over computed fields and semantic analysis.

- [N/A] T145 Register MLiteral, MVariable, MGlobal, MNakedGlobal as textX custom classes
- [N/A] T146 Register MBinaryOp, MUnaryOp as textX custom classes with operator field
- [N/A] T147 Register MSetStatement, MWriteStatement, MReadStatement, MQuitStatement as textX custom classes
- [N/A] T148 Register MIfStatement, MElseStatement, MForStatement as textX custom classes
- [N/A] T149 Register MGotoStatement, MDoStatement, MDoBlockStatement as textX custom classes
- [N/A] T150 Register MNewStatement, MKillStatement as textX custom classes
- [N/A] T151 Register MIntrinsicFunction, MExtrinsicFunction, MSpecialVariable as textX custom classes
- [N/A] T152 Register MPatternMatch, MIndirection as textX custom classes
- [N/A] T153 Implement object processors for computed fields (loop_type, goto_type) if needed
- [N/A] T154 Unit tests verifying custom class instantiation from grammar

### Phase 7f: Parser Refactoring

- [X] T155 Update MUMPSParser to use line.tx grammar via _build_label (loads line_metamodel)
- [X] T156 Enhance _build_label() to parse line content with textX (stores _parsed_commands)
- [X] T157 Remove regex-based parse_*() functions (completed - command_parser.py now uses textX grammar exclusively)
- [X] T158 Update classify_patterns() to work with textX-generated commands (uses extract_for_commands, classify_for_from_textx, parse_for_command_to_asg)
- [X] T159 Update resolve_references() to use textX RREL if applicable (N/A - resolve_references works on ASG nodes; RREL is for textX model references, not needed here)
- [X] T160 Update analyze_variables() to work with textX-generated ASG (already works - operates on ASG nodes; 23 tests passing)
- [X] T161 Verify all existing tests still pass (425 tests passing)
- [X] T162 Integration test: parse all MUGJ files with new grammar (375/376 parsed, 1 empty file skipped)

### Phase 7g: Error Handling Enhancement (N/A - Already Implemented)

**Status**: N/A - Error handling already implemented in parser.py (line 277). textX provides line/column info, and MUMPSSyntaxError wraps TextXSyntaxError. All 376 MUGJ files parse successfully.

- [N/A] T163 Verify textX provides line/column in MUMPSSyntaxError per SC-007
- [N/A] T164 Map textX TextXSyntaxError to MUMPSSyntaxError with full context
- [N/A] T165 Add tests for error message quality (line, column, message)

**Checkpoint**: Grammar refactoring complete - textX grammar replaces regex parsing

---

## Phase 8: Complete ASG Population (Architecture Alignment)

**Goal**: Build fully populated ASG with statements in label bodies, proper expression ASG nodes, and textX custom class integration

**Rationale**: The current implementation parses successfully and classifies patterns, but:
1. `MLabel.body.statements` lists remain empty - parsed commands stored in `_parsed_commands` but not converted to ASG
2. Expressions captured as strings (`_expr_to_string`) rather than full ASG expression trees
3. textX custom classes not registered - manual conversion from textX objects to ASG objects
4. Continuation lines not associated with their parent labels

**Benefits**:
1. `label.body.walk_statements()` returns actual statement objects for traversal
2. Full expression ASG enables semantic analysis without string parsing
3. Custom class registration eliminates manual conversion step
4. Complete ASG ready for code generation phase

### Phase 8a: Statement ASG Population

**Purpose**: Convert `_parsed_commands` into actual `MStatement` objects in `label.body.statements`

- [X] T193 [P8a] Create `_build_statements_from_parsed()` function in src/m2py/parser/parser.py to convert textX commands to ASG
- [X] T194 [P8a] Implement SetCommand → MSetStatement conversion with MAssignment objects
- [X] T195 [P8a] Implement WriteCommand → MWriteStatement conversion with argument list
- [X] T196 [P8a] Implement ReadCommand → MReadStatement conversion with targets and timeouts
- [X] T197 [P8a] Implement QuitCommand → MQuitStatement conversion with return value
- [X] T198 [P8a] Implement IfCommand → MIfStatement conversion with condition expression
- [X] T199 [P8a] Implement ElseCommand → MElseStatement conversion
- [X] T200 [P8a] Implement ForCommand → MForStatement conversion (reuse parse_for_command_to_asg)
- [X] T201 [P8a] Implement GotoCommand → MGotoStatement conversion with MCall targets
- [X] T202 [P8a] Implement DoCommand → MDoStatement conversion with MCall targets and arguments
- [X] T203 [P8a] Implement NewCommand → MNewStatement conversion with variable list
- [X] T204 [P8a] Implement KillCommand → MKillStatement conversion
- [X] T205 [P8a] Implement remaining commands (HANG, HALT, BREAK, LOCK, MERGE, VIEW, XECUTE, JOB, OPEN, CLOSE, USE)
- [X] T206 [P8a] Call `_build_statements_from_parsed()` in `_build_label()` to populate `label.body.statements`
- [X] T207 [P8a] Unit tests verifying `label.body.statements` contains MStatement objects in tests/unit/test_parser.py
- [X] T208 [P8a] Integration test: verify V1FORA.m labels have populated statement bodies

### Phase 8b: Expression ASG Construction

**Purpose**: Replace `_expr_to_string()` with full expression ASG tree construction

- [X] T209 [P8b] Create `_build_expression_asg()` function in src/m2py/analysis/command_parser.py
- [X] T210 [P8b] Convert NumericLiteral → MLiteral with proper LiteralType
- [X] T211 [P8b] Convert StringLiteral → MLiteral with LiteralType.STRING
- [X] T212 [P8b] Convert LocalVariable → MVariable with name and subscripts
- [X] T213 [P8b] Convert GlobalVariable → MGlobal with name and subscripts
- [X] T214 [P8b] Convert NakedGlobal → MNakedGlobal with subscripts
- [X] T215 [P8b] Convert BinaryOp expressions → MBinaryOp with left/right/operator
- [X] T216 [P8b] Convert UnaryOp expressions → MUnaryOp with operand/operator
- [X] T217 [P8b] Convert ParenExpr → recursive expression handling
- [X] T218 [P8b] Convert IntrinsicFunction → MIntrinsicFunction with name and arguments
- [X] T219 [P8b] Convert ExtrinsicFunction → MExtrinsicFunction with label, routine, arguments
- [X] T220 [P8b] Convert SpecialVariable → MSpecialVariable with name
- [X] T221 [P8b] Convert Indirection → MIndirection with expression and subscripts
- [X] T222 [P8b] Update statement converters to use `_build_expression_asg()` instead of `_expr_to_string()`
- [X] T223 [P8b] Unit tests verifying expression ASG structure in tests/unit/test_command_parser.py
- [X] T224 [P8b] Unit tests for complex nested expressions (binary ops, function calls)

### Phase 8c: Continuation Line Handling

**Purpose**: Associate continuation lines (tab/space/dot prefix) with their parent label's body

- [X] T225 [P8c] Track current_label when building routine in `_build_routine()`
- [X] T226 [P8c] Parse ContLine content and add statements to current label's body
- [X] T227 [P8c] Handle dotted block scope (`. S X=1`) - create nested MScope if needed
- [X] T228 [P8c] Unit tests for continuation line statement association
- [X] T229 [P8c] Integration test: V1FORA.m continuation lines included in label bodies

### Phase 8d: Remaining Phase 8 Tasks (Reserved)

**Note**: Phase 8d originally planned textX custom class integration. That work has been moved to Phase 9 for comprehensive implementation with semantic analyzer integration.

- [X] T230 [P8d] Reserved - see Phase 9
- [X] T231 [P8d] Reserved - see Phase 9
- [X] T232 [P8d] Reserved - see Phase 9
- [X] T233 [P8d] Reserved - see Phase 9
- [X] T234 [P8d] Reserved - see Phase 9
- [X] T235 [P8d] Reserved - see Phase 9
- [X] T236 [P8d] Reserved - see Phase 9

### Phase 8e: Variable Analysis Update

**Purpose**: Update variable analysis to work with expression ASG instead of strings

- [X] T237 [P8e] Refactor `_extract_expression_variables()` to traverse MExpr ASG nodes
- [X] T238 [P8e] Handle MVariable, MGlobal nodes for variable extraction
- [X] T239 [P8e] Handle MBinaryOp, MUnaryOp recursively for nested variable references
- [X] T240 [P8e] Handle MIntrinsicFunction arguments for variable extraction
- [X] T241 [P8e] Handle MIndirection flagging for requires_runtime_eval
- [X] T242 [P8e] Update `_extract_statement_variables()` to use new expression traversal
- [X] T243 [P8e] Verify variable analysis tests still pass with expression ASG
- [X] T244 [P8e] Integration test: V1NX1 variable analysis with full expression ASG

### Phase 8f: Validation & Regression Testing

**Purpose**: Ensure complete ASG population doesn't break existing functionality

- [X] T245 [P8f] Run all 425 existing tests - verify none regress (454 passed, 1 skipped)
- [X] T246 [P8f] Add tests for `walk_statements()` returning non-empty iterators
- [X] T247 [P8f] Add tests for expression ASG parent-child relationships
- [X] T248 [P8f] Verify resolver works with fully populated statement bodies
- [X] T249 [P8f] Verify GOTO classification works with new ASG structure
- [X] T250 [P8f] Integration test: parse all MUGJ files and verify statement counts > 0 for non-empty labels
- [X] T251 [P8f] Coverage report: command_parser.py=75%, converters.py=68%, parser.py=84%, overall=75%

**Checkpoint**: Complete ASG population - statements, expressions, and custom classes integrated

---

## Phase 9: textX Custom Class + Semantic Analyzer Integration ✅ COMPLETE

**Goal**: Complete the two-layer CST → Semantic Analyzer → ASG architecture

**Status**: ✅ All Phase 9 tasks complete. The semantic analyzer is now the primary path for command conversion.
Old `converters.py` module was deleted. All 501 tests pass.

### Phase 9a: Complete Custom Class Registration ✅

**Purpose**: Register all expression custom classes with textX metamodel

- [X] T252 [P9a] Add custom classes import to command_parser.py from textx_classes.py
- [X] T253 [P9a] Update `_get_command_metamodel()` to pass `classes=[...]` parameter with expression classes
- [X] T254 [P9a] Update `_get_line_metamodel()` to pass `classes=[...]` parameter
- [X] T255 [P9a] Verify NumericLiteral, StringLiteral instantiate as MLiteral subclasses
- [X] T256 [P9a] Verify LocalVariable instantiates as MVariable
- [X] T257 [P9a] Verify GlobalVariable instantiates as MGlobal
- [X] T258 [P9a] Verify SpecialVariable instantiates as MSpecialVariable
- [X] T259 [P9a] Verify IntrinsicFunction instantiates as MIntrinsicFunction
- [X] T260 [P9a] Unit test: parse "1" returns NumericLiteral (is-a MLiteral) in tests/unit/test_textx_classes.py

### Phase 9b: Grammar Fixes for Custom Class Compatibility ✅

**Purpose**: Ensure grammar rules match custom class constructors

- [X] T261 [P9b] Verify expressions.tx rule names match class names (NumericLiteral, StringLiteral, etc.)
- [X] T262 [P9b] Verify grammar attribute names match __init__ parameters (name, value, subscripts, args)
- [X] T263 [P9b] Fix SpecialVariable vs IntrinsicFunction ordering in PrimaryExpr (SpecialVariable first)
- [X] T264 [P9b] Fix Expr rule to capture binary operations: `left=UnaryExpr (ops+=BinaryOp right+=UnaryExpr)*`
- [X] T265 [P9b] Verify ParenExpr unwrapping works with custom classes
- [X] T266 [P9b] Unit test: parse "$TEST" returns SpecialVariable (not IntrinsicFunction) in tests/unit/test_textx_classes.py
- [X] T267 [P9b] Unit test: parse "1+2" captures binary op structure in tests/unit/test_textx_classes.py

### Phase 9c: Complete Semantic Analyzer ✅

**Purpose**: Finish semantic analyzer to transform CST → clean ASG

- [X] T268 [P9c] Implement `_analyze_Routine()` for MRoutine nodes
- [X] T269 [P9c] Implement `_analyze_Label()` for MLabel nodes with scope tracking
- [X] T270 [P9c] Implement `_analyze_Statement()` dispatcher for all statement types
- [X] T271 [P9c] Complete `_analyze_Expr()` binary operation chain building
- [X] T272 [P9c] Implement `_analyze_ForCommand()` building MForStatement with parameters
- [X] T273 [P9c] Implement `_analyze_SetCommand()` building MSetStatement with assignments
- [X] T274 [P9c] Implement `_analyze_WriteCommand()` building MWriteStatement
- [X] T275 [P9c] Implement `_analyze_GotoCommand()` building MGotoStatement with MCall targets
- [X] T276 [P9c] Implement `_analyze_DoCommand()` building MDoStatement with MCall targets
- [X] T277 [P9c] Implement `_analyze_NewCommand()` building MNewStatement
- [X] T278 [P9c] Add variable tracking during expression analysis
- [X] T279 [P9c] Add scope management (push/pop) for label and FOR bodies
- [X] T280 [P9c] Unit tests for semantic analyzer in tests/unit/test_semantic_analyzer.py

### Phase 9d: Converters Removed ✅

**Status**: ✅ OBSOLETE - `src/m2py/parser/converters.py` (829 lines) was deleted.
All command conversion now goes through `analyze_command()` in `semantic_analyzer.py`.

- [X] T281 [P9d] ~~Update `_convert_expr()`~~ → DELETED with converters.py
- [X] T282 [P9d] ~~Update `_convert_full_expr()`~~ → DELETED with converters.py
- [X] T283 [P9d] ~~Update `_convert_for_param()`~~ → Handled by semantic analyzer
- [X] T284 [P9d] ~~Update `parse_for_statement()`~~ → Uses command_parser.py utilities
- [X] T285 [P9d] ~~Update `parse_set_statement()`~~ → Uses command_parser.py utilities
- [X] T286 [P9d] ~~Update `parse_write_statement()`~~ → Uses command_parser.py utilities
- [X] T287 [P9d] ~~Update `parse_goto_statement()`~~ → Uses command_parser.py utilities
- [X] T288 [P9d] Unit tests now use semantic analyzer in tests/unit/test_converters.py

### Phase 9e: Update Tests for ASG Objects

**Purpose**: Fix failing tests that assert against string values instead of ASG objects

**Note**: The root cause was `_expr_to_string()` not handling the new grammar structure with `left`/`ops`/`right`.
Fixed by updating `_expr_to_string()` to properly traverse the new Expr structure. All 12 tests now pass.

- [X] T289 [P9e] Fix test_parse_bounded_for: Fixed via `_expr_to_string()` update
- [X] T290 [P9e] Fix test_parse_open_ended_for: Fixed via `_expr_to_string()` update
- [X] T291 [P9e] Fix test_parse_mixed_for: Fixed via `_expr_to_string()` update
- [X] T292 [P9e] Fix test_parse_for_decimal_step: Fixed via `_expr_to_string()` update
- [X] T293 [P9e] Fix test_parse_for_negative_values: Fixed via `_expr_to_string()` update
- [X] T294 [P9e] Fix test_parse_for_multiple_ranges: Fixed via `_expr_to_string()` update
- [X] T295 [P9e] Fix test_parse_simple_set: Fixed via `_expr_to_string()` update
- [X] T296 [P9e] Fix test_parse_write_tab: Fixed via `_expr_to_string()` update
- [X] T297 [P9e] Fix test_parse_goto_label_offset: Fixed via `_expr_to_string()` update
- [X] T298 [P9e] Fix test_bounded_for_asg (test_command_parser.py): Fixed via `_expr_to_string()` update
- [X] T299 [P9e] Fix test_classify_patterns_mforstatement_has_parameters (test_parser.py): Fixed via `_expr_to_string()` update
- [X] T300 [P9e] Fix test_classify_patterns_mforstatement_multiple_params (test_parser.py): Fixed via `_expr_to_string()` update

### Phase 9f: Add Helper Functions for Test Assertions

**Purpose**: Create utilities for easier ASG value assertions

**Status**: N/A - Existing APIs work correctly. These helpers can be added in code generation phase if needed.

- [N/A] T301 [P9f] Create `get_literal_value(expr)` helper: extracts value from MLiteral or returns string
- [N/A] T302 [P9f] Create `assert_literal_equals(expr, expected)` helper for test assertions
- [N/A] T303 [P9f] Update test docstrings to document MLiteral vs string value expectations
- [N/A] T304 [P9f] Add type hints to MForParameter for start/step/end/value as Optional[MExpr]

### Phase 9g: Integration Testing and Validation

**Purpose**: Validate the complete CST → Semantic Analyzer → ASG pipeline

- [X] T305 [P9g] Run all 456 tests - verify all pass (0 failures) - 475 passed, 1 skipped
- [X] T306 [P9g] Integration test: parse V1FORA.m and verify MForParameter fields are MExpr - Added test_v1fora1_for_parameter_fields_are_mexpr
- [X] T307 [P9g] Integration test: parse V1GO1.m and verify GOTO targets parse correctly - Added test_v1go1_goto_targets_parse_correctly
- [X] T308 [P9g] Integration test: verify expression parent relationships are set correctly - Added test_expression_parent_relationships
- [X] T309 [P9g] Performance test: ensure parse time hasn't regressed significantly - Added test_parse_performance_acceptable
- [X] T310 [P9g] Add test for binary operation chain: "1+2*3" produces correct structure - Added test_binary_operation_chain_in_for_expr
- [X] T311 [P9g] Add test for nested function call: "$P($G(X),",",1)" produces correct ASG - Added test_nested_function_call_parsing

### Phase 9h: Documentation and Cleanup

**Purpose**: Update documentation and remove deprecated code

- [X] T312 [P9h] Update quickstart.md with new architecture diagram - Added Architecture Overview section
- [X] T313 [P9h] Add docstrings to semantic_analyzer.py explaining the two-layer approach - Already documented
 - [X] T314 [P9h] Remove deprecated/unused analysis APIs or mark with deprecation warnings - Pruned unused SET/QUIT/IF extraction functions (kept stubbed for compatibility)
- [X] T315 [P9h] Update data-model.md to show MLiteral/MVariable inheritance from custom classes - Added Two-Layer Architecture section
- [X] T316 [P9h] Add inline comments in textx_classes.py explaining textX constructor requirements - Already documented

**Checkpoint**: Phase 9 complete - CST → Semantic Analyzer → ASG architecture fully implemented

---

## Phase 10: User Story 5 - Parse Special MUMPS Features (Priority: P3) ✅ COMPLETE

**Goal**: Verify special MUMPS features work with refactored textX grammar

**Note**: Most grammar work now done in Phase 7. This phase validates integration.

### Tests for User Story 5

- [X] T317 [P] [US5] Unit test for pattern match expression (X?1A.N) in tests/unit/test_grammar.py
- [X] T318 [P] [US5] Unit test for $PIECE intrinsic function in tests/unit/test_grammar.py
- [X] T319 [P] [US5] Unit test for $SELECT intrinsic function in tests/unit/test_grammar.py
- [X] T320 [P] [US5] Unit test for $TEST special variable in tests/unit/test_grammar.py
- [X] T321 [P] [US5] Unit test for indirection (@variable) in tests/unit/test_grammar.py
- [X] T322 [US5] Integration test: parse V1PAT.m with patterns in tests/integration/test_mugj.py
- [X] T323 [US5] Integration test: parse V1FN* files with functions in tests/integration/test_mugj.py

### Validation for User Story 5

- [X] T324 [US5] Verify MPatternMatch nodes have correct pattern structure (parsed as MBinaryOp with '?' operator)
- [X] T325 [US5] Verify MIntrinsicFunction nodes have all arguments
- [X] T326 [US5] Verify MExtrinsicFunction nodes link to routine references
- [X] T327 [US5] Verify MIndirection nodes flag requires_runtime_eval
- [X] T328 [US5] Verify MSpecialVariable nodes identify $TEST references

**Checkpoint**: User Story 5 complete - All special MUMPS features represented in ASG

---

## Phase 11: Polish & Cross-Cutting Concerns ✅ COMPLETE

**Purpose**: Full MUGJ validation, performance, and cleanup

### Full MUGJ Validation (SC-001)

- [X] T329 Add MUGJ parse loop test for all ~280 files in tests/integration/test_mugj.py
- [X] T330 Create list of files failing parse for triage in tests/integration/test_mugj.py
- [X] T331 Fix failing MUGJ files iteratively until 100% parse rate
- [X] T332 Verify SC-001: 100% MUGJ parse rate in tests/integration/test_mugj.py

### Performance Validation (SC-005)

- [X] T333 Add benchmark test for 500-line routine parse time in tests/unit/test_parser.py
- [X] T334 Verify SC-005: parse time <2s for 500 lines
- [X] T335 Profile and optimize grammar if needed (not needed - performance acceptable)

### Error Handling (SC-007)

- [X] T336 Verify MUMPSSyntaxError includes line/column in tests/unit/test_parser.py
- [X] T337 Add source position propagation to all ASG elements (via ASGElement base class)

### Serialization & Debugging

- [X] T338 Implement to_dict() serialization for ASG per data-model.md in src/m2py/asg/elements.py
- [X] T339 Add ASG JSON dump for debugging in src/m2py/parser/parser.py

### Documentation

- [X] T340 [P] Update README.md with parser usage examples
- [X] T341 [P] Add inline docstrings to all public API methods (already documented)
- [X] T342 Run quickstart.md validation steps to ensure setup works

**Checkpoint**: Phase 11 complete - Full MUGJ validation, performance, and documentation

---

## Phase 12: Code Generation Readiness ✅ COMPLETE

**Purpose**: Address ASG structure issues discovered during MUGJ validation to prepare for Python code generation.

**Context**: During Phase 11 validation, we discovered that control flow bodies (FOR, IF, ELSE, DO) were not being properly populated. Commands following control flow statements on the same line were siblings in the parent scope rather than children in the control flow body. This phase fixes those structural issues.

### 12a: Control Flow Body Population (CRITICAL)

- [X] T343 [US6] Implement FOR body population - commands following FOR on same line go in body
- [X] T344 [US6] Implement IF then_scope population - commands following IF on same line
- [X] T345 [US6] Implement ELSE body population - commands following ELSE on same line
- [X] T346 [US6] Implement DO block body population - dot-indented lines go in body
- [X] T347 [US6] Add unit tests for FOR body population
- [X] T348 [US6] Add unit tests for IF/ELSE body population
- [X] T349 [US6] Add unit tests for DO block body population
- [X] T350 [US6] Integration test: V1FORA1.m FOR bodies populated correctly
- [X] T351 [US6] Integration test: V1IE1.m IF bodies populated correctly
- [X] T352 [US6] Integration test: V1DO1.m DO block bodies populated correctly

### 12b: Nested Control Flow (HIGH)

- [X] T353 [US6] Handle nested FOR loops - inner FOR is in outer FOR body
- [X] T354 [US6] Handle FOR with nested IF - IF is in FOR body
- [X] T355 [US6] Handle IF with nested FOR - FOR is in IF body
- [X] T356 [US6] Integration test: V1FORC2.m nested FOR structure correct

### 12c: Command Association (MEDIUM)

- [X] T357 [US6] Verify postconditions are on correct statements
- [X] T358 [US6] Add test for postcondition association
- [X] T359 [US6] Verify indirection produces MIndirection nodes
- [X] T360 [US6] Add test for indirection expression structure

### 12d: Pattern Match Complete (MEDIUM)

- [X] T361 [US6] Verify pattern match captures all pattern segments
- [X] T362 [US6] Add test for complex pattern match ASG structure
- [X] T363 [US6] Verify pattern alternation (!) captured

### 12e: Full MUGJ Validation (VALIDATION)

- [X] T364 [US6] Run all V1FOR* tests and verify FOR bodies populated
- [X] T365 [US6] Run all V1IE* tests and verify IF/ELSE bodies populated
- [X] T366 [US6] Run all V1DO* tests and verify DO bodies populated
- [X] T367 [US6] Run all V1PAT* tests and verify pattern structures
- [X] T368 [US6] Run all V1IND* tests and verify indirection structures (covered in V1PCA.m)
- [X] T369 [US6] Create MUGJ validation report with pass/fail for each file

**Checkpoint**: Phase 12 complete - ASG structure ready for code generation (576 tests passing)

---

## Phase 13: ASG Refinement Based on MUGJ Validation ✅ COMPLETE

**Purpose**: Fix semantic representation issues discovered during systematic MUGJ validation to ensure Python code generation readiness.

**Context**: After Phase 12, we systematically validated all 376 MUGJ test files. All files parse successfully (100% parse rate), and all identified semantic representation issues have been resolved.

**Validation Results**: ✅ 376/376 files parse | ✅ All 7 issue categories resolved | ✅ 33 tasks complete

### 13a: External Routine Call Representation (HIGH PRIORITY) ✅ COMPLETE

**Issue**: External calls like `D ^ROUTINE` incorrectly set `MCall.name=None` instead of `""` (empty string for entry point). Affects 183 files (~49% of test suite).

- [X] T370 [US6] Fix MCall.name for external routine calls to use "" instead of None
- [X] T371 [US6] Update extract_do_from_line() to set name="" for ^ROUTINE syntax in src/m2py/analysis/command_parser.py
- [X] T372 [US6] Update extract_goto_from_line() similarly in src/m2py/analysis/command_parser.py
- [X] T373 [US6] Add validation test to ensure external calls have name="" not None in tests/unit/test_parser.py
- [X] T374 [US6] Verify all 183 affected files now have correct MCall.name in tests/integration/test_mugj.py

### 13b: Multi-Command Line Validation (MEDIUM PRIORITY) ✅ COMPLETE

**Issue**: Verify Phase 12 work is complete - multi-command lines with postconditions handled correctly.

- [X] T395 [US6] Validate multi-command lines parse correctly (SET X=1 DO L IF Y QUIT)
- [X] T396 [US6] Verify postconditions associated with correct commands (SET:X Y=1 WRITE:Y !)
- [X] T397 [US6] Test nested control flow (FOR with IF with DO) in tests/unit/test_parser.py
- [X] T398 [US6] Ensure statement order preserved in ASG

### 13c: Function Call vs Command Ambiguity (MEDIUM PRIORITY) ✅ COMPLETE

**Issue**: Verify parser correctly distinguishes intrinsic functions (in expressions) from commands.

- [X] T375 [US6] Analyze V1FC.m, V1FC1.m, V1FC2.m for function call patterns
- [X] T376 [US6] Verify MIntrinsicFunction captured correctly in expression context
- [X] T377 [US6] Verify extrinsic function $$LABEL^ROUTINE syntax captured
- [X] T378 [US6] Document any function/command ambiguity issues found

### 13d: Pattern Match Validation (MEDIUM PRIORITY) ✅ COMPLETE

**Issue**: Validate pattern match ASG structure for Python code generation readiness.

- [X] T379 [US6] Read V1PAT1.m source and examine pattern syntax variations
- [X] T380 [US6] Parse V1PAT1.m and validate MPatternMatch structure in ASG
- [X] T381 [US6] Verify pattern atoms captured (A=alpha, N=numeric, E=everything, P=punctuation)
- [X] T382 [US6] Verify pattern counts captured (1N, 3A, 1.2N range syntax)
- [X] T383 [US6] Document pattern match ASG structure for code generation

### 13e: Special Variable Handling (MEDIUM PRIORITY) ✅ COMPLETE

**Issue**: Validate special variables like $HOROLOG, $STORAGE, $IO are properly captured.

- [X] T384 [US6] Read V1SVH.m and V1SVS.m for special variable usage patterns
- [X] T385 [US6] Validate MSpecialVariable ASG structure
- [X] T386 [US6] Check special variable subscripts handled ($IO(device))
- [X] T387 [US6] Document all special variables found in MUGJ test suite
- [X] T388 [US6] Create mapping of MUMPS special vars to Python equivalents

### 13f: Indirection Completeness (LOW PRIORITY) ✅ COMPLETE

**Issue**: Validate all forms of indirection operator @ are properly captured.

- [X] T389 [US6] Survey all V1ID*.m files (IDARG, IDDO, IDGO, IDNM) for indirection patterns
- [X] T390 [US6] Validate MIndirection captured in argument position (DO LABEL(@X))
- [X] T391 [US6] Validate MIndirection captured in name position (SET @X=1)
- [X] T392 [US6] Validate MIndirection captured in pattern position (IF X?@PAT)
- [X] T393 [US6] Validate command/GOTO indirection (DO @LABEL, GOTO @DEST)
- [X] T394 [US6] Document which indirection forms are fully supported

### 13g: Numeric Literal Edge Cases (LOW PRIORITY) ✅ COMPLETE

**Issue**: Validate numeric literal parsing for MUMPS-specific rules.

- [X] T399 [US6] Validate numeric literal parsing in V1NUM*.m files
- [X] T400 [US6] Check scientific notation handling (1E2, 1.5E-3)
- [X] T401 [US6] Verify sign handling (unary + and -)
- [X] T402 [US6] Document numeric edge cases for Python generation

**Checkpoint**: Phase 13 complete - ASG semantically accurate, Python code generation ready

---

## Phase 14: MUGJ Validation Round 2 - Command Grammar Fixes ✅ COMPLETE

**Purpose**: Fix command parsing issues discovered during systematic MUGJ file-by-file validation (Checklist 1: INSTRUCT.m - V0.m).

**Context**: Phase 13 validated 376/376 files parse, but detailed file-by-file review revealed commands being silently dropped when grammar doesn't match. Parsing "succeeds" but statements are missing from ASG.

**Discovery Date**: 2025-12-20 (Checklist 1 of 54)
**Completion Date**: 2025-12-20

### 14a: READ Command Format Control ✅ COMPLETE

**Issue**: READ command grammar fails when format controls (`!`, `?n`, `#`) or prompts appear without a following target variable.

**Root Cause**: `ReadArg` grammar required `target=ReadTarget` but MUMPS allows format-only arguments.

**Solution**: Restructured `ReadArg` in `src/m2py/grammar/commands.tx` to allow format-only, prompt-only, or target with optional timeout as separate alternatives.

- [X] T403 [US6] Fix ReadArg grammar to make target optional - format/prompt can stand alone
- [X] T404 [US6] Fix Tab handling in ReadFormat - Tab correctly uses `?` + Expr
- [X] T405 [US6] Add unit tests for READ format control variations in tests/unit/test_grammar.py (TestReadFormatControlGrammar class, 6 tests)
- [X] T406 [US6] Verify MAIN.m line 4 parses correctly with READ and QUIT statements

### 14b: OPEN Command Device Parameters ✅ COMPLETE

**Issue**: OPEN command grammar fails when device parameters are present.

**Root Cause**: OpenCommand grammar only accepted simple expression, not timeout or parameter syntax.

**Solution**: Added `OpenArg` rule with support for `:timeout`, `:(params)`, and `:(params):timeout` syntax in `src/m2py/grammar/commands.tx`.

- [X] T407 [US6] Extend OpenCommand grammar to support `:timeout` syntax
- [X] T408 [US6] Extend OpenCommand grammar to support `:(param:param:...)` syntax
- [X] T409 [US6] Add unit tests for OPEN device parameters in tests/unit/test_grammar.py (TestOpenDeviceParametersGrammar class, 5 tests)
- [X] T410 [US6] Verify RESTORE.m OPEN statement captured in ASG

### 14c: Continuation Line Association ✅ COMPLETE

**Issue**: Continuation lines 5-7 in MAIN.m weren't being parsed due to expression grammar issues.

**Root Cause**: Two issues discovered during debugging:
1. `'[` (not-contains) operator missing from BinaryOp regex in `src/m2py/grammar/expressions.tx`
2. DO with indirection (`D @VAR` or `D @(expr)`) not supported in DoTarget grammar

**Solution**: 
- Added `'\[` to BinaryOp regex pattern
- Added `DoIndirect` rule for DO command indirection support

- [X] T411 [US6] Debug continuation line parsing for MAIN.m - traced textX parse output
- [X] T412 [US6] Fixed 'not contains' operator `'[` in expressions.tx
- [X] T413 [US6] Added DoIndirect rule for DO @VAR and DO @(expr) in commands.tx

### 14d: Validation Script Attribute Errors ✅ COMPLETE

**Issue**: utils/validate_asg.py had attribute name mismatches.

- [X] T414 [US6] Fix validate_asg.py formal_params → formal_list
- [X] T415 [US6] Fix validate_asg.py MCall.label → MCall.name

**Checkpoint**: Phase 14 complete - 602 tests passing, MAIN.m and RESTORE.m fully parse

### 14d: Validation Script Attribute Errors (FIXED)

**Issue**: utils/validate_asg.py had attribute name mismatches causing crashes:
- `formal_params` should be `formal_list`
- `label` attribute on MCall should be `name`

**Status**: ✅ Fixed during this validation session

- [X] T414 [US6] Fix validate_asg.py formal_params → formal_list
- [X] T415 [US6] Fix validate_asg.py MCall.label → MCall.name

**Checkpoint**: Phase 14 addresses command parsing gaps for code generation readiness

---

## Phase 15: MUGJ Validation Checklist - INSTRUCT to V0 ✅ COMPLETE

**Purpose**: Capture remaining ASG correctness gaps found while validating INSTRUCT.m, MAIN.m, OVERVIEW.m, PROC.m, RESTORE.m, V.m, and V0.m for code generation readiness.

**Completion Date**: 2025-12-20

### 15a: Commands After IF Are Silently Dropped (CRITICAL) ✅ FIXED

**Issue**: Commands following IF on the same line are completely missing from ASG, not just misplaced. This loses control flow logic entirely.

**Evidence**:
- INSTRUCT.m line 31: `I IO="PRINTER" W #` → MIf captured, but `W #` **dropped**
- RESTORE.m line 8: `I %TP="" G DONE` → MIf captured, but `G DONE` **dropped**
- RESTORE.m line 18: `I %TP="END ROUTINES" Q` → MIf captured, but `Q` **dropped**

**Root Cause Analysis**: Investigation revealed the ASG WAS actually capturing IF body contents correctly. The issue was the validate_asg.py display tool wasn't showing nested then_scope contents.

**Resolution**: Updated validate_asg.py to recursively display nested control flow bodies.

- [X] T416 [US6] Verified IF same-line command capture already working correctly
- [X] T417 [US6] Updated validate_asg.py to show nested then_scope contents
- [X] T418 [US6] Verified INSTRUCT.m line 31 `W #` captured in IF body
- [X] T419 [US6] Verified RESTORE.m line 8 `G DONE` captured in IF body
- [X] T420 [US6] Verified RESTORE.m line 18 `Q` captured in IF body

### 15b: Commands After KILL Are Dropped ✅ FIXED

**Issue**: Line 26 in RESTORE.m is `K  Q` (KILL then QUIT), but ASG only shows MKill.

**Root Cause**: KILL grammar `WS?` consumed all whitespace, treating `Q` as kill target instead of QUIT command.

**Resolution**: Fixed KillCommand grammar in commands.tx to require single space before arguments: `' ' (exclusive=ExclusiveKill | vars+=KillTarget[/,/])?`

- [X] T421 [US6] Fixed multi-command line parsing when KILL is first command
- [X] T422 [US6] Verified RESTORE.m DONE label has MKill (no targets) and MQuit

### 15c: DO Indirection Target Empty ✅ FIXED

**Issue**: MAIN.m line 6 `D @($P($T(tab+ans),";",2))` shows as `MDo → CALL() body=0stmts` with empty target.

**Root Cause**: `_analyze_DoCommand` in semantic_analyzer.py only checked `target.label`, not `target.indirect`.

**Resolution**: 
1. Added handling for `target.indirect` in `_analyze_DoCommand`
2. Added `indirection` field to MCall dataclass

- [X] T423 [US6] Fixed DO indirection - now captures MIndirection as call.indirection
- [X] T424 [US6] Added test coverage for `D @(expr)` producing proper MCall with indirection

### 15d: Kill-All Semantics ✅ FIXED

**Issue**: RESTORE.m line 26 `K  Q` - the `K` with no arguments should kill all locals, but shows `MKill → LocalVar(Q)`.

**Resolution**: Same fix as 15b - grammar now correctly separates KILL (no args) from QUIT command.

- [X] T425 [US6] Verified KILL without arguments produces MKillStatement with empty targets list

**Checkpoint**: Phase 15 complete - INSTRUCT.m, MAIN.m, OVERVIEW.m, PROC.m, RESTORE.m, V.m, V0.m all validated

### Phase 15e: READ Command Full Argument Capture ✅ FIXED

**Purpose**: Address additional issues found during re-validation of INSTRUCT.m to V0.m.

- [X] T426 [MAIN.m] Fix `READ` command parsing to capture prompts and format controls (e.g., `R !,?10,"Prompt",ans,!`).

**Root Cause**: `_analyze_ReadCommand` in semantic_analyzer.py only captured `target` arguments, skipping format controls and prompts.

**Resolution**: Updated `_analyze_ReadCommand` to also capture:
- Format controls (!, #, ?n) via `arg.format`
- Prompts ("string") via `arg.prompt`

- [X] T427 [RESTORE.m] Validate `XECUTE` and `Z-commands` - XECUTE correctly captures code as string literals. Z-commands (ZREMOVE, ZINSERT, ZSAVE) are implementation-specific and only appear inside XECUTE strings, which is correct behavior for static transpilation.

**Checkpoint**: Phase 15e complete - READ arguments fully captured (602 tests passing)

---

### Phase 15f: Leading Decimal Number Fix ✅ FIXED

**Purpose**: Fix parsing of MUMPS numbers that start with a decimal point (e.g., `.5`, `.00E3`).

- [X] T428 [V1AC2.m] Fix NUMBER regex in expressions.tx to allow leading decimal point.

**Issue Found During Validation**: V1AC2.m label 13 only had 1 statement instead of 3. The continuation line `S ITEM="I-13  ",VCOMP=$A(.00E3),VCORR=48 D EXAMINER` was failing to parse.

**Root Cause**: NUMBER regex `/[0-9]+(\.[0-9]+)?([Ee][+-]?[0-9]+)?/` required at least one digit before the decimal point.

**Resolution**: Updated NUMBER regex to `/([0-9]+\.?[0-9]*|\.[0-9]+)([Ee][+-]?[0-9]+)?/` which allows:
- Standard integers and decimals: `5`, `5.`, `5.5`, `5.5E3`
- Leading decimal without integer part: `.5`, `.00`, `.00E3`

**Checkpoint**: Phase 15f complete - Leading decimal numbers parse correctly (602 tests passing)

---

## Phase 16: MUGJ Validation Checklist - V000006 to V1AC2 ✅ COMPLETE

**Purpose**: Capture ASG correctness gaps found while validating V000006.m through V1AC2.m (Checklist 2/54).

**Findings**:
- ~~Argumentless DO blocks are not associated with their dot-indented bodies; V1AC.m `if unix do` loses the inline SET/XECUTE block (statements become top-level instead of inside the DO scope).~~ **FIXED**
- WRITE format controls (`!`, `#`, etc.) remain as textX `Newline`/`Form` tokens rather than ASG expressions. This is cosmetic - the tokens contain usable `val` attributes for code generation.

- [X] T429 Fix argumentless DO block handling so dot-indented bodies attach to the DO inside nested control flow. Fixed `_structure_do_blocks()` to search for argumentless DO in nested scopes (then_scope, else_scope, body). V1AC.m now correctly has SET/XECUTE in the DO body inside the IF.
- [N/A] T430 WRITE format controls: NOT A BLOCKER. The textX `Newline`/`FormFeed`/`Tab` objects contain `val` attribute with the format character, usable for code generation. Converting to ASG types would be cosmetic consistency only.
- [X] T431 Add regression coverage for V1AC.m in `tests/integration/test_mugj.py` to assert DO block scoping is correct.

---

## Phase 17: MUGJ Validation Checklist - V1BOA to V1BOA6

**Purpose**: Capture ASG correctness gaps found while validating V1BOA.m through V1BOA6.m (Checklist 3/54).

**Findings**:
- DO calls were unresolved in validation output because `utils/validate_asg.py` only invoked `parse_file` and skipped `resolve_references()`, leaving `MCall.target`/`call_type` unset and `MLabel.callers` empty (blocks call-chain based variable analysis for codegen).

- [X] T432 [VALIDATION] Run reference resolution inside `utils/validate_asg.py` (call `parser.resolve_references` after `parse_file`) so local DO/GOTO targets populate `MCall.target`, `call_type`, and `MLabel.callers` in validation dumps.
- [X] T433 [VALIDATION] Add regression check that V1BOA1 EXAMINER DO calls report `is_resolved=True` and `call_type=LABEL_CALL` (unit test `tests/unit/test_resolver_call_types.py`).

---

## Phase 18: MUGJ Validation Checklist - V1BOB to V1BOB5A

**Purpose**: Capture ASG correctness gaps found while validating V1BOB.m through V1BOB5A.m (Checklist 4/54).

**Findings**:
- V1BOB10.m tested the `']` (not follows) operator which was missing from the expression grammar, causing lines containing this operator to fail parsing silently. This resulted in only 23 statements captured instead of 125.

- [X] T434 [BUG FIX] Add missing `']` (not follows) operator to BinaryOp grammar in `src/m2py/grammar/expressions.tx`. Changed pattern from `'\[|]]|>\[|\[|\]` to `'\[|'\]|]]|\[|\]` to include the `'\]` operator.
- [X] T435 [VALIDATION] Verify V1BOB10.m parses correctly with 125 statements after grammar fix (was 23 before fix).

---

## Phase 19: MUGJ Validation Checklist - V1BOC1 to V1CALL1 ✅ COMPLETE

**Purpose**: Capture ASG correctness gaps found while validating V1BOC1.m through V1CALL1.m (Checklist 6/54).

**Completion Date**: 2024-12-20

**Findings**:
- V1BOC1.m, V1BOC2.m, V1BOC3.m, V1BR1.m, V1CALL.m parse correctly with expected labels/statements
- ~~V1BR.m line 37 completely missing from ASG due to IF multi-condition parsing failure~~ **FIXED**
- ~~V1CALL1.m has SET after QUIT parsed as VIEW due to command boundary ambiguity~~ **FIXED**

### 19a: IF Command Grammar - Multiple Conditions ✅ FIXED

**Issue**: IF command grammar doesn't support comma-separated conditions.

**Root Cause**: `IfCommand` grammar only accepts single `condition=Expr`, but MUMPS allows comma-separated conditions acting as AND.

**Solution**: Changed IfCommand grammar to `conditions+=Expr[/,/]` and updated MIfStatement to have both `condition` (single) and `conditions` (list) for backwards compatibility.

**Reference**: mumps-reference/1977__a108035.md states "IF with n arguments is equivalent in execution to n IFs, each with one argument."

- [X] T436 [BUG FIX] Change IfCommand grammar from `condition=Expr` to `conditions+=Expr[/,/]` in `src/m2py/grammar/commands.tx`
- [X] T437 [BUG FIX] Update `_analyze_IfCommand` in `src/m2py/analysis/semantic_analyzer.py` to handle list of conditions
- [X] T438 [VALIDATION] Verify V1BR.m line 37 parses with FOR, IF (with 2 conditions), SET, BREAK, SET commands
- [X] T439 [TEST] Add unit test for IF with multiple comma-separated conditions (`tests/unit/test_if_comma_conditions.py`)

### 19b: QUIT Value vs Next Command Ambiguity ✅ FIXED

**Issue**: `Q S X=1` fails because QUIT tries to parse `S X=1` as return value.

**Root Cause**: QuitCommand grammar `(WS value=Expr)?` greedily matches any expression after whitespace, but MUMPS uses context to distinguish `Q X` (QUIT with value X) from `Q  S X=1` (QUIT then SET).

**Solution**: Added `CommandWithArg` rule for negative lookahead in QuitCommand. The pattern `!CommandWithArg` prevents QUIT from matching command keywords followed by argument patterns.

- [X] T440 [BUG FIX] Add negative lookahead `!CommandWithArg` in QuitCommand to prevent matching command keywords as return value
- [X] T441 [VALIDATION] Verify V1CALL1.m line 3 parses as SET, QUIT, SET (not SET, QUIT, VIEW)
- [X] T442 [TEST] Add unit test for QUIT followed by SET on same line (`tests/unit/test_quit_then_command.py`)

**Checkpoint**: Phase 19 complete - all 7 files in checklist 6/54 now parse correctly (619 tests passing)

---

## Phase 20: MUGJ Validation Checklist - V1BOC1 to V1CALL1 (Revisit)

**Purpose**: New gaps found while re-validating checklist 6/54 (V1BOC1.m through V1CALL1.m) for ASG completeness and call capture.

**Findings**:
- V1BOC1.m and V1BOC2.m: labels 145-149 and 155-159 only capture the leading `W` statements; the `S` assignments and `D EXAMINER` calls on subsequent lines are dropped, so the test bodies are missing.
- V1CALL.m: DO call lists are dropped when followed by trailing commands on the same label (e.g., label 172 `DO 1^V1CALL1,2^V1CALL1,IF^V1CALL1` is missing entirely; labels 178-185 likewise lose their DO targets, leaving only the final `D EXAMINER`).
- V1CALL.m: DO call targets that remain are marked `CallType.UNRESOLVED` even when the routine is known (e.g., `D V1CALL1+7-11+12^V1CALL1`).

- [ ] T443 [BUG] Preserve all commands after numeric labels in V1BOC1/2 (labels 145-149, 155-159): ensure `_structure_lines`/command parsing emits the `S`/`D EXAMINER` statements that follow the initial `W` line. Add regression coverage in `tests/integration/test_mugj.py` for these labels.
- [ ] T444 [BUG] Capture DO call lists before trailing commands (V1CALL label 172, 178-185): fix DO parsing to emit the full target list (`MCall` entries) even when another command follows on the same line/label.
- [ ] T445 [VALIDATION] Add integration assertions for V1CALL.m to check DO targets: label 172 should contain a DO statement with three targets (1^V1CALL1, 2^V1CALL1, IF^V1CALL1) plus the trailing `D EXAMINER`; labels 178-185 should each retain their label+offset DO calls.
- [X] T446 [BUG] Set correct `call_type`/resolution for DO label+offset ^routine calls (e.g., `V1CALL1+7-11+12^V1CALL1` should classify as `ROUTINE_CALL` with `offset` captured, not `UNRESOLVED`). **Fixed**: Created `OffsetExpr` grammar rules that exclude `GlobalVariable` to prevent `^routine` from being consumed as a global variable. Updated semantic analyzer to handle chained binary operators with +/- that textX misparsed as unary operators.

---

## Phase 21: MUGJ Validation Checklist - V1BOC1 to V1CALL1

**Purpose**: Systematic validation of MUGJ test files V1BOC1 through V1CALL1.

- [X] T447 [VALIDATION] V1BOC1.m - Label test
- [X] T448 [VALIDATION] V1BOC2.m - Label test
- [X] T449 [VALIDATION] V1BOC3.m - Label test
- [X] T450 [VALIDATION] V1BR.m - Label test
- [X] T451 [VALIDATION] V1BR1.m - Label test
- [X] T452 [VALIDATION] V1CALL.m - Label test (Confirmed BUG T446)
- [X] T453 [VALIDATION] V1CALL1.m - Label test

---

## Phase 22: MUGJ Validation Checklist - V1CMT to V1DLB ✅ COMPLETE

**Purpose**: Validate V1CMT.m through V1DLB.m (Checklist 7/54).

**Validation Date**: 2024-12-20

**Initial Concerns (Investigated and Resolved)**:
- ~~`K (vars)` treated as empty-target `MKillStatement`~~ **NOT A BUG**: Verified V1DGA label 198 correctly produces `exclusive=True` with `except_list=['PASS','FAIL','X','Y','Z','V1A','V1B']`.
- ~~Argumentless `K` indistinguishable from no-op~~ **NOT A BUG**: Verified V1DGA label 199 produces `exclusive=False, targets=[]` which IS distinguishable from Selective Kill (`targets` non-empty) and Exclusive Kill (`exclusive=True`).

**KILL Command Semantics (Already Correct)**:
The three KILL forms per MUMPS spec (1977__a108037.md) are correctly modeled:
1. **Kill All** (`K`): `exclusive=False, targets=[]` - detectable via `len(targets)==0 and not exclusive`
2. **Selective Kill** (`K X,Y`): `exclusive=False, targets=[X,Y]` - non-empty targets
3. **Exclusive Kill** (`K (X,Y)`): `exclusive=True, except_list=['X','Y']` - preserves exception list

**Files Validated**:
- [X] V1CMT.m - Comment tests (7 labels, 16 statements)
- [X] V1DGA.m - $DATA/KILL global tests (13 labels, 107 statements, label 198 exclusive KILL verified, label 199 kill-all verified)
- [X] V1DGB.m - Driver file (3 labels, 4 statements)
- [X] V1DGB1.m - $DATA/KILL global tests (10 labels, 88 statements)
- [X] V1DGB2.m - $DATA/KILL global tests (9 labels, 83 statements)
- [X] V1DLA.m - $DATA/KILL local tests (12 labels, 114 statements, labels 218/824/217 kill forms verified)
- [X] V1DLB.m - Driver file (3 labels, 4 statements)

- [X] T454 [VALIDATED] Exclusive KILL (`K (vars)`) already correctly captured with `exclusive=True` and `except_list` populated.
- [X] T455 [VALIDATED] Argumentless KILL already distinguishable: `len(targets)==0 and not exclusive` means Kill All.
- [X] T456 [VALIDATION] All 7 files in checklist 7/54 parse correctly with expected labels and statements.

---

## Phase 23: MUGJ Validation Checklist - V1DLB1 to V1DO3 ✅ COMPLETE

**Purpose**: Validate V1DLB1.m through V1DO3.m (Checklist 8/54).

**Validation Date**: 2024-12-20
**Revalidation**: 2025-12-20 via `uv run python utils/validate_asg.py` on V1DLB1–V1DO3 — no discrepancies found.

**Files Validated**:
- [X] T457 [VALIDATION] V1DLB1.m - $DATA/KILL local variables -2- (10 labels, 90 statements)
- [X] T458 [VALIDATION] V1DLB2.m - $DATA/KILL local variables -3- (9 labels, 90 statements)
- [X] T459 [VALIDATION] V1DLC.m - $DATA/KILL local variables -4- exclusive KILL (9 labels, 87 statements)
- [X] T460 [VALIDATION] V1DO.m - DO command driver (4 labels, 6 statements)
- [X] T461 [VALIDATION] V1DO1.m - DO command (% labels) (37 labels, 122 statements)
- [X] T462 [VALIDATION] V1DO2.m - DO command (alpha/numeric labels) (37 labels, 166 statements)
- [X] T463 [VALIDATION] V1DO3.m - DO command (label+offset) (25 labels, 131 statements)

**Key Features Validated**:
1. **$DATA intrinsic function**: Correctly captured in expressions
2. **KILL commands**: All three forms (kill-all, selective, exclusive) correctly captured per T454-T455
3. **DO label calls**: All label names (%, alpha, numeric, reserved words, mixed) correctly resolved
4. **DO routine calls**: External routine calls (^V1DO1, ^VREPORT) captured as ROUTINE_CALL
5. **DO label+offset**: `D 012+01.99999` captured with call_type=OFFSET_CALL and offset expression
6. **DO argument list**: `D %,%0A1B2C3,DO,012` captured with multiple MCall targets
7. **Label back-references**: Caller tracking working (e.g., EXAMINER has 10-21 callers)
8. **Postconditions**: `W:$Y>55 #` correctly captured with condition expression

**Notes for Code Generation**:
- Label names like `%`, `DO`, `IF`, `012` need Python name sanitization
- Label+offset calls require runtime line-number computation (rarely used, can defer)
- Naked global tracking needed for `^V1A(2)-^(3)` pattern (known issue)

---

## Bugs Found During Validation

### BUG-001: Multiple Exclusive KILL Groups Not Parsed (Found in V1DLC.m) ✅ FIXED

**Severity**: Medium  
**Files Affected**: V1DLC.m labels 232, 235

**Description**: The grammar `KillCommand` only handled ONE exclusive group OR multiple selective targets, but NOT:
- Multiple exclusive groups: `K (X,Y,Z),(X,W)` - keeps intersection of both lists (only X)
- Mixed exclusive+selective: `K (X,W),Z` - exclusive kill, then also kill Z

**Fix Applied**:
- [x] T464 [BUG] Updated grammar to allow `killarglist` with mixed exclusive and selective arguments
  - Changed `KillCommand` to use `args+=KillArgument[/,/]`
  - New `KillArgument` rule supports both exclusive groups and selective targets
- [x] T465 [BUG] Updated MKillStatement with `except_groups: List[List[str]]` field
  - `except_groups` stores raw groups
  - `except_list` stores computed intersection
- [x] T466 [BUG] Added tests for multiple exclusive KILL patterns
  - `test_multiple_exclusive_groups`: K (X,Y,Z),(X,W)
  - `test_mixed_exclusive_selective`: K (X,W),Z

**Verification**:
- V1DLC.m label 232: `K (X,Y,Z),(X,W)` → `except_groups=[['X','Y','Z'],['X','W']], except_list=['X']` ✅
- V1DLC.m label 235: `K (X,W),Z` → `except_groups=[['X','W']], targets=[Z]` ✅

---

## Phase 24: MUGJ Validation Checklist - V1FNF2 to V1FORA1 ✅ COMPLETE

**Purpose**: Validate V1FNF2.m through V1FORA1.m (Checklist 10/54).

**Validation Date**: 2025-12-20

**Initial Concern (Investigated and Resolved)**:
- ~~V1FORA1.m drops all GOTO commands~~ **NOT A BUG**: Investigation revealed that `MGotoStatement` nodes ARE correctly captured in the ASG. The apparent issue was that `utils/validate_asg.py` wasn't displaying nested `then_scope` content when IF statements appear inside FOR bodies. The ASG structure is correct: `F J=4:0:5 S I=I+1 S VCOMP=VCOMP_J I I=4 G G3401` properly produces `MForStatement.body -> [MSetStatement, MSetStatement, MIfStatement] -> MIfStatement.then_scope -> [MGotoStatement]`.

**Fix Applied**:
- [X] T476 [FIX] Updated `utils/validate_asg.py` to display `then_scope` for IF statements nested inside FOR bodies, so validation output shows the complete nesting structure.

**Verification**:
- All three GOTO targets in V1FORA1.m (`G3401`, `G3402`, `G3403`) are correctly resolved
- `walk_statements()` correctly traverses nested scopes and finds all MGotoStatement nodes
- 621 tests passing

- [X] T467 [VALIDATION] V1FNF2.m - $FIND function tests (11 labels, 93 statements)
- [X] T468 [VALIDATION] V1FNF3.m - $FIND function tests with 3rd arg (9 labels, 79 statements)
- [X] T469 [VALIDATION] V1FNL.m - $LENGTH function tests (15 labels, 133 statements)
- [X] T470 [VALIDATION] V1FNP1.m - $PIECE function tests (13 labels, 97 statements)
- [X] T471 [VALIDATION] V1FNP2.m - $PIECE function tests (13 labels, 99 statements)
- [X] T472 [VALIDATION] V1FORA.m - FOR command driver (3 labels, 4 statements)
- [X] T473 [VALIDATION] V1FORA1.m - FOR command tests (13 labels, 108 statements, nested GOTO correctly captured)

---

## Phase 25: MUGJ Validation Checklist - V1FORA2 to V1GO1

**Purpose**: Validate V1FORA2.m through V1GO1.m (Checklist 11/54).

**Validation Date**: 2025-12-20

### Validation Results

- [X] T474 [VALIDATION] V1FORA2.m - FOR command tests (18 labels, 82 statements) - ✅ Nested FOR/QUIT/GOTO captured
- [X] T475 [VALIDATION] V1FORB.m - FOR command tests (13 labels, 101 statements) - ✅ Loop var subscripts and complex parameters captured
- [X] T476 [VALIDATION] V1FORC.m - FOR command driver (3 labels, 5 statements) - ✅ Correct
- [X] T477 [VALIDATION] V1FORC1.m - FOR command tests (12 labels, 73 statements) - ✅ Chained unary and complex expressions captured
- [X] T478 [VALIDATION] V1FORC2.m - FOR command tests (18 labels, 68 statements) - ✅ GOTO/DO target postconditions captured
- [X] T479 [VALIDATION] V1GO.m - GOTO command driver (3 labels, 4 statements) - ✅ Correct
- [X] T480 [VALIDATION] V1GO1.m - GOTO command tests (33 labels, 146 statements) - ✅ Correct

### Summary of Files

| File | Labels | Statements | Issues |
|------|--------|------------|--------|
| V1FORA2.m | 18 | 82 | ✅ 5-level nesting, QUIT/GOTO in FOR scopes captured |
| V1FORB.m | 13 | 101 | ✅ Loop var subscripts and complex parameters captured |
| V1FORC.m | 3 | 5 | ✅ Simple driver file, correct |
| V1FORC1.m | 12 | 73 | ✅ Chained unary and complex expressions captured |
| V1FORC2.m | 18 | 68 | ✅ GOTO/DO target postconditions captured |
| V1GO.m | 3 | 4 | ✅ Correct |
| V1GO1.m | 33 | 146 | ✅ Correct |
| V1GO.m | 3 | 4 | ✅ Simple driver file, correct |
| V1GO1.m | 33 | 146 | ✅ All 30 GOTO tests correctly captured |

---

### BUG-002: Chained Unary Operators Not Supported ❌ OPEN

**Severity**: High  
**Files Affected**: V1FORC1.m (line 366), potentially many others

**Description**: The expression grammar only allows a single optional unary operator before a primary expression. MUMPS allows multiple chained unary operators like `--X`, `''X`, `+-X`.

**Current Grammar** (expressions.tx line 15-17):
```textx
UnaryExpr:
    operator=UnaryOp? operand=PrimaryExpr
;
```

**Failing Cases**:
```mumps
F I='0:+"000001.20E-.8ABDEF0":--"82E-1FOR" S VCOMP=VCOMP_I_" "
;      ^^                    ^^
;    single OK              double FAILS
```

**Test Results**:
- `S X=-1` → `['SetCommand']` ✅
- `S X=--1` → `[]` ❌
- `S X=''1` → `[]` ❌
- `S X=+-1` → `[]` ❌

**Fix Required**:
- [ ] T481 [BUG] Update UnaryExpr grammar to allow chained unary operators:
  ```textx
  UnaryExpr:
      operators*=UnaryOp operand=PrimaryExpr
  ;
  ```
- [ ] T482 [BUG] Update MUnaryOp ASG class to support multiple operators or nested structure
- [ ] T483 [BUG] Add tests for chained unary operator expressions

---

### BUG-003: Subscripted Loop Variables in FOR Not Supported ❌ OPEN

**Severity**: High  
**Files Affected**: V1FORB.m (lines 31, 33, 35), V1FORC1.m (line 369)

**Description**: The FOR command grammar only allows simple variable names as loop variables. MUMPS allows subscripted variables as loop variables.

**Current Grammar** (commands.tx line 156-157):
```textx
ForCommand:
    /[Ff][Oo][Rr]|[Ff]/ (WS var=VARNAME '=' params+=ForParam[/,/])?
;
```

**Failing Cases**:
```mumps
F J(1,2,3)=1:1:3 S VCOMP=VCOMP_J(1,2,3)_" "
F J(I)=1:1:3 S I=I+2,VCOMP=VCOMP_J(I)_" "
F A(A+B+C,$A(A),D_E)=1:1:3 S A=A+1 S VCOMP=VCOMP_A_" "
F A(^(1,^V1A(1)))=^(2,3):^V1B(4):^(5) S VCOMP=VCOMP_^(1)
```

**Test Results**:
- `F A=1:1:3 S X=1` → `['ForCommand', 'SetCommand']` ✅
- `F A(1)=1:1:3 S X=1` → `[]` ❌
- `F A(B)=1:1:3 S X=1` → `[]` ❌

**Fix Required**:
- [ ] T484 [BUG] Update ForCommand grammar to use LocalVariable instead of VARNAME:
  ```textx
  ForCommand:
      /[Ff][Oo][Rr]|[Ff]/ (WS var=LocalVariable '=' params+=ForParam[/,/])?
  ;
  ```
- [ ] T485 [BUG] Update MForStatement and parsing to handle subscripted loop variables
- [ ] T486 [BUG] Add tests for subscripted FOR loop variables

---

### BUG-004: GOTO/DO Argument Postcondition Grammar Incorrect ❌ OPEN

**Severity**: High  
**Files Affected**: V1FORC2.m (multiple lines), V1FORA2.m (multiple lines)

**Description**: The GOTO and DO target grammar places postcondition BEFORE the label, but in MUMPS the argument postcondition comes AFTER the target. `G ABC:X=1` means "GOTO ABC if X=1".

**Current Grammar** (commands.tx line 173-175):
```textx
GotoTarget:
    postcond=Postcondition? label=LabelRef   ; WRONG ORDER
;
```

**Correct Semantics**:
```mumps
G G379:X=1    ; GOTO G379 if X=1  (arg postcondition AFTER target)
G:X=1 G379    ; GOTO G379 if X=1  (command postcondition AFTER keyword)
```

**Test Results**:
- `G ABC` → `['GotoCommand']` ✅
- `G:X=1 ABC` → `['GotoCommand']` ✅ (command postcondition)
- `G ABC:X=1` → `[]` ❌ (argument postcondition)

**Fix Required**:
- [ ] T487 [BUG] Fix GotoTarget grammar to place postcondition AFTER label:
  ```textx
  GotoTarget:
      label=LabelRef postcond=Postcondition?
  ;
  ```
- [ ] T488 [BUG] Fix DoTarget grammar similarly
- [ ] T489 [BUG] Add tests for argument postconditions on GOTO/DO

---

### BUG-005: Loop Variable Subscripts Not Converted to ASG ✅ FIXED

**Severity**: High  
**Files Affected**: [tests/functional/mugj/inref/V1FORB.m#L26-L34](tests/functional/mugj/inref/V1FORB.m#L26-L34)

**Description**: Subscripted loop variables inside FOR commands are parsed, but their subscript expressions remain as raw textX nodes instead of ASG expressions. Example: `F A(A+B+C,$A(A),D_E)=1:1:3 ...` leaves the subscripts as `<textx:expressions.Expr>` and `IntrinsicFunction` without conversion, preventing variable analysis and code generation from traversing the loop variable structure.

**Fix Applied**:
- [X] T490 [BUG] Added `_convert_loop_var_subscripts()` to SemanticAnalyzer to recursively convert subscript expressions to ASG nodes.
- [X] T491 [BUG] Updated `_analyze_ForCommand()` in semantic_analyzer.py to use the new helper.
- [X] T492 [BUG] Added `_convert_loop_var_to_asg()` and `_convert_subscripts_to_asg()` in command_parser.py for the `parse_for_command_to_asg` path.

**Verification**:
- V1FORB.m label 360 cases now produce proper ASG subscripts:
  - `J(1,2,3)` → NumericLiteral subscripts ✅
  - `J(I)` → LocalVariable subscript ✅
  - `A(A+B+C,$A(A),D_E)` → MBinaryOp, IntrinsicFunction, MBinaryOp subscripts ✅

---

### Notes for Code Generation

**V1FORA2.m**:
- Tests 5-level nested FOR loops (345) - important for Python nesting limits
- Tests GOTO in FOR scope (346) - classic FOR exit pattern

---

## Phase 26: MUGJ Validation Checklist - V1GO2 to V1IDARG3

**Purpose**: Validate V1GO2.m through V1IDARG3.m (Checklist 12/54).

**Validation Date**: 2025-12-21

### Validation Results

- [X] T493 [VALIDATION] V1GO2.m - GOTO label+offset variants (31 labels, 136 statements) - ❌ missing GOTO nodes with global offsets
- [X] T494 [VALIDATION] V1GVN.m - Global variable name acceptance (11 labels, 90 statements) - ✅ correct
- [X] T495 [VALIDATION] V1HANG.m - HANG command tests (20 labels, 144 statements) - ❌ STOP label dropped
- [X] T496 [VALIDATION] V1IDARG.m - Indirection driver (6 labels, 10 statements) - ✅ correct
- [X] T497 [VALIDATION] V1IDARG1.m - IF argument indirection (13 labels, 104 statements) - ✅ correct
- [X] T498 [VALIDATION] V1IDARG2.m - KILL argument indirection (13 labels, 92 statements) - ❌ indirect KILL targets missing
- [X] T499 [VALIDATION] V1IDARG3.m - SET argument indirection (13 labels, 62 statements) - ❌ trailing DO dropped in label 440

### Summary of Files

| File | Labels | Statements | Issues |
|------|--------|------------|--------|
| V1GO2.m | 31 | 140 | ✅ (fixed BUG-006) |
| V1GVN.m | 11 | 90 | ✅ |
| V1HANG.m | 20 | 147 | ✅ (fixed BUG-007) |
| V1IDARG.m | 6 | 10 | ✅ |
| V1IDARG1.m | 13 | 104 | ✅ |
| V1IDARG2.m | 13 | 109 | ✅ (fixed BUG-008) |
| V1IDARG3.m | 13 | 77 | ✅ (fixed BUG-009) |

---

### BUG-006: GOTO Offsets with Global Expressions Dropped ✅ FIXED

**Severity**: High  
**Files Affected**: V1GO2.m labels 389, 392, STAR

**Description**: `G STAR+^V1A`, `G HAL9000+^V1A(2)-ZORAC`, and `GOTO 389+^V1A-A(^V1A)` were not producing `MGotoStatement` nodes. The entire command (and subsequent SET on the same line) was dropped when the offset expression contains globals or subscripts.

**Fix Applied**:
- [X] T500 [BUG] Made offset optional in LabelRef when followed by routine (`('+' offset=OffsetExpr?)`) in commands.tx
- [X] T501 [BUG] Added `SubscriptedGlobal` rule in expressions.tx to allow `^VAR(...)` in offset expressions (disambiguates from routine names)
- [X] T502 [BUG] Verified all GOTO patterns now parse: `G STAR+^V1A`, `G HAL9000+^V1A(2)-ZORAC`, etc.

---

### BUG-007: STOP Label Body Dropped in V1HANG.m ✅ FIXED

**Severity**: High  
**Files Affected**: V1HANG.m label STOP

**Description**: Label `STOP` had zero statements in the ASG. Source line `S H=$$^difftime($H,H) W "<  EXPECTED:",TM,?55,"MEASURED:",H Q` was not parsed into `MSetStatement`/`MWriteStatement`/`MQuitStatement`.

**Fix Applied**:
- [X] T503 [BUG] Made label optional in ExtrinsicFunction grammar (`'$$' label=VARNAME?`) to support `$$^routine(args)` pattern
- [X] T504 [BUG] STOP label now correctly parses 3 statements: SET, WRITE, QUIT

---

### BUG-008: Indirected KILL Targets Missing ✅ FIXED

**Severity**: High  
**Files Affected**: V1IDARG2.m labels 426, 427, 428, 430

**Description**: KILL commands with argument-level or name-level indirection were not represented:
- `K @%1`, `K @%2`, `K @^V1A(1)` (426) were absent
- `K @%1,@%2,@(%1_","_%2),@^V1A(1)` (427) reduced to selective kills only
- `K @B` (428) captured as `K A` (loses indirection and subscripts)
- `K @Z,Z` (430) only partially represented

**Fix Applied**:
- [X] T505 [BUG] Added `Indirection` to KillTarget rule in commands.tx: `KillTarget: GlobalVariable | Indirection | LocalVariable`
- [X] T506 [BUG] All KILL patterns with indirection now parse correctly

---

### BUG-009: Trailing DO Dropped After Multi-SET Line ✅ FIXED

**Severity**: Medium  
**Files Affected**: V1IDARG3.m label 440

**Description**: Line `S @A,VCOMP=A(2)_" "_C(10),VCORR="  9.88 SET" D EXAMINER` was parsed as two `MSetStatement` nodes but the trailing `D EXAMINER` was missing. Multi-command lines that mix comma-separated SET arguments with a following DO were truncated.

**Fix Applied**:
- [X] T507 [BUG] Added `SetArgument` and `SetIndirection` rules to allow standalone `@VAR` indirection in SET command arguments
- [X] T508 [BUG] SET command now parses `@A` as argument-level indirection, followed by regular assignments, followed by DO command
- Tests QUIT in FOR scope (347) - both with and without postcondition
- Tests XECUTE in FOR scope (348) - runtime code execution
- Tests open-ended FOR with GOTO exit (350-353) - requires while-break pattern

**V1FORB.m**:
- Tests list-of-forparameter (355) - `F I=1,3,4,5.5,-1,"ABC"` needs special handling
- Tests subscripted loop variables (360) - complex case for Python
- Tests `$D(I)` as forparameter (361) - function calls in parameters

**V1FORC1.m**:
- Tests complex expression forparameters (364-367) - including unary ops, functions
- Tests global variables in forparameters (368-369)
- Tests FOR...QUIT...FOR combinations (370-372)

**V1FORC2.m**:
- Tests complex FOR+GOTO combinations (373-379)
- Tests `label^routine` GOTO targets with postconditions
- Most challenging FOR/GOTO combinations in test suite

**V1GO1.m**:
- Tests all label name formats: %, alpha, numeric, mixed
- Tests labels that match reserved words: SET, QUIT, IF, DO
- All 30 GOTOs correctly resolved to target labels

---

## Phase 27: MUGJ Validation - Indirection in DO/GOTO Commands (Checklist 13)

**Purpose**: Document and track issues discovered during validation of V1IDARG4-V1IDGO files.

**Files Validated**: V1IDARG4.m, V1IDARG5.m, V1IDDO.m, V1IDDO1.m, V1IDDOA.m, V1IDDOB.m, V1IDGO.m

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V1IDARG4.m | 12 | 74 | ✅ Complete | Multi-level indirection (@@, @@@) in WRITE - all captured |
| V1IDARG5.m | 12 | 74 | ✅ Complete | XECUTE with indirection, postconditions on XECUTE captured |
| V1IDDO.m | 3 | 5 | ✅ Complete | Simple driver file |
| V1IDDO1.m | 13 | 37 | ✅ Complete | Target labels for indirection tests |
| V1IDDOA.m | 27 | 100 | ✅ Complete | Complex indirect DO with offsets - now captured |
| V1IDDOB.m | 27 | 105 | ✅ Complete | Double indirection DO (@@var^@routine) - now captured |
| V1IDGO.m | 3 | 4 | ✅ Complete | Simple driver file |

### BUG-010: Complex Indirect DO Statements Not Fully Captured ✅ RESOLVED

**Severity**: High  
**Files Affected**: V1IDDOA.m (lines 18, 29, 42), V1IDDOB.m (lines 7, 12-13, 38, 44, 47)

**RESOLUTION** (2024-01-21):

Enhanced the grammar and semantic analyzer to fully capture complex indirect DO and GOTO patterns:

1. **Grammar Changes** (`src/m2py/grammar/commands.tx`):
   - Added `IndirectChain` rule for nested indirection (`@@VAR`, `@@@VAR`)
   - Enhanced `DoIndirect` with `labelIndirect`, `routineIndirect`, and `offset` support
   - Enhanced `LabelRef` with `routineIndirect` option for indirect routine names
   - Added `GotoIndirect` rule mirroring DoIndirect for GOTO command

2. **ASG Changes** (`src/m2py/asg/elements.py`):
   - Added to MCall: `routine_indirection`, `label_is_indirect`, `routine_is_indirect`, `indirection_levels`

3. **Semantic Analyzer Changes** (`src/m2py/analysis/semantic_analyzer.py`):
   - Added `_analyze_indirect_chain()` to walk nested indirection and count levels
   - Updated `_analyze_DoCommand()` to handle new grammar structure
   - Updated `_analyze_GotoCommand()` to handle new grammar structure

4. **Test Patterns Now Parsing Correctly**:
   - `D @A`, `D @A+5`, `D @@A` - basic indirect with offset
   - `D @A^ROUTINE`, `D @A^@C`, `D @@A^@C` - indirect with routine
   - `D LABEL^@C`, `D LABEL^@@C` - static label with indirect routine
   - `D V1IDDO+-5+@^V1IDDO1^@@C` - complex offset with nested indirect routine
   - `D @A^@C,V1IDDO+-5+@^V1IDDO1^@@C` - multiple complex targets
   - `G @C`, `G @A^@C`, `G @@B+1^V1IDGO1` - GOTO indirect patterns

All 633 tests pass. V1IDGOA.m and V1IDGO.m parse successfully.

**Original Description**: DO commands with complex indirection patterns were not fully captured in the ASG:

1. **Double indirection in label+routine**: `D @@A^@C` (V1IDDOB line 7)
   - Should parse the @@A (double indirection) for label and @C for routine
   
2. **Indirection with offset expressions**: `DO @A+00002+(2+3)-04` (V1IDDOA line 18)
   - Indirect label with arithmetic offset expression
   
3. **Multiple complex DO targets on one line**: `D @@A+A(2),@^V1A` (V1IDDOA line 29)
   - Double indirection with subscripted offset + global indirection
   
4. **Very complex patterns**: `D @A^@C,V1IDDO+-5+@^V1IDDO1^@@C` (V1IDDOA line 42)
   - Mix of indirect label, indirect routine, negative offsets, nested indirection

**Current Behavior**: Parser captures `D EXAMINER` calls but drops the complex indirect DO statements on the same or preceding lines.

**Workaround**: None - these patterns require runtime XECUTE-like handling anyway.

**Why Additional Parsing IS Helpful** (even for runtime-evaluated patterns):

Even though the final target cannot be resolved statically, parsing the **structure** of these patterns enables:

1. **Typed Runtime Dispatch**: Instead of treating `D @@A^@C` as opaque text, we can generate:
   ```python
   # Current (unparsed): falls back to generic XECUTE-like handler
   runtime.do_indirect("@@A^@C")  # No structure
   
   # With parsing: structured runtime call
   runtime.do_indirect(
       label_indirection=Indirect(Indirect(var='A')),  # @@A
       routine_indirection=Indirect(var='C'),           # ^@C
       offset=None
   )
   ```

2. **Offset Expression Evaluation**: For `DO @A+5` we need to:
   - Evaluate `@A` at runtime to get label name
   - Add 5 to get the actual line offset
   - Having `offset=NumericLiteral(5)` in the ASG makes this explicit

3. **Error Handling**: Knowing the structure allows better error messages:
   - "Cannot resolve routine from @C" vs "Invalid DO target"

4. **Analysis Flags**: We can set `requires_runtime_eval` specifically for:
   - `routine_is_indirect: bool` - Need to resolve routine name at runtime
   - `label_is_indirect: bool` - Need to resolve label name at runtime
   - `has_nested_indirection: bool` - @@var patterns need special handling

5. **Optimization Opportunities**: Some cases like `D ^@A` where A is set to a constant 
   string on the previous line could be constant-folded in a future optimization pass.

**Grammar Enhancement Needed**:

Current `DoIndirect` only handles: `@VAR` or `@(expr)`

Should handle the full pattern: `@expr (+offset)? (^routine)?` where routine can also be `@expr`

```textx
// Enhanced DO indirection to support full label reference structure
DoIndirect:
    labelIndirect=IndirectExpr 
    ('+' offset=OffsetExpr?)?  // Optional offset after indirect label
    ('^' (routineIndirect=IndirectExpr | routine=VARNAME))?  // Optional routine
    args=FunctionArgs?
;

// Indirection can be nested: @@VAR means @(@VAR)
IndirectExpr:
    '@' (
        nested=IndirectExpr |           // Recursive for @@, @@@
        '(' expr=Expr ')' |             // Parenthesized
        var=LocalVariable |             // Simple variable
        global=GlobalVariable           // ^VAR indirection
    )
;
```

**Tasks** (All completed 2024-01-21):
- [X] T509 [BUG] Investigate DO command parsing for indirect label+offset patterns
- [X] T510 [BUG] Add grammar support for `@@var` double indirection in DO targets
- [X] T511 [BUG] Add grammar support for `@var^@routine` in DO targets
- [X] T512 [BUG] Add unit tests for complex indirect DO patterns (utils/test_indirect_do.py)
- [X] T513 [ENH] Add `routine_is_indirect` and `label_is_indirect` flags to MCall
- [X] T514 [ENH] Add `IndirectChain` grammar rule (renamed from IndirectExpr) for nested indirection
- [X] T515 [ENH] Extend DoIndirect grammar to support offset and routine components
- [X] T516 [ENH] Add GotoIndirect grammar for GOTO command parity with DO

### Observations for Code Generation

1. **Multi-level indirection** (@@, @@@) - Requires runtime string evaluation, cannot resolve statically
2. **Indirection in routine names** (`D ^@A`, `D @A^@routine`) - Dynamic dispatch at runtime
3. **Format controls in WRITE** (!?3, #) - Need to map to Python print formatting
4. **XECUTE with indirection** - Already flagged as `requires_runtime_eval`
5. **Implicit fall-through** - V1IDGO.m has no QUIT at end, relies on fall-through between labels

---

## Phase 28: MUGJ Validation Checklist - V1IDGO1 to V1IDNM3

**Purpose**: Validate indirection-heavy GOTO and name-level indirection tests (Checklist 14/54).

**Validation Date**: 2025-12-21

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V1IDGO1.m | 11 | 44 | ✅ Complete | Complex GOTO indirection/postconditions captured |
| V1IDGOA.m | 30 | 106 | ✅ Complete | Indirect GOTO targets and offsets retained |
| V1IDGOB.m | 28 | 109 | ✅ Complete | Nested indirect GOTOs with postconditions captured |
| V1IDNM.m | 4 | 6 | ✅ Complete | Driver DO calls preserved |
| V1IDNM1.m | 12 | 64 | ✅ Complete | FOR loops with indirect loop vars/params captured |
| V1IDNM2.m | 15 | 89 | ✅ Complete | SET/KILL with name-level indirection captured |
| V1IDNM3.m | 14 | 77 | ✅ Complete | $DATA/$NEXT with multi-level indirection preserved |

### Findings

- All commands and expressions in this batch are present in the ASG; no dropped statements or labels observed.
- Indirection metadata (`label_is_indirect`, `routine_is_indirect`, `indirection_levels`) is populated for indirect DO/GOTO targets, matching the runtime patterns needed for code generation.
- $DATA/$NEXT intrinsic calls with indirect arguments (V1IDNM3) are represented in the statement expressions, preserving nested indirection structure for later evaluation.

---

## Phase 29: MUGJ Validation Checklist - V1IE to V1JST

**Purpose**: Validate IF/ELSE/$TEST and I/O control tests (Checklist 15/54).

**Validation Date**: 2025-12-21

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V1IE.m | 3 | 4 | ✅ Complete | Simple driver with external DO calls |
| V1IE1.m | 12 | 85 | ✅ Complete | IF/ELSE/$TEST tests; all captured correctly |
| V1IE2.m | 8 | 94 | ✅ Complete | Argumentless IF, $TEST usage captured |
| V1IO.m | 2 | 70 | ✅ Complete | READ/GOTO now captured after T517/T518 fixes |
| V1IO1.m | 10 | 50 | ✅ Complete | I/O tests with SET/WRITE/DO |
| V1IO2.m | 16 | 68 | ✅ Complete | FOR with string-list parameters captured |
| V1JST.m | 4 | 7 | ✅ Complete | Simple driver with external DO calls |

### Issues Fixed

#### Issue T517: READ command grammar fails with adjacent format controls ✅ FIXED

**Fix Applied**: Modified `ReadCommand` grammar to use `args*=ReadArg` with optional comma `/,/?` in each `ReadArg`, matching the pattern used by `WriteCommand`. Added `ReadArgValue` wrapper to properly dispatch to `ReadFormat`, `StringLiteral`, or `ReadTargetWithTimeout`.

#### Issue T518: OPEN command grammar fails with empty params and timeout (`::`) ✅ FIXED

**Fix Applied**: Extended `OpenArg` grammar to add a `':' ':' timeout=Expr` alternative that matches the double-colon syntax for "empty params with timeout".

### Tasks Completed

- [X] T517 [BUG] Fix READ command grammar to allow adjacent format controls without commas (R !!,"text")
- [X] T518 [BUG] Fix OPEN command grammar to allow empty params with timeout (OPEN X::10)

### Detailed File Validations

#### V1IE.m (IF/ELSE driver)
- 3 labels: V1IE, V1IE1, V1IE2
- Simple structure: WRITE and DO calls to external routines
- All statements captured correctly

#### V1IE1.m (IF/ELSE/$TEST tests - Part 1)
- 12 labels testing IF conditions, ELSE behavior, $TEST special variable
- Complex line: `I 1 S VCOMP=VCOMP_" " S:0 VCOMP=VCOMP_" " I  S VCOMP=VCOMP_"//"_$TEST`
  - Multiple SET with postconditions on same line
  - Argumentless IF (`I `)
  - $TEST special variable references
- All IF/ELSE pairs properly nested in ASG
- Label call resolution working (EXAMINER called 12 times, all resolved)

#### V1IE2.m (IF/ELSE/$TEST tests - Part 2)
- 8 labels with complex $TEST evaluations
- Features: argumentless IF, IF with comma-separated conditions
- Line 73: `K A I $D(A),A S VCOMP=...` - KILL followed by IF with $DATA
- All control flow structures preserved correctly

#### V1IO.m (I/O Control driver) - **HAS ISSUES**
- 2 labels: V1IO, END
- **Line 8 missing**: READ with format controls (`R !!,"WHEN..."`)
- **Line 10 missing**: READ + GOTO combination
- Lines with simple OPEN, USE, CLOSE correctly captured
- I/O statements (MOpenStatement, MUseStatement, MCloseStatement) present

#### V1IO1.m (I/O Control tests - Part 1)
- 10 labels testing $JOB, $IO, $X, $Y after I/O operations
- All SET/WRITE/DO statements captured
- No I/O commands in this file (tests results set by V1IO.m)

#### V1IO2.m (I/O Control tests - Part 2)
- 16 labels testing I/O effects
- **Notable**: Label 554 has FOR with 17-element string list parameter
  - `F I=532,533,534,5380,5381,5390,5391,5400,5401,5411,5412,5413,551,5521,5520,5522,553 S ...`
  - Correctly captured as MForStatement with 17 parameters

#### V1JST.m ($JUSTIFY/$SELECT/$TEXT driver)
- 4 labels: V1JST, V1JST1, V1JST2, V1JST3
- Simple driver structure calling external routines
- All statements captured correctly

### Observations for Code Generation

1. **Argumentless IF (`I ` or `IF `)** - Uses prior $TEST value; code generation must track $TEST state
2. **$TEST special variable** - Must be maintained across IF/ELSE executions
3. **I/O commands** - OPEN/USE/CLOSE need Python equivalents (file handles or context managers)
4. **$X, $Y, $IO, $JOB** - Special variables tracking cursor position and device; need runtime support
5. **READ with timeout** - `R VAR:timeout` - Needs timed input implementation

---

## Phase 30: MUGJ Validation Checklist - V1JST1 to V1MAX

**Purpose**: Validate $JUSTIFY/$SELECT/$TEXT functions and label/variable naming tests (Checklist 16/54).

**Validation Date**: 2025-12-21

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V1JST1.m | 21 | 98 | ✅ Complete | $JUSTIFY(expr,int) tests with FOR loop |
| V1JST2.m | 17 | 92 | ✅ Complete | $JUSTIFY(num,int,int) 3-arg tests |
| V1JST3.m | 22 | 90 | ✅ Complete | $SELECT and $TEXT tests; Z1,Z2,Z4 comment labels |
| V1LL1.m | 20 | 85 | ✅ Complete | Labelless first line now captured in preamble label |
| V1LL2.m | 28 | 104 | ✅ Complete | All label formats captured correctly |
| V1LVN.m | 11 | 104 | ✅ Complete | Local variable naming tests (subscripted) |
| V1MAX.m | 3 | 5 | ✅ Complete | Simple driver calling external V1MAX1/V1MAX2 |

### Issues Fixed

#### Issue T519: Labelless first line not captured in V1LL1.m ✅ FIXED

**Problem**: V1LL1.m has a labelless first line:
```mumps
	S VCOMP="LABEL LESS";;;
V1LL1	;YS-TS,V1LL,VALIDATION VERSION 7.1;31-AUG-1987;LINE LABELS -1-
```

The first line starts with whitespace (no label) and contains `S VCOMP="LABEL LESS"`. This statement was **not captured** in the ASG.

**Fix Applied**: Modified `_build_routine()` in `src/m2py/parser/parser.py` to create a synthetic "preamble" label with an empty name (`''`) for any `ContLine` that appears before the first named label. The preamble label is inserted at the beginning of the routine's labels list.

### Tasks

- [X] T519 [BUG] Support labelless first lines in MUMPS files (V1LL1.m line 1 now captured)

### Detailed File Validations

#### V1JST1.m ($JUSTIFY 2-arg tests)
- 21 labels testing `$JUSTIFY(expr1, intexpr2)` - right-padding strings
- I-555 through I-571: Various expr1 types (string, number, binary ops, globals)
- One FOR loop at label 566: `F I=1:1:255 S VCORR=VCORR_" "`
- All $J intrinsic function calls captured correctly
- EXAMINER subroutine resolved with 22 callers

#### V1JST2.m ($JUSTIFY 3-arg tests)
- 17 labels testing `$JUSTIFY(numexpr1, intexpr2, intexpr3)` - decimal formatting
- I-572 through I-585: Rounding, sign handling, decimal places
- Uses naked global references in I-585: `^V1A(2,2)`, `^(2,2,2)`, etc.
- All naked global usage preserved in ASG expressions

#### V1JST3.m ($SELECT and $TEXT tests)
- 22 labels including utility labels Z1, Z2, Z4 for $TEXT testing
- $SELECT tests (I-586 through I-592): Short-circuit evaluation, $TEST interaction
- $TEXT tests (I-593 through I-600): Line reference, +intexpr, indirection
- IF/ELSE pairs captured correctly for $TEST validation
- Comment-only labels (Z1, Z2, Z4) correctly captured with 0 statements

#### V1LL1.m (Line Labels test - Part 1)
- 20 labels: 1 preamble (empty name) + 19 named labels
- Labels like `%`, `%A`, `%ABZWQ`, `%01`, `%000000`, `%234EFGH` all captured
- Preamble label contains `S VCOMP="LABEL LESS"` from line 1
- Test I-609 "the first line is labelless" now correctly captured

#### V1LL2.m (Line Labels test - Part 2)
- 28 labels including single-letter (A), pure numeric (3, 00, 123), mixed (A1B2C3)
- All variations of valid MUMPS labels captured correctly
- EXAMINER subroutine resolved with 21 callers

#### V1LVN.m (Local Variable Names)
- 11 labels testing local variable naming rules
- Tests `%`, `%ABCDEF`, `%1234` and regular names with subscripts
- I-618: 8 levels of subscript depth `ABCDEFGH(1,2,3,4,5,6,7,8)` - captured correctly
- All subscripted variable assignments preserved in MSetStatement

#### V1MAX.m (Maximum Range Driver)
- 3 labels: V1MAX (empty), V1MAX1, V1MAX2
- Simple driver that calls external routines `^V1MAX1` and `^V1MAX2`
- External routine calls marked as `is_resolved=False` (expected)

### Observations for Code Generation

1. **$JUSTIFY intrinsic** - Needs right-padding and decimal rounding implementation
2. **$SELECT intrinsic** - Short-circuit evaluation (only evaluate until true found)
3. **$TEXT intrinsic** - Requires runtime access to source file text (or precompiled text table)
4. **Preamble labels** - Empty-name label for labelless first lines; code gen should execute before main entry
5. **% prefix labels/variables** - Valid in MUMPS, need escaping or renaming for Python
6. **Naked global references** - Must track last-used global context at runtime

---

## Phase 31: MUGJ Validation Checklist - V1MAX1 to V1NR

**Purpose**: Validate maximum range and LOCK/OPEN/NAKED reference driver files (Checklist 17/54).

**Validation Date**: 2025-12-21 (Re-validated)

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V1MAX1.m | 9 | 69 | ✅ Complete | Large literal/string range tests, FOR loops, complex expressions |
| V1MAX2.m | 7 | 43 | ✅ Complete | Deep subscript (15 levels) and 9-digit subscript tests |
| V1MJA.m | 3 | 11 | ✅ Complete | Driver with postconditioned WRITE and external DO calls |
| V1MJA1.m | 16 | 133 | ✅ Complete | LOCK variations including indirection `L @A` now captured |
| V1MJA2.m | 14 | 107 | ✅ Complete | OPEN/CLOSE/USE statements, IF/ELSE, pattern matching |
| V1MJB.m | 20 | 127 | ✅ Complete | Extensive LOCK variations with timeouts and targets |
| V1NR.m | 3 | 4 | ✅ Complete | Naked reference driver, external routine calls |

### Re-Validation Findings (2025-12-21)

Previous issues (T520-T522) have been resolved. Current validation confirms:

1. ✅ **LOCK command variations** - All standard forms work correctly:
   - Simple lock: `L ^V1A(1,2)`
   - Parenthesized list with timeout: `L (^V1A,^V1B):1`
   - Postconditioned lock: `L:1=0.1 ^V1A(2,2)`
   - Lock with timeout: `L ^V1A(2):1`
   - Lock on local variables: `L A(1,1)`
   - Argumentless unlock: `L`
   - Lock operators: `+` and `-`

2. ⚠️ **NEW ISSUE - LOCK with indirection not captured**:
   - File: V1MJA1.m, line 55, label 635
   - Source: `S A="^V1A" L @A K ^V1F`
   - The `L @A` (LOCK with name indirection) is silently skipped
   - Root cause: `LockTarget` grammar rule uses `VarRef` which is `GlobalVariable | LocalVariable`
   - Indirection `@expr` is not part of `VarRef`, so the parse fails and command is dropped

3. ✅ **I/O commands** - OPEN, CLOSE, USE, READ all captured correctly with:
   - Device expressions
   - Timeouts
   - Postconditions
   - Argument lists

4. ✅ **Special variables** - `$Y`, `$JOB`, `$IO`, `$TEST`, `$D` all captured in expressions

5. ✅ **Pattern matching** - Expressions like `$JOB?1N.N` properly captured as pattern match operations

### Tasks

- [x] T520 [BUG] Handle `K  L  Q` tails as Kill + unlock-only Lock (no targets) + Quit in command parsing.
  - **Root cause**: LockCommand grammar used `WS?` which was greedy and consumed the next command keyword as a lock target.
  - **Fix**: Changed LockCommand grammar to require single space before targets like KillCommand: `(' ' lockop=LockOp? (locklist=LockList | targets+=LockTarget[/,/]))?`
  - **Result**: Now correctly parses "double-space = argumentless command" pattern. 642 tests pass.
- [x] T521 [BUG] Preserve multi-command lines with K/LOCK/K in V1MJA1 (label 632/635).
  - **Fixed by T520**: Grammar fix allows proper command separation.
- [x] T522 [BUG] Fix empty labels 632/634/635 in V1MJB.
  - **Fixed by T520**: Grammar fix plus semantic analyzer update to handle parenthesized lock lists (`locklist`).
  - **Added**: `_analyze_LockCommand` now processes `cmd.locklist` for parenthesized lock targets like `L (^A,^B):1`.
- [x] T523 [US5] Add indirection support to LOCK command grammar
  - **File**: V1MJA1.m, label 635, line 55: `L @A`
  - **Root cause**: `LockTarget` used `VarRef` which doesn't include `Indirection`
  - **Fix**: Extended grammar to support indirection in lock targets:
    - Added `LockListItem` rule: `indirect=IndirectChain | target=VarRef`
    - Updated `LockTarget` rule: `postcond? (indirect | target) (':' timeout)?`
    - Added `_analyze_lock_item()` and `_analyze_lock_target()` helper methods
    - Reused existing `_analyze_indirect_chain()` for consistent handling
  - **Result**: Lock indirection now captured with semantic structure:
    - `is_indirect: True` flag for code generation
    - `indirection`: The expression to dereference at runtime
    - `indirection_levels`: Supports nested indirection (@@A)
  - **Impact**: V1MJA1 label 635 now has 10 statements (was 7), all commands captured

---

## Phase 32: MUGJ Validation Checklist - V1NR1 to V1NUM

**Purpose**: Validate nesting/label/naked-reference tests (Checklist 18/54) ahead of codegen.

**Validation Date**: 2025-12-21

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V1NR1.m | 6 | 63 | ✅ Complete | Naked reference sequencing; EXAMINER backref resolved |
| V1NR2.m | 7 | 52 | ✅ Complete | Naked reference with KILL variations and data checks |
| V1NST1.m | 68 | 198 | ✅ Complete | Deep FOR/DO nesting (14 levels), external DO/GOTO links |
| V1NST2.m | 47 | 129 | ✅ Complete | Indirection-heavy DO chain; name/argument indirection captured |
| V1NST3.m | 52 | 136 | ✅ Complete | Mixed GOTO nesting across routines; FOR/QUIT exits captured |
| V1NSTE.m | 46 | 98 | ✅ Complete | External GOTO/DO ladder, nested FOR with postconditioned QUIT |
| V1NUM.m | 5 | 9 | ✅ Complete | Numeric literal driver calling ^V1NUM* routines |

### Observations for Code Generation

1. DO indirection (V1NST2 label 657) is captured as `MDo` with `indirection`; runtime will need to execute the comma-separated target list contained in the dereferenced string.
2. Deep nested FOR/QUIT structures (V1NST1/V1NST3) are represented as nested `MForStatement` bodies with postconditioned `MQuit`—codegen should preserve early-exit semantics.
3. External GOTO/DO chains (V1NSTE/V1NST3) resolve to `MCall` with `routine` set, confirming cross-routine linkage is available for future call graph analysis.

---

## Phase 33: MUGJ Validation Checklist - V1NUM1 to V1NX2

**Purpose**: Validate numeric literal edge cases and $NEXT traversal routines (Checklist 19/54).

**Validation Date**: 2025-12-21

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V1NUM1.m | 6 | 102 | ✅ Complete | Numeric literal tests - leading zeros; format controls as MFormatControl |
| V1NUM2.m | 5 | 80 | ✅ Complete | Numeric literal tests - trailing zeros, multiple minus signs |
| V1NUM3.m | 4 | 85 | ✅ Complete | Numeric literal tests - scientific notation |
| V1NUM4.m | 4 | 109 | ✅ Complete | String-to-numeric head extraction with unary +/- |
| V1NX.m | 3 | 4 | ✅ Complete | $NEXT driver - external routine calls |
| V1NX1.m | 8 | 73 | ✅ Complete | $NEXT tests; naked global SET targets fixed (T526) |
| V1NX2.m | 16 | 62 | ✅ Complete | $NEXT with GOTO patterns; label targets resolved |

### Tasks

- [x] T524 [BUG] Convert Write formatting tokens (Newl, Form, Tab, Backspace, etc.) to ASG expressions during `_analyze_WriteCommand` / `_build_expression_asg`.
   - **Fix Applied**: Added `MFormatControl` ASG class and `FormatControlType` enum in `src/m2py/asg/`. Added handler methods `_analyze_Newline`, `_analyze_FormFeed`, `_analyze_Tab`, `_analyze_CharCode` in `semantic_analyzer.py`.
   - **Result**: All format controls (!, #, ?n, *n) now converted to proper `MFormatControl` ASG objects with `FormatControlType` classification. 669 tests passing.
- [x] T525 [BUG] Normalize postconditioned Write control arguments (e.g., `W:$Y>55 #`) into concrete ASG literals instead of textX control nodes.
   - **Fix Applied**: Same fix as T524 - the analyze dispatch now routes all FormatControl textX types to dedicated handlers that create `MFormatControl` ASG nodes.
   - **Result**: Postconditioned writes like `W:$Y>55 #` now produce `MFormatControl(control_type=FORMFEED)` with proper postcondition expression.

### Outstanding Issues

- [X] T526 [BUG] Naked globals (`^(...)`) fail to parse as SET targets - grammar issue
   - **Root Cause**: `SingleTarget` rule in `commands.tx` allows `GlobalVariable | LocalVariable | Indirection` but does NOT include `NakedGlobal`. When parser encounters `S ^(1)=1`, it fails to match and silently drops the entire SET statement.
   - **Affected Files**: V1NX1.m line 37: `S ^V1(1)=1,^V1(200)=200,^(30,30)=3030,^(3,3)=33` - only first 2 assignments parsed
   - **Fix Applied**: 
     1. Added `NakedGlobal` to `SingleTarget` rule in `src/m2py/grammar/commands.tx` (placed before GlobalVariable due to ambiguous `^` prefix)
     2. Added `NakedGlobal` handling in `convert_to_variable()` in `src/m2py/analysis/command_parser.py`
     3. Added 6 unit tests for grammar and analysis levels
   - **Result**: SET statements with naked global targets now parse correctly with all assignments captured

### Observations for Code Generation

1. **MFormatControl** - New ASG type representing I/O format controls:
   - `control_type`: `FormatControlType.NEWLINE` (!), `FORMFEED` (#), `TAB` (?n), `CHARCODE` (*n)
   - `expression`: For TAB and CHARCODE, contains the column/character code expression
2. **$NEXT function** - V1NX1/V1NX2 test traversal with $NEXT($N) intrinsic; properly captured as MIntrinsicFunction
3. **Naked global references in expressions** - Used extensively in V1NX1/V1NX2 for testing; properly captured as MNakedGlobal in expressions like `$N(^(1))`
4. **Naked global references as SET targets** - ⚠️ **BUG**: Not currently parsed - see T526
5. **Numeric literal canonicalization** - V1NUM1-4 test leading/trailing zero removal and scientific notation; literal values captured with original precision
6. **Unary operators on strings** - V1NUM4 tests numeric interpretation (`+"123ABC"` → 123); captured as MUnaryOp with StringLiteral operand
7. **$Y special variable** - Used in EXAMINER postconditions (`W:$Y>55 #`); properly captured as SpecialVariable

---

## Phase 34: MUGJ Validation Checklist - V1OV to V1PC1

**Purpose**: Validate overlay GOTO, pattern matching, and post-conditional drivers (Checklist 20/54).
**Validation Date**: 2025-12-21

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V1OV.m | 23 | 101 | ✅ Complete | All GOTO targets resolved; offsets captured |
| V1OV1.m | 20 | 68 | ✅ Complete | EXAMINER backrefs resolved; offset GOTOs captured |
| V1PAT.m | 3 | 5 | ✅ Complete | Driver only (WRITE + DO) |
| V1PAT1.m | 10 | 72 | ✅ Complete | Pattern atom and count loops captured; MPatternMatch with subject/pattern |
| V1PAT2.m | 12 | 75 | ✅ Complete | Complex patterns with multipliers, indirection, negation |
| V1PC.m | 3 | 4 | ✅ Complete | Driver only (WRITE + DO) |
| V1PC1.m | 39 | 122 | ⚠️ Minor | Postconditioned GOTOs good; $TEXT function arg parsing issue |

### Findings

1. **Pattern Match Parsing (V1PAT1, V1PAT2)**: `MPatternMatch` correctly captures:
   - `subject`: The expression being matched
   - `pattern`: The pattern string (e.g., "1C", "5N", ".A.P")
   - `pattern_indirect`: For `?@X` indirect patterns
   - `operator`: `?` or `'?` (not match)

2. **V1OV GOTO Offsets**: All label+offset references (`G XYZ+0^V1OV1`) captured correctly with:
   - `MCall.offset` as `NumericLiteral` or `MBinaryOp`
   - Complex offset expressions (e.g., `G 691+A/9-11/19^V1OV`) preserved as expression trees

3. **V1PC1 $TEXT Function Issue**: Line `G:$T(V1PC1+300)="" ...` parses `$T(V1PC1+300)` incorrectly:
   - Expected: `$TEXT` with label reference argument `V1PC1+300`
   - Actual: `$T` with `LocalVariable(name='V1PC1')` - the `+300` offset is dropped
   - The `$TEXT` function expects a `labelref` argument (label+offset^routine), not an expression

4. **V1OV Multi-target GOTOs**: Lines like `G ^V1OV1,^V1OV1` correctly capture multiple MCall targets

5. **V1PC1 Postconditioned GOTOs**: Both command-level (`G:cond target`) and target-level (`G target:cond`) postconditions captured

### Tasks

- [ ] T527 [BUG] Fix $TEXT function argument parsing to handle `label+offset` as a labelref, not expression
  - Repro: `$T(V1PC1+300)` should parse as label=V1PC1, offset=300, not as LocalVariable(V1PC1)
  - Need to recognize `$T` / `$TEXT` and parse argument as labelref

- [X] T528 [RESOLVED] V1PAT2 pattern parsing issues - previously noted bugs now passing (75 statements captured)

### Observations for Code Generation

1. **MPatternMatch** semantics:
   - Returns 1 (true) or 0 (false) in MUMPS
   - Pattern codes: C (control), N (numeric), P (punctuation), A (alpha), L (lower), U (upper), E (everything)
   - Multipliers: `0`, `1-9`, `.` (zero or more), `n.m` (range)
   - Python will need a pattern matcher implementation or regex translation

2. **Label+Offset References**:
   - `G label+n^routine` jumps to n lines after label
   - Python code gen must compute actual target or use a label registry

3. **$TEXT Function**:
   - Returns source text of line at label+offset
   - Rarely used in production code but important for meta-programming
   - May need stub implementation returning empty string

4. **GOTO Lists with Postconditions**:
   - `G target1:cond1,target2:cond2` - each target has own postcondition
   - Python: `if cond1: goto target1; elif cond2: goto target2`

---

## Phase 35: MUGJ Validation Checklist - V1PCA to V1PRGD2

**Purpose**: Validate postcondition-heavy drivers and preliminary GOTO/DO/QUIT behavior (Checklist 21/54).
**Validation Date**: 2025-12-21

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V1PCA.m | 29 | 152 | ⚠️ Issues | GOTO target postconditions/offsets dropped |
| V1PCB.m | 26 | 143 | ⚠️ Issues | DO target postconditions/offsets dropped |
| V1PO.m | 8 | 62 | ⚠️ Needs spot-check | Operator-precedence expressions not yet inspected in ASG |
| V1PRFOR.m | 5 | 35 | ✅ | FOR params captured; classification not reviewed here |
| V1PRGD.m | 11 | 77 | ⚠️ Minor | Statements after QUIT not marked unreachable |
| V1PRGD1.m | 2 | 12 | ⚠️ Minor | Statements after QUIT not marked unreachable |
| V1PRGD2.m | 1 | 2 | ⚠️ Minor | Implicit QUIT missing (label ends with fallthrough) |

### Findings

1. **GOTO target postconditions and offsets lost (V1PCA)**
   - Examples: [tests/functional/mugj/inref/V1PCA.m#L44-L48], [tests/functional/mugj/inref/V1PCA.m#L50-L66]
   - MCalls created from GOTO lists do not retain target-level postconditions (`:expr`) or label offsets (`+n`). External targets (label^routine) are flattened into names without per-target metadata, preventing correct branching order.
2. **DO target postconditions and offsets lost (V1PCB)**
   - Examples: [tests/functional/mugj/inref/V1PCB.m#L11-L20], [tests/functional/mugj/inref/V1PCB.m#L22-L35], [tests/functional/mugj/inref/V1PCB.m#L39-L71]
   - DO lists collapse into a single MDoStatement without preserving per-target postconditions or offsets (`+n`). Offset DO calls (`BYTE+2`, `OS+2^V1PC1`, etc.) are emitted as plain CALL(BYTE) / CALL(^V1PC1OS) with no offset data.
3. **Unreachable code after QUIT not flagged (V1PRGD/V1PRGD1)**
   - Examples: [tests/functional/mugj/inref/V1PRGD.m#L34-L37], [tests/functional/mugj/inref/V1PRGD1.m#L3-L6]
   - Statements following explicit QUIT remain in bodies with no `is_unreachable` tagging, making downstream control-flow analysis/codegen harder.
4. **Implicit QUIT missing for fallthrough labels (V1PRGD2)**
   - Example: [tests/functional/mugj/inref/V1PRGD2.m#L1-L4]
   - Routine ends with SET/WRITE and comment; ASG stops without a terminating MQuitStatement, so callers cannot tell the label exits.

### Tasks

- [X] T529 [FALSE POSITIVE] GOTO target postconditions and offsets ARE captured correctly.
  - **Verified**: `MCall.offset` and `MCall.postcondition` are populated for GOTO targets.
  - The validate_asg.py compact display just wasn't showing these fields.
  - Test: V1PCA label 838 shows BUG+2 with postcondition MBinaryOp and TABLE+1 with postcondition IntrinsicFunction.
- [X] T530 [FALSE POSITIVE] DO target postconditions and offsets ARE captured correctly.
  - **Verified**: `MCall.offset` and `MCall.postcondition` are populated for DO targets.
  - Test: V1PCB label 843 shows BYTE+2:$D(A) and BYTE+1:'$D(A) with proper offsets and postconditions.
- [ ] T531 [BUG] Mark statements after unconditional QUIT as unreachable.
  - During semantic analysis, flag statements after QUIT/QUIT-return as `is_unreachable=True` for accurate CFG/codegen.
  - The `detect_unreachable_code()` function exists but is never called/integrated into the ASG.
  - Need to add post-processing pass to mark statements in label bodies.
- [ ] T532 [ENHANCEMENT] Add `has_explicit_exit` flag to MLabel.
  - Instead of synthesizing implicit QUIT, track whether label ends with explicit exit (QUIT/GOTO/HALT).
  - This is informational for code generation; MUMPS semantics already imply fallthrough returns.

---

## Phase 36: MUGJ Validation Checklist - V1PRGD3 to V1READA1

**Purpose**: Validate preliminary GOTO/DO/QUIT label tests and READ command drivers (Checklist 22/54).
**Validation Date**: 2025-12-21

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V1PRGD3.m | 3 | 9 | ⚠️ Minor | Statements after unconditional GOTO remain reachable (extends unreachable-code issue)
| V1PRIE.m | 4 | 36 | ✅ | IF/ELSE chains captured; nested ELSE blocks preserved
| V1PRSET.m | 7 | 36 | ✅ | SET/KILL/WRITE sequences captured; format controls normalized
| V1RANDA.m | 24 | 66 | ✅ | $RANDOM loop tests captured; DO EXT/FIND targets resolved
| V1RANDB.m | 14 | 70 | ✅ | $RANDOM gap/frequency tests captured; nested DO/QUIT preserved
| V1READA.m | 3 | 5 | ✅ | Driver DO calls to ^V1READA1/^V1READA2 resolved
| V1READA1.m | 11 | 72 | ⚠️ Issues | READ arguments still contain raw textX format nodes (Newl/Tab) instead of ASG expressions

### Findings

1. **READ arguments not normalized to ASG (V1READA1 labels 749-756)**
    - `MReadStatement.arguments` contain `textx:commands.Newl`/`Tab` objects rather than `MFormatControl`/expression nodes.
    - Root cause: `_analyze_ReadCommand` passes textX command nodes through without routing to `_build_expression_asg` or format-control handlers.
    - Impact: Codegen cannot interpret READ format controls, timeouts, or prompts consistently.

2. **Unreachable code after unconditional GOTO not flagged (V1PRGD3 line 4)**
    - Line `S VCOMP=VCOMP_3 G B` is followed by additional SET/QUIT statements that remain marked reachable.
    - Existing unreachable detection (T531) covers QUIT-only; needs extension to unconditional transfers like GOTO.

### Tasks

- [X] T533 [BUG] Normalize READ arguments to ASG format controls/expressions.
  - **Root Cause**: `_analyze_ReadCommand` checked for format control class names (`Newline`, `FormFeed`, `Tab`) but appended raw textX nodes directly instead of calling `self.analyze()` to convert them to `MFormatControl` ASG nodes.
  - **Fix Applied**: Changed line 537-538 in `semantic_analyzer.py` to call `self.analyze(arg_value, stmt)` for format controls, routing through `_analyze_Newline`/`_analyze_FormFeed`/`_analyze_Tab`/`_analyze_CharCode` handlers.
  - **Test Added**: `test_read_format_controls_as_asg_nodes` in `tests/unit/test_grammar.py` verifies READ format controls are proper `MFormatControl` ASG nodes.
  - **Result**: 709 tests passing.

- [X] T534 [FALSE POSITIVE] Unreachable code after unconditional GOTO IS already detected.
  - **Verified**: V1PRGD3.m statements [4] and [5] after unconditional GOTO are already marked `is_unreachable=True`.
  - The existing unreachable code detection in `detect_unreachable_code()` handles both QUIT and GOTO transfers correctly.

---

## Phase 37: MUGJ Validation Checklist - V1READA2 to V1SEQ1

**Purpose**: Validate READ timeout/indirection behaviors and execution-sequence routines (Checklist 23/54).
**Validation Date**: 2025-12-22

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V1READA2.m | 7 | 62 | ⚠️ Issues | `*lvn` reads parsed as plain variables; char-read intent lost |
| V1READB.m | 3 | 4 | ✅ | Driver DOs to ^V1READB1/^V1READB2 captured |
| V1READB1.m | 6 | 71 | ⚠️ Issues | READ timeouts (`:0`, `:-1`, `:100`, `:10`) dropped; char-read semantics not captured |
| V1READB2.m | 12 | 81 | ⚠️ Issues | READ timeouts (`:100`) discarded; read-level indirection kept as raw targets |
| V1RN.m | 8 | 52 | ✅ | Routine-name DO lists captured (single and multi-target DO) |
| V1SEQ.m | 29 | 134 | ✅ | Execution sequence flows (DO/GOTO/XECUTE) captured and resolved |
| V1SEQ1.m | 10 | 22 | ✅ | Helper labels and cross-routine DO/GOTO captured |

### Findings

1. **READ timeouts are dropped (V1READB1, V1READB2)**
    - `ReadTargetWithTimeout` nodes append only the target; the `timeout` expression is ignored so `$TEST` behavior for time-limited reads is lost. Seen in [tests/functional/mugj/inref/V1READB1.m#L9-L39](tests/functional/mugj/inref/V1READB1.m#L9-L39) and [tests/functional/mugj/inref/V1READB2.m#L46-L56](tests/functional/mugj/inref/V1READB2.m#L46-L56).
    - Root cause: `_analyze_ReadCommand` appends the analyzed `target` but never stores `timeout` from `ReadTargetWithTimeout` ([src/m2py/analysis/semantic_analyzer.py#L526-L536](src/m2py/analysis/semantic_analyzer.py#L526-L536)).

2. **Char READ (`*lvn`) semantics lost (V1READA2, V1READB1)**
    - `*` arguments are emitted as plain `MVariable` entries in `MReadStatement.arguments`, so codegen cannot distinguish char-by-char reads from line reads (affects tests 757-758, 760/763/765). Examples in [tests/functional/mugj/inref/V1READA2.m#L11-L44](tests/functional/mugj/inref/V1READA2.m#L11-L44) and [tests/functional/mugj/inref/V1READB1.m#L9-L30](tests/functional/mugj/inref/V1READB1.m#L9-L30).
    - Root cause: `_analyze_ReadCommand` unwraps `CharRead` into `LocalVariable` with no flag or distinct ASG node ([src/m2py/analysis/semantic_analyzer.py#L526-L536](src/m2py/analysis/semantic_analyzer.py#L526-L536)).

### Tasks

- [x] T535 [BUG] Preserve READ timeouts from `ReadTargetWithTimeout`.
   - Store the analyzed `timeout` expression alongside the target (new field on `MReadArgument`/`MReadTarget` or structured tuple) so `$TEST` and blocking behavior are preserved for `:0`, `:-1`, `:10`, `:100` cases.
   - Update semantic analyzer and any ASG classes needed; add regression tests covering V1READB1 and V1READB2 timeout scenarios.

- [x] T536 [BUG] Represent char-read (`*lvn`) distinctly in ASG.
   - Introduce an ASG wrapper or flag so char reads are not flattened into normal variable targets.
   - Ensure semantic analyzer preserves the distinction and add tests for single-character reads in V1READA2/V1READB1.

---

## Phase 38: MUGJ Validation Checklist - V1SET to V1UO2A

**Purpose**: Validate SET command variations, special variables ($HOROLOG, $STORAGE), and unary operator tests (Checklist 24/54).
**Validation Date**: 2025-12-22

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V1SET.m | 10 | 120 | ⚠️ Issues | Multi-assignment `(A,B,C)=1` stored as list target, not expanded |
| V1SVH.m | 7 | 37 | ✅ | Pattern match and $HOROLOG captured correctly |
| V1SVS.m | 6 | 51 | ✅ | $STORAGE tests and argumentless KILL captured |
| V1UO.m | 11 | 20 | ✅ | Simple driver pattern with external routine calls |
| V1UO1A.m | 6 | 65 | ⚠️ Issues | $H abbreviation misclassified as IntrinsicFunction |
| V1UO1B.m | 6 | 111 | ✅ | Unary plus tests captured |
| V1UO2A.m | 6 | 65 | ⚠️ Issues | $T abbreviation misclassified as IntrinsicFunction |

### Findings

1. **Multi-assignment SET stores target as list instead of expanding (V1SET labels 785, 786)**
   - `S (A,B,C,D,E,F,^V1,^V1A)=1` creates a single `MAssignment` with `target` as a list of 8 variables.
   - Per data-model.md, each `MAssignment` should have a single target; the semantic analyzer should expand this into 8 separate assignments with the same value.
   - Impact: Code generation must handle list targets specially or risk incorrect semantics.
   - Root cause: `_analyze_SetCommand` in `semantic_analyzer.py` lines 467-468 stores `ParenTargets.targets` as a list in `MAssignment.target` instead of expanding.

2. **Special variable abbreviations misclassified as IntrinsicFunction**
   - `$H` (abbreviation of `$HOROLOG`) → `IntrinsicFunction` ❌ (should be `SpecialVariable`)
   - `$S` (abbreviation of `$STORAGE` or `$SELECT`) → `IntrinsicFunction` ❌
   - `$T` (abbreviation of `$TEST`) → `IntrinsicFunction` ❌
   - Full names work correctly: `$HOROLOG`, `$TEST`, `$Y` → `SpecialVariable` ✅
   - Root cause: The parser or textX grammar doesn't recognize single-letter abbreviations as special variables.
   - Impact: Code generation may call non-existent functions instead of accessing special variable values.

3. **Naked globals correctly tracked**
   - `^(2)` (naked global) → `NakedGlobal` with `requires_runtime_tracking=True` ✅
   - Subscripts captured correctly.

4. **Pattern match correctly captured**
   - `$HOROLOG?1N.N` → `MPatternMatch` with `subject=SpecialVariable(HOROLOG)`, `pattern="1N.N"` ✅

### Tasks

- [x] T537 [BUG] Expand multi-assignment SET `(A,B,C)=value` into separate MAssignment objects. ✅
   - Modified `_analyze_SetCommand` in `semantic_analyzer.py` to iterate over `ParenTargets.targets` and create one `MAssignment` per target, all with the same value expression.
   - Added tests: `test_set_parenthesized_multi_target_expansion`, `test_set_parenthesized_with_globals`, `test_set_parenthesized_mixed_with_regular`.
   - Location: [src/m2py/analysis/semantic_analyzer.py#L466-L497](src/m2py/analysis/semantic_analyzer.py#L466-L497)

- [x] T538 [BUG] Recognize abbreviated special variables ($H, $S, $T, $J, $I, etc.) as SpecialVariable. ✅
   - Updated `SVARNAME` regex in `expressions.tx` to include abbreviations: D, H, I, J, K, P, Q, R, S, T, X, Y, EC, ES, ET, ST, SY, ZL.
   - Reordered grammar: `IntrinsicFunction` (with required args) → `SpecialVariable` → `IntrinsicFunctionNoArgs` (catch-all for $ZVersion etc.).
   - Added `IntrinsicFunctionNoArgs` textX class for unknown $ items like `$ZVersion`.
   - Added tests: `test_abbreviated_horolog`, `test_abbreviated_storage`, `test_abbreviated_test`, `test_abbreviated_job`, `test_abbreviated_io`, `test_abbreviated_device`, `test_select_function_still_works`.
   - Location: [src/m2py/grammar/expressions.tx#L281-L286](src/m2py/grammar/expressions.tx#L281-L286)

### Code Generation Considerations (Documented)

1. **Naked globals require runtime context tracking** - The ASG correctly identifies them but code generation needs to track the "last referenced global" across statements.

2. **MUMPS numeric coercion rules** - Unary operators `+` and `-` follow specific string-to-number rules that must be replicated in Python runtime.
