# Cross-Ontology Link Architecture & Ownership

This document specifies how relationships spanning **Computation** (`csi://`), **Information** (`data://`), and **Intent** (`req://`) are authored, stored, indexed, and navigated across the Tripartite Federation.

---

## 1. The Core Problem: Who Owns Cross-Domain Edges?

In a multi-authority federation, no single domain owns all nodes:
* `csi://sample_ecommerce/services/OrderService.create_order` $\in$ **CodeMesh (Computation)**
* `data://logical/sales/Order` $\in$ **Data Authority (Information)**
* `req://payments/idempotent-capture` $\in$ **Intent Authority (Intent)**

If an edge connects a code symbol to a logical data entity (`csi://...` $\xrightarrow{\text{CREATES}}$ `data://...`), which system owns that edge?

### Design Axioms:
1. **Never leave ownership to the AI agent's ephemeral memory**: Cross-model links must be persistent, deterministic, version-controlled, and accessible to CI/CD tools, linters, and human engineers without running an LLM.
2. **Multiple authoring sources, unified indexing**: Links can be authored in code annotations, domain registries, or repository sidecars, but CodeMesh provides the unified in-memory multigraph for the agent runtime.

---

## 2. The Three-Tier Storage & Authoring Model

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 THREE STORAGE TIERS FOR CROSS EDGES                             │
├────────────────────────────────┬────────────────────────────────┬───────────────────────────────┤
│ TIER 1: IN-CODE ANNOTATIONS    │ TIER 2: REPOSITORY SIDECAR     │ TIER 3: EXTERNAL REGISTRIES   │
│ (Intrinsic to Source Code)     │ (.codemesh/links.yaml)         │ (Data & Intent Catalogs)      │
│                                │                                │                               │
│ • Python Decorators            │ • Human Architect declarations │ • req:// <-> data:// links    │
│ • Type Annotations & Protocols │ • AI Agent proposed links      │ • Enterprise Governance tools │
│ • ORM / SQL Declarations       │ • Non-invasive bindings        │ • Synced via REST / JSON-RPC  │
│                                │                                │                               │
│ └──> Extracted by AST/LSP ────┴──> Merged into Graph View <────┴──> Queried on Demand           │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Tier 1: Intrinsic In-Code Annotations
Developers and agents can declare cross-domain bindings directly inside Python source code:

```python
from codemesh.annotations import satisfies, governed_by, creates
from sample_ecommerce.interfaces import LogicalEntity

@satisfies("req://payments/idempotent-charge-execution")
@governed_by("decision://payments/adr-004-stripe-idempotency-keys")
@creates("data://logical/sales/Order")
def create_order(self, user_id: str, items: List[OrderItem]) -> Order:
    ...
```

* **Ingestion**: `LspGraphBuilder` / AST parser extracts `@satisfies`, `@creates`, `@governed_by`, and type annotations, automatically registering `Relationship` edges with `authority=DECLARED`.

---

### Tier 2: Repository Sidecar File (`.codemesh/links.yaml`)
For non-invasive bindings where modifying source code is undesirable (legacy code, third-party libraries, or high-level architectural mappings):

```yaml
# .codemesh/links.yaml
version: "1.0"

links:
  # Code -> Data Links
  - source: "csi://sample_ecommerce/services/OrderService.create_order"
    verb: "CREATES"
    target: "data://logical/sales/Order"
    authority: "DECLARED"
    created_by: "larry.dawson@gmail.com"

  # Code -> Intent Links
  - source: "csi://sample_ecommerce/services/OrderService.create_order"
    verb: "SATISFIES"
    target: "req://payments/idempotent-charge-execution"
    authority: "DECLARED"

  - source: "csi://sample_ecommerce/services/OrderService"
    verb: "GOVERNED_BY"
    target: "decision://architecture/adr-002-dependency-inversion"
    authority: "DECLARED"

  # AI-Inferred Candidate Links (Pending Human / Architect Review)
  - source: "csi://sample_ecommerce/gateways/StripePaymentGateway.charge"
    verb: "VALIDATES"
    target: "data://logical/billing/CreditCard.cvv"
    authority: "INFERRED"
    confidence: 0.96
    created_by: "agent-session-b772c2f2"
```

