"""Variable system module — global variables and expression evaluation."""

from .variable import Variable, VariableType
from .registry import VariableRegistry, variable_registry
from .expression import ExpressionEngine, expression_engine

__all__ = [
    "Variable",
    "VariableType",
    "VariableRegistry",
    "variable_registry",
    "ExpressionEngine",
    "expression_engine",
]
