# 03. Context Slicing and Agent Projections Specification `[Implemented]`

This document details how the Semantic Graph is projected into **token-optimized, highly focused context slices** designed specifically for AI agents and LLM prompts.

---

## 1. The Context Overload Problem

In traditional file-based AI coding:
* An agent modifying a 20-line method is often fed 5 whole files (3,000 lines / ~12,000 tokens) because the method calls utilities in other files.
* **90% of those tokens are implementation noise** (the bodies of helper functions that the agent never needs to see—only their signatures matter).
* This noise dilutes the attention mechanism, inflates cost/latency, and introduces hallucinations.

### The Semantic Slicing Solution
With a Semantic Graph, we construct **surgical context closures**:
$$\text{ContextSlice}(S) = \text{Body}(S) \cup \bigcup_{d \in \text{Callees}(S)} \text{Contract}(d) \cup \bigcup_{t \in \text{Types}(S)} \text{Contract}(t)$$

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Target: OrderService                            │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                 Full Implementation Body                       │   │
│   │  def create_order(self, user_id: str, items: List[OrderItem]): │   │
│   │      # Full method body here...                                │   │
│   └────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │          Dependency Contracts Only (No Function Bodies)        │   │
│   │                                                                │   │
│   │  • OrderRepository.save_order(order: Order) -> None: ...       │   │
│   │  • UserRepository.get_by_id(user_id: str) -> Optional[User]:...│   │
│   │  • Order(order_id: str, user_id: str, items: List[OrderItem])  │   │
│   │  • generate_unique_id(prefix: str) -> str: ...                 │   │
│   └────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Slicing Archetypes

### 2.1 Archetype A: Implementation Slicing `[Implemented]`
* **Use Case**: The agent is tasked with writing, editing, or debugging a specific function implementation.
* **Method**: `workspace.get_symbol_context(csi)`
* **Contents**: Full body of target + contract signatures & docstrings of direct dependencies.

### 2.2 Archetype B: Multi-Symbol Task Slicing `[Implemented]`
* **Use Case**: The agent is implementing a coordinated cross-cutting feature across multiple modules (e.g. models, interfaces, and service methods).
* **Method**: `workspace.get_multi_symbol_context([csi1, csi2, ...])`
* **Contents**: Full bodies of all specified target symbols + deduplicated `.pyi` contracts for all shared dependencies.

### 2.3 Archetype C: Architectural / Interface Slicing `[Implemented]`
* **Use Case**: The agent is planning a system refactor or designing a new feature across multiple modules.
* **Contents**: Namespaces, classes, and pure contracts with zero implementation bodies.

### 2.4 Archetype D: Blast-Radius / Impact Slicing `[Implemented]`
* **Use Case**: The agent is modifying an existing interface or method signature and needs to update all call sites.
* **Contents**: Proposed modified contract of the target symbol + implementation bodies of all direct callers that must be adjusted.

---

## 3. Token-Budget Optimization Algorithm

When generating prompt context under strict token constraints:

```python
class ContextSlicer:
    """Builds token-budgeted context slices from the SemanticGraph."""
    
    def __init__(self, graph: SemanticGraph) -> None:
        self.graph = graph

    def build_implementation_slice(
        self,
        target_csi: CanonicalSymbolId,
        max_tokens: int = 4000,
    ) -> ContextSlice:
        target_node = self.graph.get_node(target_csi)
        if not target_node:
            raise ValueError(f"Symbol not found: {target_csi}")

        # Priority 1: Target Contract and Target Body
        slice_obj = ContextSlice(target_csi=target_csi)
        slice_obj.target_contract = target_node.contract
        slice_obj.target_implementation = target_node.implementation

        # Priority 2: Direct Dependencies (Types & Callees)
        direct_callees = self.graph.get_callees(target_csi)
        direct_types = self.graph.get_type_dependencies(target_csi)
        
        for dep_csi in direct_callees.union(direct_types):
            dep_contract = self.graph.get_contract(dep_csi)
            if dep_contract:
                slice_obj.dependency_contracts[dep_csi] = dep_contract
                if slice_obj.estimated_tokens > max_tokens:
                    break

        return slice_obj
```

---

## 4. Prompt Serialization Formats

The `ContextSlice` can be rendered in multiple representations based on LLM preference:

### 4.1 Python Stub Format (`.pyi` style) - Preferred for LLMs
```python
# Context Slice for: sample_project.services.OrderService.create_order

# --- TARGET IMPLEMENTATION ---
class OrderService:
    def create_order(self, user_id: str, items: List[OrderItem]) -> Order:
        """Create and persist a new customer order."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise OrderProcessingError(f"User not found: {user_id}")
        ...

# --- DEPENDENCY CONTRACTS (READ-ONLY INTERFACES) ---
class OrderRepository:
    def save_order(self, order: Order) -> None: ...

class UserRepository:
    def get_by_id(self, entity_id: str) -> Optional[User]: ...

@dataclass
class Order:
    order_id: str
    user_id: str
    items: List[OrderItem]
    status: OrderStatus
    payment_status: PaymentStatus

def generate_unique_id(prefix: str = "id") -> str: ...
```

### 4.2 Structured JSON Schema
```json
{
  "target": {
    "csi": "csi://sample_project/services/OrderService.create_order",
    "contract": {
      "kind": "method",
      "parameters": [{"name": "user_id", "type": "str"}, {"name": "items", "type": "List[OrderItem]"}],
      "return_type": "Order"
    },
    "body": "user = self.user_repo.get_by_id(user_id)\n..."
  },
  "dependencies": [
    {
      "csi": "csi://sample_project/repositories/OrderRepository.save_order",
      "signature": "def save_order(self, order: Order) -> None: ..."
    }
  ]
}
```

