from textx import metamodel_from_file

grammar_path = "src/m2py/grammar/commands.tx"

# Set skipws=False as implied by the grammar comments
mm = metamodel_from_file(grammar_path, skipws=False)


def test_command(cmd_str):
    try:
        _model = mm.model_from_str(cmd_str)
        print(f"Success: {cmd_str}")
    except Exception as e:
        print(f"Failed: {cmd_str}")
        print(e)


test_command("TS ()")
test_command("TS (A)")
test_command("TS *")
test_command("TS")
