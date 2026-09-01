"""Mutation Engine orchestrating blast-radius analysis, invariants, and graph updates."""

from __future__ import annotations
from typing import List, Tuple

from semantic_engine.core.graph import SemanticGraph
from semantic_engine.core.node import SymbolImplementation, SymbolNode
from semantic_engine.mutation.blast_radius import BlastRadiusCalculator, BlastRadiusReport
from semantic_engine.mutation.invariants import InvariantValidator, InvariantViolationError
from semantic_engine.mutation.primitives import (
    AddSymbolMutation,
    DeleteSymbolMutation,
    RenameSymbolMutation,
    ReplaceImplementationMutation,
    SemanticMutation,
    UpdateContractMutation,
)


class MutationEngine:
    """Calculates blast radiuses and applies verified semantic mutations to SemanticGraph."""

    @classmethod
    def calculate_blast_radius(
        cls,
        graph: SemanticGraph,
        mutation: SemanticMutation,
    ) -> BlastRadiusReport:
        return BlastRadiusCalculator.calculate(graph, mutation)

    @classmethod
    def validate_invariants(
        cls,
        graph: SemanticGraph,
        mutation: SemanticMutation,
    ) -> Tuple[bool, List[str]]:
        return InvariantValidator.validate(graph, mutation)

    @classmethod
    def apply_mutation(
        cls,
        graph: SemanticGraph,
        mutation: SemanticMutation,
    ) -> None:
        """Apply mutation to the graph after verifying invariants."""
        valid, errors = cls.validate_invariants(graph, mutation)
        if not valid:
            raise InvariantViolationError("\n".join(errors))

        if isinstance(mutation, ReplaceImplementationMutation):
            node = graph.get_node(mutation.target_csi)
            if node:
                node.implementation = SymbolImplementation(body_source=mutation.new_body_source)

        elif isinstance(mutation, UpdateContractMutation):
            node = graph.get_node(mutation.target_csi)
            if node:
                node.contract = mutation.new_contract

        elif isinstance(mutation, AddSymbolMutation):
            new_csi = mutation.parent_csi.child(mutation.contract.name)
            new_node = SymbolNode(
                csi=new_csi,
                contract=mutation.contract,
                implementation=mutation.implementation,
            )
            graph.add_node(new_node)

        elif isinstance(mutation, DeleteSymbolMutation):
            if mutation.target_csi in graph.nodes:
                del graph.nodes[mutation.target_csi]

