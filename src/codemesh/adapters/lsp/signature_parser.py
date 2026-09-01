"""Parses raw LSP hover markdown and signature strings into structured SymbolContracts."""

from __future__ import annotations
import re
from typing import Dict, List, Optional, Tuple
from codemesh.core.contract import (
    DocstringSpec,
    ExecutionModel,
    FunctionSignature,
    Parameter,
    ParameterKind,
    PurityType,
    SymbolContract,
    SymbolKind,
    TypeRef,
)


class SignatureParser:
    """Extracts structured contracts and docstrings from LSP markdown hover contents."""

    KIND_MAP: Dict[str, SymbolKind] = {
        "class": SymbolKind.CLASS,
        "method": SymbolKind.METHOD,
        "function": SymbolKind.FUNCTION,
        "variable": SymbolKind.VARIABLE,
        "field": SymbolKind.FIELD,
        "property": SymbolKind.PROPERTY,
        "enum": SymbolKind.ENUM,
        "module": SymbolKind.MODULE,
        "interface": SymbolKind.INTERFACE,
    }

    @classmethod
    def parse_hover_markdown(cls, hover_content: str, default_name: str = "") -> SymbolContract:
        """Parse complete markdown hover string into a SymbolContract."""
        if not hover_content or not hover_content.strip():
            return SymbolContract(name=default_name, kind=SymbolKind.VARIABLE)

        # 1. Extract code block and docstring section
        code_block = ""
        docstring_text = ""

        code_match = re.search(r"```(?:python)?\s*\n(.*?)\n```", hover_content, re.DOTALL)
        if code_match:
            code_block = code_match.group(1).strip()
            # Everything after the code block (skipping horizontal rule '---') is docstring
            after_code = hover_content[code_match.end() :].strip()
            docstring_text = re.sub(r"^\s*---\s*", "", after_code).strip()
        else:
            docstring_text = hover_content.strip()

        # 2. Extract Kind and Signature from code block
        kind, name, signature, is_async = cls._parse_code_header(code_block, default_name)

        # 3. Parse Docstring sections (Summary, Args, Returns, Raises)
        doc_spec = cls._parse_docstring(docstring_text)

        execution_model = ExecutionModel.ASYNC_EVENT_LOOP if is_async else ExecutionModel.SYNC_BLOCKING

        return SymbolContract(
            name=name,
            kind=kind,
            signature=signature,
            docstring=doc_spec,
            purity=PurityType.PURE if kind == SymbolKind.FUNCTION and not is_async else PurityType.MUTATES_LOCAL,
            execution_model=execution_model,
        )

    @classmethod
    def _parse_code_header(
        cls,
        code_block: str,
        default_name: str,
    ) -> Tuple[SymbolKind, str, Optional[FunctionSignature], bool]:
        """Parse language server signature header like '(method) def create_order(...) -> Order'."""
        if not code_block:
            return SymbolKind.VARIABLE, default_name, None, False

        kind = SymbolKind.VARIABLE
        name = default_name
        is_async = "async def " in code_block

        # Check for (kind) prefix e.g. "(method) def func(..." or "(class) Order"
        kind_match = re.match(r"^\((\w+)\)\s*(.*)", code_block, re.DOTALL)
        remainder = code_block
        if kind_match:
            kind_str = kind_match.group(1).lower()
            kind = cls.KIND_MAP.get(kind_str, SymbolKind.VARIABLE)
            remainder = kind_match.group(2).strip()

        # If it's a function or method definition
        if "def " in remainder:
            if kind == SymbolKind.VARIABLE:
                kind = SymbolKind.FUNCTION
            sig, parsed_name = cls._parse_callable_signature(remainder)
            if parsed_name:
                name = parsed_name
            return kind, name, sig, is_async

        if "class " in remainder:
            kind = SymbolKind.CLASS
            class_match = re.match(r"^class\s+([A-Za-z0-9_]+)", remainder)
            if class_match:
                name = class_match.group(1)
            return kind, name, None, False

        return kind, name, None, False

    @classmethod
    def _parse_callable_signature(cls, text: str) -> Tuple[Optional[FunctionSignature], Optional[str]]:
        """Parse callable signature into parameters and return type."""
        cleaned = re.sub(r"^(?:async\s+)?def\s+", "", text).strip()
        match = re.match(r"^([A-Za-z0-9_]+)\s*\((.*?)\)(?:\s*->\s*(.+?))?(?::)?$", cleaned, re.DOTALL)
        if not match:
            return None, None

        func_name = match.group(1)
        params_raw = match.group(2).strip()
        return_type_raw = (match.group(3) or "None").strip()

        params: List[Parameter] = []
        if params_raw:
            for param_str in cls._split_params(params_raw):
                p = cls._parse_single_parameter(param_str)
                if p:
                    if p.name == "self" or p.name == "cls":
                        continue
                    params.append(p)

        return (
            FunctionSignature(
                parameters=params,
                return_type=TypeRef(return_type_raw),
            ),
            func_name,
        )

    @classmethod
    def _split_params(cls, params_str: str) -> List[str]:
        """Split parameter list on comma, respecting nested brackets and parentheses."""
        items: List[str] = []
        current: List[str] = []
        depth = 0
        for char in params_str:
            if char in "([{<":
                depth += 1
                current.append(char)
            elif char in ")]}>":
                depth -= 1
                current.append(char)
            elif char == "," and depth == 0:
                item = "".join(current).strip()
                if item:
                    items.append(item)
                current = []
            else:
                current.append(char)
        if current:
            item = "".join(current).strip()
            if item:
                items.append(item)
        return items

    @classmethod
    def _parse_single_parameter(cls, param_text: str) -> Optional[Parameter]:
        param_text = param_text.strip()
        if not param_text or param_text in ("/", "*"):
            return None

        kind = ParameterKind.POSITIONAL_OR_KEYWORD
        if param_text.startswith("**"):
            kind = ParameterKind.VAR_KEYWORD
            param_text = param_text[2:]
        elif param_text.startswith("*"):
            kind = ParameterKind.VAR_POSITIONAL
            param_text = param_text[1:]

        # Split default value
        default_val = None
        if "=" in param_text:
            parts = param_text.split("=", 1)
            param_text = parts[0].strip()
            default_val = parts[1].strip()

        # Split name and type annotation
        if ":" in param_text:
            name, type_str = param_text.split(":", 1)
            name = name.strip()
            type_str = type_str.strip()
        else:
            name = param_text.strip()
            type_str = "Any"

        return Parameter(
            name=name,
            type_ref=TypeRef(type_str),
            kind=kind,
            default_value_expression=default_val,
        )

    @classmethod
    def _parse_docstring(cls, docstring_text: str) -> DocstringSpec:
        """Parse structured docstrings (Google/Sphinx style summary, args, returns, raises)."""
        if not docstring_text:
            return DocstringSpec()

        cleaned = docstring_text.replace(r"\_", "_").replace("&nbsp;", " ")
        lines = [line.rstrip() for line in cleaned.split("\n")]
        summary = lines[0] if lines else ""
        description_lines: List[str] = []
        params_doc: Dict[str, str] = {}
        returns_doc: Optional[str] = None
        raises_doc: Dict[str, str] = {}

        current_section = "desc"

        for line in lines[1:]:
            line_str = line.strip()
            if not line_str:
                continue

            lower = line_str.lower()
            if lower.startswith("args:") or lower.startswith("parameters:"):
                current_section = "args"
                continue
            elif lower.startswith("returns:") or lower.startswith("return:"):
                current_section = "returns"
                continue
            elif lower.startswith("raises:"):
                current_section = "raises"
                continue

            if current_section == "desc":
                description_lines.append(line_str)
            elif current_section == "args":
                param_match = re.match(r"^([A-Za-z0-9_]+)\s*:\s*(.*)", line_str)
                if param_match:
                    params_doc[param_match.group(1)] = param_match.group(2)
            elif current_section == "returns":
                returns_doc = line_str if not returns_doc else f"{returns_doc} {line_str}"
            elif current_section == "raises":
                raises_match = re.match(r"^([A-Za-z0-9_]+)\s*:\s*(.*)", line_str)
                if raises_match:
                    raises_doc[raises_match.group(1)] = raises_match.group(2)

        return DocstringSpec(
            summary=summary,
            description=" ".join(description_lines).strip(),
            parameters_doc=params_doc,
            returns_doc=returns_doc,
            raises_doc=raises_doc,
        )

