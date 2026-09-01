---
name: semantic-program-engineering
description: Canonical Semantic-First Program Engineering SDK for AI Coding Agents
---

# Semantic Program Engineering Skill

Use this skill when developing, exploring, modifying, or refactoring Python codebases using the `semantic_engine` framework.

---

## 1. Overview & Core Advantages

Traditional AI coding assistants manipulate code by reading entire physical files, calculating line-number offsets, and submitting fragile text diff patches. This leads to:
* **Token waste**: Ingesting thousands of lines of irrelevant helper functions.
* **Patch failures**: Whitespace, indentation, and offset errors when applying text edits.
* **Import drift**: Missing or broken module imports and circular dependency bugs.

The **Semantic Engine SDK** eliminates physical file management by maintaining an in-memory **Semantic Graph** where symbols are addressed by **Canonical Symbol ID (CSI)**:
* `csi://<package>/<namespace>/<symbol>[.<member>]`

---

## 2. Standard Workflow for AI Agents

```python
import asyncio
from semantic_engine.workspace import SemanticWorkspace

async def work_on_codebase():
    # 1. Ingest codebase into in-memory SemanticGraph
    workspace = await SemanticWorkspace.load(target_dir="src/my_package")

    # 2. Extract minimal prompt context for target symbol
    # Slices target implementation body + exact .pyi contracts of dependencies
    target_csi = "csi://my_package/services/OrderService.create_order"
    context_slice = workspace.get_symbol_context(target_csi)
    prompt_stub = context_slice.to_python_stub_prompt()
    print(prompt_stub)

    # 3. Apply Zero-Diff Symbol Modification
    # No line numbers! No regex matching! Provide clean Python body.
    new_body = """def create_order(self, user_id: str, items: List[OrderItem]) -> Order:
        \"\"\"Create order with updated telemetry and validation.\"\"\"
        order_id = generate_unique_id("ord_v3")
        order = Order(order_id=order_id, user_id=user_id, items=items)
        self.order_repo.save_order(order)
        return order
    """

    result = workspace.edit_symbol(
        csi=target_csi,
        new_body=new_body,
        auto_materialize=True,  # Automatically writes updated code to disk with auto-generated imports
    )

    if result.success:
        print("✓ Symbol updated successfully!")
        print(f"Impacted callers: {len(result.blast_radius.direct_callers)}")
    else:
        print(f"✗ Error: {result.error_message}")
```

---

## 3. Key APIs Reference

### Initializing the Workspace
```python
workspace = await SemanticWorkspace.load(workspace_root=".", target_dir="path/to/target")
```

### Reading Context (Minimal AI Stub Slicing)
```python
# Returns ContextSlice containing target body and read-only dependency stubs
slice_obj = workspace.get_symbol_context("csi://package/module/Class.method")
print(slice_obj.to_python_stub_prompt())
```

### Modifying Symbols (Zero-Diff Editing)
```python
# Normalizes AST, validates syntax, matches indentation, checks invariants
result = workspace.edit_symbol(
    csi="csi://package/module/Class.method",
    new_body="def method(self, ...): ...",
    auto_materialize=True,
    output_dir="output_path",
)
```

### Materializing to Disk (Automated Imports)
```python
# Materializes all modified graph nodes with deterministically synthesized import headers
written_files = workspace.materialize(output_dir="dist", src_dir="src")
```

