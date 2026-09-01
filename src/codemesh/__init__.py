"""Semantic Engine: Canonical Semantic-First Program Representation."""

from codemesh.adapters.lsp import LspClient, LspGraphBuilder
from codemesh.core import (
    CanonicalSymbolId,
    DocstringSpec,
    EdgeType,
    ExecutionModel,
    FunctionSignature,
    LocalVariable,
    Parameter,
    ParameterKind,
    PurityType,
    Relationship,
    SemanticGraph,
    SymbolContract,
    SymbolImplementation,
    SymbolKind,
    SymbolNode,
    TypeRef,
)
from codemesh.mutation import (
    AddSymbolMutation,
    BlastRadiusReport,
    DeleteSymbolMutation,
    InvariantViolationError,
    MoveSymbolMutation,
    MutationEngine,
    MutationResult,
    NormalizationError,
    RenameSymbolMutation,
    ReplaceImplementationMutation,
    SemanticMutation,
    SymbolBodyNormalizer,
    UpdateContractMutation,
)
from codemesh.projection import FileSystemProjector, MaterializedFile
from codemesh.slicing import ContextSlice, ContextSlicer
from codemesh.workspace import SemanticWorkspace

__all__ = [
    # Top-Level Workspace Coordinator
    "SemanticWorkspace",
    # Core Domain
    "CanonicalSymbolId",
    "SymbolKind",
    "ParameterKind",
    "PurityType",
    "ExecutionModel",
    "TypeRef",
    "Parameter",
    "FunctionSignature",
    "DocstringSpec",
    "SymbolContract",
    "LocalVariable",
    "SymbolImplementation",
    "SymbolNode",
    "EdgeType",
    "Relationship",
    "SemanticGraph",
    # Ingestion
    "LspClient",
    "LspGraphBuilder",
    # Slicing
    "ContextSlice",
    "ContextSlicer",
    # Mutation & Invariants
    "SemanticMutation",
    "AddSymbolMutation",
    "ReplaceImplementationMutation",
    "UpdateContractMutation",
    "RenameSymbolMutation",
    "DeleteSymbolMutation",
    "BlastRadiusReport",
    "MutationEngine",
    "MutationResult",
    "SymbolBodyNormalizer",
    "NormalizationError",
    "InvariantViolationError",
    # Projection
    "FileSystemProjector",
    "MaterializedFile",
]
