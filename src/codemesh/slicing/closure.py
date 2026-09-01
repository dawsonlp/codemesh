"""AI Context Slicing engine extracting minimal prompt-ready contract closures."""

from __future__ import annotations
from dataclasses import dataclass, field
import json
from typing import Any, Dict, List, Optional, Set, Tuple

from codemesh.core.contract import SymbolContract, SymbolKind
from codemesh.core.csi import CanonicalSymbolId
from codemesh.core.graph import EdgeType, SemanticGraph
from codemesh.core.node import SymbolImplementation


@dataclass
class TargetSymbolEntry:
    """Target symbol representation in a slice."""
    csi: CanonicalSymbolId
    contract: Optional[SymbolContract] = None
    implementation: Optional[SymbolImplementation] = None


@dataclass
class ContextSlice:
    """A surgical context closure tailored for LLM prompt ingestion."""
    target_csis: List[CanonicalSymbolId] = field(default_factory=list)
    targets: Dict[CanonicalSymbolId, TargetSymbolEntry] = field(default_factory=dict)
    dependency_contracts: Dict[CanonicalSymbolId, SymbolContract] = field(default_factory=dict)
    caller_contracts: Dict[CanonicalSymbolId, SymbolContract] = field(default_factory=dict)

    def __init__(
        self,
        target_csi: Optional[CanonicalSymbolId] = None,
        target_contract: Optional[SymbolContract] = None,
        target_implementation: Optional[SymbolImplementation] = None,
        target_csis: Optional[List[CanonicalSymbolId]] = None,
        targets: Optional[Dict[CanonicalSymbolId, TargetSymbolEntry]] = None,
        dependency_contracts: Optional[Dict[CanonicalSymbolId, SymbolContract]] = None,
        caller_contracts: Optional[Dict[CanonicalSymbolId, SymbolContract]] = None,
    ) -> None:
        self.target_csis = target_csis or []
        self.targets = targets or {}
        self.dependency_contracts = dependency_contracts or {}
        self.caller_contracts = caller_contracts or {}

        if target_csi:
            if target_csi not in self.target_csis:
                self.target_csis.append(target_csi)
            self.targets[target_csi] = TargetSymbolEntry(
                csi=target_csi,
                contract=target_contract,
                implementation=target_implementation,
            )

    @property
    def target_csi(self) -> Optional[CanonicalSymbolId]:
        return self.target_csis[0] if self.target_csis else None

    @property
    def target_contract(self) -> Optional[SymbolContract]:
        primary = self.target_csi
        return self.targets[primary].contract if primary and primary in self.targets else None

    @property
    def target_implementation(self) -> Optional[SymbolImplementation]:
        primary = self.target_csi
        return self.targets[primary].implementation if primary and primary in self.targets else None

    def to_python_stub_prompt(self) -> str:
        """Render prompt as a clean Python stub (.pyi) with target bodies and dependency contracts."""
        lines: List[str] = []

        if len(self.target_csis) == 1:
            primary_csi = self.target_csis[0]
            lines.append(f"# === TARGET CONTEXT FOR: {primary_csi.qualified_name} ===")
            lines.append("")
            lines.append("# --- TARGET TO INSPECT / MODIFY ---")
            entry = self.targets.get(primary_csi)
            if entry and entry.implementation and not entry.implementation.is_empty:
                lines.append(entry.implementation.body_source.strip())
            elif entry and entry.contract:
                lines.append(self._format_contract_stub(entry.contract))
            lines.append("")
        else:
            lines.append(f"# === MULTI-TARGET CONTEXT ({len(self.target_csis)} SYMBOLS) ===")
            lines.append("")
            for csi in self.target_csis:
                lines.append(f"# --- TARGET: {csi.qualified_name} (CSI: {csi}) ---")
                entry = self.targets.get(csi)
                if entry and entry.implementation and not entry.implementation.is_empty:
                    lines.append(entry.implementation.body_source.strip())
                elif entry and entry.contract:
                    lines.append(self._format_contract_stub(entry.contract))
                lines.append("")

        # Filter out dependencies that are already present in target_csis
        filtered_deps = {
            k: v for k, v in self.dependency_contracts.items() if k not in self.target_csis
        }

        # Dependency Contracts (Zero foreign implementation bodies!)
        if filtered_deps:
            title = "# --- SHARED DEPENDENCY CONTRACTS (READ-ONLY INTERFACES) ---" if len(self.target_csis) > 1 else "# --- DEPENDENCY CONTRACTS (READ-ONLY INTERFACES) ---"
            lines.append(title)
            for dep_csi, contract in filtered_deps.items():
                lines.append(f"# CSI: {dep_csi}")
                lines.append(self._format_contract_stub(contract))
                lines.append("")

        # Caller Contracts (if present)
        filtered_callers = {
            k: v for k, v in self.caller_contracts.items() if k not in self.target_csis
        }
        if filtered_callers:
            lines.append("# --- CALLERS / DEPENDENT SYMBOLS ---")
            for caller_csi, contract in filtered_callers.items():
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
            "targets": [
                {
                    "csi": str(csi),
                    "qualified_name": csi.qualified_name,
                    "contract": {
                        "name": entry.contract.name if entry.contract else "",
                        "kind": entry.contract.kind.value if entry.contract else "",
                        "signature": entry.contract.signature.to_declaration_string(entry.contract.name) if entry.contract and entry.contract.signature else None,
                        "docstring": entry.contract.docstring.summary if entry.contract else "",
                    } if entry.contract else None,
                    "body": entry.implementation.body_source if entry.implementation else None,
                }
                for csi, entry in self.targets.items()
            ],
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
        return self.build_multi_target_slice([target_csi], include_callers=include_callers)

    def build_multi_target_slice(
        self,
        target_csis: List[CanonicalSymbolId],
        include_callers: bool = False,
    ) -> ContextSlice:
        """Extract multiple target implementations plus minimal unified contract closures."""
        if not target_csis:
            raise ValueError("target_csis list cannot be empty")

        slice_obj = ContextSlice()
        for csi in target_csis:
            node = self.graph.get_node(csi)
            if not node:
                raise ValueError(f"Symbol not found in graph: {csi}")
            slice_obj.target_csis.append(csi)
            slice_obj.targets[csi] = TargetSymbolEntry(
                csi=csi,
                contract=node.contract,
                implementation=node.implementation,
            )

            # Retrieve direct dependencies (callees, types, instantiations, depends_on)
            outgoing = self.graph.get_outgoing_edges(csi)
            direct_deps = {
                e.target_csi
                for e in outgoing
                if e.edge_type in (EdgeType.CALLS, EdgeType.TYPES, EdgeType.INSTANTIATES, EdgeType.DEPENDS_ON)
            }

            for dep_csi in direct_deps:
                if dep_csi not in slice_obj.dependency_contracts and dep_csi not in target_csis:
                    contract = self.graph.get_contract(dep_csi)
                    if contract:
                        slice_obj.dependency_contracts[dep_csi] = contract

            if include_callers:
                for caller_csi in self.graph.get_callers(csi):
                    if caller_csi not in slice_obj.caller_contracts and caller_csi not in target_csis:
                        contract = self.graph.get_contract(caller_csi)
                        if contract:
                            slice_obj.caller_contracts[caller_csi] = contract

        return slice_obj

    def build_impact_slice(self, target_csi: CanonicalSymbolId) -> ContextSlice:
        """Extract target contract plus all caller contracts for blast-radius inspection."""
        return self.build_implementation_slice(target_csi, include_callers=True)
