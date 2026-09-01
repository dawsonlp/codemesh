# Experiment 01: Raw LSP Client & Pyright Exploration

This directory contains the **initial exploratory spike** conducted to understand how to:
1. Spawn a Language Server (`pyright-langserver --stdio`) in an async Python process.
2. Implement an asynchronous JSON-RPC protocol over stdio.
3. Query raw LSP methods (`textDocument/hover`, `textDocument/definition`, `textDocument/references`, `textDocument/documentSymbol`).

---

## Structure of this Experiment

* `demo.py`: Standalone script demonstrating raw LSP queries against `sample_project/`.
* `lsp_client/`: The initial lightweight JSON-RPC client built for this spike.
* `sample_project/`: The mock e-commerce codebase created as a target for testing queries.
* `tests/`: Integration tests verifying raw LSP functionality.

---

## Running this Exploration

```bash
# Run the raw LSP interactive demo
PYTHONPATH=experiments/01_raw_lsp_exploration python experiments/01_raw_lsp_exploration/demo.py

# Run the raw LSP spike tests
pytest experiments/01_raw_lsp_exploration/tests/
```

> **Note**: This directory is preserved purely for educational reference. The canonical framework implementation lives in `src/codemesh/`.
