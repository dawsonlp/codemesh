"""AI Context Slicing engine extracting minimal prompt-ready contract closures."""

from __future__ import annotations
from dataclasses import dataclass, field
import json
from typing import Any, Dict, List, Optional, Set

from semantic_engine.core.contract import SymbolContract, SymbolKind
from semantic_engine.core.csi import CanonicalSymbolId
from semantic_engine.core.graph import EdgeType, SemanticGraph
from semantic_engine.core.node import SymbolImplementation


@dataclass
class ContextSlice:
    """A surgical context closure tailored for LLM prompt ingestion."""
    target_csi: CanonicalSymbolId
    target_contract: Optional[SymbolContract] = None
    target_implementation: Optional[SymbolImplementation] = None
    dependency_contracts: Dict[CanonicalSymbolId, SymbolContract] = field(default_factory=dict)
    caller_contracts: Dict[CanonicalSymbolId, SymbolContract] = field(default_factory=dict)

    def to_python_stub_prompt(self) -> str:
        """Render prompt as a clean Python stub (.pyi) with target body and dependency contracts."""
        lines: List[str] = []
        lines.append(f"# === TARGET CONTEXT FOR: {self.target_csi.qualified_name} ===")
        lines.append("")

        # 1. Target Contract & Implementation
        lines.append("# --- TARGET TO INSPECT / MODIFY ---")
        if self.target_implementation and not self.target_implementation.is_empty:
            lines.append(self.target_implementation.body_source.strip())
        elif self.target_contract:
            lines.append(self._format_contract_stub(self.target_contract))
        lines.append("")

        # 2. Dependency Contracts (Zero foreign implementation bodies!)
        if self.dependency_contracts:
            lines.append("# --- DEPENDENCY CONTRACTS (READ-ONLY INTERFACES) ---")
            for dep_csi, contract in self.dependency_contracts.items():
                lines.append(f"# CSI: {dep_csi}")
                lines.append(self._format_contract_stub(contract))
                lines.append("")

        # 3. Caller Contracts (if present)
        if self.caller_contracts:
            lines.append("# --- CALLERS / DEPENDENT SYMBOLS ---")
            for caller_csi, contract in self.caller_contracts.items():
                lines.append(f"# CSI: {caller_csi}")
                lines.append(self._format_contract_stub(contract))
                lines.append("")

        return "\n".join(lines).strip()

    def _format_contract_stub(self, contract: SymbolContract) -> str:
        """Format a single contract as a clean declaration stub."""
        out_lines: List[str] = []
        doc = f'    """{contract.docstring.summary}"""' if contract.docstring.summary else ""

        if contract.kind in (SymbolKind.CLASS, SymbolKind.INTERFACE):
            bases = f"({', '.join(b.to_display_string() for b in contract.base_types)})" if contract.base_types else ""
            out_lines.append(f"class {contract.name}{bases}:")
            if doc:
                out_lines.append(doc)
            out_lines.append("    ...")
        elif contract.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD):
            if contract.signature:
                decl = contract.signature.to_declaration_string(contract.name)
                out_lines.append(decl)
                if doc:
                    out_lines.append(doc)
                out_lines.append("    ...")
            else:
                out_lines.append(f"def {contract.name}(*args, **kwargs): ...")
        elif contract.kind == SymbolKind.ENUM:
            out_lines.append(f"class {contract.name}(Enum):")
            out_lines.append("    ...")
        else:
            out_lines.append(f"{contract.name}: Any")

        return "\n".join(out_lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert slice to structured dictionary for JSON export."""
        return {
            "target": {
                "csi": str(self.target_csi),
                "qualified_name": self.target_csi.qualified_name,
                "contract": {
                    "name": self.target_contract.name if self.target_contract else "",
                    "kind": self.target_contract.kind.value if self.target_contract else "",
                    "signature": self.target_contract.signature.to_declaration_string(self.target_contract.name) if self.target_contract and self.target_contract.signature else None,
                    "docstring": self.target_contract.docstring.summary if self.target_contract else "",
                },
                "body": self.target_implementation.body_source if self.target_implementation else None,
            },
            "dependencies": [
                {
                    "csi": str(dep_csi),
                    "name": c.name,
                    "kind": c.kind.value,
                    "stub": self._format_contract_stub(c),
                }
                for dep_csi, c in self.dependency_contracts.items()
            ],
            "callers": [
                {
                    "csi": str(caller_csi),
                    "name": c.name,
                    "kind": c.kind.value,
                    "stub": self._format_contract_stub(c),
                }
                for caller_csi, c in self.caller_contracts.items()
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


class ContextSlicer:
    """Builds surgical, token-budgeted context closures from a SemanticGraph."""

    def __init__(self, graph: SemanticGraph) -> None:
        self.graph = graph

    def build_implementation_slice(
        self,
        target_csi: CanonicalSymbolId,
        include_callers: bool = False,
    ) -> ContextSlice:
        """Extract target implementation plus minimal contract signatures of direct dependencies."""
        target_node = self.graph.get_node(target_csi)
        if not target_node:
            raise ValueError(f"Symbol not found in graph: {target_csi}")

        slice_obj = ContextSlice(
            target_csi=target_csi,
            target_contract=target_node.contract,
            target_implementation=target_node.implementation,
        )

        # Retrieve direct dependencies (callees, types, instantiations, depends_on)
        outgoing = self.graph.get_outgoing_edges(target_csi)
        direct_deps = {
            e.target_csi
            for e in outgoing
            if e.edge_type in (EdgeType.CALLS, EdgeType.TYPES, EdgeType.INSTANTIATES, EdgeType.DEPENDS_ON)
        }

        for dep_csi in direct_deps:
            contract = self.graph.get_contract(dep_csi)
            if contract:
                slice_obj.dependency_contracts[dep_csi] = contract

        if include_callers:
            for caller_csi in self.graph.get_callers(target_csi):
                contract = self.graph.get_contract(caller_csi)
                if contract:
                    slice_obj.caller_contracts[caller_csi] = contract

        return slice_obj

    def build_impact_slice(self, target_csi: CanonicalSymbolId) -> ContextSlice:
        """Extract target contract plus all caller contracts for blast-radius inspection."""
        return self.build_implementation_slice(target_csi, include_callers=True)
