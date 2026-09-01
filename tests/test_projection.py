"""Unit tests for FileSystem Projection and Import Synthesis."""

import os
import shutil
import tempfile
from semantic_engine.core.contract import SymbolContract, SymbolKind
from semantic_engine.core.csi import CanonicalSymbolId
from semantic_engine.core.graph import EdgeType, Relationship, SemanticGraph
from semantic_engine.core.node import SymbolImplementation, SymbolNode
from semantic_engine.projection.file_projector import FileSystemProjector


def test_filesystem_projection_and_import_synthesis():
    graph = SemanticGraph()

    csi_service = CanonicalSymbolId.parse("csi://ecommerce/services/OrderService")
    csi_model = CanonicalSymbolId.parse("csi://ecommerce/models/Order")

    node_service = SymbolNode(
        csi=csi_service,
        contract=SymbolContract(name="OrderService", kind=SymbolKind.CLASS),
        implementation=SymbolImplementation(body_source="class OrderService:\n    def create(self) -> Order:\n        pass"),
    )
    node_model = SymbolNode(
        csi=csi_model,
        contract=SymbolContract(name="Order", kind=SymbolKind.CLASS),
        implementation=SymbolImplementation(body_source="class Order:\n    pass"),
    )

    graph.add_node(node_service)
    graph.add_node(node_model)
    graph.add_edge(Relationship(source_csi=csi_service, target_csi=csi_model, edge_type=EdgeType.TYPES))

    temp_dir = tempfile.mkdtemp(prefix="test_proj_")
    try:
        projector = FileSystemProjector(graph, src_dir="src")
        written = projector.project_to_disk(temp_dir)

        assert len(written) == 2
        service_file = [p for p in written if "services.py" in p][0]

        with open(service_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Check synthesized import
        assert "from ecommerce.models import Order" in content
        assert "class OrderService:" in content
    finally:
        shutil.rmtree(temp_dir)

