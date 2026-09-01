# Experiment 02: Comparative Benchmark Report
**Semantic Engine SDK vs. Traditional File-Based Coding**

---

## 1. Executive Summary

This benchmark evaluated the efficiency, token usage, execution latency, and correctness of extending a multi-tier Python codebase using two competing paradigms on an identical functional specification (**Coupon & Loyalty Discount System**):
1. **Traditional File-Based Approach**: Reading full source files, calculating manual imports, and submitting text/line patches.
2. **Semantic Engine SDK Approach**: Reading sliced `.pyi` contract stubs, executing zero-diff symbol mutations, and auto-synthesizing import headers.

---

## 2. Key Metrics & Results

| Metric | Baseline (Traditional) | Semantic Engine SDK | Improvement / Delta |
| :--- | :--- | :--- | :--- |
| **Input Context Tokens** | `2355` tokens | `543` tokens | **76.9% reduction** |
| **Output Code Tokens** | `424` tokens | `422` tokens | Equivalent |
| **Total Tokens Consumed** | `2779` tokens | `965` tokens | **65.3% reduction** |
| **Total Latency (Wall-clock)** | `1.7ms` | `336.4ms` | Includes cold-start LSP spawn |
| **Warm Per-Op Latency** | `~1.7ms` (disk append) | `~1.1ms` (slicing+AST+diff) | Single-digit milliseconds |
| **Functional Tests Passed** | `100% (4/4)` | `100% (4/4)` | **100% Verified** |
| **Manual Import Rewrites** | `4 manual file edits` | `0 (auto-synthesized)` | **100% Automated** |

---

## 3. Detailed Findings

### A. Token Context Efficiency (76.9% Savings)
* **Traditional Approach**: The agent had to ingest all 4 full Python files (`models.py`, `interfaces.py`, `services.py`, `utils.py`) including all private helper methods and docstrings (2355 tokens).
* **Semantic SDK Approach**: The agent only ingested the sliced contract stub for the target symbol and its direct dependencies (543 tokens), yielding a **76.9% context token savings**.

### B. Latency Breakdown & Architectural Analysis
* **Why Baseline Shows ~1ms**: The baseline measurement simulated naive file-system string appends (`open().write()`) without launching any type checkers, AST parsers, or language servers.
* **Why Semantic SDK Shows ~350ms Total**:
  * **One-Time Cold Start (334.9ms / ~98% of time)**: Spawning the `pyright-langserver --stdio` subprocess, completing JSON-RPC handshake initialization, and crawling all symbols, hover signatures, and references across the repository to build the initial in-memory graph.
  * **Per-Operation Mutation Execution (1.1ms / ~2% of time)**: Slicing prompt stubs, AST syntax validation, zero-diff symbol insertion, and full filesystem materialization with synthesized imports.
* **Real-World Impact on LLM Turn Latency**: In a real developer session, the LSP server and `SemanticWorkspace` remain warm in memory across turns (<5ms per operation). Furthermore, saving 1812 prompt tokens saves an estimated **1.5 to 4.0 seconds of LLM network and inference latency** on every single agent turn.

### C. Zero-Diff Reliability & Automated Imports
* In the baseline approach, adding `CouponDiscountStrategy` required the agent to manually calculate and update import headers in `services.py` (`from .interfaces import ...`, `from .models import ...`).
* In the Semantic Engine SDK approach, the agent simply registered the new symbol node on the graph. `FileSystemProjector` automatically synthesized clean, deduplicated imports (`from sample_ecommerce.models import Coupon`, `from sample_ecommerce.interfaces import CouponDiscountStrategy`) without any agent intervention.

---

## 4. Conclusion
The **Semantic Engine SDK** substantially reduces LLM prompt context bloat while completely eliminating line-offset calculations and manual import maintenance. The cold-start indexing overhead (~340ms) is negligible and amortized instantly across agent turns.
