# Architecture & Design Documents

This directory contains the detailed engineering specifications for the **Semantic-First Program Representation for AI-Native Development**.

---

## Document Index

```
docs/
├── quickstart.md                          # Quick Start Guide for Agents & Developers
├── roadmap.md                             # Architectural Capabilities Roadmap
├── literature_review.md                   # Historical Context, Prior Art & Paradigm Survey
├── mvp_development_plan.md                # Phased Implementation & Verification Checklist
└── design/
    ├── README.md                          # Design Index & Architectural Overview (This file)
    ├── 01_core_semantic_ontology.md       # Pure Domain Model, CSIs, Contracts, Graph Schema
    ├── 02_anti_corruption_lsp_adapter.md  # LSP Anti-Corruption Layer & Translation Engine
    ├── 03_context_slicing_and_agent_projections.md # Token-Optimized AI Views & Dependency Slicing
    ├── 04_mutation_invariants_and_verification.md # Semantic Edits, Blast-Radius & Test Binding
    └── 05_materialization_and_filesystem_sync.md  # File Synthesis, Import Generation & Round-Tripping
```

> 🚀 **Quick Start**: See the [Quick Start Guide](../quickstart.md) for step-by-step setup with AI coding agents.  
> 🗺️ **Long-Term Roadmap**: See the [Capabilities Roadmap](../roadmap.md) for upcoming milestones.  
> 📜 **Historical Context**: For a thorough survey of Smalltalk, Lisp, LSP/LSIF/SCIP, Kythe, Glean, CodeQL, and Unison, see the [Literature Review](../literature_review.md).

---

## High-Level Architecture Overview

```
                                  ┌───────────────────────────────────────────┐
                                  │      AI Agent / Autonomous Workflow       │
                                  └─────────────────────┬─────────────────────┘
                                                        │ (CSI queries, Slices, Semantic Mutations)
                                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                          CORE SEMANTIC PROGRAM MODEL                                            │
│                                           (Pure Domain - 01_*.md)                                               │
│                                                                                                                 │
│   ┌───────────────────────────┐    ┌───────────────────────────┐    ┌──────────────────────────────────────┐    │
│   │ Canonical Symbol IDs (CSI)│    │ Symbol Contracts (Types)  │    │ Relational Graph (Calls/Subtypes)    │    │
│   └───────────────────────────┘    └───────────────────────────┘    └──────────────────────────────────────┘    │
│   ┌───────────────────────────┐    ┌───────────────────────────┐    ┌──────────────────────────────────────┐    │
│   │ Executable Implementations│    │ State & Execution Topology│    │ Bound Verification Tests             │    │
│   └───────────────────────────┘    └───────────────────────────┘    └──────────────────────────────────────┘    │
└───────────────────────▲───────────────────────────────▲───────────────────────────────▲─────────────────────────┘
                        │                               │                               │
        ┌───────────────┴───────────────┐               │               ┌───────────────┴───────────────┐
        │                               │               │               │                               │
        ▼                               ▼               ▼               ▼                               ▼
┌─────────────────────────────┐ ┌─────────────────────────────┐ ┌─────────────────────────────┐ ┌───────────────┐
│     lsp_adapter/            │ │   Context Slicing Engine    │ │   Mutation & Invariant Engine│ │ FileSystem    │
│ (Anti-Corruption Layer)     │ │       (03_*.md)             │ │       (04_*.md)             │ │ Projector     │
│       (02_*.md)             │ │                             │ │                             │ │ (05_*.md)     │
│                             │ │ • Minimal Contract Closures │ │ • Atomic Semantic Mutations │ │               │
│ • Maps (file,line,col)↔CSI  │ │ • Implementation Slices     │ │ • Blast-Radius Computation  │ │ • Code Gen    │
│ • Parses signatures/hovers  │ │ • Token Budget Optimizer    │ │ • Pre-commit Invariant Check│ │ • Auto-Import │
│ • Populates Semantic Graph  │ │ • Prompt Serializer         │ │ • Incremental Test Runner   │ │ • Round-Trip  │
└──────────────▲──────────────┘ └─────────────────────────────┘ └─────────────────────────────┘ └───────┬───────┘
               │                                                                                        │
               ▼ (JSON-RPC stdio)                                                                       ▼
┌─────────────────────────────┐                                                         ┌───────────────┴───────┐
│   lsp_client / pyright      │                                                         │   Physical Files on   │
│   (Infrastructure Engine)   │                                                         │   Disk (.py files)    │
└─────────────────────────────┘                                                         └───────────────────────┘
```

---

## Architectural Principles

1. **Semantic Ground Truth**: The Semantic Graph is the canonical authority. Physical files and editor coordinates are derivative projections.
2. **Zero-Leakage Anti-Corruption Boundary**: The Core Domain Model must contain zero references to LSP types (`Range`, `Position`, `Hover`, `Location`, line numbers).
3. **Contract-Implementation Separation**: Contracts (public interfaces, types, docstrings) are distinct from implementation bodies, enabling agents to reason about systems at high levels of abstraction without token waste.
4. **Invariant-Guarded Evolution**: Code modifications are applied as atomic semantic mutations validated against type consistency and caller contracts before persistence.
5. **Deterministic Materialization**: Files on disk are generated deterministically with automatic import resolution, guaranteeing zero unused or missing imports.

