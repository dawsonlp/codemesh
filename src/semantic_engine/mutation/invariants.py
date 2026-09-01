"""Pre-commit invariant validation rules."""

from __future__ import annotations
from typing import List, Tuple

from semantic_engine.core.graph import SemanticGraph
from semantic_engine.mutation.primitives import (
    AddSymbolMutation,
    DeleteSymbolMutation,
    ReplaceImplementationMutation,
    SemanticMutation,
)


class InvariantViolationError(Exception):
    """Raised when a semantic mutation violates system structural or contract invariants."""
    pass


class InvariantValidator:
    """Validates structural and relational invariants before committing a mutation."""

    @classmethod
    def validate(
        cls,
        graph: SemanticGraph,
        mutation: SemanticMutation,
    ) -> Tuple[bool, List[str]]:
        """Verify pre-commit structural and contract invariants."""
        errors: List[str] = []

        if isinstance(mutation, ReplaceImplementationMutation):
            node = graph.get_node(mutation.target_csi)
            if not node:
                errors.append(f"Target symbol not found: {mutation.target_csi}")
            elif not mutation.new_body_source.strip():
                errors.append("New implementation body cannot be empty.")

        elif isinstance(mutation, DeleteSymbolMutation):
            node = graph.get_node(mutation.target_csi)
            if not node:
                errors.append(f"Target symbol not found: {mutation.target_csi}")
            else:
                incoming = graph.get_incoming_edges(mutation.target_csi)
                if incoming:
                    referencer_names = ", ".join(sorted({e.source_csi.qualified_name for e in incoming}))
                    errors.append(f"Cannot delete symbol {mutation.target_csi}: actively referenced by [{referencer_names}]")

        elif isinstance(mutation, AddSymbolMutation):
            new_csi = mutation.parent_csi.child(mutation.contract.name)
            if graph.get_node(new_csi):
                errors.append(f"Symbol collision: {new_csi} already exists in graph.")

        return len(errors) == 0, errors

