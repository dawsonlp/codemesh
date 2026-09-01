"""Symbol nodes and executable leaf implementations."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Set
from semantic_engine.core.contract import SymbolContract, TypeRef
from semantic_engine.core.csi import CanonicalSymbolId


@dataclass
class LocalVariable:
    """Local variable or temporary binding inside an implementation."""
    name: str
    type_ref: Optional[TypeRef] = None


@dataclass
class SymbolImplementation:
    """Executable leaf body and internal semantic bindings."""
    body_source: str
    referenced_symbols: Set[CanonicalSymbolId] = field(default_factory=set)
    local_variables: List[LocalVariable] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not bool(self.body_source and self.body_source.strip())


@dataclass
class SymbolNode:
    """A complete semantic entity possessing a contract and optional implementation."""
    csi: CanonicalSymbolId
    contract: SymbolContract
    implementation: Optional[SymbolImplementation] = None
    is_foreign: bool = False  # True for standard library or external package symbols
    children: List[CanonicalSymbolId] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.contract.name

    @property
    def kind(self) -> str:
        return self.contract.kind.value

