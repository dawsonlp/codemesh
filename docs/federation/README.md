# Tripartite Semantic Federation: Architecture Overview

This document defines the architectural blueprint for the **Tripartite Semantic Federation** that connects **CodeMesh** with its companion semantic authorities.

---

## 1. The Tripartite Ontology: Three Orthogonal Domains

Autonomous AI software engineering cannot succeed by looking at code in isolation. High-quality software engineering requires reasoning simultaneously across three fundamentally distinct semantic planes:

```
                          ┌─────────────────────────────────────────────────────────┐
                          │               INTENT & GOVERNANCE DOMAIN                │
                          │                 (Why & What Is Permitted)               │
                          │                                                         │
                          │   • Requirements (Functional / Non-Functional)          │
                          │   • Constraints & Executable Guardrails                 │
                          │   • Architectural Decision Records (ADRs)               │
                          │   • Policies (Security, Privacy, Compliance, SLOs)      │
                          └───────────────▲─────────────────────────▲───────────────┘
                                          │                         │
                            GOVERNS /     │                         │ CONSTRAINS /
                            SATISFIES     │                         │ VALIDATES
                                          │                         │
┌─────────────────────────────────────────┴─────────────┐     ┌─────┴───────────────────────────────────┐
│                 COMPUTATION DOMAIN                    │     │           INFORMATION DOMAIN            │
│                      (CodeMesh)                       │     │            (Data Dictionary)            │
│                     (How It Computes)                 │     │          (What Data Exists & Means)     │
│                                                       │     │                                         │
│   • Canonical Symbol IDs (csi://)                     │     │   • Conceptual Models (Business Terms)  │
│   • Symbol Contracts (Signatures, Types, Docstrings)  │ ─── │   • Logical Data Models (Entities, Attrs│
│   • Implementations (ASTs, Code, Purity, Effects)     │     │   • Physical Data Objects (Tables, Wire)│
│   • Call Graphs, Invariants & File Projections        │     │   • Schema Evolution, Lineage & Keys    │
└───────────────────────────────────────────────────────┘     └─────────────────────────────────────────┘
                               READS / WRITES / CREATES / VALIDATES / SERIALIZES
```

### The Three Authorities

| Semantic Domain | Primary Authority | Focus & Responsibility | Canonical URI Scheme |
| :--- | :--- | :--- | :--- |
| **Computation** | **CodeMesh** | How computation is structured, executed, tested, and materialized into physical source code. | `csi://<package>/<namespace>/<Symbol>[.<member>]` |
| **Information** | **GroundTruth** | The structure, business meaning, relationships, integrity rules, and physical schemas of persistent and transient data. | `data://conceptual/...`<br>`data://logical/...`<br>`data://physical/...` |
| **Intent & Governance** | **Northstar** | Why the software exists, business goals, regulatory constraints, architectural decisions, and executable guardrails. | `req://...`<br>`decision://...`<br>`constraint://...`<br>`policy://...`<br>`quality://...` |

---

## 2. Core Federation Principles

### 1. Decentralized Ownership, Unified Traversal
No single tool or database owns all three domains. CodeMesh does not attempt to be an enterprise data dictionary or a Jira/requirements management system. Instead, each authority manages its own domain lifecycle while exposing **stable canonical URIs** and **machine-queryable APIs**. A unified graph traverser allows agents to navigate seamlessly across boundaries.

### 2. Zero Ontological Conflation
* Code is **not** data schema: A Python dataclass `Order` is a *computational representation* (`csi://...`), whereas the canonical business concept is an *information entity* (`data://logical/...`).
* Data schema is **not** intent: A non-nullable SQL column is a physical invariant; the requirement that *“Every order must belong to an authenticated customer”* is an intent constraint (`req://...`).

### 3. Explicit Cross-Domain Relational Grammar
Cross-domain relationships use unambiguous, typed verbs:

```
Code Symbol         ──[ CREATES ]──────────> Logical Data Entity
Code Symbol         ──[ WRITES ]───────────> Physical Database Table
Code Symbol         ──[ VALIDATES ]────────> Logical Entity Attribute
Code Symbol         ──[ SERIALIZES ]───────> Physical Wire Schema (Protobuf/Avro)
Code Symbol         ──[ SATISFIES ]────────> Functional Requirement
Code Symbol         ──[ GOVERNED_BY ]──────> Architectural Decision (ADR)
Logical Entity      ──[ CONSTRAINED_BY ]───> Regulatory Policy (GDPR/PCI)
Physical Column     ──[ REALIZES ]─────────> Logical Entity Attribute
Executable Rule     ──[ ENFORCES ]─────────> Invariant / Quality Constraint
```

### 4. Explicit Provenance & Confidence Tiers
Every non-code semantic node and relationship maintains explicit provenance metadata:
* **`DECLARED`**: Authoritatively established by humans, data governance teams, formal specifications, or regulations (Confidence: `1.0`).
* **`DERIVED`**: Deterministically extracted from ASTs, LSP type checkers, database schemas, or test assertions (Confidence: `1.0`).
* **`INFERRED`**: Discovered or proposed by AI models or heuristic pattern scanners (Confidence: `0.0 - 0.99`, flagged for human or architect validation).

---

## 3. The Companion Requirements Specifications

To build the complete federated ecosystem, detailed requirements for the two companion authorities are specified in:

1. 📄 **[Information / Data Authority Requirements Specification](information_data_authority_requirements.md)**:
   * Conceptual $\to$ Logical $\to$ Physical hierarchy preservation.
   * Cross-model data linking (`READS`, `WRITES`, `CREATES`, `VALIDATES`, `SERIALIZES`).
   * Schema evolution, compatibility rules, and data classification.
2. 📄 **[Intent & Requirements Authority Requirements Specification](intent_requirements_authority_requirements.md)**:
   * First-class `Requirement`, `Constraint`, `Policy`, `Decision` (ADR) entities.
   * Declarative intent + machine-executable constraint validators.
   * Cross-boundary impact analysis and invariant gating.
3. 📄 **[Cross-Ontology Link Architecture & Ownership](cross_ontology_link_architecture.md)**:
   * Specification of the Three-Tier Link Storage model (In-Code annotations, `.codemesh/links.yaml` repository sidecar, and external catalog APIs).
   * Canonical cross-edge schema and agent interaction lifecycle.

