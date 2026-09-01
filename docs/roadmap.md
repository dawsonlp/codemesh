# CodeMesh: Architecture & Capabilities Roadmap

This document outlines the strategic roadmap for evolving **CodeMesh** into a federated semantic graph engine and agent runtime. CodeMesh bridges **computation semantics** (code symbols, contracts, ASTs), **information semantics** (logical and physical data models), and **intent semantics** (requirements, constraints, architectural decisions) for autonomous AI software engineering.

---

## 1. Core Vision & Architectural Principles

Current AI coding assistants interact with software through raw text files, line ranges, and regex search/replace patches. This model forces LLMs to waste context tokens on irrelevant boilerplate, suffer from fragile patch failures, hallucinate missing contracts, and lack awareness of system constraints and data models.

CodeMesh replaces this file-centric paradigm with a **Federated Semantic Knowledge Graph** guided by five foundational principles:

1. **Multiple Semantic Authorities, One Connected Graph**:
   * CodeMesh is the authority for **computation semantics** (symbols, implementations, ASTs, execution flow).
   * The Data Dictionary is the authority for **information semantics** (conceptual, logical, and physical data models).
   * The Policy Engine is the authority for **intent semantics** (requirements, constraints, decisions, governance).
2. **Federated Canonical Identifiers**:
   * Entities maintain canonical identities across authority boundaries:
     * Code Symbols: `csi://<package>/<namespace>/<Symbol>[.<member>]`
     * Logical Data: `data://logical/<domain>/<Entity>[.<attribute>]`
     * Physical Data: `data://physical/<system>/<schema>/<table>[.<column>]`
     * Requirements & Policies: `req://<domain>/<slug>`
3. **Orthogonal Conceptual $\to$ Logical $\to$ Physical Hierarchy**:
   * Preserves standard DAMA data governance. Business logic links to **Logical Data Entities** (`CREATES`, `READS`, `VALIDATES`), while repository and persistence adapters link to **Physical Data Objects** (`WRITES`, `SERIALIZES`).
4. **Explicit Fact Provenance & Confidence**:
   * Every non-code semantic node and edge records its authority class: `DECLARED` (human/authority), `DERIVED` (deterministic AST/compiler analysis), or `INFERRED` (AI/heuristic).
5. **Interactive & Invariant-Guarded Evolution**:
   * Context is navigated interactively (`context` $\to$ `expand`), mutations are atomic and zero-diff, and executable constraints validate changes *before* touching disk.

---

## 2. Feature Maturity Classification

All capabilities across CodeMesh documentation are labeled with their current development status:

* `[Implemented]`: Fully functional, tested, and available in the current release.
* `[Experimental]`: Functional in prototypes or benchmarks; active API stabilization.
* `[Designed]`: Fully specified in design docs with concrete schemas; ready for implementation.
* `[Planned]`: On the strategic roadmap; conceptual design in progress.

---

## 3. Capability Pillars

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   CODEMESH ARCHITECTURE PILLARS                                 │
├──────────────────────┬──────────────────────┬───────────────────────────────────────────────────┤
│ PILLAR 1: FEDERATED  │ PILLAR 2: AGENT TOOL │ PILLAR 3: CROSS-MODEL IMPACT &                    │
│      KNOWLEDGE GRAPH │           SURFACE    │           SEMANTIC TRANSACTIONS                   │
│ • Code Symbol Nodes  │ • Native MCP Tools   │ • Cross-Model Blast Radius (Data ↔ Code ↔ Req)    │
│ • Logical Data Links │ • Zero-Diff Edits    │ • Multi-Symbol Semantic Transactions              │
│ • Requirements Nodes │ • Context Expansion  │ • Semantic Correctness Benchmarks                 │
├──────────────────────┼──────────────────────┼───────────────────────────────────────────────────┤
│ PILLAR 4: INVARIANTS │ PILLAR 5: PYTHON     │ PILLAR 6: SYSTEM & RUNTIME                        │
│     & GUARDRAILS     │      SPECIALIZATION  │           SEMANTICS                               │
│ • In-Memory LSP Diags│ • Pydantic & FastAPI │ • APIs, Events & Messaging                        │
│ • Executable Rules   │ • Auto-Import Engine │ • State Transitions & Telemetry                   │
│ • Targeted Testing   │ • Ruff/Black PEP 8   │ • Multi-Agent Workspaces                          │
└──────────────────────┴──────────────────────┴───────────────────────────────────────────────────┘
```

---

### Pillar 1: Federated Semantic Knowledge Graph & Ontology
*Bridging computation, information, and requirement semantics under unified URI addressing.*

#### Capabilities
1. **Core Symbol Ontology & Canonical Symbol IDs (CSI)** `[Implemented]`:
   * `csi://<package>/<namespace>/<symbol>[.<member>]` addressing classes, methods, functions, and properties with contract-implementation separation.
2. **Federated External URIs (`data://`, `req://`)** `[Designed]`:
   * Extends the graph to reference entities owned by external authorities (`data://logical/sales/Order`, `req://payments/idempotent-capture`).
