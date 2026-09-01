"""Mutation Engine orchestrating blast-radius analysis, invariants, and graph updates."""

from __future__ import annotations
import re
from typing import List, Tuple

from codemesh.core.csi import CanonicalSymbolId
from codemesh.core.graph import SemanticGraph
from codemesh.core.node import SymbolImplementation, SymbolNode
from codemesh.mutation.blast_radius import BlastRadiusCalculator, BlastRadiusReport
from codemesh.mutation.invariants import InvariantValidator, InvariantViolationError
from codemesh.mutation.primitives import (
    AddSymbolMutation,
    DeleteSymbolMutation,
    MoveSymbolMutation,
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
            new_csi = mutation.parent_csi.child(mutation.contract.name) if mutation.parent_csi else CanonicalSymbolId.parse(f"csi://root/{mutation.contract.name}")
            new_node = SymbolNode(
                csi=new_csi,
                contract=mutation.contract,
                implementation=mutation.implementation,
            )
            graph.add_node(new_node)

        elif isinstance(mutation, RenameSymbolMutation):
            old_csi = mutation.target_csi
            node = graph.get_node(old_csi)
            if node:
                old_name = old_csi.symbol_name if not old_csi.member_path else old_csi.member_path[-1]
                if old_csi.member_path:
                    new_csi = CanonicalSymbolId(
                        package=old_csi.package,
                        namespace=old_csi.namespace,
                        symbol_name=old_csi.symbol_name,
                        member_path=old_csi.member_path[:-1] + (mutation.new_name,),
                    )
                else:
                    new_csi = CanonicalSymbolId(
                        package=old_csi.package,
                        namespace=old_csi.namespace,
                        symbol_name=mutation.new_name,
                        member_path=(),
                    )
                node.contract.name = mutation.new_name
                node.csi = new_csi

                # Update implementation body
                if node.implementation and node.implementation.body_source:
                    node.implementation.body_source = re.sub(
                        rf"\bdef {old_name}\b",
                        f"def {mutation.new_name}",
                        node.implementation.body_source,
                    )
                    node.implementation.body_source = re.sub(
                        rf"\bclass {old_name}\b",
                        f"class {mutation.new_name}",
                        node.implementation.body_source,
                    )

                del graph.nodes[old_csi]
                graph.nodes[new_csi] = node

                for edge in graph.edges:
                    if edge.source_csi == old_csi:
                        edge.source_csi = new_csi
                    if edge.target_csi == old_csi:
                        edge.target_csi = new_csi

                if old_csi.parent_csi and old_csi.parent_csi in graph.nodes:
                    parent_node = graph.nodes[old_csi.parent_csi]
                    if old_csi in parent_node.children:
                        parent_node.children.remove(old_csi)
                        parent_node.children.append(new_csi)

                graph.rebuild_indices()

        elif isinstance(mutation, MoveSymbolMutation):
            old_csi = mutation.target_csi
            node = graph.get_node(old_csi)
            if node:
                new_csi = CanonicalSymbolId(
                    package=mutation.new_package,
                    namespace=mutation.new_namespace,
                    symbol_name=old_csi.symbol_name,
                    member_path=old_csi.member_path,
                )
                node.csi = new_csi
                del graph.nodes[old_csi]
                graph.nodes[new_csi] = node

                for edge in graph.edges:
                    if edge.source_csi == old_csi:
                        edge.source_csi = new_csi
                    if edge.target_csi == old_csi:
                        edge.target_csi = new_csi

                graph.rebuild_indices()

        elif isinstance(mutation, DeleteSymbolMutation):
            if mutation.target_csi in graph.nodes:
                del graph.nodes[mutation.target_csi]
                graph.edges = [
                    e for e in graph.edges
                    if e.source_csi != mutation.target_csi and e.target_csi != mutation.target_csi
                ]
                graph.rebuild_indices()
