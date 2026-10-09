from langchain_core.tools import tool
import ast
from typing import Any

@tool
async def calculator(expression: str) -> str:
    """Evaluate a simple arithmetic expression safely.

    Supported operators: +, -, *, /, %, ** and parentheses.
    """
    parsed = ast.parse(expression, mode="eval")
    allowed_nodes = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Constant,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Mod,
        ast.Pow,
        ast.USub,
        ast.UAdd,
        ast.Load,
    )

    for node in ast.walk(parsed):
        if not isinstance(node, allowed_nodes):
            raise ValueError("Expression contains unsupported syntax")

    # Pure CPU eval; still made async to avoid blocking agent tool pipeline.
    # If you expect very heavy expressions, consider running this in a thread.
    result: Any = eval(
        compile(parsed, "<calculator>", "eval"),
        {"__builtins__": {}},
        {},
    )
    return str(result)