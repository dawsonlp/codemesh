# 05. Materialization and FileSystem Synchronization

This document specifies the **FileSystem Projection Engine** responsible for compiling the Semantic Graph into physical source files on disk and synchronizing external edits back into the graph.

---

## 1. The Projection Concept

Physical files on disk are a **projection format** required by standard compilers, runtimes (CPython), debuggers, and packaging tools.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Semantic Source Graph                           │
│                       (Single Source of Truth)                         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │  FileSystem Projection Engine │
                    └───────────────┬───────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        Physical File System                            │
│                                                                        │
│   sample_project/                                                      │
│   ├── models.py         (Synthesized dataclasses, enums, & imports)    │
│   ├── interfaces.py     (Synthesized protocols & type annotations)     │
│   ├── repositories.py   (Synthesized classes & method implementations) │
│   └── services.py       (Synthesized business logic & decorators)      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Deterministic Code Synthesis

### 2.1 Namespace to Directory/File Mapping
A configurable layout mapper projects symbol namespaces to file paths:

| CSI Namespace | Materialized File Path |
| :--- | :--- |
| `csi://sample_project/models/*` | `sample_project/models.py` |
| `csi://sample_project/domain/orders/*` | `sample_project/domain/orders.py` |
| `csi://sample_project/services/*` | `sample_project/services.py` |

### 2.2 Intra-File Symbol Ordering
Within each generated file, symbols are emitted in deterministic topological order:
1. **Module Docstring**
2. **Future Imports** (`from __future__ import annotations`)
3. **Synthesized Import Block** (Standard library, 3rd party, local project)
4. **Constants & Enums**
5. **Type Aliases & Protocols**
6. **Data Models / Classes**
7. **Functions & Service Classes**
8. **Export List** (`__all__ = [...]`)

---

## 3. Automated Import Synthesis

Because the Semantic Graph explicitly tracks all `CALLS`, `INSTANTIATES`, and `TYPES` edges, the materializer synthesizes exact import headers automatically.

```
                                  ┌────────────────────────┐
                                  │ Symbol Implementation  │
                                  │ Referenced CSIs:       │
                                  │ • models.Order         │
                                  │ • models.Money         │
                                  │ • utils.generate_id    │
                                  └───────────┬────────────┘
                                              │
                                              ▼
                                  ┌────────────────────────┐
                                  │ Import Synthesizer     │
                                  │ (Groups & deduplicates)│
                                  └───────────┬────────────┘
                                              │
                                              ▼
              from sample_project.models import Money, Order
              from sample_project.utils import generate_id
```

### 3.1 Benefits of Automated Import Synthesis
* **Zero Unused Imports**: Eliminates dead imports that clutter files.
* **Zero Missing Imports**: No `NameError` from forgot-to-import symbols.
* **Cycle-Free Structuring**: The synthesizer detects circular module dependencies and automatically introduces runtime conditional imports (`if TYPE_CHECKING:`) when needed.

---

## 4. Bi-Directional Synchronization (Round-Tripping)

When a human developer or external tool modifies files directly on disk:

```
[ Disk File Changed ] ──► [ AST Parser ] ──► [ Semantic Diff Engine ]
                                                     │
                                                     ▼
                                       ┌───────────────────────────┐
                                       │ Contract Change?          │
                                       │ -> Trigger Invariant Check│
                                       │ Implementation Change?    │
                                       │ -> Update Node Body       │
                                       └─────────────┬─────────────┘
                                                     │
                                                     ▼
                                       [ Update Semantic Graph ]
```

### 4.1 Diff Classification
The round-trip engine parses the modified file into an AST and compares it against the existing graph node:
1. **Implementation-Only Edit**: Function body changed, but signature, docstring, and return type remain identical. Updated in the graph immediately.
2. **Contract Edit**: Parameter added/removed, return type changed, or method renamed. Triggers blast-radius analysis to verify no external contracts were broken.

