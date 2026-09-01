"""Automated import synthesis deriving import headers directly from relational graph edges."""

from __future__ import annotations
from typing import Dict, List, Set

from semantic_engine.core.graph import EdgeType, SemanticGraph
from semantic_engine.core.node import SymbolNode


class ImportSynthesizer:
    """Derives clean, minimal, and deduplicated import statements for a file."""

    @classmethod
    def synthesize_imports(cls, graph: SemanticGraph, nodes: List[SymbolNode]) -> List[str]:
        """Synthesize minimal, deduplicated import headers from relational graph edges."""
        imports_by_module: Dict[str, Set[str]] = {}

        for node in nodes:
            # Check outgoing edges from this node and its children
            relevant_csis = [node.csi] + node.children
            for csi in relevant_csis:
                outgoing = graph.get_outgoing_edges(csi)
                for edge in outgoing:
                    if edge.edge_type in (EdgeType.CALLS, EdgeType.TYPES, EdgeType.INSTANTIATES, EdgeType.IMPORTS):
                        target_csi = edge.target_csi
                        # If target is in a different namespace/module
                        if target_csi.package != csi.package or target_csi.namespace != csi.namespace:
                            mod_name = f"{target_csi.package}.{'.'.join(target_csi.namespace)}" if target_csi.namespace else target_csi.package
                            sym_name = target_csi.symbol_name
                            if sym_name:
                                imports_by_module.setdefault(mod_name, set()).add(sym_name)

        import_lines: List[str] = []
        for mod, syms in sorted(imports_by_module.items()):
            sorted_syms = ", ".join(sorted(syms))
            import_lines.append(f"from {mod} import {sorted_syms}")

        return import_lines

