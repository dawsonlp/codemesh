"""LSP Anti-Corruption Ingestion Adapter."""

from semantic_engine.adapters.lsp.client import LspClient
from semantic_engine.adapters.lsp.graph_builder import LspGraphBuilder
from semantic_engine.adapters.lsp.protocol import (
    Diagnostic,
    Hover,
    Location,
    Position,
    Range,
    SymbolInformation,
    path_to_uri,
    uri_to_path,
)
from semantic_engine.adapters.lsp.signature_parser import SignatureParser
from semantic_engine.adapters.lsp.spatial_index import SpatialIndex, SymbolSpan

__all__ = [
    "LspClient",
    "LspGraphBuilder",
    "SpatialIndex",
    "SymbolSpan",
    "SignatureParser",
    "Diagnostic",
    "Hover",
    "Location",
    "Position",
    "Range",
    "SymbolInformation",
    "path_to_uri",
    "uri_to_path",
]

