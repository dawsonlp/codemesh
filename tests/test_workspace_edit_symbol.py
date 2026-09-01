"""Integration tests for SemanticWorkspace.edit_symbol zero-diff operations."""

import os
import shutil
import tempfile
import pytest

from semantic_engine.workspace import SemanticWorkspace


@pytest.mark.asyncio
async def test_workspace_edit_symbol_zero_diff_lifecycle():
    # 1. Load Workspace
    workspace = await SemanticWorkspace.load(
        workspace_root=".",
        target_dir="fixtures/sample_ecommerce",
    )
    assert len(workspace.graph.nodes) >= 15

    # 2. Get prompt context slice
    csi_str = "csi://sample_ecommerce/services/OrderService.create_order"
    context = workspace.get_symbol_context(csi_str)
    assert "def create_order" in context.to_python_stub_prompt()

    # 3. Perform Zero-Diff edit with unindented snippet
    new_impl = """def create_order(self, user_id: str, items: List[OrderItem]) -> Order:
    \"\"\"Telemetry-wrapped order creation.\"\"\"
    order_id = generate_unique_id("ord_telemetry")
    order = Order(order_id=order_id, user_id=user_id, items=items)
    self.order_repo.save_order(order)
    return order
"""
    temp_dir = tempfile.mkdtemp(prefix="test_workspace_edit_")
    try:
        result = workspace.edit_symbol(
            csi=csi_str,
            new_body=new_impl,
            auto_materialize=True,
            output_dir=temp_dir,
        )

        assert result.success is True
        assert result.blast_radius is not None
        assert result.blast_radius.is_safe_local_change is True
        assert len(result.materialized_files) > 0

        # 4. Verify disk materialization content
        services_file = [p for p in result.materialized_files if "services.py" in p][0]
        with open(services_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Check synthesized imports
        assert "from sample_ecommerce.models import Money, Order" in content
        assert "from sample_ecommerce.utils import generate_unique_id" in content

        # Check that method body was normalized with 4 spaces inside class
        assert "    def create_order(self, user_id: str, items: List[OrderItem]) -> Order:" in content
        assert '        order_id = generate_unique_id("ord_telemetry")' in content

    finally:
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_workspace_edit_symbol_error_handling():
    workspace = await SemanticWorkspace.load(
        workspace_root=".",
        target_dir="fixtures/sample_ecommerce",
    )

    # 1. Non-existent symbol
    res_missing = workspace.edit_symbol("csi://sample_ecommerce/services/NoSuchSymbol", "def foo(): pass")
    assert res_missing.success is False
    assert "not found in graph" in res_missing.error_message

    # 2. Syntax error
    res_syntax = workspace.edit_symbol(
        "csi://sample_ecommerce/services/OrderService.create_order",
        "def create_order(self): return (((",
    )
    assert res_syntax.success is False
    assert "Syntax error" in res_syntax.error_message

    # 3. Name mismatch
    res_name = workspace.edit_symbol(
        "csi://sample_ecommerce/services/OrderService.create_order",
        "def cancel_order(self): pass",
    )
    assert res_name.success is False
    assert "Function name mismatch" in res_name.error_message

