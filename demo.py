import asyncio
import os
from pathlib import Path
import shutil
import sys

# Ensure 'src' is importable when running standalone
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from codemesh.core import CanonicalSymbolId
from codemesh.mutation import DeleteSymbolMutation, MutationEngine
from codemesh.workspace import SemanticWorkspace

console = Console()


async def main() -> None:
    console.print(Panel.fit(
        "[bold cyan]CodeMesh 🕸️ : Semantic Assistance & Zero-Diff Runtime Demo[/]\n"
        "[dim]Multi-Target Slicing • Graph Discovery • Zero-Diff Edits • AST Scaffolding • Auto-Imports[/]",
        border_style="magenta",
    ))

    # --- STEP 1: INGEST CODEBASE VIA SEMANTIC WORKSPACE ---
    console.print("\n[bold green]1. Initializing SemanticWorkspace from codebase fixtures...[/]")
    workspace = await SemanticWorkspace.load(
        workspace_root=".",
        target_dir="fixtures/sample_ecommerce",
    )

    table = Table(title="SemanticGraph Ingestion Metrics", border_style="cyan")
    table.add_column("Metric", style="bold white")
    table.add_column("Value", style="green")
    table.add_row("Total Ingested Symbol Nodes", str(len(workspace.graph.nodes)))
    table.add_row("Total Relational Edges", str(len(workspace.graph.edges)))
    console.print(table)

    # --- STEP 2: GRAPH SEMANTIC DISCOVERY ---
    console.print("\n[bold green]2. Graph Semantic Discovery (Zero-Grep Architecture Queries)...[/]")
    impls = workspace.find_implementations("csi://sample_ecommerce/interfaces/PaymentGateway")
    callers = workspace.find_callers("csi://sample_ecommerce/services/OrderService.calculate_order_total")

    disc_table = Table(title="Graph Discovery Query Results", border_style="blue")
    disc_table.add_column("Query", style="bold yellow")
    disc_table.add_column("Discovered Symbol CSIs", style="white")
    disc_table.add_row("find_implementations(PaymentGateway)", "\n".join(str(c) for c in impls) or "None")
    disc_table.add_row("find_callers(calculate_order_total)", "\n".join(str(c) for c in callers) or "None")
    console.print(disc_table)

    # --- STEP 3: MULTI-SYMBOL TASK SLICING ---
    console.print("\n[bold green]3. Slicing Unified Multi-Symbol Context for Coordinated Tasks...[/]")
    multi_slice = workspace.get_multi_symbol_context([
        "csi://sample_ecommerce/models/Order",
        "csi://sample_ecommerce/services/OrderService.calculate_order_total",
    ])
    prompt_stub = multi_slice.to_python_stub_prompt()
    syntax = Syntax(prompt_stub, "python", theme="monokai", line_numbers=True)
    console.print(Panel(
        syntax,
        title="[bold yellow]Multi-Target Prompt Slice (2 Target Bodies + Deduplicated Shared Contracts)[/]",
        border_style="yellow",
    ))

    # --- STEP 4: ZERO-DIFF SYMBOL EDIT WITH AST NORMALIZATION ---
    console.print("\n[bold green]4. Agent calls Zero-Diff `edit_symbol` (Unindented raw Python snippet)...[/]")
    target_csi = "csi://sample_ecommerce/services/OrderService.create_order"
    raw_llm_code = """def create_order(self, user_id: str, items: List[OrderItem]) -> Order:
    \"\"\"Telemetry-monitored high-performance order creation.\"\"\"
    order_id = generate_unique_id("ord_v2")
    order = Order(order_id=order_id, user_id=user_id, items=items, status=OrderStatus.PENDING)
    self.order_repo.save_order(order)
    return order
"""
    result = workspace.edit_symbol(
        csi=target_csi,
        new_body=raw_llm_code,
        auto_materialize=False,
    )

    if result.success:
        console.print(Panel(
            "[bold green]✓ Zero-Diff Symbol Modification Applied Successfully![/]\n"
            f"• Target Symbol: [cyan]{result.target_csi}[/]\n"
            f"• AST Syntax Check: [green]Passed[/]\n"
            f"• Indentation Normalized: [green]4-spaces applied automatically[/]\n"
            f"• Invariant Check: [green]No breaking changes detected[/]\n"
            f"• Blast Radius Impacted Callers: [yellow]{len(result.blast_radius.direct_callers)}[/]",
            border_style="green",
        ))

    # --- STEP 5: TOP-DOWN SYMBOL ADDITION ---
    console.print("\n[bold green]5. Agent adds new entity `Coupon` via `add_symbol`...[/]")
    coupon_code = """class Coupon:
    \"\"\"Customer discount voucher entity.\"\"\"
    def __init__(self, code: str, discount_percent: float, min_order_amount: Money, is_active: bool = True) -> None:
        self.code = code
        self.discount_percent = discount_percent
        self.min_order_amount = min_order_amount
        self.is_active = is_active

    def is_applicable(self, order_subtotal: Money) -> bool:
        if not self.is_active:
            return False
        return order_subtotal.amount >= self.min_order_amount.amount
"""
    add_res = workspace.add_symbol(
        target_package="sample_ecommerce/models",
        code=coupon_code,
        auto_materialize=False,
    )
    if add_res.success:
        console.print(f"✓ Added symbol [cyan]{add_res.target_csi}[/] with child methods to SemanticGraph.")

    # --- STEP 6: PRE-COMMIT INVARIANT CHECK ---
    console.print("\n[bold green]6. Invariant Engine: Verifying Breaking Deletion Protection...[/]")
    csi_order = CanonicalSymbolId.parse("csi://sample_ecommerce/models/Order")
    delete_mut = DeleteSymbolMutation(target_csi=csi_order)
    valid, errors = MutationEngine.validate_invariants(workspace.graph, delete_mut)

    if not valid:
        console.print(Panel(
            f"[bold red]✗ Mutation Blocked (Invariant Violation):[/]\n{errors[0]}",
            border_style="red",
        ))

    # --- STEP 7: FILESYSTEM MATERIALIZATION ---
    console.print("\n[bold green]7. Materializing SemanticGraph back to Physical Disk Files...[/]")
    output_dir = "projected_output"
    shutil.rmtree(output_dir, ignore_errors=True)
    os.makedirs(output_dir, exist_ok=True)

    written = workspace.materialize(output_dir=output_dir, src_dir="src")
    console.print(f"✓ Deterministically synthesized [bold]{len(written)}[/] source files with auto-generated imports to [cyan]{output_dir}/[/]:")
    for f in written:
        rel = os.path.relpath(f, ".")
        console.print(f"  • [green]{rel}[/]")

    console.print("\n[bold magenta]✓ CodeMesh Semantic Assistance Lifecycle Executed Successfully![/]\n")


if __name__ == "__main__":
    asyncio.run(main())
