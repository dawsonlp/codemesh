"""High-level Workspace Coordinator managing the complete semantic lifecycle."""

from __future__ import annotations
import os
from typing import List, Optional, Union

from semantic_engine.adapters.lsp.client import LspClient
from semantic_engine.adapters.lsp.graph_builder import LspGraphBuilder
from semantic_engine.core.contract import SymbolKind
from semantic_engine.core.csi import CanonicalSymbolId
from semantic_engine.core.graph import SemanticGraph
from semantic_engine.mutation.engine import MutationEngine
from semantic_engine.mutation.invariants import InvariantViolationError
from semantic_engine.mutation.normalizer import NormalizationError, SymbolBodyNormalizer
from semantic_engine.mutation.primitives import (
    MutationResult,
    ReplaceImplementationMutation,
)
from semantic_engine.projection.file_projector import FileSystemProjector
from semantic_engine.slicing.closure import ContextSlice, ContextSlicer


class SemanticWorkspace:
    """Coordinator providing high-level agent operations over a codebase's SemanticGraph."""

    def __init__(
        self,
        graph: SemanticGraph,
        workspace_root: str = ".",
        target_dir: Optional[str] = None,
    ) -> None:
        self.graph = graph
        self.workspace_root = os.path.abspath(workspace_root)
        self.target_dir = os.path.abspath(target_dir) if target_dir else self.workspace_root
        self.slicer = ContextSlicer(self.graph)

    @classmethod
    async def load(
        cls,
        workspace_root: str = ".",
        target_dir: Optional[str] = None,
    ) -> SemanticWorkspace:
        """Ingest a target codebase directory via the LSP Anti-Corruption Adapter."""
        async with LspClient(workspace_root=workspace_root) as client:
            builder = LspGraphBuilder(
                client=client,
                workspace_root=workspace_root,
                package_root=target_dir,
            )
            graph = await builder.build_graph(target_dir=target_dir)
            return cls(graph=graph, workspace_root=workspace_root, target_dir=target_dir)

    def _resolve_csi(self, csi: Union[str, CanonicalSymbolId]) -> CanonicalSymbolId:
        return CanonicalSymbolId.parse(csi) if isinstance(csi, str) else csi

    def get_symbol_context(
        self,
        csi: Union[str, CanonicalSymbolId],
        include_callers: bool = False,
    ) -> ContextSlice:
        """Extract a surgical prompt-ready context slice for a symbol."""
        csi_obj = self._resolve_csi(csi)
        return self.slicer.build_implementation_slice(csi_obj, include_callers=include_callers)

    def edit_symbol(
        self,
        csi: Union[str, CanonicalSymbolId],
        new_body: str,
        auto_materialize: bool = False,
        output_dir: Optional[str] = None,
    ) -> MutationResult:
        """Zero-Diff Symbol Modification: Parse AST, normalize indentation, apply mutation, and verify invariants.

        Args:
            csi: Target CanonicalSymbolId or csi:// URI string.
            new_body: Raw Python implementation body text.
            auto_materialize: If True, writes updated files to disk immediately.
            output_dir: Directory to project to if auto_materialize is True.

        Returns:
            MutationResult containing success status, blast radius, and materialized file paths.
        """
        csi_obj = self._resolve_csi(csi)
        node = self.graph.get_node(csi_obj)
        if not node:
            return MutationResult(
                success=False,
                target_csi=csi_obj,
                error_message=f"Target symbol not found in graph: {csi_obj}",
            )

        # 1. AST Validation and Indentation Normalization
        is_method = node.contract.kind in (SymbolKind.METHOD, SymbolKind.PROPERTY) or bool(csi_obj.member_path)
        try:
            normalized_body = SymbolBodyNormalizer.normalize_callable_body(
                raw_source=new_body,
                target_csi=csi_obj,
                is_method=is_method,
            )
        except NormalizationError as e:
            return MutationResult(
                success=False,
                target_csi=csi_obj,
                error_message=f"Normalization failed: {e}",
            )

        # 2. Invariant Validation & Blast-Radius Calculation
        mutation = ReplaceImplementationMutation(
            target_csi=csi_obj,
            new_body_source=normalized_body,
        )
        blast_radius = MutationEngine.calculate_blast_radius(self.graph, mutation)

        try:
            MutationEngine.apply_mutation(self.graph, mutation)
        except InvariantViolationError as e:
            return MutationResult(
                success=False,
                target_csi=csi_obj,
                error_message=f"Invariant violation: {e}",
                blast_radius=blast_radius,
            )

        # 3. Optional Auto-Materialization
        materialized_files: List[str] = []
        if auto_materialize:
            target_out = output_dir or "projected_output"
            materialized_files = self.materialize(output_dir=target_out)

        return MutationResult(
            success=True,
            target_csi=csi_obj,
            blast_radius=blast_radius,
            materialized_files=materialized_files,
        )

    def materialize(
        self,
        output_dir: str = "projected_output",
        src_dir: Optional[str] = "src",
    ) -> List[str]:
        """Materialize the entire in-memory SemanticGraph to disk with auto-generated imports."""
        projector = FileSystemProjector(self.graph, src_dir=src_dir)
        return projector.project_to_disk(output_dir)

