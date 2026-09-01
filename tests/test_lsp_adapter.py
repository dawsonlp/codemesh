"""Tests for the LSP Anti-Corruption Ingestion Adapter."""

import pytest
from semantic_engine.adapters.lsp.client import LspClient
from semantic_engine.adapters.lsp.graph_builder import LspGraphBuilder
from semantic_engine.adapters.lsp.signature_parser import SignatureParser
from semantic_engine.adapters.lsp.spatial_index import SpatialIndex
from semantic_engine.core.contract import ParameterKind, SymbolKind
from semantic_engine.core.csi import CanonicalSymbolId


def test_spatial_index():
    index = SpatialIndex(workspace_root="/workspace", package_root="/workspace/pkg")
    csi_class = CanonicalSymbolId.parse("csi://pkg/models/Order")
    csi_method = CanonicalSymbolId.parse("csi://pkg/models/Order.calculate_subtotal")

    index.register(csi_class, "/workspace/pkg/models.py", full_start_line=10, full_end_line=30, target_line=10, target_col=6)
    index.register(csi_method, "/workspace/pkg/models.py", full_start_line=20, full_end_line=28, target_line=20, target_col=8)

    # Line 15 should match the outer class
    assert index.lookup_csi("/workspace/pkg/models.py", line=15, col=0) == csi_class
    # Line 22 should match the tighter method
    assert index.lookup_csi("/workspace/pkg/models.py", line=22, col=0) == csi_method
    # Line 35 is outside
    assert index.lookup_csi("/workspace/pkg/models.py", line=35, col=0) is None


def test_signature_parser_method():
    hover_sample = """```python
(method) def create_order(
    self: Self@OrderService,
    user_id: str,
    items: List[OrderItem]
) -> Order
```
---
Create and persist a new customer order.

Args:
    user_id: The ID of the customer placing the order.
    items: Non-empty list of items to purchase.

Returns:
    The newly created Order object in PENDING state.

Raises:
    OrderProcessingError: If the user does not exist or item list is empty.
"""
    contract = SignatureParser.parse_hover_markdown(hover_sample, default_name="create_order")

    assert contract.name == "create_order"
    assert contract.kind == SymbolKind.METHOD
    assert contract.signature is not None
    assert len(contract.signature.parameters) == 2
    assert contract.signature.parameters[0].name == "user_id"
    assert contract.signature.parameters[0].type_ref.raw_type_string == "str"
    assert contract.signature.parameters[1].name == "items"
    assert contract.signature.return_type.raw_type_string == "Order"

    assert contract.docstring.summary == "Create and persist a new customer order."
    assert "user_id" in contract.docstring.parameters_doc
    assert "OrderProcessingError" in contract.docstring.raises_doc


@pytest.mark.asyncio
async def test_lsp_graph_builder_integration():
    async with LspClient() as client:
        builder = LspGraphBuilder(client=client, workspace_root=".")
        graph = await builder.build_graph(target_dir="fixtures/sample_ecommerce")

        assert len(graph.nodes) > 10

        # Check OrderService.create_order
        csi_create_order = CanonicalSymbolId.parse("csi://sample_ecommerce/services/OrderService.create_order")
        node = graph.get_node(csi_create_order)
        assert node is not None
        assert node.contract.kind == SymbolKind.METHOD
        assert node.contract.signature is not None
        assert node.contract.signature.return_type.raw_type_string == "Order"
        assert node.implementation is not None
        assert "def create_order" in node.implementation.body_source

        # Check relational edges
        csi_order = CanonicalSymbolId.parse("csi://sample_ecommerce/models/Order")
        callees = graph.get_callees(csi_create_order)
        type_deps = graph.get_type_dependencies(csi_create_order)
        assert csi_order in callees or csi_order in type_deps
