# CodeMesh Documentation Portal 📚

Welcome to the **CodeMesh** documentation library. This portal organizes architectural specifications, developer guides, agent skills, and federation standards across the codebase.

---

## 1. Documentation Sitemap & Reading Paths

```
docs/
├── README.md                              # Documentation Portal & Index (This file)
├── quickstart.md                          # Quick Start Guide for Agents & Developers
├── roadmap.md                             # Capabilities Roadmap & Maturity Matrix
├── literature_review.md                   # Prior Art, Academic Survey & Comparative Matrix
├── mvp_development_plan.md                # Phased MVP Implementation & Verification History
│
├── federation/                            # Tripartite Semantic Federation
│   ├── README.md                          # Tripartite Federation Architecture Overview
│   ├── cross_ontology_link_architecture.md# Cross-Ontology Link Storage & Ownership Spec
│   ├── information_data_authority_requirements.md # Information / Data Domain Requirements
│   ├── intent_requirements_authority_requirements.md # Intent & Policy Domain Requirements
│   └── (Governing Federation ADR: /adrs/0007-projection-as-category-theoretic-retraction.md)
│

└── design/                                # Core Engine Architectural Specifications
    ├── README.md                          # Design Index & Component Overview
    ├── 01_core_semantic_ontology.md       # Pure Domain Model, CSIs, Contracts, Graph Schema
    ├── 02_anti_corruption_lsp_adapter.md  # LSP Anti-Corruption Layer & Translation Engine
    ├── 03_context_slicing_and_agent_projections.md # Token-Optimized Context Closures (.pyi)
    ├── 04_mutation_invariants_and_verification.md # Zero-Diff Mutations, Invariants & Blast Radius
    └── 05_materialization_and_filesystem_sync.md  # Deterministic Code & Auto-Import Synthesis
```

---

## 2. Recommended Reading Paths by Role

Choose your role below to follow the optimal reading path:

### 🤖 Path 1: AI Coding Agents & Framework Authors
*Goal: Understand how to query, slice, modify, and verify code using the CodeMesh SDK.*
1. **[Quick Start Guide](quickstart.md)**: Set up the environment and run basic workspace commands.
2. **[CodeMesh Agent Skill](../skills/codemesh/SKILL.md)**: The authoritative instruction set for LLM agents.
3. **[Context Slicing Specification](design/03_context_slicing_and_agent_projections.md)**: How `.pyi` contract closures are constructed with 76.9% token savings.
4. **[Zero-Diff Mutation Specification](design/04_mutation_invariants_and_verification.md)**: How AST normalizers and invariant checks eliminate diff patches.

---

### 💻 Path 2: Software Engineers & Contributors
*Goal: Understand the internal architecture of CodeMesh to extend or contribute.*
1. **[Quick Start Guide](quickstart.md)**: Installation, running tests (`pytest -v`), and interactive runner (`demo.py`).
2. **[Architecture Overview](design/README.md)**: High-level system topology and core components.
3. **[Core Semantic Ontology](design/01_core_semantic_ontology.md)**: Canonical Symbol IDs (`csi://`), contracts, nodes, and edges.
4. **[LSP Anti-Corruption Adapter](design/02_anti_corruption_lsp_adapter.md)**: Spatial indexing and pyright JSON-RPC translation.
5. **[FileSystem Materializer](design/05_materialization_and_filesystem_sync.md)**: Deterministic code and import synthesis.

---

### 🏛️ Path 3: Enterprise Data & Governance Architects
*Goal: Understand how CodeMesh federates with Data Dictionaries, PRDs, ADRs, and Policy Engines.*
1. **[Tripartite Federation Overview](federation/README.md)**: The separation of Computation, Information, and Intent.
2. **[Information / Data Authority Requirements](federation/information_data_authority_requirements.md)**: DAMA hierarchy preservation and code-to-data links (`CREATES`, `WRITES`, `VALIDATES`).
3. **[Intent & Requirements Authority Requirements](federation/intent_requirements_authority_requirements.md)**: Requirements (`req://`), Decisions (`decision://`), and executable constraint gates.
4. **[Cross-Ontology Link Architecture](federation/cross_ontology_link_architecture.md)**: Three-tier link storage (`.codemesh/links.yaml`) and ownership.

---

### 🔬 Path 4: Systems & Language Researchers
*Goal: Explore how CodeMesh relates to historical structure editors, knowledge graphs, and Unison.*
1. **[Literature Review](literature_review.md)**: Historical evolution from Smalltalk-80 and Lisp to Kythe, Glean, Unison, and LSP.
2. **[Capabilities Roadmap](roadmap.md)**: The strategic vision for multi-agent graph partitioning and semantic transactions.

---

## 3. Master Document Catalog & Maturity Status

| Document | Focus & Scope | Maturity |
| :--- | :--- | :--- |
| **[`quickstart.md`](quickstart.md)** | Developer & agent setup guide, end-to-end SDK workflow | `[Implemented]` |
| **[`skills/codemesh/SKILL.md`](../skills/codemesh/SKILL.md)** | Standardized Agent Skill for Claude Code, Cursor, Antigravity | `[Implemented]` |
| **[`design/01_core_semantic_ontology.md`](design/01_core_semantic_ontology.md)** | Domain model, CSI schema, `SymbolContract`, `SemanticGraph` | `[Implemented]` |
| **[`design/02_anti_corruption_lsp_adapter.md`](design/02_anti_corruption_lsp_adapter.md)** | Spatial index, signature parser, LSP stdio client | `[Implemented]` |
| **[`design/03_context_slicing_and_agent_projections.md`](design/03_context_slicing_and_agent_projections.md)** | Single & multi-target slicing, prompt stub serialization | `[Implemented]` |
| **[`design/04_mutation_invariants_and_verification.md`](design/04_mutation_invariants_and_verification.md)** | Zero-diff `edit_symbol`, AST normalizer, blast radius | `[Implemented]` |
| **[`design/05_materialization_and_filesystem_sync.md`](design/05_materialization_and_filesystem_sync.md)** | Deterministic file projection & import synthesis | `[Implemented]` |
| **[`federation/README.md`](federation/README.md)** | Tripartite Semantic Federation blueprint | `[Designed]` |
| **[`federation/information_data_authority_requirements.md`](federation/information_data_authority_requirements.md)** | Data Dictionary requirements, DAMA hierarchy, data URIs | `[Designed]` |
| **[`federation/intent_requirements_authority_requirements.md`](federation/intent_requirements_authority_requirements.md)** | Requirements, ADRs, executable constraint gates | `[Designed]` |
| **[`federation/cross_ontology_link_architecture.md`](federation/cross_ontology_link_architecture.md)** | Cross-edge storage tiers (`.codemesh/links.yaml`), ownership | `[Designed]` |
| **[`roadmap.md`](roadmap.md)** | Long-term capability pillars, milestone Gantt chart | `[Designed]` / `[Planned]` |
| **[`literature_review.md`](literature_review.md)** | History of non-file environments, LSP, and knowledge graphs | `Reference` |

