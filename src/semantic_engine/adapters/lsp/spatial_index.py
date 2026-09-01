"""Spatial index mapping physical (file, line, col) coordinates to CanonicalSymbolIds."""

from __future__ import annotations
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from semantic_engine.core.csi import CanonicalSymbolId


@dataclass
class SymbolSpan:
    """Location span occupied by a symbol in a physical file (0-indexed)."""
    csi: CanonicalSymbolId
    file_path: str
    full_start_line: int
    full_end_line: int
    target_line: int
    target_col: int
    full_start_col: int = 0
    full_end_col: int = 0

    def contains(self, line: int, col: int) -> bool:
        if line < self.full_start_line or line > self.full_end_line:
            return False
        if line == self.full_start_line and col < self.full_start_col:
            return False
        if line == self.full_end_line and col > self.full_end_col:
            return False
        return True

    @property
    def line_count(self) -> int:
        return self.full_end_line - self.full_start_line + 1


class SpatialIndex:
    """Two-way spatial mapping between physical editor coordinates and CSIs."""

    def __init__(self, workspace_root: str, package_root: Optional[str] = None) -> None:
        self.workspace_root = os.path.abspath(workspace_root)
        self.package_root = os.path.abspath(package_root) if package_root else self.workspace_root
        self._spans_by_csi: Dict[CanonicalSymbolId, SymbolSpan] = {}
        self._spans_by_file: Dict[str, List[SymbolSpan]] = {}

    def register(
        self,
        csi: CanonicalSymbolId,
        file_path: str,
        full_start_line: int,
        full_end_line: int,
        target_line: int,
        target_col: int,
        full_start_col: int = 0,
        full_end_col: int = 0,
    ) -> None:
        """Register a symbol's full location span and target identifier point."""
        abs_path = os.path.abspath(file_path)
        span = SymbolSpan(
            csi=csi,
            file_path=abs_path,
            full_start_line=full_start_line,
            full_end_line=full_end_line,
            target_line=target_line,
            target_col=target_col,
            full_start_col=full_start_col,
            full_end_col=full_end_col,
        )
        self._spans_by_csi[csi] = span
        self._spans_by_file.setdefault(abs_path, []).append(span)

    def lookup_csi(self, file_path: str, line: int, col: int) -> Optional[CanonicalSymbolId]:
        """Find the tightest (innermost) enclosing symbol at (line, col)."""
        abs_path = os.path.abspath(file_path)
        matching_spans = [
            span for span in self._spans_by_file.get(abs_path, [])
            if span.contains(line, col)
        ]
        if not matching_spans:
            return None
        # Return the span with the smallest line_count (tightest enclosing scope)
        tightest = min(matching_spans, key=lambda s: (s.line_count, -(s.full_start_line)))
        return tightest.csi

    def get_span(self, csi: CanonicalSymbolId) -> Optional[SymbolSpan]:
        """Retrieve the registered physical span for a CSI."""
        return self._spans_by_csi.get(csi)

    def get_file_symbols(self, file_path: str) -> List[CanonicalSymbolId]:
        """Return all symbol CSIs registered in the specified file."""
        abs_path = os.path.abspath(file_path)
        return [span.csi for span in self._spans_by_file.get(abs_path, [])]

    def derive_csi_for_file(
        self,
        file_path: str,
        symbol_name: str,
        parent_csi: Optional[CanonicalSymbolId] = None,
    ) -> CanonicalSymbolId:
        """Derive a clean logical CSI for a symbol defined in a file."""
        if parent_csi:
            return parent_csi.child(symbol_name)

        abs_path = os.path.abspath(file_path)
        
        # If package_root is configured, base the package/namespace on package_root
        if self.package_root and abs_path.startswith(self.package_root):
            package_base = os.path.basename(self.package_root.rstrip("/"))
            rel_to_pkg = os.path.relpath(abs_path, self.package_root)
            path_obj = Path(rel_to_pkg)
            package = package_base or "app"
            namespace_parts = list(path_obj.parts[:-1])
            stem = path_obj.stem
            if stem != "__init__":
                namespace_parts.append(stem)
        else:
            rel_path = os.path.relpath(abs_path, self.workspace_root)
            path_obj = Path(rel_path)
            parts = list(path_obj.parts)
            package = parts[0] if parts else "app"
            namespace_parts = list(parts[1:-1])
            stem = path_obj.stem
            if stem != "__init__" and stem != package:
                namespace_parts.append(stem)

        return CanonicalSymbolId(
            package=package,
            namespace=tuple(namespace_parts),
            symbol_name=symbol_name,
        )

