---
name: codemesh
description: Canonical Semantic-First Graph Engine & Zero-Diff Development SDK for AI Coding Agents
---

# CodeMesh Agent Skill

Use this skill when exploring, reasoning about, developing, modifying, or refactoring Python codebases using the **CodeMesh** semantic graph framework.

---

## 1. Core Philosophy: Why CodeMesh?

Traditional AI assistants interact with code through raw files, line numbers, and fragile diff patches. This causes:
* **Token waste**: Reading thousands of lines of irrelevant helper functions.
* **Patch failures**: Whitespace, indentation, and offset errors when applying text edits.
* **Import drift**: Missing or circular imports when adding/moving classes.

**CodeMesh** replaces physical files with an in-memory **Semantic Knowledge Graph** addressed by **Canonical Symbol IDs (CSI)** (`csi://<package>/<namespace>/<symbol>[.<member>]`).

---

## 2. Standard Agent Workflows

### A. Initializing the Workspace
```python
from codemesh import SemanticWorkspace

# Ingest target codebase via the LSP Anti-Corruption Layer
workspace = await SemanticWorkspace.load(
    workspace_root=".",
    target_dir="src/my_package",
)
```

---

### B. Multi-Symbol Task Slicing (Coordinated Multi-File Context)
When implementing a feature that spans multiple symbols, extract a unified multi-target context slice:
```python
# Slices requested targets with full bodies, and deduplicates all shared dependency contracts (.pyi)
context = workspace.get_multi_symbol_context([
    "csi://my_package/models/Order",
    "csi://my_package/interfaces/DiscountStrategy",
    "csi://my_package/services/OrderService.create_order",
])

# Inject this minimal, high-density stub directly into your prompt/reasoning
prompt_stub = context.to_python_stub_prompt()
```

---

### C. Zero-Diff Symbol Modification (`edit_symbol`)
Modify functions or class methods without worrying about line numbers, regex patches, or indentation:
```python
# Pass unindented raw Python snippet
result = workspace.edit_symbol(
    csi="csi://my_package/services/OrderService.create_order",
    new_body="""def create_order(self, user_id: str, items: List[OrderItem]) -> Order:
    \"\"\"Telemetry-wrapped order creation.\"\"\"
    order_id = generate_unique_id("ord_v2")
    order = Order(order_id=order_id, user_id=user_id, items=items)
    self.order_repo.save_order(order)
    return order
""",
    auto_materialize=True,  # Automatically projects to disk with synthesized imports
)

if not result.success:
    print(f"Edit failed: {result.error_message}")
```

---

### D. Adding New Symbols (`add_symbol`)
Add new classes, functions, or protocols to a target module:
```python
result = workspace.add_symbol(
    target_package="my_package/models",
    code="""
class Coupon:
    \"\"\"Customer discount voucher.\"\"\"
    def __init__(self, code: str, discount_percent: float, min_order_amount: Money, is_active: bool = True) -> None:
        self.code = code
        self.discount_percent = discount_percent
        self.min_order_amount = min_order_amount
        self.is_active = is_active

    def is_applicable(self, order_subtotal: Money) -> bool:
        if not self.is_active:
            return False
        return order_subtotal.amount >= self.min_order_amount.amount
""",
    auto_materialize=True,
)
```

---

### E. Graph Semantic Discovery (No `grep` Noise!)
Explore relationships, callers, and interface implementations across the codebase:
```python
# 1. Find all classes implementing a protocol
impls = workspace.find_implementations("csi://my_package/interfaces/DiscountStrategy")
# -> [csi://my_package/gateways/PercentageDiscountStrategy, ...]

# 2. Find all callers of a function
callers = workspace.find_callers("csi://my_package/services/OrderService.calculate_order_total")
# -> [csi://my_package/services/OrderService.checkout_order]

# 3. Find all dependents/references
refs = workspace.find_references("csi://my_package/models/Money")

# 4. Search symbols by query
matches = workspace.find_symbols("order")
```

---

### F. Atomic Semantic Refactoring (`rename_symbol`, `move_symbol`)
Refactor symbols cleanly across the entire graph with auto-reconciled imports:
```python
# 1. Rename symbol across all definitions and call sites
workspace.rename_symbol(
    csi="csi://my_package/services/OrderService.create_order",
    new_name="place_order",
    auto_materialize=True,
)

# 2. Relocate symbol to another package/module
workspace.move_symbol(
    csi="csi://my_package/utils/format_discount_summary",
    new_package="my_package/telemetry",
    auto_materialize=True,
)
```

---

### G. Disk Materialization
Deterministically compile the entire semantic graph back to formatted source files with auto-generated imports:
```python
written_files = workspace.materialize(output_dir="src", src_dir="src")
```

