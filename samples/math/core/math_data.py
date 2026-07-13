"""数学数据包装类 - 用于在节点间传递数学表达式和矩阵。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MathExpression:
    """数学表达式包装。"""
    expr: Any  # sympy.Expr
    latex: str = ""
    text: str = ""
    variables: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.expr is not None and not self.latex:
            from sympy import latex
            self.latex = latex(self.expr)
        if self.expr is not None and not self.text:
            self.text = str(self.expr)

    def __str__(self):
        return self.text

    def __repr__(self):
        return f"MathExpression({self.text})"


@dataclass
class MathMatrix:
    """矩阵包装。"""
    matrix: Any  # sympy.Matrix
    latex: str = ""
    shape: tuple = (0, 0)

    def __post_init__(self):
        if self.matrix is not None:
            from sympy import latex
            self.latex = latex(self.matrix)
            self.shape = self.matrix.shape

    def __str__(self):
        return str(self.matrix)

    def __repr__(self):
        return f"MathMatrix({self.shape})"


@dataclass
class MathEquation:
    """方程包装。"""
    lhs: Any  # sympy.Expr (left-hand side)
    rhs: Any  # sympy.Expr (right-hand side)
    latex: str = ""
    text: str = ""

    def __post_init__(self):
        from sympy import Eq, latex as sym_latex
        self._eq = Eq(self.lhs, self.rhs)
        if not self.latex:
            self.latex = sym_latex(self._eq)
        if not self.text:
            self.text = str(self._eq)

    def __str__(self):
        return self.text

    def __repr__(self):
        return f"MathEquation({self.text})"
