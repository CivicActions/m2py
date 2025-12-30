from textx import metamodel_from_file

grammar_path = "src/m2py/grammar/commands.tx"

# Set skipws=False as implied by the grammar comments
mm = metamodel_from_file(grammar_path, skipws=False)


def test_command(cmd_str):
    try:
        _model = mm.model_from_str(cmd_str)
        print(f"Success: {cmd_str}")
    except Exception:
        print(f"Failed: {cmd_str}")
        # print(e)


test_command('S $P(X,"^")=1')
test_command("S $E(X,1)=1")
test_command("S $X=1")
test_command("S $Y=1")
test_command("S $EC=1")
test_command("S $ET=1")
test_command("S $K=1")
