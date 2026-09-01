"""Integration tests for Python LSP client against pyright-langserver."""

import asyncio
import os
import pytest
from lsp_client.client import LspClient
from lsp_client.context_builder import describe_symbol_at_position, get_file_outline


@pytest.mark.asyncio
async def test_lsp_handshake_and_hover():
    async with LspClient() as client:
        # Hover on Money in sample_project/models.py (line 30: class Money)
        # 0-indexed: line 29, char 6
        hover = await client.get_hover("experiments/01_raw_lsp_exploration/sample_project/models.py", line=29, character=6)
        assert hover is not None
        assert "Money" in hover.contents


@pytest.mark.asyncio
async def test_lsp_definition_cross_file():
    async with LspClient() as client:
        # In sample_project/services.py, line 55 (0-indexed: 54): order = Order(
        # Char 17 is 'Order'
        defs = await client.get_definition("experiments/01_raw_lsp_exploration/sample_project/services.py", line=54, character=17)
        assert len(defs) > 0
        def_file = defs[0].file_path
        assert "models.py" in def_file


@pytest.mark.asyncio
async def test_lsp_references():
    async with LspClient() as client:
        # In sample_project/models.py, Money is at line 29 (0-indexed): class Money
        refs = await client.get_references("experiments/01_raw_lsp_exploration/sample_project/models.py", line=29, character=6)
        assert len(refs) >= 4  # Used in models, interfaces, gateways, services


@pytest.mark.asyncio
async def test_lsp_document_symbols():
    async with LspClient() as client:
        symbols = await client.get_document_symbols("experiments/01_raw_lsp_exploration/sample_project/models.py")
        names = [s.name for s in symbols]
        assert "Money" in names
        assert "Order" in names
        assert "OrderStatus" in names


@pytest.mark.asyncio
async def test_lsp_workspace_symbols():
    async with LspClient() as client:
        # Open documents first
        for fname in ["models.py", "interfaces.py", "repositories.py", "services.py"]:
            await client.open_document(f"experiments/01_raw_lsp_exploration/sample_project/{fname}")

        symbols = await client.get_workspace_symbols("Order")
        names = [s.name for s in symbols]
        assert any("Order" in n for n in names)


@pytest.mark.asyncio
async def test_lsp_context_builder():
    async with LspClient() as client:
        outline = await get_file_outline(client, "experiments/01_raw_lsp_exploration/sample_project/models.py")
        assert len(outline) >= 3

        desc = await describe_symbol_at_position(
            client,
            "experiments/01_raw_lsp_exploration/sample_project/services.py",
            line=34,  # 0-indexed line for OrderService.create_order
            character=8,
        )
        assert desc is not None
        assert "create_order" in desc["hover"]
