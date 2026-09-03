# 01. Core Semantic Ontology Specification `[Implemented]`

This document specifies the **Pure Semantic Domain Model** in `codemesh.core`. This model contains **zero references to file paths, byte offsets, text line/column numbers, or LSP protocol structures**.

---

## 1. Option B Canonical Symbol Identifiers (CSI)

A **Canonical Symbol Identifier (CSI)** uniquely identifies any computational entity across an entire software ecosystem under Option B coordinates (ADR 0004).

### 1.1 Option B URI Format
```
csi://[tenant:][package]/<namespace_path>/<symbol_hierarchy>[@version][#fragment]
```

### 1.2 Examples
| Symbol | Canonical Symbol Identifier (CSI) |
| :--- | :--- |
| Package Namespace | `csi://tripartite:ecommerce/services@v1` |
| Class Definition | `csi://tripartite:ecommerce/services/OrderService@v1` |
| Method inside Class | `csi://tripartite:ecommerce/services/OrderService.create_order@v1` |
| Overloaded Method (Java/C#/C++) | `csi://tripartite:ecommerce/services/OrderService.findOrders(String,int)@v1` |
| Method Parameter | `csi://tripartite:ecommerce/services/OrderService.create_order@v1#user_id` |
| Dataclass Field | `csi://tripartite:ecommerce/models/Money.amount@v1` |
| Protocol / Interface | `csi://tripartite:ecommerce/interfaces/PaymentGateway@v1` |
| Third-party Dependency | `csi://global:pydantic/main/BaseModel@latest` |


### 1.3 CSI Data Schema
```python
from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass(frozen=True)
class CanonicalSymbolId:
    package: str                               # e.g., "sample_project"
    namespace: Tuple[str, ...]                 # e.g., ("services",)
    symbol_name: str                           # e.g., "OrderService"
    member_path: Tuple[str, ...]               # e.g., ("create_order",)
    signature_spec: Optional[Tuple[str, ...]]  # e.g., ("String", "int") for overloads (None for Python)
    fragment: Optional[str]                    # e.g., "user_id" (for params/sub-elements)

    @classmethod
    def parse(cls, uri_string: str) -> "CanonicalSymbolId": ...
    
    def __str__(self) -> str: ...
    
    @property
    def parent_csi(self) -> Optional["CanonicalSymbolId"]: ...
```

---

## 2. Symbol Taxonomy & Contracts

Every symbol in the semantic model is partitioned into a **Contract** (its public interface and semantic expectations) and an optional **Implementation** (its executable body).

```
┌────────────────────────────────────────────────────────────────────────┐
│                              SymbolNode                                │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                 SymbolContract (Public Interface)              │   │
│   │                                                                │   │
│   │  • name: str                                                   │   │
│   │  • kind: SymbolKind (CLASS, FUNCTION, INTERFACE, etc.)         │   │
│   │  • signature: FunctionSignature / TypeContract                 │   │
│   │  • docstring: DocstringSpec                                    │   │
│   │  • purity: PurityType (PURE, IO_EFFECTFUL, MUTATES_SHARED)     │   │
│   │  • execution_model: ExecutionModel (SYNC, ASYNC, WORKER)       │   │
│   │  • declared_exceptions: List[TypeRef]                          │   │
│   └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │             SymbolImplementation (Executable Leaf)             │   │
│   │                                                                │   │
│   │  • body_source: str (clean executable statements)              │   │
│   │  • referenced_symbols: Set[CSI] (symbol references)            │   │
│   │  • local_variables: List[LocalVariable]                        │   │
│   └────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Symbol Kinds (`SymbolKind`)
```python
from enum import Enum

class SymbolKind(str, Enum):
    MODULE = "module"
    NAMESPACE = "namespace"
    CLASS = "class"
    INTERFACE = "interface"        # Protocol or abstract base
    FUNCTION = "function"
    METHOD = "method"
    PROPERTY = "property"
    FIELD = "field"
    ENUM = "enum"
    ENUM_MEMBER = "enum_member"
    TYPE_ALIAS = "type_alias"
    CONSTANT = "constant"
    VARIABLE = "variable"
```

### 2.2 Function Signature & Parameters
Signatures are expressed as structured trees of types rather than raw strings:

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

class ParameterKind(str, Enum):
    POSITIONAL_ONLY = "positional_only"
    POSITIONAL_OR_KEYWORD = "positional_or_keyword"
    VAR_POSITIONAL = "var_positional"     # e.g., *args
    KEYWORD_ONLY = "keyword_only"
    VAR_KEYWORD = "var_keyword"           # e.g., **kwargs

@dataclass
class TypeRef:
    raw_type_string: str
    resolved_csi: Optional[CanonicalSymbolId] = None
    type_arguments: List["TypeRef"] = field(default_factory=list)
    is_optional: bool = False

@dataclass
class Parameter:
    name: str
    type_ref: TypeRef
    kind: ParameterKind = ParameterKind.POSITIONAL_OR_KEYWORD
    default_value_expression: Optional[str] = None
    docstring: Optional[str] = None

@dataclass
class FunctionSignature:
    parameters: List[Parameter] = field(default_factory=list)
    return_type: TypeRef = field(default_factory=lambda: TypeRef("None"))
    type_parameters: List[str] = field(default_factory=list)  # Generics: [T, U]
```

### 2.3 Purity & Execution Archetypes
```python
class PurityType(str, Enum):
    PURE = "pure"                             # Deterministic, referentially transparent
    READ_ONLY = "read_only"                   # Reads system state; no side-effects
    MUTATES_LOCAL = "mutates_local"           # Mutates self/instance state only
    MUTATES_SHARED = "mutates_shared"         # Mutates global or shared thread state
    IO_EFFECTFUL = "io_effectful"             # Network, disk, or external side-effects

class ExecutionModel(str, Enum):
    SYNC_BLOCKING = "sync_blocking"
    ASYNC_EVENT_LOOP = "async_event_loop"
    PARALLEL_WORKER = "parallel_worker"
    TRANSACTIONAL = "transactional"
```

### 2.4 Structured Docstrings (`DocstringSpec`)
```python
from typing import Dict

@dataclass
class DocstringSpec:
    summary: str
    description: str = ""
    parameters_doc: Dict[str, str] = field(default_factory=dict)
    returns_doc: Optional[str] = None
    raises_doc: Dict[str, str] = field(default_factory=dict)
```

---

## 3. Relational Graph Schema

The semantic program structure is a directed multigraph where nodes are `SymbolNode` instances and edges are strongly typed relationships.

```
       [OrderService.create_order]
             │              │
             │ calls        │ instantiates
             ▼              ▼
     [OrderRepo.save]    [Order]
             │              │
             │ implements   │ types
             ▼              ▼
       [Repository]      [Money]
```

### 3.1 Edge Types (`EdgeType`)
```python
class EdgeType(str, Enum):
    # Behavioral Relationships
    CALLS = "calls"                   # Function A invokes Function B
    INSTANTIATES = "instantiates"     # Function/Method A constructs Class B
    READS_STATE = "reads_state"       # Function A reads state variable B
    MUTATES_STATE = "mutates_state"   # Function A writes to state variable B

    # Structural & Type Relationships
    IMPLEMENTS = "implements"         # Class A satisfies Protocol/Interface B
    SUBTYPES = "subtypes"             # Class A inherits from Class B
    TYPES = "types"                   # Field/Parameter A has Type B
    DEPENDS_ON = "depends_on"         # Module/Symbol A requires Symbol B

    # Verification Relationships
    VERIFIES = "verifies"             # Test Symbol A tests Target Symbol B
```

### 3.2 Relationship Edge Schema
```python
from typing import Any, Dict

@dataclass
class Relationship:
    source_csi: CanonicalSymbolId
    target_csi: CanonicalSymbolId
    edge_type: EdgeType
    metadata: Dict[str, Any] = field(default_factory=dict)
```

---

## 4. SemanticGraph Interface

The complete semantic state of a codebase is maintained in a queryable `SemanticGraph` structure:

```python
from typing import Dict, List, Set

class SemanticGraph:
    def __init__(self) -> None:
        self.nodes: Dict[CanonicalSymbolId, SymbolNode] = {}
        self.edges: List[Relationship] = []

    # Node Access
    def add_node(self, node: SymbolNode) -> None: ...
    def get_node(self, csi: CanonicalSymbolId) -> Optional[SymbolNode]: ...
    def get_contract(self, csi: CanonicalSymbolId) -> Optional[SymbolContract]: ...

    # Relational Traversal
    def get_callers(self, csi: CanonicalSymbolId) -> Set[CanonicalSymbolId]: ...
    def get_callees(self, csi: CanonicalSymbolId) -> Set[CanonicalSymbolId]: ...
    def get_implementations(self, interface_csi: CanonicalSymbolId) -> Set[CanonicalSymbolId]: ...
    def get_subtypes(self, base_class_csi: CanonicalSymbolId) -> Set[CanonicalSymbolId]: ...
    def get_dependency_closure(self, csi: CanonicalSymbolId, depth: int = 1) -> Set[CanonicalSymbolId]: ...
```

---

## 5. Federated External Identifiers & Cross-Domain Links `[Designed]`

While `CanonicalSymbolId` (`csi://`) addresses computational entities, CodeMesh connects to companion semantic authorities via federated URIs:
* **Logical & Physical Data Entities**: `data://logical/<domain>/<Entity>` and `data://physical/...` (See [Data Authority Specification](../federation/information_data_authority_requirements.md)).
* **Requirements & Policies**: `req://<domain>/<slug>` and `decision://...` (See [Intent Authority Specification](../federation/intent_requirements_authority_requirements.md)).
* **Cross-Ontology Links**: Typed edges (`CREATES`, `READS`, `WRITES`, `VALIDATES`, `SATISFIES`, `GOVERNED_BY`) are managed via in-code decorators and `.codemesh/links.yaml` (See [Cross-Ontology Link Architecture](../federation/cross_ontology_link_architecture.md)).

