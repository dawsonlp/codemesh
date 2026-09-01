# CodeMesh Quick Start Guide 🚀

This guide walks you through setting up **CodeMesh** to supercharge your AI coding assistant (Claude Code, Antigravity, Cursor, Windsurf, Aider, or custom LLM agent scripts) with semantic graph context slicing, zero-diff symbol editing, and automated import synthesis.

---

## 1. Prerequisites & Installation

### A. System Requirements
* **Python**: `3.10` or higher
* **Node.js**: (Required to run the underlying `pyright` language server)

### B. Install Pyright Language Server
CodeMesh uses Pyright via stdio JSON-RPC for fast AST indexing and type resolution:
```bash
npm install -g pyright
```

### C. Install CodeMesh
Install CodeMesh in your development virtual environment:
```bash
# Clone and install in editable mode
git clone https://github.com/dawsonlp/codemesh.git
cd codemesh
pip install -e .
```

---

## 2. Equipping Your AI Agent with CodeMesh

CodeMesh includes a standardized Agent Skill that teaches any LLM how to interact with your codebase via the CodeMesh SDK rather than reading raw text files.

### Where to Place the Agent Skill

| Environment / Tool | Setup Location | How It Works |
| :--- | :--- | :--- |
| **Antigravity / Gemini CLI** | Copy [`skills/codemesh/SKILL.md`](../skills/codemesh/SKILL.md) to `.gemini/skills/codemesh/SKILL.md` | Agent automatically triggers the skill for Python development. |
| **Claude Code** | Copy [`skills/codemesh/SKILL.md`](../skills/codemesh/SKILL.md) to your prompt / instructions | Informs Claude how to run Python SDK commands in its shell tool. |
| **Cursor / Windsurf** | Add contents of [`skills/codemesh/SKILL.md`](../skills/codemesh/SKILL.md) to `.cursorrules` or `.windsurfrules` | Instructs the model to write CodeMesh scripts for multi-file refactoring. |
| **Custom Agent / Python Scripts** | Direct SDK import: `from codemesh import SemanticWorkspace` | Direct programmatic access. |

---

## 3. End-to-End Workflow: How an Agent Uses CodeMesh

Here is how an agent explores, slices, edits, and compiles code using CodeMesh:

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│ 1. INGEST       │  ──>  │ 2. DISCOVER     │  ──>  │ 3. SLICE        │  ──>  │ 4. MUTATE &     │
│ Codebase into   │       │ Query callers & │       │ Target body +   │       │    MATERIALIZE  │
│ SemanticGraph   │       │ implementations │       │ .pyi contracts  │       │ Zero-diff edits │
└─────────────────┘       └─────────────────┘       └─────────────────┘       └─────────────────┘
```

### Step 1: Ingest Your Codebase
The agent loads your project into an in-memory graph:
```python
import asyncio
from codemesh import SemanticWorkspace

async def main():
    workspace = await SemanticWorkspace.load(
        workspace_root=".",
        target_dir="src/my_project",
    )
    print(f"Ingested {len(workspace.graph.nodes)} symbols and {len(workspace.graph.edges)} relational edges.")

asyncio.run(main())
```

---

### Step 2: Query Architecture (No `grep` Noise)
Before touching any code, the agent queries relations directly:
```python
# Find all classes that implement the PaymentGateway protocol
gateways = workspace.find_implementations("csi://my_project/interfaces/PaymentGateway")

# Find all functions that call calculate_order_total
callers = workspace.find_callers("csi://my_project/services/OrderService.calculate_order_total")

# Find all dependencies and references to the Money entity
references = workspace.find_references("csi://my_project/models/Money")
```

---

### Step 3: Slice Minimal Prompt Context (76.9% Token Savings)
Instead of dumping full files into prompt context, the agent extracts a surgical stub containing **only the target functions + `.pyi` signature contracts of direct dependencies**:
```python
# Multi-symbol slice for coordinated feature development
context = workspace.get_multi_symbol_context([
    "csi://my_project/models/Order",
    "csi://my_project/services/OrderService.calculate_order_total",
])

prompt_stub = context.to_python_stub_prompt()
# The agent now passes prompt_stub to the LLM
```

---

### Step 4: Zero-Diff Symbol Modification (`edit_symbol`)
The agent modifies function or method implementations directly. **No line numbers, regex matches, or search-and-replace hunks needed**:
```python
result = workspace.edit_symbol(
    csi="csi://my_project/services/OrderService.calculate_order_total",
    new_body="""def calculate_order_total(self, order_id: str) -> Money:
    \"\"\"Telemetry-wrapped order total calculation.\"\"\"
    order = self.order_repo.get_by_id(order_id)
    if not order:
        raise OrderProcessingError(f"Order not found: {order_id}")
    return order.calculate_subtotal()
""",
    auto_materialize=True,  # Automatically writes updated file to disk
)

if result.success:
    print("✓ Symbol updated cleanly on disk!")
else:
    print(f"✗ Invariant or Syntax error: {result.error_message}")
```

---

### Step 5: Adding New Entities (`add_symbol`)
Add new classes or functions with automated AST parsing and parent/child linking:
```python
workspace.add_symbol(
    target_package="my_project/models",
    code="""
class Coupon:
    \"\"\"Customer discount voucher entity.\"\"\"
    def __init__(self, code: str, discount_percent: float, min_spend: Money) -> None:
        self.code = code
        self.discount_percent = discount_percent
        self.min_spend = min_spend

    def is_valid(self, subtotal: Money) -> bool:
        return subtotal.amount >= self.min_spend.amount
""",
    auto_materialize=True,
)
```

---

### Step 6: Atomic Refactoring (`rename_symbol`, `move_symbol`)
Rename or relocate symbols across modules; CodeMesh updates definitions, references, and imports automatically:
```python
# Rename method across the entire graph
workspace.rename_symbol(
    csi="csi://my_project/services/OrderService.create_order",
    new_name="place_order",
    auto_materialize=True,
)
```

---

## 4. Best Practices for Agent Prompts

1. **Avoid Whole-File Reading**:
   * *Traditional*: "Read `models.py`, `interfaces.py`, and `services.py`" (consumes 3,000+ tokens).
   * *With CodeMesh*: "Use `workspace.get_multi_symbol_context(...)`" (consumes ~500 tokens).
2. **Never Write Manual Import Headers**:
   * CodeMesh automatically analyzes relational graph edges and synthesizes clean, deduplicated module headers on disk.
3. **Rely on In-Memory Invariants**:
   * Deleting or modifying a symbol checks for active callers *before* touching disk, preventing broken builds and regressions.

---

## 5. Troubleshooting & FAQ

#### Q: Pyright reports `Cannot find module` during indexing
Ensure you have a `pyrightconfig.json` in your repository root specifying your source folders:
```json
{
  "include": ["src", "fixtures"],
  "pythonVersion": "3.11",
  "typeCheckingMode": "basic"
}
```

#### Q: How do I run the test suite to verify my setup?
```bash
pytest -v
```

#### Q: How do I run the interactive demonstration?
```bash
python demo.py
```

