"""Unit tests for Semantic Mutations, Blast-Radius, and Invariant Verification."""

import pytest
from semantic_engine.core.contract import SymbolContract, SymbolKind
from semantic_engine.core.csi import CanonicalSymbolId
from semantic_engine.core.graph import EdgeType, Relationship, SemanticGraph
from semantic_engine.core.node import SymbolImplementation, SymbolNode
from semantic_engine.mutation.engine import MutationEngine
from semantic_engine.mutation.invariants import InvariantViolationError
from semantic_engine.mutation.primitives import (
    AddSymbolMutation,
    DeleteSymbolMutation,
    ReplaceImplementationMutation,
    UpdateContractMutation,
)


def test_replace_implementation_and_blast_radius():
    graph = SemanticGraph()
    csi_method = CanonicalSymbolId.parse("csi://pkg/services/Service.run")
    csi_test = CanonicalSymbolId.parse("csi://pkg/tests/test_service.test_run")

    node_method = SymbolNode(
        csi=csi_method,
        contract=SymbolContract(name="run", kind=SymbolKind.METHOD),
        implementation=SymbolImplementation(body_source="pass"),
    )
    node_test = SymbolNode(
        csi=csi_test,
        contract=SymbolContract(name="test_run", kind=SymbolKind.FUNCTION),
    )

    graph.add_node(node_method)
    graph.add_node(node_test)
    graph.add_edge(Relationship(source_csi=csi_test, target_csi=csi_method, edge_type=EdgeType.VERIFIES))

    # Mutation
    mut = ReplaceImplementationMutation(target_csi=csi_method, new_body_source="return 42")
    report = MutationEngine.calculate_blast_radius(graph, mut)

    assert report.target_csi == csi_method
    assert report.verifying_tests == {csi_test}

    MutationEngine.apply_mutation(graph, mut)
    assert graph.get_node(csi_method).implementation.body_source == "return 42"


def test_delete_invariant_prevents_breaking_change():
    graph = SemanticGraph()
    csi_service = CanonicalSymbolId.parse("csi://pkg/services/Service.run")
    csi_model = CanonicalSymbolId.parse("csi://pkg/models/User")

    node_service = SymbolNode(csi=csi_service, contract=SymbolContract(name="run", kind=SymbolKind.METHOD))
    node_model = SymbolNode(csi=csi_model, contract=SymbolContract(name="User", kind=SymbolKind.CLASS))

    graph.add_node(node_service)
    graph.add_node(node_model)
    graph.add_edge(Relationship(source_csi=csi_service, target_csi=csi_model, edge_type=EdgeType.TYPES))

    # Deleting User while Service references it must fail validation
    mut = DeleteSymbolMutation(target_csi=csi_model)
    valid, errors = MutationEngine.validate_invariants(graph, mut)
    assert not valid
    assert "actively referenced by" in errors[0]

    with pytest.raises(InvariantViolationError):
        MutationEngine.apply_mutation(graph, mut)

