"""Tests for QUIT command code generation (§8.2.16).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.16
"""

import pytest


@pytest.mark.codegen
class TestQuitCommandCodegen:
    """Codegen-level tests for QUIT command code generation (§8.2.16)."""

    def test_quit_to_return(self, generate_python):
        """QUIT outside loop generates return statement (§8.2.16).

        T046: QUIT in label body (not in FOR) generates return.
        """
        source = "TEST W 1 Q"
        code = generate_python(source)
        assert "return" in code

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: QUIT with value - Spec 008")
    def test_quit_with_value(self, generate_python):
        """QUIT expr generates return value (§8.2.16).

        T048: QUIT with return_value generates return <expr>.
        Full extrinsic function support is Spec 008.
        """
        pytest.fail("Stub - extrinsic functions deferred to Spec 008")

    def test_quit_in_for(self, generate_python):
        """QUIT in FOR generates break (§8.2.16).

        T046: QUIT with exits_for=True or inside loop_stack generates break.
        """
        source = """TEST F I=1:1:10 Q
 Q"""
        code = generate_python(source)
        # The QUIT inside FOR should generate break
        assert "break" in code


@pytest.mark.codegen
class TestQuitContextAwareness:
    """Tests for QUIT context-aware code generation (US6).

    Phase 8: QUIT generates different Python code based on context:
    - In FOR loop: break
    - In DO block: break (exits the block's while True wrapper)
    - With return value: return <expr>
    - Otherwise: return
    """

    def test_quit_in_for_generates_break(self, generate_python):
        """T046: QUIT inside FOR loop generates break.

        When exits_for flag is set or loop_stack is non-empty,
        QUIT exits the innermost FOR loop.
        """
        source = """TEST F I=1:1:5 W I I I=3 Q
 Q"""
        code = generate_python(source)
        assert "break" in code
        # Verify it's inside the for loop structure
        assert "for " in code

    def test_quit_in_do_block_generates_break(self, generate_python):
        """T047: QUIT inside DO block generates break.

        DO blocks use while True: pattern, so QUIT exits via break.
        This allows code after the DO block to continue executing.
        """
        source = """TEST D
 . W "A"
 . Q
 . W "B"
 W "C" Q"""
        code = generate_python(source)
        # DO block should use while True pattern
        assert "while True:" in code
        # QUIT inside block should be break
        lines = code.split("\n")
        # Find break inside the while True block
        in_while = False
        found_break_in_while = False
        for line in lines:
            if "while True:" in line:
                in_while = True
            if in_while and "break" in line:
                found_break_in_while = True
                break
        assert found_break_in_while, "QUIT in DO block should generate break"

    def test_quit_do_block_execution(self, execute_mumps):
        """T047: QUIT in DO block exits only the block (execution test).

        MUMPS semantics: QUIT in DO block returns from the block,
        execution continues after the block.
        Expected output: "AC" (A written, Q exits block, C written)
        """
        source = """TEST D
 . W "A"
 . Q
 . W "B"
 W "C" Q"""
        result = execute_mumps(source)
        assert result.output == "AC"

    def test_quit_for_execution(self, execute_mumps):
        """T046: QUIT in FOR exits the loop (execution test).

        MUMPS semantics: QUIT in FOR loop terminates the loop.
        Expected output: "123" (writes 1,2,3 then QUIT at I=3)
        """
        source = """TEST F I=1:1:10 W I I I=3 Q
 Q"""
        result = execute_mumps(source)
        assert result.output == "123"

    def test_quit_in_nested_for_do(self, execute_mumps):
        """QUIT from DO block inside FOR continues the FOR loop.

        When QUIT is inside a DO block within a FOR loop, it only
        exits the DO block. The FOR loop continues to the next iteration.
        """
        source = """TEST F I=1:1:5 D  W "!"
 . W I
 . I I=3 Q
 Q"""
        result = execute_mumps(source)
        # QUIT exits DO block but FOR continues
        assert result.output == "1!2!3!4!5!"
