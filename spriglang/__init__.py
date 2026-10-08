"""Public API for the Sprig programming language."""

from .api import compile_source, parse_source, run_source
from .errors import SprigError

__all__ = ["compile_source", "parse_source", "run_source", "SprigError"]
__version__ = "1.0.0"

