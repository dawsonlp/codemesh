"""Symbol contracts, typed signatures, docstrings, and execution archetypes."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
from semantic_engine.core.csi import CanonicalSymbolId


class SymbolKind(str, Enum):
    """Semantic category of a code symbol."""
    MODULE = "module"
    NAMESPACE = "namespace"
    CLASS = "class"
    INTERFACE = "interface"        # Protocol, abstract class, or interface trait
    FUNCTION = "function"
    METHOD = "method"
    PROPERTY = "property"
    FIELD = "field"
    ENUM = "enum"
    ENUM_MEMBER = "enum_member"
    TYPE_ALIAS = "type_alias"
    CONSTANT = "constant"
    VARIABLE = "variable"


class ParameterKind(str, Enum):
    """Parameter passing convention."""
    POSITIONAL_ONLY = "positional_only"
    POSITIONAL_OR_KEYWORD = "positional_or_keyword"
    VAR_POSITIONAL = "var_positional"     # e.g., *args
    KEYWORD_ONLY = "keyword_only"
    VAR_KEYWORD = "var_keyword"           # e.g., **kwargs


class PurityType(str, Enum):
    """Operational purity and side-effect guarantees."""
    PURE = "pure"                             # Deterministic, referentially transparent
    READ_ONLY = "read_only"                   # Reads system/instance state; zero side effects
    MUTATES_LOCAL = "mutates_local"           # Modifies self/instance state only
    MUTATES_SHARED = "mutates_shared"         # Modifies global, database, or shared state
    IO_EFFECTFUL = "io_effectful"             # Network, disk, or external environment I/O


class ExecutionModel(str, Enum):
    """Execution concurrency and threading topology."""
    SYNC_BLOCKING = "sync_blocking"
    ASYNC_EVENT_LOOP = "async_event_loop"
    PARALLEL_WORKER = "parallel_worker"
    TRANSACTIONAL = "transactional"


@dataclass
class TypeRef:
    """Type reference, optionally resolved to a known CanonicalSymbolId."""
    raw_type_string: str
    resolved_csi: Optional[CanonicalSymbolId] = None
    type_arguments: List[TypeRef] = field(default_factory=list)
    is_optional: bool = False

    def to_display_string(self) -> str:
        if self.type_arguments:
            args_str = ", ".join(arg.to_display_string() for arg in self.type_arguments)
            base = f"{self.raw_type_string}[{args_str}]"
        else:
            base = self.raw_type_string
        return f"Optional[{base}]" if self.is_optional and not base.startswith("Optional") else base

    def __str__(self) -> str:
        return self.to_display_string()


@dataclass
class Parameter:
    """Declared parameter in a function or method signature."""
    name: str
    type_ref: TypeRef
    kind: ParameterKind = ParameterKind.POSITIONAL_OR_KEYWORD
    default_value_expression: Optional[str] = None
    docstring: Optional[str] = None

    def to_signature_string(self) -> str:
        prefix = ""
        if self.kind == ParameterKind.VAR_POSITIONAL:
            prefix = "*"
        elif self.kind == ParameterKind.VAR_KEYWORD:
            prefix = "**"

        out = f"{prefix}{self.name}: {self.type_ref.to_display_string()}"
        if self.default_value_expression is not None:
            out += f" = {self.default_value_expression}"
        return out


@dataclass
class FunctionSignature:
    """Structured callable signature."""
    parameters: List[Parameter] = field(default_factory=list)
    return_type: TypeRef = field(default_factory=lambda: TypeRef("None"))
    type_parameters: List[str] = field(default_factory=list)  # Generics, e.g. [T, U]

    def to_declaration_string(self, function_name: str, is_async: bool = False) -> str:
        async_prefix = "async " if is_async else ""
        params_str = ", ".join(p.to_signature_string() for p in self.parameters)
        return f"{async_prefix}def {function_name}({params_str}) -> {self.return_type.to_display_string()}:"


@dataclass
class DocstringSpec:
    """Structured documentation specification."""
    summary: str = ""
    description: str = ""
    parameters_doc: Dict[str, str] = field(default_factory=dict)
    returns_doc: Optional[str] = None
    raises_doc: Dict[str, str] = field(default_factory=dict)

    def to_markdown(self) -> str:
        lines = []
        if self.summary:
            lines.append(self.summary)
        if self.description:
            lines.append("\n" + self.description)
        if self.parameters_doc:
            lines.append("\n**Parameters:**")
            for name, desc in self.parameters_doc.items():
                lines.append(f"- `{name}`: {desc}")
        if self.returns_doc:
            lines.append(f"\n**Returns:** {self.returns_doc}")
        if self.raises_doc:
            lines.append("\n**Raises:**")
            for exc, desc in self.raises_doc.items():
                lines.append(f"- `{exc}`: {desc}")
        return "\n".join(lines).strip()


@dataclass
class SymbolContract:
    """Public semantic contract and invariant specification of a symbol."""
    name: str
    kind: SymbolKind
    signature: Optional[FunctionSignature] = None
    docstring: DocstringSpec = field(default_factory=DocstringSpec)
    purity: PurityType = PurityType.PURE
    execution_model: ExecutionModel = ExecutionModel.SYNC_BLOCKING
    declared_exceptions: List[TypeRef] = field(default_factory=list)
    base_types: List[TypeRef] = field(default_factory=list)  # Inherited classes / protocols
    type_variables: List[str] = field(default_factory=list)  # Generic type parameters
    is_public: bool = True

