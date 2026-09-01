"""Queryable semantic relational multigraph of symbols and dependencies."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from semantic_engine.core.contract import SymbolContract
from semantic_engine.core.csi import CanonicalSymbolId
from semantic_engine.core.node import SymbolNode


class EdgeType(str, Enum):
    """Semantic relationship types between code symbols."""
    # Behavioral Relationships
    CALLS = "calls"                   # Function A invokes Function B
    INSTANTIATES = "instantiates"     # Function/Method A constructs Class B
    READS_STATE = "reads_state"       # Function A reads state variable B
    MUTATES_STATE = "mutates_state"   # Function A writes to state variable B

    # Structural & Type Relationships
    IMPLEMENTS = "implements"         # Class A satisfies Protocol/Interface B
    SUBTYPES = "subtypes"             # Class A inherits from Class B
    TYPES = "types"                   # Field/Parameter A has Type B
    DEPENDS_ON = "depends_on"         # Module/Symbol A requires Symbol B
    IMPORTS = "imports"               # Namespace A imports Symbol B

    # Verification Relationships
    VERIFIES = "verifies"             # Test Symbol A tests Target Symbol B


@dataclass
class Relationship:
    """A directed semantic edge between two Canonical Symbol Identifiers."""
    source_csi: CanonicalSymbolId
    target_csi: CanonicalSymbolId
    edge_type: EdgeType
    metadata: Dict[str, Any] = field(default_factory=dict)


class SemanticGraph:
    """Canonical in-memory multigraph storing symbols, contracts, and relationships."""

    def __init__(self) -> None:
        self.nodes: Dict[CanonicalSymbolId, SymbolNode] = {}
        self.edges: List[Relationship] = []
        self._outgoing_index: Dict[CanonicalSymbolId, List[Relationship]] = {}
        self._incoming_index: Dict[CanonicalSymbolId, List[Relationship]] = {}

    def add_node(self, node: SymbolNode) -> None:
        """Register or replace a symbol node in the graph."""
        self.nodes[node.csi] = node
        self._outgoing_index.setdefault(node.csi, [])
        self._incoming_index.setdefault(node.csi, [])

        # Link parent/child relations
        parent_csi = node.csi.parent_csi
        if parent_csi and parent_csi in self.nodes:
            parent_node = self.nodes[parent_csi]
            if node.csi not in parent_node.children:
                parent_node.children.append(node.csi)

    def get_node(self, csi: CanonicalSymbolId) -> Optional[SymbolNode]:
        """Fetch a symbol node by its CSI."""
        return self.nodes.get(csi)

    def get_contract(self, csi: CanonicalSymbolId) -> Optional[SymbolContract]:
        """Fetch only the contract of a symbol."""
        node = self.nodes.get(csi)
        return node.contract if node else None

    def add_edge(self, edge: Relationship) -> None:
        """Add a directed relational edge to the graph."""
        self.edges.append(edge)
        self._outgoing_index.setdefault(edge.source_csi, []).append(edge)
        self._incoming_index.setdefault(edge.target_csi, []).append(edge)

    def get_outgoing_edges(
        self,
        csi: CanonicalSymbolId,
        edge_type: Optional[EdgeType] = None,
    ) -> List[Relationship]:
        """Retrieve outgoing edges from a symbol, optionally filtered by EdgeType."""
        edges = self._outgoing_index.get(csi, [])
        if edge_type is None:
            return edges
        return [e for e in edges if e.edge_type == edge_type]

    def get_incoming_edges(
        self,
        csi: CanonicalSymbolId,
        edge_type: Optional[EdgeType] = None,
    ) -> List[Relationship]:
        """Retrieve incoming edges to a symbol, optionally filtered by EdgeType."""
        edges = self._incoming_index.get(csi, [])
        if edge_type is None:
            return edges
        return [e for e in edges if e.edge_type == edge_type]

    def get_callers(self, csi: CanonicalSymbolId) -> Set[CanonicalSymbolId]:
        """Return all symbol CSIs that call this symbol."""
        return {e.source_csi for e in self.get_incoming_edges(csi, EdgeType.CALLS)}

    def get_callees(self, csi: CanonicalSymbolId) -> Set[CanonicalSymbolId]:
        """Return all symbol CSIs called by this symbol."""
        return {e.target_csi for e in self.get_outgoing_edges(csi, EdgeType.CALLS)}

    def get_implementations(self, interface_csi: CanonicalSymbolId) -> Set[CanonicalSymbolId]:
        """Return all classes that implement the specified interface/protocol."""
        return {e.source_csi for e in self.get_incoming_edges(interface_csi, EdgeType.IMPLEMENTS)}

    def get_subtypes(self, base_class_csi: CanonicalSymbolId) -> Set[CanonicalSymbolId]:
        """Return all classes that inherit from the specified base class."""
        return {e.source_csi for e in self.get_incoming_edges(base_class_csi, EdgeType.SUBTYPES)}

    def get_type_dependencies(self, csi: CanonicalSymbolId) -> Set[CanonicalSymbolId]:
        """Return all types used in parameters, return types, or fields of this symbol."""
        return {e.target_csi for e in self.get_outgoing_edges(csi, EdgeType.TYPES)}

    def get_dependency_closure(
        self,
        csi: CanonicalSymbolId,
        depth: int = 1,
    ) -> Set[CanonicalSymbolId]:
        """Compute the transitive dependency closure for a symbol up to a given depth."""
        result: Set[CanonicalSymbolId] = set()
        current_layer = {csi}
        visited: Set[CanonicalSymbolId] = {csi}

        for _ in range(depth):
            next_layer: Set[CanonicalSymbolId] = set()
            for node_csi in current_layer:
                outgoing = self.get_outgoing_edges(node_csi)
                for edge in outgoing:
                    if edge.edge_type in (EdgeType.CALLS, EdgeType.TYPES, EdgeType.INSTANTIATES, EdgeType.DEPENDS_ON):
                        if edge.target_csi not in visited:
                            visited.add(edge.target_csi)
                            next_layer.add(edge.target_csi)
                            result.add(edge.target_csi)
            current_layer = next_layer
            if not current_layer:
                break

        return result

