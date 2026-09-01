# Experiment 02: CodeMesh Agent Skill Benchmark

This experiment measures the efficiency, token consumption, and code quality of an autonomous coding agent using the **CodeMesh Python SDK** via an agent **Skill**, compared directly against a **Traditional File-Based Coding** baseline on an identical programming specification.

---

## Structure of this Experiment

* `skill/SKILL.md`: The agent skill documentation teaching agents how to use `codemesh` (slicing minimal prompt contexts, zero-diff `edit_symbol` mutations, auto-import synthesis). Also available at the project top-level at `skills/codemesh/SKILL.md`.
* `task_spec.md`: The functional specification for the benchmark task (**Coupon & Loyalty Discount System**).
* `eval_tests.py`: Objective test suite validating functional correctness across both arms.
* `harness.py`: The benchmark execution runner that executes both approaches and records comparative metrics.
* `benchmark_report.md`: Generated comparative report containing token metrics, execution time, and reliability analysis.

---

## Running the Benchmark

```bash
# Run the benchmark harness
python experiments/02_agent_semantic_skill_benchmark/harness.py
```

