"""Unit tests for high-level semantic assistance methods (add_symbol, rename_symbol, move_symbol)."""

import os
import shutil
import tempfile
import pytest

from codemesh.core.contract import SymbolKind
from codemesh.workspace import SemanticWorkspace


@pytest.mark.asyncio
async def test_workspace_add_symbol():
    workspace = await SemanticWorkspace.load(
        workspace_root=".",
        target_dir="fixtures/sample_ecommerce",
    )

    temp_dir = tempfile.mkdtemp(prefix="test_add_symbol_")
    try:
        new_coupon_code = """
class Coupon:
    \"\"\"Customer discount voucher entity.\"\"\"
    def __init__(self, code: str, discount_percent: float) -> None:
        self.code = code
        self.discount_percent = discount_percent

    def is_valid(self) -> bool:
        return self.discount_percent > 0
"""
        result = workspace.add_symbol(
            target_package="sample_ecommerce/models",
            code=new_coupon_code,
            auto_materialize=True,
            output_dir=temp_dir,
        )

        assert result.success is True
        assert str(result.target_csi) == "csi://sample_ecommerce/models/Coupon"

        # Check graph node
        node = workspace.graph.get_node(result.target_csi)
        assert node is not None
        assert node.contract.kind == SymbolKind.CLASS

        # Check child method node
        method_node = workspace.graph.get_node(result.target_csi.child("is_valid"))
        assert method_node is not None
        assert method_node.contract.kind == SymbolKind.METHOD

        # Verify disk output
        models_file = [p for p in result.materialized_files if "models.py" in p][0]
        with open(models_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert "class Coupon:" in content
        assert "def is_valid(self) -> bool:" in content

    finally:
        shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_workspace_rename_symbol():
    workspace = await SemanticWorkspace.load(
        workspace_root=".",
        target_dir="fixtures/sample_ecommerce",
    )

    csi = "csi://sample_ecommerce/services/OrderService.create_order"
    result = workspace.rename_symbol(csi=csi, new_name="place_order")

    assert result.success is True
    assert str(result.target_csi) == "csi://sample_ecommerce/services/OrderService.place_order"

    # Old CSI should not exist
    assert workspace.graph.get_node("csi://sample_ecommerce/services/OrderService.create_order") is None

    # New CSI should exist
    new_node = workspace.graph.get_node(result.target_csi)
    assert new_node is not None
    assert new_node.contract.name == "place_order"
    assert "def place_order" in new_node.implementation.body_source


@pytest.mark.asyncio
async def test_workspace_move_symbol():
    workspace = await SemanticWorkspace.load(
        workspace_root=".",
        target_dir="fixtures/sample_ecommerce",
    )

    csi = "csi://sample_ecommerce/utils/generate_unique_id"
    result = workspace.move_symbol(csi=csi, new_package="sample_ecommerce/identifiers")

    assert result.success is True
    assert str(result.target_csi) == "csi://sample_ecommerce/identifiers/generate_unique_id"
    assert workspace.graph.get_node("csi://sample_ecommerce/utils/generate_unique_id") is None
    assert workspace.graph.get_node(result.target_csi) is not None

