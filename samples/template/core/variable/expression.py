"""Expression engine — safe expression evaluation with variables."""

from __future__ import annotations

from core.logger import logger

from .registry import variable_registry


class ExpressionEngine:
    """Evaluates mathematical expressions with variable support.

    Uses simpleeval for safe expression evaluation.
    Variables from the registry are automatically available.
    """

    def __init__(self):
        self._evaluator = None
        self._init_evaluator()

    def _init_evaluator(self):
        """Initialize the simpleeval evaluator."""
        try:
            from simpleeval import SimpleEval
            self._evaluator = SimpleEval()
            # Add common math functions
            self._evaluator.functions.update({
                "abs": abs,
                "round": round,
                "min": min,
                "max": max,
                "int": int,
                "float": float,
            })
        except ImportError:
            logger.warning("[ExpressionEngine] simpleeval not installed, expression evaluation disabled")

    def evaluate(self, expression: str) -> Any:
        """Evaluate an expression with current variable values.

        Args:
            expression: Mathematical expression string.

        Returns:
            Evaluation result.

        Raises:
            Exception: If expression is invalid.
        """
        if self._evaluator is None:
            raise RuntimeError("Expression engine not available (simpleeval not installed)")

        # Update variables from registry
        self._evaluator.names = self._get_variables()

        try:
            result = self._evaluator.eval(expression)
            logger.debug(f"[ExpressionEngine] '{expression}' = {result}")
            return result
        except Exception as e:
            logger.error(f"[ExpressionEngine] Failed to evaluate '{expression}': {e}")
            raise

    def _get_variables(self) -> dict:
        """Get all variables as a dict for the evaluator."""
        return {v.name: v.value for v in variable_registry.list()}


# Singleton instance
expression_engine = ExpressionEngine()
