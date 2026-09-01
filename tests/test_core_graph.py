"""Unit tests for Core Contracts and SemanticGraph."""

from semantic_engine.core.contract import (
    DocstringSpec,
    ExecutionModel,
    FunctionSignature,
    Parameter,
    ParameterKind,
    PurityType,
    SymbolContract,
    SymbolKind,
    TypeRef,
)
from semantic_engine.core.csi import CanonicalSymbolId
from semantic_engine.core.graph import EdgeType, Relationship, SemanticGraph
from semantic_engine.core.node import SymbolImplementation, SymbolNode


def test_symbol_contract_and_signature():
    param_user = Parameter(name="user_id", type_ref=TypeRef("str"), kind=ParameterKind.POSITIONAL_OR_KEYWORD)
    param_items = Parameter(name="items", type_ref=TypeRef("List[OrderItem]"), kind=ParameterKind.POSITIONAL_OR_KEYWORD)

    sig = FunctionSignature(
        parameters=[param_user, param_items],
        return_type=TypeRef("Order"),
    )

    contract = SymbolContract(
        name="create_order",
        kind=SymbolKind.METHOD,
        signature=sig,
        purity=PurityType.MUTATES_LOCAL,
        execution_model=ExecutionModel.SYNC_BLOCKING,
        docstring=DocstringSpec(summary="Create a new order."),
    )

    decl = sig.to_declaration_string("create_order")
    assert decl == "def create_order(user_id: str, items: List[OrderItem]) -> Order:"
    assert contract.name == "create_order"
    assert contract.kind == SymbolKind.METHOD


def test_semantic_graph_relationships_and_traversal():
    graph = SemanticGraph()

    csi_service = CanonicalSymbolId.parse("csi://sample_project/services/OrderService.create_order")
    csi_repo = CanonicalSymbolId.parse("csi://sample_project/repositories/OrderRepository.save_order")
    csi_order = CanonicalSymbolId.parse("csi://sample_project/models/Order")

    node_service = SymbolNode(
        csi=csi_service,
        contract=SymbolContract(name="create_order", kind=SymbolKind.METHOD),
        implementation=SymbolImplementation(body_source="self.repo.save_order(order)"),
    )
    node_repo = SymbolNode(
        csi=csi_repo,
        contract=SymbolContract(name="save_order", kind=SymbolKind.METHOD),
        implementation=SymbolImplementation(body_source="..."),
    )
    node_order = SymbolNode(
        csi=csi_order,
        contract=SymbolContract(name="Order", kind=SymbolKind.CLASS),
    )

    graph.add_node(node_service)
    graph.add_node(node_repo)
    graph.add_node(node_order)

    # Add edges
    graph.add_edge(Relationship(source_csi=csi_service, target_csi=csi_repo, edge_type=EdgeType.CALLS))
    graph.add_edge(Relationship(source_csi=csi_service, target_csi=csi_order, edge_type=EdgeType.INSTANTIATES))

    assert graph.get_node(csi_service) is not None
    assert graph.get_callees(csi_service) == {csi_repo}
    assert graph.get_callers(csi_repo) == {csi_service}

    closure = graph.get_dependency_closure(csi_service, depth=1)
    assert csi_repo in closure
    assert csi_order in closure

