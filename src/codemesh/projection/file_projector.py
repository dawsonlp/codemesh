"""FileSystem Projection engine compiling a SemanticGraph into physical source files on disk."""

from __future__ import annotations
from dataclasses import dataclass
import os
from pathlib import Path
import textwrap
from typing import Dict, List, Optional, Set, Tuple

from codemesh.core.contract import SymbolKind
from codemesh.core.csi import CanonicalSymbolId
from codemesh.core.graph import SemanticGraph
from codemesh.core.node import SymbolNode
from codemesh.projection.import_synthesizer import ImportSynthesizer


@dataclass
class MaterializedFile:
    """Represents a generated source file on disk."""
    relative_path: str
    content: str


class FileSystemProjector:
    """Projects a SemanticGraph into a deterministic physical file tree on disk."""

    def __init__(self, graph: SemanticGraph, src_dir: Optional[str] = "src") -> None:
        self.graph = graph
        self.src_dir = src_dir

    def _csi_to_file_path(self, csi: CanonicalSymbolId) -> str:
        """Map a CSI to its physical relative file path."""
        path_parts: List[str] = []
        if self.src_dir:
            path_parts.append(self.src_dir)
        path_parts.append(csi.package)
        if csi.namespace:
            path_parts.extend(csi.namespace[:-1])
            stem = csi.namespace[-1]
            path_parts.append(f"{stem}.py")
        else:
            path_parts.append(f"{csi.package}.py")
        return os.path.join(*path_parts)

    def group_symbols_by_file(self) -> Dict[str, List[SymbolNode]]:
        """Group top-level symbol nodes by their destination file path."""
        file_map: Dict[str, List[SymbolNode]] = {}
        for csi, node in self.graph.nodes.items():
            # Only group top-level symbols (symbols without a member_path)
            if not csi.member_path:
                file_path = self._csi_to_file_path(csi)
                file_map.setdefault(file_path, []).append(node)
        return file_map

    def render_file_content(self, file_path: str, nodes: List[SymbolNode]) -> str:
        """Render complete source file text with synthesized imports and symbol bodies."""
        sections: List[str] = []

        # 1. Header & Synthesized Imports
        imports = ImportSynthesizer.synthesize_imports(self.graph, nodes)
        if imports:
            sections.append("\n".join(imports))

        # 2. Topologically render symbols (Classes / Functions)
        for node in nodes:
            if node.contract.kind in (SymbolKind.CLASS, SymbolKind.INTERFACE) and node.children:
                child_nodes = [self.graph.get_node(c) for c in node.children]
                child_renderable: List[str] = []
                for cn in child_nodes:
                    if cn and cn.implementation and not cn.implementation.is_empty:
                        cleaned_body = textwrap.dedent(cn.implementation.body_source).strip()
                        # Exclude instance attributes assigned inside methods (e.g. self.api_key = api_key)
                        if cleaned_body.startswith("self."):
                            continue
                        indented = "\n".join(f"    {line}" if line.strip() else "" for line in cleaned_body.splitlines())
                        child_renderable.append(indented)

                if child_renderable:
                    class_lines: List[str] = []
                    bases = f"({', '.join(b.to_display_string() for b in node.contract.base_types)})" if node.contract.base_types else ""
                    class_lines.append(f"class {node.contract.name}{bases}:")
                    if node.contract.docstring.summary:
                        class_lines.append(f'    """{node.contract.docstring.summary}"""\n')

                    class_lines.extend(child_renderable)
                    sections.append("\n\n".join(class_lines))
                    continue

            if node.implementation and not node.implementation.is_empty:
                sections.append(node.implementation.body_source.strip())
            else:
                # Stub generation if no implementation text
                contract = node.contract
                if contract.kind in (SymbolKind.CLASS, SymbolKind.INTERFACE):
                    sections.append(f"class {contract.name}:\n    pass")
                elif contract.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD):
                    sections.append(f"def {contract.name}():\n    pass")

        return "\n\n\n".join(sections).strip() + "\n"

    def project_to_memory(self) -> List[MaterializedFile]:
        """Compile all graph nodes into in-memory file representations."""
        file_map = self.group_symbols_by_file()
        materialized: List[MaterializedFile] = []
        for file_path, nodes in file_map.items():
            content = self.render_file_content(file_path, nodes)
            materialized.append(MaterializedFile(relative_path=file_path, content=content))
        return materialized

    def project_to_disk(self, output_dir: str) -> List[str]:
        """Materialize files directly onto the physical file system."""
        abs_output = os.path.abspath(output_dir)
        materialized_files = self.project_to_memory()
        written_paths: List[str] = []

        for mat_file in materialized_files:
            full_path = os.path.join(abs_output, mat_file.relative_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(mat_file.content)
            written_paths.append(full_path)

        return written_paths

