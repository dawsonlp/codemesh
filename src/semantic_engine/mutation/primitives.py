"""Semantic mutation primitives for structured program edits."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from semantic_engine.core.contract import SymbolContract
from semantic_engine.core.csi import CanonicalSymbolId
from semantic_engine.core.node import SymbolImplementation


class SemanticMutation:
    """Base class for all structured semantic modification commands."""
    pass


@dataclass
class AddSymbolMutation(SemanticMutation):
    parent_csi: CanonicalSymbolId
    contract: SymbolContract
    implementation: Optional[SymbolImplementation] = None


@dataclass
class ReplaceImplementationMutation(SemanticMutation):
    target_csi: CanonicalSymbolId
    new_body_source: str


@dataclass
class UpdateContractMutation(SemanticMutation):
    target_csi: CanonicalSymbolId
    new_contract: SymbolContract


@dataclass
class RenameSymbolMutation(SemanticMutation):
    target_csi: CanonicalSymbolId
    new_name: str


@dataclass
class DeleteSymbolMutation(SemanticMutation):
    target_csi: CanonicalSymbolId


@dataclass
class MutationResult:
    """Outcome of an atomic semantic mutation operation."""
    success: bool
    target_csi: CanonicalSymbolId
    error_message: Optional[str] = None
    blast_radius: Optional[object] = None  # BlastRadiusReport
    materialized_files: list[str] = field(default_factory=list)

