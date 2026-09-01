"""Demonstration script showing how an AI workflow can query the codebase via LSP."""

import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lsp_client import LspClient, describe_symbol_at_position, get_file_outline

console = Console()


async def main() -> None:
    console.print(Panel.fit("[bold magenta]LSP Intelligence for AI Development Demo[/]", border_style="cyan"))

    async with LspClient() as client:
        console.print("[green]✓ LSP server connected and initialized.[/]\n")

        # 1. Document Outline / Symbol Exploration
        console.print("[bold cyan]1. Querying Document Outline for `lsp_prototype/sample_project/services.py`...[/]")
        outline = await get_file_outline(client, "lsp_prototype/sample_project/services.py")
        console.print(f"Found [bold]{outline['total_symbols']}[/] top-level symbols.")
        for tree_line in outline["tree"][:10]:
            console.print(tree_line)
        console.print("  ...\n")

        # 2. Hover / Type Signature & Docstring Extraction
        console.print("[bold cyan]2. Hover inspection on `OrderService.create_order` in `lsp_prototype/sample_project/services.py`...[/]")
        # Line 35 (0-indexed 34), col 9 is 'def create_order'
        hover = await client.get_hover("lsp_prototype/sample_project/services.py", line=34, character=9)
        if hover:
            console.print(Panel(hover.contents, title="Hover (Type Signature + Docstring)", border_style="blue"))
        console.print()

        # 3. Cross-File Definition Lookup
        console.print("[bold cyan]3. Resolving Cross-File Definition for `Order` instantiated in `services.py`...[/]")
        # 'order = Order(' at line 55 (0-indexed 54) col 17
        defs = await client.get_definition("lsp_prototype/sample_project/services.py", line=54, character=17)
        if defs:
            for d in defs:
                console.print(f"  -> Defined in [green]{d.file_path}[/] at line [yellow]{d.range.start.line + 1}[/]")
        console.print()

        # 4. Finding References across the workspace
        console.print("[bold cyan]4. Finding all References to `Order` dataclass across the codebase...[/]")
        # In sample_project/models.py, line 84 (0-indexed 83) is 'class Order:'
        refs = await client.get_references("lsp_prototype/sample_project/models.py", line=83, character=6)
        table = Table(title=f"References to `Order` ({len(refs)} usages found)")
        table.add_column("File", style="cyan")
        table.add_column("Line", style="yellow")
        for r in refs:
            table.add_row(r.file_path, f"L{r.range.start.line + 1}:{r.range.start.character + 1}")
        console.print(table)
        console.print()

        # 5. Workspace Symbol Search
        console.print("[bold cyan]5. Workspace Symbol Search for 'Payment'...[/]")
        ws_symbols = await client.get_workspace_symbols("Payment")
        ws_table = Table(title="Workspace Symbols matching 'Payment'")
        ws_table.add_column("Name", style="bold cyan")
        ws_table.add_column("Kind", style="magenta")
        ws_table.add_column("Location", style="yellow")
        for s in ws_symbols:
            ws_table.add_row(s.name, s.kind_name, f"{s.location.file_path}:{s.location.range.start.line + 1}")
        console.print(ws_table)
        console.print()

        # 6. Complete AI Symbol Profile
        console.print("[bold cyan]6. Unified AI Symbol Context Profile for `PaymentGateway`...[/]")
        profile = await describe_symbol_at_position(client, "lsp_prototype/sample_project/interfaces.py", line=29, character=6)
        console.print(Panel(
            f"[bold]File:[/] {profile['file']}:{profile['query_position']}\n"
            f"[bold]Definitions:[/] {len(profile['definitions'])}\n"
            f"[bold]Total References:[/] {profile['reference_count']}\n\n"
            f"[bold]Hover Documentation:[/]\n{profile['hover']}",
            title="AI Symbol Context",
            border_style="green",
        ))


if __name__ == "__main__":
    asyncio.run(main())
