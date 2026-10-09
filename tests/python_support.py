from __future__ import annotations

import sys
from types import ModuleType

from spriglang import compile_python


def run_python(source: str, filename: str = "<source>") -> list[str]:
    module = ModuleType("_sprig_test_program")
    previous = sys.modules.get(module.__name__)
    sys.modules[module.__name__] = module
    try:
        exec(compile(compile_python(source, filename), "<generated>", "exec"), module.__dict__)
        output: list[str] = []
        module.main(output.append)
        return output
    finally:
        if previous is None:
            del sys.modules[module.__name__]
        else:
            sys.modules[module.__name__] = previous
