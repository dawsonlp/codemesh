# MVP Development Plan: Semantic Program Representation

This document outlines the phased checklist to build and verify the **Minimum Viable Product (MVP)** for the Semantic-First Program Representation.

The goal of the MVP is to prove the end-to-end lifecycle:
$$\text{LSP Ingestion} \longrightarrow \text{Pure Semantic Graph} \longrightarrow \text{AI Context Slicing} \longrightarrow \text{Semantic Mutation \& Blast Radius} \longrightarrow \text{File Projection}$$

---

## MVP Verification Target Scenario

The MVP will be verified against an end-to-end integration test case:
1. **Ingest Codebase**: Ingest `fixtures/sample_ecommerce` into a pure `SemanticGraph` via the LSP Anti-Corruption Layer.
2. **Context Slice**: Extract a prompt-ready context slice for `OrderService.create_order` containing its full body and only the contract signatures of its dependencies (`OrderRepository`, `Money`, `Order`, `generate_unique_id`).
3. **Semantic Mutation**: Execute a structured mutation (e.g., renaming a parameter or updating an implementation) and calculate the blast radius of impacted callers.
4. **Invariant Check**: Verify that valid mutations commit cleanly while breaking contract mutations are caught with structured diagnostics.
5. **Materialization**: Synthesize clean, executable Python files to a target directory with automated import headers, and execute `pytest` on the generated code.

---

## Development Checklist

### Phase 1: Pure Semantic Model Core (`src/codemesh/core/`)
- [x] **1.1 Canonical Symbol IDs (CSI)**: Implement `CanonicalSymbolId` parsing, formatting (`csi://package/namespace/Symbol`), and parent/child hierarchy navigation.
- [x] **1.2 Contract & Types**: Implement `SymbolContract`, `FunctionSignature`, `Parameter`, `TypeRef`, `DocstringSpec`, `SymbolKind`, and `ExecutionModel`.
- [x] **1.3 Symbol Nodes & Implementation**: Implement `SymbolNode` and `SymbolImplementation` (separating public contracts from executable bodies).
- [x] **1.4 Semantic Graph**: Implement `SemanticGraph` with node storage and typed relational edges (`CALLS`, `TYPES`, `IMPLEMENTS`, `SUBTYPES`, `VERIFIES`).

### Phase 2: Anti-Corruption LSP Adapter (`src/codemesh/adapters/lsp/`)
- [x] **2.1 Spatial Indexer**: Build two-way mapping between `(file_path, line, col)` coordinates and `CanonicalSymbolId`.
- [x] **2.2 Signature Parser**: Parse raw LSP hover Markdown strings and type strings into structured `SymbolContract` instances.
- [x] **2.3 Graph Ingester**: Ingest an entire workspace by querying LSP symbols, definitions, and references, populating the pure `SemanticGraph`.

### Phase 3: AI Context Slicing Engine (`src/codemesh/slicing/`)
- [x] **3.1 Dependency Closure Slicer**: Given a target CSI, extract a `ContextSlice` containing the target's implementation body plus the minimal contract signatures of direct callees and parameter/return types.
- [x] **3.2 Prompt Formatter**: Serialize `ContextSlice` into prompt-ready Python stub format (`.pyi` style) and structured JSON.

### Phase 4: Semantic Mutation & Invariant Engine (`src/codemesh/mutation/`)
- [x] **4.1 Mutation Primitives**: Implement structured mutations (`ReplaceImplementation`, `UpdateContract`, `AddSymbol`, `RenameSymbol`, `DeleteSymbol`).
- [x] **4.2 Blast-Radius Calculator**: Traverse reverse dependency edges to identify all impacted callers, subtypes, and test units for a proposed mutation.
- [x] **4.3 Pre-Commit Invariant Verifier**: Validate type and contract consistency before applying changes to the graph.

### Phase 5: FileSystem Projection & Code Generation (`src/codemesh/projection/`)
- [x] **5.1 Automated Import Synthesizer**: Compute minimal, deduplicated `import` statements directly from relational graph edges.
- [x] **5.2 File Materializer**: Deterministically project namespaces and symbol nodes into idiomatic directory and `.py` file structures on disk.

### Phase 6: End-to-End Integration & Verification (`tests/` & `demo.py`)
- [x] **6.1 Ingestion Test**: Verify complete symbol graph and relational edges constructed from sample project.
- [x] **6.2 Slicing Test**: Verify context slice for `OrderService.create_order` contains zero foreign function bodies.
- [x] **6.3 Mutation & Blast-Radius Test**: Verify blast radius correctly detects affected callers when a contract changes.
- [x] **6.4 Materialization & Execution Test**: Project graph to disk and run automated tests against synthesized files.
- [x] **6.5 Interactive Demo Script**: Create `demo.py` demonstrating the entire workflow from ingestion to slicing to mutation and projection.

