"""Graph builder that populates a pure SemanticGraph by querying the LSP server."""

from __future__ import annotations
import asyncio
import os
from pathlib import Path
from typing import List, Optional, Set

from semantic_engine.adapters.lsp.client import LspClient
from semantic_engine.adapters.lsp.protocol import SymbolInformation
from semantic_engine.adapters.lsp.signature_parser import SignatureParser
from semantic_engine.adapters.lsp.spatial_index import SpatialIndex
from semantic_engine.core.contract import SymbolContract, SymbolKind
from semantic_engine.core.csi import CanonicalSymbolId
from semantic_engine.core.graph import EdgeType, Relationship, SemanticGraph
from semantic_engine.core.node import SymbolImplementation, SymbolNode


class LspGraphBuilder:
    """Anti-Corruption Adapter that crawls LSP data to construct a SemanticGraph."""

    def __init__(
        self,
        client: LspClient,
        workspace_root: Optional[str] = None,
        package_root: Optional[str] = None,
    ) -> None:
        self.client = client
        self.workspace_root = os.path.abspath(workspace_root or client.workspace_root)
        self.package_root = os.path.abspath(package_root) if package_root else None
        self.spatial_index = SpatialIndex(self.workspace_root, package_root=self.package_root)

    def _discover_python_files(self, target_dir: Optional[str] = None) -> List[str]:
        """Find all Python source files in the workspace, skipping virtualenvs and hidden dirs."""
        root = target_dir or self.workspace_root
        py_files: List[str] = []
        for dirpath, dirnames, filenames in os.walk(root):
            # Skip hidden and cache folders
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in ("__pycache__", "venv", ".venv")]
            for f in filenames:
                if f.endswith(".py"):
                    py_files.append(os.path.join(dirpath, f))
        return py_files

    def _read_file_lines(self, file_path: str) -> List[str]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.readlines()
        except Exception:
            return []

    async def build_graph(self, target_dir: Optional[str] = None) -> SemanticGraph:
        """Execute full workspace ingestion pipeline and return populated SemanticGraph."""
        if target_dir and not self.package_root:
            self.spatial_index.package_root = os.path.abspath(target_dir)

        graph = SemanticGraph()
        py_files = self._discover_python_files(target_dir)

        # 1. Open all documents with LSP server
        for file_path in py_files:
            await self.client.ensure_document_open(file_path)

        # 2. Extract Document Symbols and register spatial spans
        for file_path in py_files:
            lsp_symbols = await self.client.get_document_symbols(file_path)
            self._ingest_symbol_tree(graph, file_path, lsp_symbols, parent_csi=None)

        # 3. Extract Contracts via Hover and Implementations from file spans
        for csi, node in list(graph.nodes.items()):
            span = self.spatial_index.get_span(csi)
            if not span:
                continue

            # Query hover for precise signature & docstring at target point
            hover = await self.client.get_hover(span.file_path, span.target_line, span.target_col)
            if hover and hover.contents:
                contract = SignatureParser.parse_hover_markdown(hover.contents, default_name=node.contract.name)
                # Keep node name and kind if parser returned default
                if contract.name:
                    node.contract.name = contract.name
                if contract.signature:
                    node.contract.signature = contract.signature
                if contract.docstring.summary or contract.docstring.description:
                    node.contract.docstring = contract.docstring
                node.contract.purity = contract.purity
                node.contract.execution_model = contract.execution_model

            # Extract implementation body text from source file
            lines = self._read_file_lines(span.file_path)
            if lines and 0 <= span.full_start_line < len(lines):
                body_lines = lines[span.full_start_line : span.full_end_line + 1]
                body_text = "".join(body_lines)
                node.implementation = SymbolImplementation(body_source=body_text)

        # 4. Discover Relational Edges via LSP References
        for csi, node in list(graph.nodes.items()):
            span = self.spatial_index.get_span(csi)
            if not span:
                continue

            refs = await self.client.get_references(
                span.file_path,
                span.target_line,
                span.target_col,
                include_declaration=False,
            )

            for ref in refs:
                caller_csi = self.spatial_index.lookup_csi(
                    ref.file_path,
                    ref.range.start.line,
                    ref.range.start.character,
                )
                if caller_csi and caller_csi != csi:
                    edge_type = EdgeType.CALLS if node.contract.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD) else EdgeType.TYPES
                    graph.add_edge(Relationship(
                        source_csi=caller_csi,
                        target_csi=csi,
                        edge_type=edge_type,
                    ))

        return graph

    def _ingest_symbol_tree(
        self,
        graph: SemanticGraph,
        file_path: str,
        symbols: List[SymbolInformation],
        parent_csi: Optional[CanonicalSymbolId],
    ) -> None:
        """Recursively process LSP document symbols and register spatial spans."""
        for sym in symbols:
            csi = self.spatial_index.derive_csi_for_file(file_path, sym.name, parent_csi)
            
            # Scope range for the entire body
            full_start_line = sym.full_range.start.line if sym.full_range else sym.location.range.start.line
            full_end_line = sym.full_range.end.line if sym.full_range else sym.location.range.end.line
            full_start_col = sym.full_range.start.character if sym.full_range else 0
            full_end_col = sym.full_range.end.character if sym.full_range else 0

            # Target point for identifier queries (hover / references)
            target_line = sym.selection_range.start.line if sym.selection_range else sym.location.range.start.line
            target_col = sym.selection_range.start.character if sym.selection_range else sym.location.range.start.character

            self.spatial_index.register(
                csi=csi,
                file_path=file_path,
                full_start_line=full_start_line,
                full_end_line=full_end_line,
                target_line=target_line,
                target_col=target_col,
                full_start_col=full_start_col,
                full_end_col=full_end_col,
            )

            # Map LSP integer symbol kind to domain SymbolKind
            kind = SymbolKind.VARIABLE
            if sym.kind_name == "Class":
                kind = SymbolKind.CLASS
            elif sym.kind_name == "Method":
                kind = SymbolKind.METHOD
            elif sym.kind_name == "Function":
                kind = SymbolKind.FUNCTION
            elif sym.kind_name == "Enum":
                kind = SymbolKind.ENUM
            elif sym.kind_name == "Interface":
                kind = SymbolKind.INTERFACE
            elif sym.kind_name == "Property":
                kind = SymbolKind.PROPERTY
            elif sym.kind_name == "Field":
                kind = SymbolKind.FIELD

            node = SymbolNode(
                csi=csi,
                contract=SymbolContract(name=sym.name, kind=kind),
            )
            graph.add_node(node)

            if sym.children:
                self._ingest_symbol_tree(graph, file_path, sym.children, parent_csi=csi)

