"""Command-line interface for querying Language Server Protocol against the codebase."""

from __future__ import annotations
import argparse
import asyncio
import json
import os
import sys
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree

from .client import LspClient
from .context_builder import describe_symbol_at_position, get_file_outline, read_file_line
from .protocol import SymbolInformation

console = Console()


def add_symbols_to_tree(tree: Tree, symbols: list[SymbolInformation]) -> None:
    for sym in symbols:
        line_no = sym.location.range.start.line + 1
        label = f"[bold cyan]{sym.name}[/] [dim]({sym.kind_name})[/] [yellow]:L{line_no}[/]"
        branch = tree.add(label)
        if sym.children:
            add_symbols_to_tree(branch, sym.children)


async def run_cli() -> int:
    parser = argparse.ArgumentParser(description="LSP CLI Client for Codebase Intelligence")
    parser.add_argument("--server", default=None, help="Path to LSP server binary (default: pyright-langserver)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of styled tables")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # symbols
    p_sym = subparsers.add_parser("symbols", help="List all symbols in a file")
    p_sym.add_argument("file", help="Target Python file")

    # hover
    p_hover = subparsers.add_parser("hover", help="Get hover documentation & type for a position")
    p_hover.add_argument("file", help="Target Python file")
    p_hover.add_argument("line", type=int, help="Line number (1-based)")
    p_hover.add_argument("col", type=int, help="Column number (1-based)")

    # definition
    p_def = subparsers.add_parser("definition", help="Go to definition for a symbol")
    p_def.add_argument("file", help="Target Python file")
    p_def.add_argument("line", type=int, help="Line number (1-based)")
    p_def.add_argument("col", type=int, help="Column number (1-based)")

    # references
    p_ref = subparsers.add_parser("references", help="Find all references to a symbol across the workspace")
    p_ref.add_argument("file", help="Target Python file")
    p_ref.add_argument("line", type=int, help="Line number (1-based)")
    p_ref.add_argument("col", type=int, help="Column number (1-based)")

    # workspace-symbols
    p_ws = subparsers.add_parser("workspace-symbols", help="Search for symbols across the whole workspace")
    p_ws.add_argument("query", help="Symbol search query")

    # describe
    p_desc = subparsers.add_parser("describe", help="Complete semantic profile (hover + def + refs) for AI context")
    p_desc.add_argument("file", help="Target Python file")
    p_desc.add_argument("line", type=int, help="Line number (1-based)")
    p_desc.add_argument("col", type=int, help="Column number (1-based)")

    # diagnostics
    p_diag = subparsers.add_parser("diagnostics", help="Show diagnostics/errors for a file")
    p_diag.add_argument("file", help="Target Python file")

    args = parser.parse_args()

    server_cmd = [args.server, "--stdio"] if args.server else None

    async with LspClient(server_command=server_cmd) as client:
        # Give background indexer brief moment if needed
        await asyncio.sleep(0.1)

        if args.command == "symbols":
            outline = await get_file_outline(client, args.file)
            if args.json:
                print(json.dumps({"file": outline["file"], "total_symbols": outline["total_symbols"], "tree": outline["tree"]}, indent=2))
            else:
                tree = Tree(f"[bold green]Symbols in {outline['file']}[/]")
                add_symbols_to_tree(tree, outline["raw_symbols"])
                console.print(tree)

        elif args.command == "hover":
            line_0 = max(0, args.line - 1)
            col_0 = max(0, args.col - 1)
            hover = await client.get_hover(args.file, line_0, col_0)
            if args.json:
                print(json.dumps({"hover": hover.contents if hover else None}, indent=2))
            else:
                if hover:
                    console.print(Panel(hover.contents, title=f"Hover @ {args.file}:{args.line}:{args.col}", border_style="blue"))
                else:
                    console.print("[yellow]No hover information found at this position.[/]")

        elif args.command == "definition":
            line_0 = max(0, args.line - 1)
            col_0 = max(0, args.col - 1)
            defs = await client.get_definition(args.file, line_0, col_0)
            if args.json:
                data = [{"file": d.file_path, "line": d.range.start.line + 1, "col": d.range.start.character + 1} for d in defs]
                print(json.dumps(data, indent=2))
            else:
                if not defs:
                    console.print("[yellow]No definition found.[/]")
                else:
                    table = Table(title=f"Definition for {args.file}:{args.line}:{args.col}")
                    table.add_column("File", style="cyan")
                    table.add_column("Position", style="yellow")
                    table.add_column("Code Preview", style="green")
                    for d in defs:
                        l_num = d.range.start.line
                        code_preview = read_file_line(d.file_path, l_num).strip()
                        rel_file = os.path.relpath(d.file_path, client.workspace_root)
                        table.add_row(rel_file, f"L{l_num + 1}:{d.range.start.character + 1}", code_preview)
                    console.print(table)

        elif args.command == "references":
            line_0 = max(0, args.line - 1)
            col_0 = max(0, args.col - 1)
            refs = await client.get_references(args.file, line_0, col_0)
            if args.json:
                data = [{"file": r.file_path, "line": r.range.start.line + 1, "col": r.range.start.character + 1} for r in refs]
                print(json.dumps(data, indent=2))
            else:
                if not refs:
                    console.print("[yellow]No references found.[/]")
                else:
                    table = Table(title=f"References for {args.file}:{args.line}:{args.col} ({len(refs)} found)")
                    table.add_column("File", style="cyan")
                    table.add_column("Line", style="yellow")
                    table.add_column("Code Preview", style="white")
                    for r in refs:
                        l_num = r.range.start.line
                        code_preview = read_file_line(r.file_path, l_num).strip()
                        rel_file = os.path.relpath(r.file_path, client.workspace_root)
                        table.add_row(rel_file, f"L{l_num + 1}", code_preview)
                    console.print(table)

        elif args.command == "workspace-symbols":
            symbols = await client.get_workspace_symbols(args.query)
            if args.json:
                data = [{"name": s.name, "kind": s.kind_name, "file": s.location.file_path, "line": s.location.range.start.line + 1} for s in symbols]
                print(json.dumps(data, indent=2))
            else:
                table = Table(title=f"Workspace Symbols matching '{args.query}' ({len(symbols)} found)")
                table.add_column("Name", style="bold cyan")
                table.add_column("Kind", style="magenta")
                table.add_column("Location", style="yellow")
                for s in symbols:
                    rel_file = os.path.relpath(s.location.file_path, client.workspace_root)
                    table.add_row(s.name, s.kind_name, f"{rel_file}:{s.location.range.start.line + 1}")
                console.print(table)

        elif args.command == "describe":
            line_0 = max(0, args.line - 1)
            col_0 = max(0, args.col - 1)
            desc = await describe_symbol_at_position(client, args.file, line_0, col_0)
            if args.json:
                print(json.dumps(desc, indent=2))
            else:
                console.print(Panel(desc["hover"], title=f"[bold]Symbol Profile:[/] {desc['file']}:{desc['query_position']}", border_style="green"))
                if desc["definitions"]:
                    d_table = Table(title="Definitions")
                    d_table.add_column("Target", style="cyan")
                    d_table.add_column("Snippet", style="green")
                    for d in desc["definitions"]:
                        d_table.add_row(f"{d['file']}:{d['line']}:{d['col']}", d["snippet"].strip())
                    console.print(d_table)

                if desc["references"]:
                    r_table = Table(title=f"References ({desc['reference_count']} across workspace)")
                    r_table.add_column("Location", style="yellow")
                    r_table.add_column("Code", style="white")
                    for r in desc["references"]:
                        r_table.add_row(f"{r['file']}:{r['line']}", r["code"])
                    console.print(r_table)

        elif args.command == "diagnostics":
            await client.ensure_document_open(args.file)
            await asyncio.sleep(0.5)  # allow server time to publish diagnostics
            diags = client.get_diagnostics(args.file)
            if args.json:
                data = [{"severity": d.severity_name, "message": d.message, "line": d.range.start.line + 1} for d in diags]
                print(json.dumps(data, indent=2))
            else:
                if not diags:
                    console.print(f"[bold green]✓ No diagnostics or errors reported for {args.file}[/]")
                else:
                    table = Table(title=f"Diagnostics for {args.file}")
                    table.add_column("Severity", style="bold red")
                    table.add_column("Line", style="yellow")
                    table.add_column("Message", style="white")
                    for d in diags:
                        table.add_row(d.severity_name, f"L{d.range.start.line + 1}", d.message)
                    console.print(table)

    return 0


def main() -> None:
    sys.exit(asyncio.run(run_cli()))


if __name__ == "__main__":
    main()

