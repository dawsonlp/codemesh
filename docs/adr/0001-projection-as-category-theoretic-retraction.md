# ADR 0001: The Transform from Semantic Model to Code as a Category-Theoretic Retraction

* **Status**: PROPOSED
* **Date**: 2026-09-01
* **Deciders**: Larry Dawson, CodeMesh Core Team
* **Consulted**: Tripartite Semantic Federation Architects
* **Category Theory Formulation**: Section-Retraction Pair & Idempotent Projection Functor

---

## 1. Context and Problem Statement

Traditional software development and AI coding agents treat physical source code (files, lines, text formatting, and manual import headers) as the primary source of truth, while treating semantic models (ASTs, LSP symbol tables, call graphs) as ephemeral, lossy caches. 

This inverted priority causes fundamental failure modes for AI agents:
1. **Fragile text diffs & line offsets**: Editing raw text frequently introduces syntax errors, indentation drifts, or broken imports.
2. **Non-idempotent code generation**: Re-formatting or refactoring files creates large, noisy diff hunks that obscure actual semantic changes.
3. **Loss of semantic invariants**: Compilers and type checkers only validate code *after* disk materialization, discovering broken callers or interface violations late in the cycle.

We need a mathematically rigorous foundation for the bidirectional transformation between in-memory semantic program graphs and physical filesystem source files.

---

## 2. Category-Theoretic Formulation

Let us formalize the software system using two categories:

### 2.1 The Categories

1. $\mathbf{Sem}$ **(The Category of Semantic Program Models)**:
   * **Objects** ($\mathcal{S} \in \mathbf{Sem}$): Pure semantic program graphs $\mathcal{S} = (V, E, \tau, \mu)$, where:
     * $V$ is the set of symbols addressed by Canonical Symbol IDs (`csi://<pkg>/<namespace>/<Symbol>`).
     * $E$ is the set of typed relational edges (`CALLS`, `INHERITS_FROM`, `USES_TYPE`, `SATISFIES`, `CREATES`).
     * $\tau$ is the typed contract signature closure (types, parameters, return types, docstrings).
     * $\mu$ is the executable leaf implementation (normalized AST body).
   * **Morphisms**: Type-preserving graph homomorphisms, symbol renamings, and semantic refactorings.

2. $\mathbf{Code}$ **(The Category of Physical Source Code Artifacts)**:
   * **Objects** ($\mathcal{C} \in \mathbf{Code}$): Concrete filesystem artifacts $\mathcal{C} = \{ (f_i, \text{text}_i) \}_{i=1}^n$ comprising files, directory hierarchies, whitespace, formatting styles, and explicit import statements.
   * **Morphisms**: Text transformations, patches, line diffs, and formatting operations.

---

### 2.2 The Functors (Morphisms)

We define two primary functors connecting these domains:

```
                          P (Projection / Materialization)
                ┌─────────────────────────────────────────────────┐
                │                                                 │
                ▼                                                 │
     ┌──────────────────────┐                         ┌──────────────────────┐
     │  Semantic Graph (Sem)│                         │ Concrete Code (Code) │
     └──────────────────────┘                         └──────────────────────┘
                │                                                 ▲
                │                                                 │
                └─────────────────────────────────────────────────┘
                            I (Ingestion / LSP Extraction)
```

1. **Projection / Materialization Functor** ($P: \mathbf{Sem} \to \mathbf{Code}$):
   Maps an in-memory semantic graph $\mathcal{S}$ to concrete physical source files $P(\mathcal{S})$ on disk by:
   * Deterministically mapping CSI namespaces to directory/file paths.
   * Topological sorting of symbols within files.
   * Synthesizing clean, deduplicated module import headers from relational graph edges ($E$).
   * Serializing AST bodies into formatted source text.

2. **Ingestion / Extraction Functor** ($I: \mathbf{Code} \to \mathbf{Sem}$):
   Extracts an in-memory semantic graph $I(\mathcal{C})$ from physical source files using LSP typecheckers, AST parsers, and spatial indexers.

---

### 2.3 The Retraction Invariant (The Axiom)

