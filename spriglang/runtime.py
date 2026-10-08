from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .errors import RuntimeSprigError


class SprigCallable(Protocol):
    @property
    def arity(self) -> int | None: ...

    def call(self, arguments: list[Any]) -> Any: ...


class Environment:
    def __init__(self, enclosing: Environment | None = None) -> None:
        self.enclosing = enclosing
        self.values: dict[str, Any] = {}

    def define(self, name: str, value: Any) -> None:
        self.values[name] = value

    def get(self, name: str, line: int | None = None, column: int | None = None) -> Any:
        if name in self.values:
            return self.values[name]
        if self.enclosing is not None:
            return self.enclosing.get(name, line, column)
        raise RuntimeSprigError(f"undefined variable {name!r}", line=line, column=column)

    def assign(self, name: str, value: Any, line: int | None = None, column: int | None = None) -> None:
        if name in self.values:
            self.values[name] = value
            return
        if self.enclosing is not None:
            self.enclosing.assign(name, value, line, column)
            return
        raise RuntimeSprigError(f"cannot assign to undefined variable {name!r}", line=line, column=column)


@dataclass
class NativeFunction:
    name: str
    function: Callable[..., Any]
    arity: int | None

    def call(self, arguments: list[Any]) -> Any:
        return self.function(*arguments)

    def __repr__(self) -> str:
        return f"<native fn {self.name}>"


def stringify(value: Any) -> str:
    if value is None:
        return "none"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, list):
        return "[" + ", ".join(stringify(item) for item in value) + "]"
    return str(value)


def type_name(value: Any) -> str:
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "list"
    if callable(value) or hasattr(value, "call"):
        return "function"
    return type(value).__name__


def make_globals(output: Callable[[str], None]) -> Environment:
    environment = Environment()

    def sprig_print(*values: Any) -> None:
        output(" ".join(stringify(value) for value in values))

    def sprig_range(*args: Any) -> list[int]:
        if not 1 <= len(args) <= 3 or not all(isinstance(value, int) and not isinstance(value, bool) for value in args):
            raise ValueError("range expects one to three integer arguments")
        return list(range(*args))

    def sprig_number(value: Any) -> int | float:
        if isinstance(value, bool) or value is None:
            raise ValueError("number expects a numeric value or numeric string")
        result = float(value) if "." in str(value) else int(value)
        return result

    builtins = {
        "print": NativeFunction("print", sprig_print, None),
        "len": NativeFunction("len", len, 1),
        "range": NativeFunction("range", sprig_range, None),
        "str": NativeFunction("str", stringify, 1),
        "number": NativeFunction("number", sprig_number, 1),
        "type": NativeFunction("type", type_name, 1),
    }
    for name, function in builtins.items():
        environment.define(name, function)
    return environment


def truthy(value: Any) -> bool:
    return bool(value)


def unary_operation(operator: str, operand: Any) -> Any:
    if operator in ("not", "!"):
        return not truthy(operand)
    if operator in ("-", "+"):
        require_number(operand, operator)
        return -operand if operator == "-" else +operand
    raise ValueError(f"unknown unary operator {operator!r}")


def binary_operation(operator: str, left: Any, right: Any) -> Any:
    if operator == "+":
        if isinstance(left, (int, float)) and not isinstance(left, bool) and isinstance(right, (int, float)) and not isinstance(right, bool):
            return left + right
        if isinstance(left, str) and isinstance(right, str):
            return left + right
        if isinstance(left, list) and isinstance(right, list):
            return left + right
        raise ValueError("'+' needs two numbers, two strings, or two lists")
    if operator in ("-", "*", "/", "%"):
        require_number(left, operator)
        require_number(right, operator)
        if operator == "-":
            return left - right
        if operator == "*":
            return left * right
        if operator == "/":
            if right == 0:
                raise ValueError("division by zero")
            return left / right
        if right == 0:
            raise ValueError("remainder by zero")
        return left % right
    if operator == "==":
        return left == right
    if operator == "!=":
        return left != right
    if operator in ("<", "<=", ">", ">="):
        try:
            return {"<": left < right, "<=": left <= right, ">": left > right, ">=": left >= right}[operator]
        except TypeError as error:
            raise ValueError(f"cannot compare {type_name(left)} and {type_name(right)}") from error
    raise ValueError(f"unknown binary operator {operator!r}")


def require_number(value: Any, operator: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"operator {operator!r} needs numbers, got {type_name(value)}")


def get_index(collection: Any, index: Any) -> Any:
    if not isinstance(collection, (list, str)):
        raise ValueError(f"only lists and strings can be indexed, got {type_name(collection)}")
    if not isinstance(index, int) or isinstance(index, bool):
        raise ValueError("list and string indexes must be integers")
    try:
        return collection[index]
    except IndexError as error:
        raise ValueError(f"index {index} is out of range") from error


def set_index(collection: Any, index: Any, value: Any) -> Any:
    if not isinstance(collection, list):
        raise ValueError(f"only lists can be changed by index, got {type_name(collection)}")
    if not isinstance(index, int) or isinstance(index, bool):
        raise ValueError("list indexes must be integers")
    try:
        collection[index] = value
    except IndexError as error:
        raise ValueError(f"index {index} is out of range") from error
    return value
