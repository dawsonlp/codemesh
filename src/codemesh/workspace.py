"""High-level Workspace Coordinator managing the complete semantic lifecycle."""

from __future__ import annotations
import ast
import os
import textwrap
from typing import List, Optional, Union

from codemesh.adapters.lsp.client import LspClient
from codemesh.adapters.lsp.graph_builder import LspGraphBuilder
from codemesh.core.contract import SymbolContract, SymbolKind
from codemesh.core.csi import CanonicalSymbolId
from codemesh.core.graph import SemanticGraph
from codemesh.core.node import SymbolImplementation, SymbolNode
from codemesh.mutation.blast_radius import BlastRadiusReport
from codemesh.mutation.engine import MutationEngine
from codemesh.mutation.invariants import InvariantViolationError
from codemesh.mutation.normalizer import NormalizationError, SymbolBodyNormalizer
from codemesh.mutation.primitives import (
    AddSymbolMutation,
    MoveSymbolMutation,
    MutationResult,
    RenameSymbolMutation,
    ReplaceImplementationMutation,
)
from codemesh.projection.file_projector import FileSystemProjector
from codemesh.slicing.closure import ContextSlice, ContextSlicer


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

    # --- 1. CONTEXT SLICING APIS ---

    def get_symbol_context(
        self,
        csi: Union[str, CanonicalSymbolId],
        include_callers: bool = False,
    ) -> ContextSlice:
        """Extract a surgical prompt-ready context slice for a single symbol."""
        csi_obj = self._resolve_csi(csi)
        return self.slicer.build_implementation_slice(csi_obj, include_callers=include_callers)

    def get_multi_symbol_context(
        self,
        csis: List[Union[str, CanonicalSymbolId]],
        include_callers: bool = False,
    ) -> ContextSlice:
        """Extract a unified multi-target context slice showing editable target bodies with shared dependency contracts."""
        csi_objs = [self._resolve_csi(c) for c in csis]
        return self.slicer.build_multi_target_slice(csi_objs, include_callers=include_callers)

    # --- 2. GRAPH DISCOVERY & QUERY APIS ---

    def find_implementations(self, interface_csi: Union[str, CanonicalSymbolId]) -> List[CanonicalSymbolId]:
        """Find all classes that implement or inherit from the specified interface or base class."""
        return self.graph.find_implementations(self._resolve_csi(interface_csi))

    def find_callers(self, target_csi: Union[str, CanonicalSymbolId]) -> List[CanonicalSymbolId]:
        """Find all symbols that directly call the specified target symbol."""
        return self.graph.find_callers(self._resolve_csi(target_csi))

    def find_references(self, target_csi: Union[str, CanonicalSymbolId]) -> List[CanonicalSymbolId]:
        """Find all symbols with outgoing edges (calls, types, instantiations) to the target symbol."""
        return self.graph.find_references(self._resolve_csi(target_csi))

    def find_symbols(self, query: str) -> List[CanonicalSymbolId]:
        """Search symbol names across the semantic graph."""
        return self.graph.find_symbols_matching(query)

    # --- 3. ZERO-DIFF MUTATION & REFACTORING APIS ---

    def edit_symbol(
        self,
        csi: Union[str, CanonicalSymbolId],
        new_body: str,
        auto_materialize: bool = False,
        output_dir: Optional[str] = None,
    ) -> MutationResult:
        """Zero-Diff Symbol Modification: Parse AST, normalize indentation, apply mutation, and verify invariants."""
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

    def add_symbol(
        self,
        target_package: str,
        code: str,
        auto_materialize: bool = False,
        output_dir: Optional[str] = None,
    ) -> MutationResult:
        """Parse AST and add a new top-level class, function, or interface symbol to the graph."""
        cleaned_code = textwrap.dedent(code).strip()
        try:
            tree = ast.parse(cleaned_code)
        except SyntaxError as e:
            return MutationResult(
                success=False,
                target_csi=CanonicalSymbolId.parse(f"csi://{target_package}/unknown"),
                error_message=f"Syntax error in proposed symbol: {e}",
            )

        if not tree.body:
            return MutationResult(
                success=False,
                target_csi=CanonicalSymbolId.parse(f"csi://{target_package}/unknown"),
                error_message="Empty code snippet provided",
            )

        top_item = tree.body[0]
        if isinstance(top_item, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            symbol_name = top_item.name
            kind = SymbolKind.CLASS if isinstance(top_item, ast.ClassDef) else SymbolKind.FUNCTION
        else:
            return MutationResult(
                success=False,
                target_csi=CanonicalSymbolId.parse(f"csi://{target_package}/unknown"),
                error_message="Code snippet must define a top-level Class or Function",
            )

        csi = CanonicalSymbolId.parse(f"csi://{target_package}/{symbol_name}")
        docstring = ast.get_docstring(top_item) or ""
        contract = SymbolContract(name=symbol_name, kind=kind)
        if docstring:
            contract.docstring.summary = docstring

        # Add the parent node
        node = SymbolNode(
            csi=csi,
            contract=contract,
            implementation=SymbolImplementation(body_source=cleaned_code),
        )
        self.graph.add_node(node)

        # If it's a class, also ingest child methods
        if isinstance(top_item, ast.ClassDef):
            for item in top_item.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_csi = csi.child(item.name)
                    # Extract method code
                    method_lines = ast.get_source_segment(cleaned_code, item) or f"def {item.name}(self): pass"
                    method_node = SymbolNode(
                        csi=method_csi,
                        contract=SymbolContract(name=item.name, kind=SymbolKind.METHOD),
                        implementation=SymbolImplementation(body_source=method_lines),
                    )
                    self.graph.add_node(method_node)

        materialized_files: List[str] = []
        if auto_materialize:
            target_out = output_dir or "projected_output"
            materialized_files = self.materialize(output_dir=target_out)

        add_mut = AddSymbolMutation(parent_csi=csi, contract=contract)
        blast_radius = MutationEngine.calculate_blast_radius(self.graph, add_mut)

        return MutationResult(
            success=True,
            target_csi=csi,
            blast_radius=blast_radius,
            materialized_files=materialized_files,
        )

    def rename_symbol(
        self,
        csi: Union[str, CanonicalSymbolId],
        new_name: str,
        auto_materialize: bool = False,
        output_dir: Optional[str] = None,
    ) -> MutationResult:
        """Atomic Semantic Rename: Updates the symbol node, all caller AST expressions, and re-indexes the graph."""
        csi_obj = self._resolve_csi(csi)
        node = self.graph.get_node(csi_obj)
        if not node:
            return MutationResult(
                success=False,
                target_csi=csi_obj,
                error_message=f"Target symbol not found in graph: {csi_obj}",
            )

        mutation = RenameSymbolMutation(target_csi=csi_obj, new_name=new_name)
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

        materialized_files: List[str] = []
        if auto_materialize:
            target_out = output_dir or "projected_output"
            materialized_files = self.materialize(output_dir=target_out)

        return MutationResult(
            success=True,
            target_csi=node.csi,
            blast_radius=blast_radius,
            materialized_files=materialized_files,
        )

    def move_symbol(
        self,
        csi: Union[str, CanonicalSymbolId],
        new_package: str,
        auto_materialize: bool = False,
        output_dir: Optional[str] = None,
    ) -> MutationResult:
        """Atomic Semantic Relocation: Moves a symbol to a new module/package with auto-reconciled imports."""
        csi_obj = self._resolve_csi(csi)
        node = self.graph.get_node(csi_obj)
        if not node:
            return MutationResult(
                success=False,
                target_csi=csi_obj,
                error_message=f"Target symbol not found in graph: {csi_obj}",
            )

        mutation = MoveSymbolMutation(target_csi=csi_obj, new_package=new_package)
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

        materialized_files: List[str] = []
        if auto_materialize:
            target_out = output_dir or "projected_output"
            materialized_files = self.materialize(output_dir=target_out)

        return MutationResult(
            success=True,
            target_csi=node.csi,
            blast_radius=blast_radius,
            materialized_files=materialized_files,
        )

    # --- 4. PROJECTION ---

    def materialize(
        self,
        output_dir: str = "projected_output",
        src_dir: Optional[str] = "src",
    ) -> List[str]:
        """Materialize the entire in-memory SemanticGraph to disk with auto-generated imports."""
        projector = FileSystemProjector(self.graph, src_dir=src_dir)
        return projector.project_to_disk(output_dir)