* **Storage**: Committed to Git alongside source code.
* **Loading**: `SemanticWorkspace.load()` automatically parses `.codemesh/links.yaml` and merges its edges into the canonical `SemanticGraph`.

---

### Tier 3: External Catalog Queries
For links between external entities (e.g. `policy://compliance/pci-dss` $\xrightarrow{\text{CONSTRAINS}}$ `data://logical/billing/CreditCard`):
* The Intent and Data Authorities store their own internal cross-edges.
* CodeMesh queries their APIs on demand during cross-model impact analysis and merges the resulting subgraphs into the active workspace view.

---

## 3. Canonical Cross-Edge Schema

Every cross-ontology edge in CodeMesh conforms to a strict data contract:

```python
@dataclass
class FederatedRelationship:
    """A directed edge connecting two entities across arbitrary semantic authorities."""
    source_uri: str              # e.g. "csi://...", "data://...", "req://..."
    target_uri: str              # e.g. "data://...", "req://...", "policy://..."
    verb: CrossDomainVerb        # CREATES, READS, WRITES, VALIDATES, SATISFIES, etc.
    authority: AuthorityTier     # DECLARED, DERIVED, INFERRED
    confidence: float = 1.0      # 1.0 for DECLARED/DERIVED; 0.0-0.99 for INFERRED
    created_by: Optional[str] = None # User, tool, or agent conversation ID
    created_at: Optional[str] = None # ISO-8601 timestamp
    metadata: Dict[str, Any] = field(default_factory=dict)
```

---

## 4. Agent Lifecycle: How the AI Agent Uses Cross-Edges

```
                                  AGENT WORKFLOW
                                        │
                                        ▼
                  ┌───────────────────────────────────────────┐
                  │ 1. CONTEXT DISCOVERY & SLICING            │
                  │ Agent requests symbol context:            │
                  │ workspace.get_symbol_context(csi)         │
                  └─────────────────────┬─────────────────────┘
                                        │
                                        ▼
                  ┌───────────────────────────────────────────┐
                  │ CodeMesh traverses cross-edges:           │
                  │ • Pulls code body & .pyi contracts        │
                  │ • Pulls data entity schemas (data://)     │
                  │ • Pulls governing ADRs & policies (req://)│
                  │ -> Emits enriched prompt slice to LLM     │
                  └─────────────────────┬─────────────────────┘
                                        │
                                        ▼
                  ┌───────────────────────────────────────────┐
                  │ 2. REASONING & MUTATION                   │
                  │ Agent writes clean zero-diff code &       │
                  │ proposes new cross-links (if applicable)  │
                  └─────────────────────┬─────────────────────┘
                                        │
                                        ▼
                  ┌───────────────────────────────────────────┐
                  │ 3. INVARIANT & CONSTRAINT GATE            │
                  │ Invariant engine checks active constraints│
                  │ attached via cross-edges before commit    │
                  └─────────────────────┬─────────────────────┘
                                        │
                                        ▼
                  ┌───────────────────────────────────────────┐
                  │ 4. MATERIALIZATION & PERSISTENCE          │
                  │ • Source files written to disk            │
                  │ • New links persisted to .codemesh/links  │
                  └───────────────────────────────────────────┘
```

---

## 5. Summary: Separation of Concerns

* **Source of Truth for Computation**: `src/` source files $\longrightarrow$ **CodeMesh**.
* **Source of Truth for Information**: Schema Registries / Data Dictionaries $\longrightarrow$ **Data Authority**.
* **Source of Truth for Intent**: PRDs, ADRs (`docs/adr/`), Policy Engines $\longrightarrow$ **Intent Authority**.
* **Source of Truth for Cross-Domain Links**:
  * In-code decorators (`src/`)
  * Sidecar registry (`.codemesh/links.yaml`)
  * Cross-model API queries
* **Runtime Operator & Traverser**: **CodeMesh `SemanticWorkspace`**, providing agents with a unified, instant, queryable knowledge graph.
