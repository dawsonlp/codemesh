"""AST validation and whitespace indentation normalizer for LLM-generated symbol bodies."""

from __future__ import annotations
import ast
import textwrap
from typing import Optional, Tuple

from codemesh.core.csi import CanonicalSymbolId


class NormalizationError(Exception):
    """Raised when an incoming code snippet fails AST validation or semantic matching."""
    pass


class SymbolBodyNormalizer:
    """Normalizes and validates raw Python code snippets for symbol body replacement."""

    @classmethod
    def normalize_callable_body(
        cls,
        raw_source: str,
        target_csi: CanonicalSymbolId,
        is_method: bool = False,
    ) -> str:
        """Parse, validate, and format an incoming function or method body snippet.

        Args:
            raw_source: The raw Python source string provided by the LLM.
            target_csi: The CanonicalSymbolId of the symbol being modified.
            is_method: True if the target symbol is a class method (needs 4-space indentation).

        Returns:
            A clean, formatted, syntactically valid Python definition string.

        Raises:
            NormalizationError: If the snippet has syntax errors or the function name does not match target CSI.
        """
        cleaned = textwrap.dedent(raw_source).strip()
        if not cleaned:
            raise NormalizationError("Symbol body cannot be empty.")

        # 1. Parse AST to ensure valid Python syntax
        try:
            tree = ast.parse(cleaned)
        except SyntaxError as e:
            raise NormalizationError(f"Syntax error in provided code: {e.msg} at line {e.lineno}") from e

        # 2. Inspect top-level nodes in parsed snippet
        expected_name = target_csi.symbol_name if not target_csi.member_path else target_csi.member_path[-1]

        # Check if snippet defines the function/method (e.g. def func(...): ...)
        func_def = next(
            (node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))),
            None,
        )

        if func_def is not None:
            if func_def.name != expected_name:
                raise NormalizationError(
                    f"Function name mismatch: snippet defines '{func_def.name}', "
                    f"but target CSI expects '{expected_name}'."
                )

        # 3. Apply target indentation
        # Top-level functions have 0 leading spaces; class methods have 4 leading spaces.
        target_indent = "    " if is_method else ""
        lines = cleaned.splitlines()
        indented_lines = [f"{target_indent}{line}" if line.strip() else "" for line in lines]
        return "\n".join(indented_lines) + "\n"

