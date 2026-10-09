"""Small adapters embedded alongside the shared runtime in Python builds."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .errors import RuntimeSprigError
from .runtime import Environment, NativeFunction


@dataclass
class CompiledFunction:
    name: str
    parameters: tuple[str, ...]
    body: Callable[[Environment, list[Any]], Any]
    closure: Environment

    @property
    def arity(self) -> int:
        return len(self.parameters)

    def call(self, arguments: list[Any]) -> Any:
        return self.body(self.closure, arguments)

    def __repr__(self) -> str:
        return f"<fn {self.name}>"


def _sp_at(line: int, column: int, operation: Callable[..., Any], *args: Any) -> Any:
    try:
        return operation(*args)
    except RuntimeSprigError:
        raise
    except RecursionError as error:
        raise RuntimeSprigError("maximum function call depth exceeded", line=line, column=column) from error
    except (TypeError, ValueError) as error:
        raise RuntimeSprigError(str(error), line=line, column=column) from error


def _sp_call(callee: Any, arguments: list[Any]) -> Any:
    if not isinstance(callee, (CompiledFunction, NativeFunction)):
        raise ValueError("only functions can be called")
    if callee.arity is not None and len(arguments) != callee.arity:
        raise ValueError(f"expected {callee.arity} arguments but got {len(arguments)}")
    return callee.call(arguments)


def _sp_assign(environment: Environment, name: str, value: Any, line: int, column: int) -> Any:
    environment.assign(name, value, line, column)
    return value


def _sp_iter(value: Any) -> Any:
    try:
        return iter(value)
    except TypeError as error:
        raise ValueError("for loops need an iterable value") from error
