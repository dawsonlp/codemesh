"""Unit tests for multi-symbol task slicing and contract deduplication."""

import pytest
from codemesh.workspace import SemanticWorkspace


@pytest.mark.asyncio
async def test_multi_symbol_context_slicing():
    workspace = await SemanticWorkspace.load(
        workspace_root=".",
        target_dir="fixtures/sample_ecommerce",
    )

    # Multi-target slice across models, interfaces, and services
    targets = [
        "csi://sample_ecommerce/models/Order",
        "csi://sample_ecommerce/services/OrderService.calculate_order_total",
    ]
    multi_slice = workspace.get_multi_symbol_context(targets)

    assert len(multi_slice.target_csis) == 2
    prompt = multi_slice.to_python_stub_prompt()

    # Both target bodies must appear
    assert "class Order:" in prompt
    assert "def calculate_order_total" in prompt

    # Shared dependency contracts must appear
    assert "class Money:" in prompt or "Money: Any" in prompt
    assert "class OrderStatus:" in prompt
    assert "def get_by_id" in prompt

    # Order must NOT be duplicated under shared dependency contracts
    dep_section = prompt.split("# --- SHARED DEPENDENCY CONTRACTS")[-1]
    assert "# CSI: csi://sample_ecommerce/models/Order\n" not in dep_section
