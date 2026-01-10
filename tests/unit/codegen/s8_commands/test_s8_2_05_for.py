"""Tests for FOR command code generation (§8.2.5).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.5
"""

import pytest


@pytest.mark.codegen
class TestForCommandCodegen:
    """Codegen-level tests for FOR command code generation (§8.2.5)."""

    def test_for_counted_to_range(self, generate_python):
        """FOR counted generates Python range loop (§8.2.5)."""
        code = generate_python("TEST\n F I=1:1:3 W I\n Q\n")
        assert "for I in range(" in code
        assert "_for_step" in code
        assert "_for_end" in code

    def test_for_list_to_for_in(self, generate_python):
        """FOR list generates Python for-in loop (§8.2.5)."""
        code = generate_python('TEST\n F I="A","B","C" W I\n Q\n')
        assert 'for I in ["A", "B", "C"]:' in code

    def test_for_bounded_iteration(self, execute_mumps):
        """FOR bounded range outputs correct values.

        User Story 3 acceptance scenario 1 (T036):
        Given: F I=1:1:3 W I
        When: generated and executed
        Then: output is "123" (end-inclusive)
        """
        result = execute_mumps("TEST\n F I=1:1:3 W I\n Q\n")
        assert result.output == "123"
        assert result.success is True

    def test_for_decrement_iteration(self, execute_mumps):
        """FOR decrement range outputs correct values.

        User Story 3 acceptance scenario 2 (T037):
        Given: F I=5:-1:3 W I
        When: generated and executed
        Then: output is "543" (end-inclusive, negative step)
        """
        result = execute_mumps("TEST\n F I=5:-1:3 W I\n Q\n")
        assert result.output == "543"
        assert result.success is True

    def test_for_string_list_iteration(self, execute_mumps):
        """FOR string list outputs correct values.

        User Story 3 acceptance scenario 3 (T038):
        Given: F I="A","B","C" W I
        When: generated and executed
        Then: output is "ABC"
        """
        result = execute_mumps('TEST\n F I="A","B","C" W I\n Q\n')
        assert result.output == "ABC"
        assert result.success is True

    def test_for_open_ended_with_quit(self, generate_python):
        """FOR open-ended generates itertools.count loop with QUIT (§8.2.5).

        T023: Open-ended FOR with QUIT
        Given: F I=1:1 W I Q:I=5
        When: generated
        Then: uses itertools.count and has conditional exit
        """
        code = generate_python("TEST\n F I=1:1 D\n . W I\n . I I=5 Q\n Q\n")
        assert "from itertools import" in code
        assert "count(" in code
        assert "for I in count(" in code

    def test_for_argumentless_with_do_block(self, generate_python):
        """FOR argumentless generates while True loop (§8.2.5).

        T024: Argumentless FOR with DO block
        Given: F  D ... (with dot-indented body)
        When: generated
        Then: uses while True pattern
        """
        code = generate_python(
            "TEST\n S X=3\n F  D\n . S X=X-1\n . W X\n . I X=0 Q\n Q\n"
        )
        assert "while True:" in code

    def test_for_mixed_parameters(self, execute_mumps):
        """FOR mixed parameters iterates all in order (§8.2.5).

        T025: Mixed parameter FOR
        Given: F I=1:1:3,"X",10:2:14 W I
        When: generated and executed
        Then: output is "123X101214"
        """
        result = execute_mumps('TEST\n F I=1:1:3,"X",10:2:14 W I\n Q\n')
        assert result.output == "123X101214"
        assert result.success is True

    def test_for_loop_var_modification(self, execute_mumps):
        """FOR with modified loop var uses while pattern (§8.2.5).

        T026: FOR with loop var modification
        Given: F I=1:1:10 S I=I+2 W I I I>8 Q
        When: generated and executed
        Then: output is "369" (I=1, set I=3, write, next I=4, set I=6, write, I=7, set I=9, write, I>8 quit)
        """
        result = execute_mumps("TEST\n F I=1:1:10 S I=I+2 W I I I>8 Q\n Q\n")
        assert result.output == "369"
        assert result.success is True

    def test_for_negative_step_bounds(self, execute_mumps):
        """FOR negative step iterates correctly (§8.2.5).

        T027: Negative step FOR bounds
        Given: F I=10:-2:2 W I
        When: generated and executed
        Then: output is "108642" (inclusive end)
        """
        result = execute_mumps("TEST\n F I=10:-2:2 W I\n Q\n")
        assert result.output == "108642"
        assert result.success is True

    def test_for_nested(self, execute_mumps):
        """Nested FOR generates nested Python loops (§8.2.5)."""
        result = execute_mumps("TEST\n F I=1:1:2 F J=1:1:2 W I,J\n Q\n")
        assert result.output == "11122122"
        assert result.success is True


