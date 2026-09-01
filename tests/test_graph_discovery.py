"""Unit tests for Graph Semantic Discovery APIs."""

import pytest
from codemesh.core.contract import SymbolKind
from codemesh.workspace import SemanticWorkspace


@pytest.mark.asyncio
async def test_graph_semantic_discovery_apis():
    workspace = await SemanticWorkspace.load(
        workspace_root=".",
        target_dir="fixtures/sample_ecommerce",
    )

    # 1. Find implementations of DiscountStrategy or PaymentGateway
    impls = workspace.find_implementations("csi://sample_ecommerce/interfaces/PaymentGateway")
    impl_strings = [str(c) for c in impls]
    assert any("StripePaymentGateway" in s for s in impl_strings)

    # 2. Find callers of calculate_order_total
    callers = workspace.find_callers("csi://sample_ecommerce/services/OrderService.calculate_order_total")
    caller_strings = [str(c) for c in callers]
    assert any("checkout_order" in s for s in caller_strings)

    # 3. Find references to Money
    refs = workspace.find_references("csi://sample_ecommerce/models/Money")
    assert len(refs) > 0

    # 4. Search symbols by query
    matches = workspace.find_symbols("order")
    match_strings = [str(m) for m in matches]
    assert any("OrderService" in s for s in match_strings)
    assert any("OrderItem" in s for s in match_strings)

