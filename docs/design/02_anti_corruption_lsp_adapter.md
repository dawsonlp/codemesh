# 02. Anti-Corruption LSP Adapter Specification `[Implemented]`

This document details the **Anti-Corruption Layer (ACL)** that wraps the Language Server Protocol (LSP) driver and translates editor-centric payloads into our pure Semantic Domain Model.

---

## 1. Architectural Role & Boundary

```
┌────────────────────────────────────────────────────────────────────────┐
│                        codemesh.core /                                 │
│                     (Pure Domain Model)                                │
│                                                                        │
│   • CanonicalSymbolId (CSI)          • SymbolNode                      │
│   • SymbolContract (Structured)      • SemanticGraph & Edges           │
└───────────────────────────────────▲────────────────────────────────────┘
                                    │
                  ┌─────────────────┴─────────────────┐
                  │    codemesh.adapters.lsp/         │
                  │    (Anti-Corruption Layer)        │
                  └─────────────────▲─────────────────┘
                                    │
                                    │ (Translates editor coordinates & strings)
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                        lsp_client / pyright                            │
│                    (LSP stdio Driver)                                  │
│                                                                        │
│   • Position { line, char }          • Location { uri, range }         │
│   • Hover { MarkupContent }          • DocumentSymbol / Range          │
└────────────────────────────────────────────────────────────────────────┘
```

The `adapters.lsp` package ensures:
1. **Zero Domain Pollution**: No LSP class or coordinate dictionary ever passes upward into `codemesh.core`.
2. **Deterministic Translation**: Bi-directional mapping between `(file_path, line, character)` $\leftrightarrow$ `CanonicalSymbolId`.
3. **Structured Ingestion**: Unstructured markdown hover tooltips are parsed into structured type contracts and docstring specifications.

---

## 2. Translation Mechanics

### 2.1 Coordinate-to-CSI Mapping (`SymbolResolver`)
The adapter maintains an internal two-way spatial index:
* **Forward Resolution**: `resolve_location(file_path, line, character) -> CanonicalSymbolId`
* **Reverse Resolution**: `resolve_csi_location(csi) -> Location (file_path, line_range)`

#### Spatial Index Algorithm
```python
class LocationIndex:
    """Internal spatial tree mapping file byte/line ranges to CSIs."""
    def register_symbol(self, csi: CanonicalSymbolId, file_path: str, start_line: int, end_line: int) -> None: ...
    def lookup_csi(self, file_path: str, line: int, character: int) -> Optional[CanonicalSymbolId]: ...
    def get_symbol_span(self, csi: CanonicalSymbolId) -> Optional[Tuple[str, int, int]]: ...
```

### 2.2 Hover & Signature Parsing (`SignatureParser`)
LSP language servers (like `pyright`) return hover documentation as formatted markdown code blocks:
```markdown
```python
(method) def create_order(
    self: Self@OrderService,
    user_id: str,
    items: List[OrderItem]
) -> Order
```
---
Create and persist a new customer order.
```

The `SignatureParser` dissects this string into structured domain objects:
1. **Kind Extraction**: `(method)` $\rightarrow$ `SymbolKind.METHOD`.
2. **Parameters Extraction**:
   - `user_id: str` $\rightarrow$ `Parameter(name="user_id", type_ref=TypeRef("str"))`
   - `items: List[OrderItem]` $\rightarrow$ `Parameter(name="items", type_ref=TypeRef("List[OrderItem]"))`
3. **Return Type Extraction**: `-> Order` $\rightarrow$ `TypeRef("Order")`.
4. **Docstring Segmentation**: Splits summary, arg descriptions, and return annotations into `DocstringSpec`.

---

## 3. Graph Ingestion Pipeline

To populate a complete `SemanticGraph` from a workspace, the adapter executes a five-stage pipeline:

```
┌──────────────────────────┐
│ 1. Workspace Discovery   │ Crawls project root and discovers all source modules.
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ 2. Symbol Tree Crawl     │ Sends `textDocument/documentSymbol` to collect
└────────────┬─────────────┘ class, method, function, and field hierarchies.
             │
             ▼
┌──────────────────────────┐
│ 3. Contract Extraction   │ Sends `textDocument/hover` for every symbol position;
└────────────┬─────────────┘ parses signatures and docstrings into `SymbolContract`.
             │
             ▼
┌──────────────────────────┐
│ 4. Relational Edge Crawl │ Sends `textDocument/references` and `definition`
└────────────┬─────────────┘ to discover `CALLS`, `TYPES`, `SUBTYPES`, and `IMPLEMENTS`.
             │
             ▼
┌──────────────────────────┐
│ 5. Foreign Binding       │ Resolves external standard library and 3rd-party
└──────────────────────────┘ references into Foreign Contract nodes.
```

### 3.1 Step-by-Step Execution Sequence

```python
class LspGraphBuilder:
    """Anti-Corruption Adapter orchestrating the SemanticGraph construction."""
    
    def __init__(self, client: LspClient, workspace_root: str) -> None:
        self.client = client
        self.workspace_root = workspace_root
        self.location_index = LocationIndex()

    async def build_semantic_graph(self) -> SemanticGraph:
        graph = SemanticGraph()
        
        # 1. Discover and open all workspace source files
        files = self._discover_source_files()
        for f in files:
            await self.client.ensure_document_open(f)
            
        # 2. Extract Document Symbols and build CSI hierarchy
        for f in files:
            lsp_symbols = await self.client.get_document_symbols(f)
            self._ingest_symbol_tree(graph, f, lsp_symbols)
            
        # 3. Resolve Contracts via Hover
        for csi, node in list(graph.nodes.items()):
            span = self.location_index.get_symbol_span(csi)
            if span:
                file_path, line, col = span
                hover = await self.client.get_hover(file_path, line, col)
                if hover:
                    node.contract = SignatureParser.parse(hover.contents, node.contract.name)
                    
        # 4. Resolve Edges via References
        for csi, node in list(graph.nodes.items()):
            span = self.location_index.get_symbol_span(csi)
            if span:
                file_path, line, col = span
                refs = await self.client.get_references(file_path, line, col, include_declaration=False)
                for ref in refs:
                    caller_csi = self.location_index.lookup_csi(ref.file_path, ref.range.start.line, ref.range.start.character)
                    if caller_csi and caller_csi != csi:
                        graph.add_edge(Relationship(
                            source_csi=caller_csi,
                            target_csi=csi,
                            edge_type=EdgeType.CALLS,
                        ))
                        
        return graph
```

---

## 4. Incremental Synchronization & Invalidation

When a file is modified (either by an agent or human editor):
1. **Target Invalidation**: The adapter removes existing symbols within the modified file from `SemanticGraph`.
2. **LSP Re-Index**: Notifies LSP via `textDocument/didChange`.
3. **Selective Re-Ingestion**: Queries document symbols and hovers only for the modified file.
4. **Edge Stitching**: Recomputes relational edges for the newly ingested nodes.

