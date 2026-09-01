"""Unit tests for AI Context Slicing."""

from semantic_engine.core.contract import FunctionSignature, Parameter, SymbolContract, SymbolKind, TypeRef
from semantic_engine.core.csi import CanonicalSymbolId
from semantic_engine.core.graph import EdgeType, Relationship, SemanticGraph
from semantic_engine.core.node import SymbolImplementation, SymbolNode
from semantic_engine.slicing.closure import ContextSlicer


def test_context_slice_generation():
    graph = SemanticGraph()

    csi_service = CanonicalSymbolId.parse("csi://sample/services/OrderService.create_order")
    csi_repo = CanonicalSymbolId.parse("csi://sample/repositories/OrderRepository.save_order")
    csi_order = CanonicalSymbolId.parse("csi://sample/models/Order")

    node_service = SymbolNode(
        csi=csi_service,
        contract=SymbolContract(
            name="create_order",
            kind=SymbolKind.METHOD,
            signature=FunctionSignature(
                parameters=[Parameter(name="user_id", type_ref=TypeRef("str"))],
                return_type=TypeRef("Order"),
            ),
        ),
        implementation=SymbolImplementation(body_source="def create_order(self, user_id): ..."),
    )
    node_repo = SymbolNode(
        csi=csi_repo,
        contract=SymbolContract(name="save_order", kind=SymbolKind.METHOD),
        implementation=SymbolImplementation(body_source="SECRET REPO BODY"),
    )
    node_order = SymbolNode(
        csi=csi_order,
        contract=SymbolContract(name="Order", kind=SymbolKind.CLASS),
    )

    graph.add_node(node_service)
    graph.add_node(node_repo)
    graph.add_node(node_order)

    graph.add_edge(Relationship(source_csi=csi_service, target_csi=csi_repo, edge_type=EdgeType.CALLS))
    graph.add_edge(Relationship(source_csi=csi_service, target_csi=csi_order, edge_type=EdgeType.INSTANTIATES))

    slicer = ContextSlicer(graph)
    slice_obj = slicer.build_implementation_slice(csi_service)

    # 1. Target implementation is present
    assert slice_obj.target_csi == csi_service
    assert slice_obj.target_implementation.body_source == "def create_order(self, user_id): ..."

    # 2. Dependency contracts are present, but foreign bodies are NOT in the contracts
    assert csi_repo in slice_obj.dependency_contracts
    assert csi_order in slice_obj.dependency_contracts

    # 3. Prompt string formatting excludes foreign bodies
    prompt_str = slice_obj.to_python_stub_prompt()
    assert "SECRET REPO BODY" not in prompt_str
    assert "class Order:" in prompt_str
    assert "def save_order" in prompt_str

