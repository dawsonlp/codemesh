"""Python LSP client and AI code intelligence utilities."""

from .client import LspClient
from .protocol import (
    Diagnostic,
    Hover,
    Location,
    Position,
    Range,
    SymbolInformation,
    path_to_uri,
    uri_to_path,
)
from .context_builder import (
    describe_symbol_at_position,
    get_file_outline,
)

__all__ = [
    "LspClient",
    "Diagnostic",
    "Hover",
    "Location",
    "Position",
    "Range",
    "SymbolInformation",
    "path_to_uri",
    "uri_to_path",
    "describe_symbol_at_position",
    "get_file_outline",
]