3. **Cross-Model Code-to-Data Relational Edges** `[Designed]`:
   * Relational verbs connecting computation to information:
     * Domain layer: `OrderService.create_order` $\xrightarrow{\text{CREATES}}$ `data://logical/sales/Order`
     * Persistence layer: `PostgresOrderRepo.save` $\xrightarrow{\text{WRITES}}$ `data://physical/postgres/orders`
     * Validation layer: `OrderValidator.validate` $\xrightarrow{\text{VALIDATES}}$ `data://logical/sales/Order.status`
4. **Requirements, Constraints & Architectural Decisions** `[Designed]`:
   * First-class nodes for `Requirement`, `Constraint`, `Policy`, and `Decision` (ADRs) with relationships: `SATISFIES`, `CONSTRAINS`, `GOVERNS`, `IMPLEMENTS`, `VERIFIES`.
5. **Semantic Fact Provenance & Confidence Classes** `[Designed]`:
   * Explicit tracking of node and edge authority:
     * `DECLARED`: Authored by humans, data dictionaries, schema registries, or regulatory specs.
     * `DERIVED`: Deterministically extracted by AST, LSP, or compiler passes.
     * `INFERRED`: Suggested by LLM analysis or heuristic scanners (tagged with confidence scores).

---

### Pillar 2: High-Leverage Agent Tool Surface & Interactive Context
*Providing AI agents with dedicated, ergonomic tools rather than requiring ad-hoc SDK scripting.*

#### Capabilities
1. **Zero-Diff Symbol Modification (`edit_symbol`)** `[Implemented]`:
   * Modifies function and method bodies directly by CSI with automated AST validation and indentation normalization.
2. **High-Level Symbol Addition (`add_symbol`)** `[Implemented]`:
   * Parses AST, constructs `SymbolContract` + `SymbolImplementation`, and links child symbols automatically.
3. **Graph Semantic Discovery API (`find_implementations`, `find_callers`)** `[Implemented]`:
   * Fast relational discovery eliminating grep/regex noise.
4. **Atomic Semantic Refactorings (`rename_symbol`, `move_symbol`)** `[Implemented]`:
   * Propagates symbol renames and relocations across definitions, edges, and callers with auto-reconciled imports.
5. **First-Class Agent Tool Protocol (MCP Server)** `[Designed]`:
   * Exposes dedicated MCP tools for agent runtimes:
     * `describe(csi)`: Returns structured signature and docstring.
     * `search(query, kind)`: Finds matching symbols, data models, or requirements.
     * `context(csi)`: Returns minimal prompt stub slice.
     * `expand(csi, hops, relations)`: Expands context into callers, requirements, data entities, or tests.
     * `impact(csi, proposed_change)`: Returns cross-model blast radius.
     * `edit_symbol(csi, body)`: Performs zero-diff mutation.
     * `add_symbol(package, code)`: Inserts new symbol node.
     * `validate()`: Runs in-memory invariant and constraint checks.
     * `materialize(output_dir)`: Projects graph to disk.
6. **Navigable / Interactive Semantic Context Expansion (`expand`)** `[Designed]`:
   * Agents start with a minimal targeted slice and interactively pull in related requirements, data entities, callers, or tests on demand.

---

### Pillar 3: Cross-Model Impact Analysis & Semantic Transactions
*End-to-end blast radius analysis and atomic multi-entity system changes.*

#### Capabilities
1. **Cross-Boundary Semantic Impact Analysis** `[Designed]`:
   * Traces consequences of modifications across the full stack:
     $$\text{Logical Data Change} \longrightarrow \text{Physical Tables} \longrightarrow \text{Code Readers/Writers} \longrightarrow \text{APIs/Events} \longrightarrow \text{Tests} \longrightarrow \text{Requirements}$$
2. **Semantic Change Sets / Transactions** `[Designed]`:
   * Enables agents to execute coordinated, multi-entity system evolutions:
     ```python
     with workspace.begin_change("Add multi-currency support") as tx:
         tx.modify_data_entity("data://logical/sales/Order", attributes={"currency": "CurrencyCode"})
         tx.edit_symbol("csi://ecommerce/models/Money", new_body=...)
         tx.edit_symbol("csi://ecommerce/services/OrderService.create_order", new_body=...)
         tx.verify_invariants() # Validates entire changeset before disk write
     ```
3. **Semantic Correctness & Reliability Benchmarking** `[Designed]`:
   * Benchmark suites measuring agent success on cross-cutting tasks:
     * Correct identification of impacted components across code and data.
     * Preservation of business and architectural constraints.
     * Regression avoidance and zero-import drift.
     * Human intervention reduction (with token efficiency as a secondary metric).

---

### Pillar 4: Fast Invariants & Executable Constraints
*Pre-commit guardrails that enforce architectural boundaries, types, and business rules.*

#### Capabilities
1. **Reverse Dependency Invariant Verification** `[Implemented]`:
   * In-memory pre-commit checks blocking breaking symbol deletions and unlinked references.
