# CodeMesh 🕸️

> **The Semantic-First Program Graph Engine & Zero-Diff Runtime for AI Coding Agents**

CodeMesh transitions software development from file-based text manipulation (fragile diffs, line offsets, whole-file context bloat, broken imports) into an in-memory **Semantic Knowledge Graph** of symbols, typed contracts, relational dependencies, and zero-diff mutations.

---

## Why CodeMesh?

| Traditional AI Coding | The CodeMesh Paradigm |
| :--- | :--- |
| **Monolithic File Contexts**: Feeding thousands of lines of irrelevant code into LLM prompts. | **Surgical Contract Slicing**: Slices only the target function body + `.pyi` signature contracts of direct dependencies (**76.9% token savings**). |
| **Fragile Line & Diff Patches**: Regex searches, line numbers, and whitespace formatting conflicts. | **Zero-Diff Symbol Mutations**: Modify functions and methods directly by Canonical Symbol ID (`csi://...`) with automated AST normalization. |
| **Import Drift & Breakage**: LLMs frequently introduce missing or circular imports. | **Automated Import Synthesis**: Relational graph edges deterministically generate clean, deduplicated module headers during projection. |
| **Post-Commit Failures**: Discovering broken callers only after running full test suites. | **In-Memory Invariant Guard**: Pre-commit blast-radius computation blocks breaking deletions and interface violations before touching disk. |

---

## Quick Start (Python SDK)

> 📖 **Looking for a full setup walkthrough? Check out the [Quick Start Guide](docs/quickstart.md) to integrate CodeMesh with Claude Code, Cursor, Antigravity, or custom agents.**

```python
import asyncio
from codemesh import SemanticWorkspace

async def main():
    # 1. Ingest codebase into in-memory SemanticGraph via LSP Anti-Corruption Layer
    workspace = await SemanticWorkspace.load(target_dir="src/my_package")

    # 2. Extract surgical prompt context slice (target body + callee contracts only)
    target_csi = "csi://my_package/services/OrderService.create_order"
    slice_obj = workspace.get_symbol_context(target_csi)
    prompt_stub = slice_obj.to_python_stub_prompt()
    print(prompt_stub)

    # 3. Perform Zero-Diff symbol modification (No line numbers or diff hunks needed!)
    result = workspace.edit_symbol(
        csi=target_csi,
        new_body="""def create_order(self, user_id: str, items: List[OrderItem]) -> Order:
        order_id = generate_unique_id("ord_v2")
        order = Order(order_id=order_id, user_id=user_id, items=items)
        self.order_repo.save_order(order)
        return order
    """,
        auto_materialize=True,  # Automatically writes to disk with synthesized imports
    )

    if result.success:
        print("✓ Symbol updated cleanly!")
```

---

## Benchmark Results (Experiment 02)

Extending an e-commerce platform with a **Coupon & Loyalty Discount System** across models, interfaces, services, and utils:

| Metric | Traditional File-Based | CodeMesh SDK | Improvement |
| :--- | :--- | :--- | :--- |
| **Input Context Tokens** | `2,355` tokens | `543` tokens | **76.9% reduction** |
| **Total Tokens Consumed** | `2,779` tokens | `965` tokens | **65.3% reduction** |
| **Manual Import Rewrites** | `4 manual file edits` | `0 (auto-synthesized)` | **100% Automated** |
| **Functional Tests Passed** | `100% (4/4)` | `100% (4/4)` | **100% Verified** |

---

## Repository Architecture

```
codemesh/
├── src/codemesh/
│   ├── core/           # Pure domain ontology: CSI, SymbolContract, SemanticGraph
│   ├── adapters/lsp/   # Anti-Corruption Layer: LSP stdio client, spatial index, graph builder
│   ├── slicing/        # Context Slicing Engine: Minimal contract closures (.pyi stubs)
│   ├── mutation/       # Zero-diff engine, AST normalizer, blast radius & invariants
│   ├── projection/     # FileSystem materialization & auto-import synthesizer
│   └── workspace.py    # High-level developer & agent workspace facade
│
├── experiments/
│   ├── 01_raw_lsp_exploration/             # Historical initial LSP client spike
│   └── 02_agent_semantic_skill_benchmark/  # Automated comparative A/B benchmark
│
├── tests/              # Full unit & integration test suite
└── demo.py             # Interactive demonstration runner
```

---

## Running the Interactive Demo & Tests

```bash
# Run the interactive demo
python demo.py

# Run the full test suite
pytest -v

# Run the Experiment 02 Benchmark
python experiments/02_agent_semantic_skill_benchmark/harness.py
```

---

## License

CodeMesh is licensed under the [Apache License, Version 2.0](LICENSE).
