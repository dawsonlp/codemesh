# 04. Mutation, Invariants and Verification Specification

This document specifies how changes are applied to the semantic program representation, how system invariants and blast radiuses are validated, and how incremental verification is executed.

---

## 1. Structured Semantic Mutations

In file-centric development, changes are applied as arbitrary character or line edits (`diff` / `patch`). In this architecture, all modifications are structured **Semantic Mutation Commands**.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Semantic Mutation Engine                        │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                 Structured Mutation Command                    │   │
│   │  • ReplaceImplementation(CSI, new_body)                        │   │
│   │  • UpdateContract(CSI, new_signature)                          │   │
│   │  • RenameSymbol(CSI, new_name)                                 │   │
│   └───────────────────────────────┬────────────────────────────────┘   │
│                                   │                                    │
│                                   ▼                                    │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                     Pre-Commit Pipeline                        │   │
│   │                                                                │   │
│   │  1. Blast-Radius Traversal (Identify impacted callers/types)   │   │
│   │  2. Virtual Invariant Check (Verify type & signature integrity)│   │
│   │  3. Incremental Test Selection (Identify verifying test units) │   │
│   └───────────────────────────────┬────────────────────────────────┘   │
│                                   │                                    │
│                     ┌─────────────┴─────────────┐                      │
│                     ▼                           ▼                      │
│            [ Commit to Graph ]        [ Invariant Violation ]          │
│            [ & Materialize   ]        [ Actionable Rejection]          │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. The Mutation Primitives

### 2.1 Specification of Mutation Operations

```python
from dataclasses import dataclass
from typing import Optional, List
from codemesh.core.csi import CanonicalSymbolId
from codemesh.core.contract import SymbolContract
from codemesh.core.node import SymbolImplementation

class SemanticMutation:
    """Base class for all semantic modification commands."""
    pass

@dataclass
class AddSymbolMutation(SemanticMutation):
    parent_csi: CanonicalSymbolId
    contract: SymbolContract
    implementation: Optional[SymbolImplementation] = None

@dataclass
class ReplaceImplementationMutation(SemanticMutation):
    target_csi: CanonicalSymbolId
    new_body_source: str

@dataclass
class UpdateContractMutation(SemanticMutation):
    target_csi: CanonicalSymbolId
    new_contract: SymbolContract

@dataclass
class RenameSymbolMutation(SemanticMutation):
    target_csi: CanonicalSymbolId
    new_name: str

@dataclass
class MoveSymbolMutation(SemanticMutation):
    target_csi: CanonicalSymbolId
    target_namespace_csi: CanonicalSymbolId

@dataclass
class DeleteSymbolMutation(SemanticMutation):
    target_csi: CanonicalSymbolId
```

---

## 3. Pre-Commit Invariant Verification

Before any mutation is applied to the canonical graph, it must pass three verification stages:

### 3.1 Stage 1: Structural Integrity
* Verify no namespace collisions.
* Verify that parent namespaces exist.
* Verify symbol kind compatibility (e.g., cannot add a method to a non-class symbol).

### 3.2 Stage 2: Blast-Radius Calculation
The engine traverses the reverse dependency edges to identify every symbol that could be broken:
$$\text{BlastRadius}(S) = \text{Callers}(S) \cup \text{Subtypes}(S) \cup \text{Implementations}(S) \cup \text{TypeUsers}(S)$$

```python
def compute_blast_radius(graph: SemanticGraph, target_csi: CanonicalSymbolId) -> Set[CanonicalSymbolId]:
    impacted = set()
    # Find all callers
    impacted.update(graph.get_callers(target_csi))
    # Find all implementing classes (if interface changed)
    impacted.update(graph.get_implementations(target_csi))
    # Find all subtypes (if base class changed)
    impacted.update(graph.get_subtypes(target_csi))
    return impacted
```

### 3.3 Stage 3: Type & Contract Invariant Checking
Using a virtual overlay graph, the engine verifies:
1. Does the new implementation satisfy the declared contract?
2. Do all symbols in $\text{BlastRadius}(S)$ remain type-safe?
3. If an error is detected, the transaction aborts with a structured diagnostic payload indicating the exact downstream breakage.

---

## 4. Semantic Test Binding & Incremental Verification

### 4.1 Test Binding Schema
Tests are explicitly attached to the symbols they verify using `VERIFIES` relational edges:

```
[test_create_order_validates_user] ──── VERIFIES ───► [OrderService.create_order]
[test_order_subtotal_calculation]  ──── VERIFIES ───► [Order.calculate_subtotal]
```

### 4.2 Incremental Test Selection
When symbol $S$ is mutated:
1. Compute $\text{ImpactedSymbols} = \{ S \} \cup \text{BlastRadius}(S)$.
2. Select **only** tests that have a `VERIFIES` edge pointing to any symbol in $\text{ImpactedSymbols}$.
3. Execute the targeted test subset, achieving sub-second feedback for AI agent loops.

