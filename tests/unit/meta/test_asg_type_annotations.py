"""Tests for ASG type annotation correctness (Phase 73 validation).

Validates that type annotations match runtime behavior for key ASG elements.
"""

from typing import get_type_hints


class TestMCallArgumentsType:
    """Verify MCall.arguments has correct type annotation."""

    def test_mcall_arguments_runtime_content(self):
        """MCall.arguments should contain MActualParameter objects."""
        from m2py.parser import MUMPSParser
        from m2py.asg.expressions import MActualParameter

        parser = MUMPSParser()
        source = "TEST\n S X=$$FN(A,B)\n"
        routine = parser.parse(source)

        # Find the extrinsic function call
        set_stmt = routine.labels[0].body.statements[0]
        # MSetStatement has assignments list, each with a value
        extrinsic = set_stmt.assignments[0].value

        # Verify arguments are MActualParameter instances
        assert len(extrinsic.arguments) == 2
        for arg in extrinsic.arguments:
            assert isinstance(arg, MActualParameter)


class TestMDoStatementArgumentlessDo:
    """Verify MDoStatement handles argumentless DO correctly."""

    def test_argumentless_do_uses_mdostatement(self):
        """Argumentless DO should produce MDoStatement with empty targets."""
        from m2py.parser import MUMPSParser
        from m2py.asg.statements import MDoStatement

        parser = MUMPSParser()
        source = "TEST\n D\n . S X=1\n"
        routine = parser.parse(source)

        do_stmt = routine.labels[0].body.statements[0]
        assert isinstance(do_stmt, MDoStatement)
        # Argumentless DO has empty targets, populated body
        assert len(do_stmt.targets) == 0
        assert len(do_stmt.body.statements) > 0

    def test_labeled_do_uses_mdostatement(self):
        """Labeled DO should produce MDoStatement with targets."""
        from m2py.parser import MUMPSParser
        from m2py.asg.statements import MDoStatement

        parser = MUMPSParser()
        source = "TEST\n D LABEL\n Q\nLABEL\n Q\n"
        routine = parser.parse(source)

        do_stmt = routine.labels[0].body.statements[0]
        assert isinstance(do_stmt, MDoStatement)
        # Labeled DO has targets, empty body
        assert len(do_stmt.targets) > 0


class TestMPatternMatchCompiledRegex:
    """Verify MPatternMatch.compiled_regex is a string, not compiled Pattern."""

    def test_compiled_regex_is_string_type(self):
        """compiled_regex should be Optional[str], not Pattern."""
        from m2py.asg.expressions import MPatternMatch

        hints = get_type_hints(MPatternMatch)
        regex_hint = hints.get("compiled_regex")
        assert regex_hint is not None
        # Should be Optional[str], not Optional[re.Pattern]
        assert regex_hint.__args__[0] is str or (
            hasattr(regex_hint, "__origin__")
            and regex_hint.__args__ == (str, type(None))
        )

    def test_compiled_regex_runtime_value(self):
        """When populated, compiled_regex should be a string."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        source = "TEST\n S X=(Y?1A.N)\n"
        routine = parser.parse(source)

        set_stmt = routine.labels[0].body.statements[0]
        # MSetStatement has assignments list, each with a value
        pattern_match = set_stmt.assignments[0].value

        # compiled_regex is populated after pattern compilation
        if pattern_match.compiled_regex is not None:
            assert isinstance(pattern_match.compiled_regex, str)