In category theory, a morphism $I: B \to A$ is a **retraction** of a morphism $P: A \to B$ (and $P$ is a **section** or split monomorphism of $I$) if and only if:

$$I \circ P = \text{id}_{\mathbf{Sem}}$$

That is, for every valid semantic graph $\mathcal{S} \in \mathbf{Sem}$:

$$I(P(\mathcal{S})) \cong \mathcal{S}$$

```
                           P
         Sem ─────────────────────────────> Code
          │                                  │
          │                                  │
   id_Sem │                                  │ I (Retraction)
          │                                  │
          ▼                                  ▼
         Sem <───────────────────────────── Sem
```

**Interpretation**: 
Projecting an in-memory semantic graph to physical disk files and immediately re-ingesting it back into the graph is the **identity morphism on $\mathbf{Sem}$**. No semantic information (types, contracts, symbols, docstrings, relationships, or AST logic) is lost or mutated across the round trip.

---

### 2.4 Idempotent Normalization Operator on Code

While $I \circ P = \text{id}_{\mathbf{Sem}}$, the reverse composition $\Pi = P \circ I: \mathbf{Code} \to \mathbf{Code}$ is not the identity on $\mathbf{Code}$ because raw text contains arbitrary whitespace, duplicate imports, and arbitrary line ordering.

However, $\Pi$ is an **idempotent projection / normalization operator**:

$$\Pi^2 = (P \circ I) \circ (P \circ I) = P \circ (I \circ P) \circ I = P \circ \text{id}_{\mathbf{Sem}} \circ I = P \circ I = \Pi$$

```
                                    P ∘ I
                     Code ────────────────────────> Code
                      │                               │
                      │                               │
                P ∘ I │                               │ P ∘ I (Idempotent)
                      │                               │
                      ▼                               ▼
                     Code ────────────────────────> Code
                                    P ∘ I
```

**Theorem**: Applying CodeMesh projection after ingestion canonicalizes any raw source code into a stable fixed point. Once normalized, subsequent materializations produce **zero diffs**:

$$\Pi(\Pi(\mathcal{C})) = \Pi(\mathcal{C})$$

---

## 3. Architectural Decision

We formally establish the following architectural principles in CodeMesh:

1. **$\mathbf{Sem}$ is the Retract and the Single Source of Truth**:
   The primary representation of software in CodeMesh is the semantic graph $\mathbf{Sem}$. Concrete source code files $\mathbf{Code}$ are treated as a materialized projection (a fiber) of $\mathbf{Sem}$.
2. **Mutations Occur Exclusively on the Retract**:
   AI agents and developer tooling must mutate code symbols directly in $\mathbf{Sem}$ using Canonical Symbol IDs (`csi://...`) and AST replacements (`workspace.edit_symbol()`). Agents do not emit diff hunks, regex patches, or line-number edits.
3. **Automated Import Synthesis as a Natural Transformation**:
   Import headers in physical files are not primitive state. They are functorially generated during $P$ from the outgoing relational edges of the symbols in each module file.
4. **Enforcement of the Retraction Invariant**:
   All core pipeline components (`lsp_adapter`, `slicing`, `mutation`, `projection`) must preserve $I(P(\mathcal{S})) = \mathcal{S}$ as a continuous property-based test invariant across all supported language runtimes.

---

## 4. Consequences

### Positive
* **Zero-Diff & Zero-Import-Drift**: LLMs never edit import headers or calculate line numbers; $P$ guarantees deterministic, syntactically clean import blocks.
* **Lossless Semantic Round-Tripping**: Guaranteed high-fidelity synchronization between disk and in-memory representation.
* **Idempotent Builds & CI/CD**: Clean repository checkouts with no unexpected formatting or import churn.
* **Mathematical Precision**: Provides a formal framework for formal verification, bidirectional transformations, and cross-ontology federation with GroundTruth and Northstar.

### Negative / Trade-offs
* **Formatting Preservation Limits**: Custom, non-standard code formatting in raw source code is normalized to the canonical AST representation during projection (mitigated by standard code style formatters like Black / Ruff).
* **Comment Association**: Non-docstring free-floating comments must be explicitly bound to nearby symbol AST nodes to ensure survival through the retraction $I \circ P$.
