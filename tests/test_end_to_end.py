"""End-to-end integration test of the complete Semantic Engine lifecycle."""

import os
import shutil
import tempfile
import pytest

from semantic_engine.adapters.lsp.client import LspClient
from semantic_engine.adapters.lsp.graph_builder import LspGraphBuilder
from semantic_engine.core.csi import CanonicalSymbolId
from semantic_engine.mutation.engine import MutationEngine
from semantic_engine.mutation.primitives import (
    DeleteSymbolMutation,
    ReplaceImplementationMutation,
)
from semantic_engine.projection.file_projector import FileSystemProjector
from semantic_engine.slicing.closure import ContextSlicer


@pytest.mark.asyncio
async def test_complete_semantic_engine_lifecycle():
    # 1. Ingest via LSP Anti-Corruption Layer
    async with LspClient() as client:
        builder = LspGraphBuilder(client=client, workspace_root=".")
        graph = await builder.build_graph(target_dir="fixtures/sample_ecommerce")

        assert len(graph.nodes) >= 15
        csi_create_order = CanonicalSymbolId.parse(
            "csi://sample_ecommerce/services/OrderService.create_order"
        )
        csi_order = CanonicalSymbolId.parse(
            "csi://sample_ecommerce/models/Order"
        )

        assert graph.get_node(csi_create_order) is not None
        assert graph.get_node(csi_order) is not None

        # 2. AI Context Slicing (Minimal Contract Closure)
        slicer = ContextSlicer(graph)
        slice_obj = slicer.build_implementation_slice(csi_create_order)

        assert slice_obj.target_csi == csi_create_order
        assert slice_obj.target_implementation is not None
        assert "def create_order" in slice_obj.target_implementation.body_source

        prompt_stub = slice_obj.to_python_stub_prompt()
        assert "TARGET CONTEXT FOR: sample_ecommerce.services.OrderService.create_order" in prompt_stub

        # 3. Semantic Mutation & Blast Radius
        new_body = """    def create_order(self, user_id: str, items: List[OrderItem]) -> Order:
        # Optimized with auditing
        return super().create_order(user_id, items)
"""
        mut_replace = ReplaceImplementationMutation(
            target_csi=csi_create_order,
            new_body_source=new_body,
        )
        blast_report = MutationEngine.calculate_blast_radius(graph, mut_replace)
        assert blast_report.is_safe_local_change

        MutationEngine.apply_mutation(graph, mut_replace)
        assert "Optimized with auditing" in graph.get_node(csi_create_order).implementation.body_source

        # 4. Invariant Engine: Breaking Deletion Prevention
        mut_delete = DeleteSymbolMutation(target_csi=csi_order)
        valid, errors = MutationEngine.validate_invariants(graph, mut_delete)
        if graph.get_incoming_edges(csi_order):
            assert not valid

        # 5. FileSystem Materialization
        temp_dir = tempfile.mkdtemp(prefix="semantic_engine_e2e_")
        try:
            projector = FileSystemProjector(graph, src_dir="src")
            written_files = projector.project_to_disk(temp_dir)
            assert len(written_files) > 0

            for path in written_files:
                assert os.path.exists(path)
                assert os.path.getsize(path) > 0
        finally:
            shutil.rmtree(temp_dir)


def test_codemesh_service_mutation_and_uri_resolve():
    from fastapi.testclient import TestClient
    from codemesh.service.app import create_app

    app = create_app()
    client = TestClient(app)

    # 1. Resolve Option B URI
    res = client.post("/api/v1/uris/resolve", json={"uri": "csi://tripartite:ecommerce/services/OrderService.create_order@v1"})
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
    assert data["coordinates"]["solution"] == "ecommerce"
    assert data["coordinates"]["version"] == "v1"

    # 2. Invariant-Gated Mutation
    mut_payload = {
        "target_csi": "csi://ecommerce/services/PaymentService.capture_funds",
        "new_implementation": "@idempotent\ndef capture_funds(): return {'status': 'CAPTURED'}",
        "validate_invariants": True,
    }
    mut_res = client.post("/api/v1/mutate", json=mut_payload)
    assert mut_res.status_code == 200
    mut_data = mut_res.json()
    assert mut_data["is_valid"] is True
    assert mut_data["status"] == "VALIDATED"


