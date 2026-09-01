"""Blast radius calculation and impact analysis."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Set

from codemesh.core.csi import CanonicalSymbolId
from codemesh.core.graph import EdgeType, SemanticGraph
from codemesh.mutation.primitives import (
    AddSymbolMutation,
    DeleteSymbolMutation,
    MoveSymbolMutation,
    RenameSymbolMutation,
    ReplaceImplementationMutation,
    SemanticMutation,
    UpdateContractMutation,
)


@dataclass
class BlastRadiusReport:
    """Structured impact analysis of a proposed semantic mutation."""
    target_csi: CanonicalSymbolId
    mutation: SemanticMutation
    direct_callers: Set[CanonicalSymbolId] = field(default_factory=set)
    implementing_classes: Set[CanonicalSymbolId] = field(default_factory=set)
    subtypes: Set[CanonicalSymbolId] = field(default_factory=set)
    verifying_tests: Set[CanonicalSymbolId] = field(default_factory=set)

    @property
    def total_impacted_count(self) -> int:
        return len(self.direct_callers) + len(self.implementing_classes) + len(self.subtypes) + len(self.verifying_tests)

    @property
    def is_safe_local_change(self) -> bool:
        """True if change has zero external blast radius (e.g. pure implementation edit)."""
        return self.total_impacted_count == 0


class BlastRadiusCalculator:
    """Calculates reverse-dependency blast radiuses across the semantic graph."""

    @classmethod
    def calculate(
        cls,
        graph: SemanticGraph,
        mutation: SemanticMutation,
    ) -> BlastRadiusReport:
        """Analyze the reverse dependency graph to discover all impacted callers, subtypes, and tests."""
        if isinstance(mutation, ReplaceImplementationMutation):
            tests = {
                e.source_csi for e in graph.get_incoming_edges(mutation.target_csi, EdgeType.VERIFIES)
            }
            return BlastRadiusReport(
                target_csi=mutation.target_csi,
                mutation=mutation,
                verifying_tests=tests,
            )

        if isinstance(mutation, (UpdateContractMutation, RenameSymbolMutation, DeleteSymbolMutation, MoveSymbolMutation)):
            target_csi = mutation.target_csi
            callers = graph.get_callers(target_csi)
            implementations = graph.get_implementations(target_csi)
            subtypes = graph.get_subtypes(target_csi)
            type_users = {
                e.source_csi for e in graph.get_incoming_edges(target_csi, EdgeType.TYPES)
            }
            tests = {
                e.source_csi for e in graph.get_incoming_edges(target_csi, EdgeType.VERIFIES)
            }
            return BlastRadiusReport(
                target_csi=target_csi,
                mutation=mutation,
                direct_callers=callers.union(type_users),
                implementing_classes=implementations,
                subtypes=subtypes,
                verifying_tests=tests,
            )

        if isinstance(mutation, AddSymbolMutation):
            return BlastRadiusReport(
                target_csi=mutation.parent_csi,
                mutation=mutation,
            )

        raise ValueError(f"Unknown mutation type: {type(mutation)}")