@pytest.mark.codegen
class TestForGenContextCodegen:
    """Tests for ForGenContext helper dataclass (Spec 005)."""

    def test_for_gen_context_from_bounded_statement(self):
        """ForGenContext correctly analyzes bounded FOR loop."""
        from m2py.asg.enums import ForLoopType, ForParamType
        from m2py.asg.statements import MForParameter, MForStatement
        from m2py.asg.elements import MScope
        from m2py.asg.expressions import MLiteral
        from m2py.codegen.statements import ForGenContext

        # Create a bounded FOR: F I=1:1:10
        param = MForParameter(
            param_type=ForParamType.RANGE,
            start=MLiteral(value=1),
            step=MLiteral(value=1),
            end=MLiteral(value=10),
        )
        stmt = MForStatement(
            loop_var="I",
            parameters=[param],
            body=MScope(statements=[]),
        )

        ctx = ForGenContext.from_statement(stmt)
        assert ctx.loop_var == "I"
        assert ctx.loop_type == ForLoopType.BOUNDED
        assert ctx.is_infinite is False

    def test_for_gen_context_from_string_list(self):
        """ForGenContext correctly analyzes string list FOR loop."""
        from m2py.asg.enums import ForLoopType, ForParamType
        from m2py.asg.statements import MForParameter, MForStatement
        from m2py.asg.elements import MScope
        from m2py.asg.expressions import MLiteral
        from m2py.codegen.statements import ForGenContext

        # Create a string list FOR: F I="A","B"
        param = MForParameter(
            param_type=ForParamType.VALUE,
            value=MLiteral(value="A"),
        )
        stmt = MForStatement(
            loop_var="I",
            parameters=[param],
            body=MScope(statements=[]),
        )

        ctx = ForGenContext.from_statement(stmt)
        assert ctx.loop_var == "I"
        assert ctx.loop_type == ForLoopType.STRING_LIST

    def test_for_gen_context_from_argumentless(self):
        """ForGenContext correctly analyzes argumentless FOR loop."""
        from m2py.asg.enums import ForLoopType
        from m2py.asg.statements import MForStatement
        from m2py.asg.elements import MScope
        from m2py.codegen.statements import ForGenContext

        # Create argumentless FOR: F (no parameters)
        stmt = MForStatement(
            loop_var="",
            parameters=[],
            body=MScope(statements=[]),
        )

        ctx = ForGenContext.from_statement(stmt)
        assert ctx.loop_type == ForLoopType.ARGUMENTLESS
        assert ctx.is_infinite is True

    def test_for_gen_context_detects_modified_loop_var(self):
        """ForGenContext detects loop variable modification from analysis."""
        from m2py.asg.enums import ForParamType
        from m2py.asg.statements import MForParameter, MForStatement
        from m2py.asg.elements import MScope
        from m2py.asg.expressions import MLiteral
        from m2py.codegen.statements import ForGenContext

        param = MForParameter(
            param_type=ForParamType.RANGE,
            start=MLiteral(value=1),
            step=MLiteral(value=1),
            end=MLiteral(value=10),
        )
        stmt = MForStatement(
            loop_var="I",
            parameters=[param],
            body=MScope(statements=[]),
        )
        # Set analysis flag
        stmt.loop_var_modified_in_body = True

        ctx = ForGenContext.from_statement(stmt)
        assert ctx.use_while is True