2. **In-Memory Live LSP Diagnostics** `[Designed]`:
   * Direct pipe to language server virtual document buffers (`textDocument/didChange`) to retrieve instant Pyright type errors without writing to disk.
3. **Executable Semantic Constraints** `[Designed]`:
   * Evaluates rules against proposed code changes:
     * *Architectural Boundaries*: Domain services cannot import persistence infrastructure directly.
     * *State Invariants*: Order state cannot transition directly from `CANCELLED` to `PAID`.
     * *Security & Governance*: Payment processing functions must include authorization decorators.
4. **Selective Impacted Test Runner** `[Planned]`:
   * Traces `VERIFIES` and `CALLS` edges to execute only the minimal affected test subset.

---

### Pillar 5: Deterministic Materialization & Code Quality
*Compiling pure semantic graphs into production-grade, beautifully formatted source trees.*

#### Capabilities
1. **Automated Import Synthesizer** `[Implemented]`:
   * Relational graph edges deterministically synthesize minimal, deduplicated import headers during disk projection.
2. **Class & Member Projection** `[Implemented]`:
   * Synthesizes formatted classes, methods, docstrings, and module structures.
3. **Integrated Ruff / Black Formatting** `[Designed]`:
   * Native integration with Ruff/Black during materialization to guarantee PEP 8 perfection.
4. **Incremental Disk Projector** `[Planned]`:
   * Emits disk writes only for modules whose symbols or imports were mutated during the session.

---

### Pillar 6: System & Runtime Semantics (Platform Horizon)
*Extending the semantic graph toward runtime operations once core semantics are mature.*

#### Capabilities
1. **API Endpoints & Event Contracts** `[Planned]`:
   * Explicit modeling of REST/GraphQL routes and Pub/Sub / Kafka message topologies.
2. **Telemetry & SLO Linkage** `[Planned]`:
   * Connecting symbol nodes to runtime observability metrics (latency budgets, error budgets, trace spans).
3. **Multi-Agent Workspace Partitioning** `[Planned]`:
   * Isolated subgraph leases allowing teams of autonomous agents to refactor decoupled modules concurrently without merge conflicts.

---

## 4. Phased Implementation Milestones

```mermaid
gantt
    title CodeMesh Development Roadmap
    dateFormat  YYYY-MM
    section Phase 1: Foundational Tooling
    Zero-Diff Symbol Modification (edit_symbol)    :done, p1_1, 2026-08, 2026-09
    Multi-Target Context Slicing                  :done, p1_2, 2026-08, 2026-09
    Graph Discovery & Refactoring APIs            :done, p1_3, 2026-08, 2026-09
    Top-Level Agent Skill & Quick Start Docs      :done, p1_4, 2026-08, 2026-09
    First-Class Agent MCP Server                  :active, p1_5, 2026-09, 2026-10
    Interactive Context Expansion (expand tool)   :active, p1_6, 2026-09, 2026-10

    section Phase 2: Cross-Model Semantics
    External URIs (data://, req://)               :p2_1, 2026-10, 2026-11
    Requirements & Constraint Nodes               :p2_2, 2026-10, 2026-11
    Provenance Classes (DECLARED/DERIVED/INFERRED):p2_3, 2026-11, 2026-11
    Cross-Model Code-to-Data Links                :p2_4, 2026-11, 2026-12
    In-Memory Live LSP Diagnostics                :p2_5, 2026-11, 2026-12

    section Phase 3: Transactions & Impact
    Cross-Model Blast Radius Impact Analysis      :p3_1, 2026-12, 2027-01
    Semantic Change Sets & Transactions           :p3_2, 2027-01, 2027-01
    Executable Semantic Constraint Validators     :p3_3, 2027-01, 2027-02
    Semantic Correctness Benchmark Suite          :p3_4, 2027-02, 2027-02

    section Phase 4: Platform & Runtime
    Ruff/Black PEP 8 Formatter Integration        :p4_1, 2027-02, 2027-03
    API & Event Stream Semantics                  :p4_2, 2027-03, 2027-04
    Multi-Agent Graph Partitioning                :p4_3, 2027-04, 2027-05
```

---

## 5. Immediate Next Steps

1. **Build First-Class Agent MCP Server**:
   * Wrap `SemanticWorkspace` in a Model Context Protocol (MCP) server exposing `describe`, `search`, `context`, `expand`, `edit_symbol`, `add_symbol`, `validate`, and `materialize`.
2. **Implement Interactive Context Expansion (`expand`)**:
   * Enable agents to request selective expansions along callers, implementations, data dependencies, and constraints.
3. **Implement Federated URI Parser & Data Link Ontology**:
   * Support `data://logical/...` and `req://...` foreign nodes and relational edges (`CREATES`, `READS`, `WRITES`, `VALIDATES`).
4. **Connect Live In-Memory LSP `didChange` Diagnostics**:
   * Provide immediate compiler/type checker validation inside the mutation lifecycle without requiring disk I/O.
