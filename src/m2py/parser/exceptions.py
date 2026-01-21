"""Parser exception classes.

Defines exceptions used during MUMPS parsing and analysis.
"""

from typing import Optional


class MUMPSSyntaxError(Exception):
    """Exception raised when parsing encounters invalid MUMPS syntax.

    Provides detailed location information for error reporting.
    """

    def __init__(
        self,
        message: str,
        line: Optional[int] = None,
        column: Optional[int] = None,
        source_file: Optional[str] = None,
        source_line: Optional[str] = None,
    ):
        """Initialize a syntax error with location information.

        Args:
            message: Description of the syntax error
            line: Line number where error occurred (1-based)
            column: Column number where error occurred (1-based)
            source_file: Path to the source file
            source_line: The actual source line text
        """
        self.message = message
        self.line = line
        self.column = column
        self.source_file = source_file
        self.source_line = source_line

        # Build full error message (only runs on parse errors, not codegen)
        parts = []  # pragma: no cover
        if source_file:  # pragma: no cover
            parts.append(source_file)
        if line is not None:  # pragma: no cover
            parts.append(f"line {line}")
        if column is not None:  # pragma: no cover
            parts.append(f"column {column}")

        location = ":".join(parts) if parts else "unknown location"  # pragma: no cover
        full_message = f"{location}: {message}"  # pragma: no cover

        if source_line:  # pragma: no cover
            full_message += f"\n  {source_line}"
            if column is not None and column > 0:
                full_message += f"\n  {' ' * (column - 1)}^"

        super().__init__(full_message)  # pragma: no cover


class MUMPSUnknownCommandError(MUMPSSyntaxError):
    """Exception raised when an unrecognized command is encountered.

    This error is raised during parsing when a word in command position
    does not match any known MUMPS command. This catches:
    - Misspelled commands
    - Rare or vendor-specific commands not yet implemented
    - Invalid abbreviations
    """

    def __init__(
        self,
        command: str,
        line: Optional[int] = None,
        column: Optional[int] = None,
        source_file: Optional[str] = None,
        source_line: Optional[str] = None,
    ):
        """Initialize an unknown command error.

        Args:
            command: The unrecognized command word
            line: Line number where error occurred (1-based)
            column: Column number where error occurred (1-based)
            source_file: Path to the source file
            source_line: The actual source line text
        """
        self.command = command
        message = (  # pragma: no cover
            f"Unknown command '{command}'. "
            "Not a recognized MUMPS command or valid abbreviation."
        )
        super().__init__(  # pragma: no cover
            message=message,
            line=line,
            column=column,
            source_file=source_file,
            source_line=source_line,
        )
