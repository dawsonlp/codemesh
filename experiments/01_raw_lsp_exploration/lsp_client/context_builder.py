"""AI-oriented context generators and semantic code summarizers using LSP data."""

from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .client import LspClient
from .protocol import DocumentSymbol, Hover, Location, SymbolInformation


def read_file_line(file_path: str, line_number: int) -> str:
    """Read a specific 0-indexed line from a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if 0 <= line_number < len(lines):
                return lines[line_number].rstrip("\r\n")
    except Exception:
        pass
    return ""


def read_file_snippet(file_path: str, start_line: int, end_line: int) -> str:
    """Read a range of lines (0-indexed, inclusive) from a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            start = max(0, start_line)
            end = min(len(lines) - 1, end_line)
            return "".join(lines[start : end + 1])
    except Exception:
        return ""


async def describe_symbol_at_position(
    client: LspClient,
    file_path: Union[str, Path],
    line: int,
    character: int,
    workspace_rel: bool = True,
) -> Dict[str, Any]:
    """Assemble a comprehensive semantic profile for a symbol:

    - Hover (type signature, markdown docstrings)
    - Definition location(s) and source snippet
    - References across the entire project with line previews
    """
    abs_path = os.path.abspath(file_path)
    root = client.workspace_root

    def format_path(p: str) -> str:
        if workspace_rel and p.startswith(root):
            return os.path.relpath(p, root)
        return p

    # 1. Hover
    hover = await client.get_hover(abs_path, line, character)
    hover_text = hover.contents if hover else "No hover documentation available."

    # 2. Definition
    definitions = await client.get_definition(abs_path, line, character)
    def_info = []
    for d in definitions:
        d_path = d.file_path
        start_line = d.range.start.line
        end_line = d.range.end.line
        snippet = read_file_snippet(d_path, start_line, min(start_line + 8, end_line))
        def_info.append({
            "file": format_path(d_path),
            "line": start_line + 1,
            "col": d.range.start.character + 1,
            "snippet": snippet,
        })

    # 3. References
    references = await client.get_references(abs_path, line, character, include_declaration=True)
    ref_info = []
    for r in references:
        r_path = r.file_path
        r_line = r.range.start.line
        code_line = read_file_line(r_path, r_line)
        ref_info.append({
            "file": format_path(r_path),
            "line": r_line + 1,
            "col": r.range.start.character + 1,
            "code": code_line.strip(),
        })

    return {
        "file": format_path(abs_path),
        "query_position": f"{line + 1}:{character + 1}",
        "hover": hover_text,
        "definitions": def_info,
        "references": ref_info,
        "reference_count": len(ref_info),
    }


def format_symbol_tree(symbols: List[SymbolInformation], indent: int = 0) -> List[str]:
    """Recursively format a symbol hierarchy into an indented list of strings."""
    lines = []
    prefix = "  " * indent
    for sym in symbols:
        line_num = sym.location.range.start.line + 1
        lines.append(f"{prefix}- [{sym.kind_name}] **{sym.name}** (line {line_num})")
        if sym.children:
            lines.extend(format_symbol_tree(sym.children, indent + 1))
    return lines


async def get_file_outline(
    client: LspClient,
    file_path: Union[str, Path],
) -> Dict[str, Any]:
    """Return an outline of classes, functions, and symbols declared in a file."""
    abs_path = os.path.abspath(file_path)
    symbols = await client.get_document_symbols(abs_path)
    formatted_tree = format_symbol_tree(symbols)
    return {
        "file": os.path.relpath(abs_path, client.workspace_root),
        "total_symbols": len(symbols),
        "tree": formatted_tree,
        "raw_symbols": symbols,
    }

