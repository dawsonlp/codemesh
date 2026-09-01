"""LSP data structures, JSON-RPC message framing, and URI utilities."""

from __future__ import annotations
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import unquote, urlparse
from urllib.request import pathname2url


def path_to_uri(file_path: Union[str, Path]) -> str:
    """Convert an absolute or relative file path to a valid file:// URI."""
    return Path(file_path).resolve().as_uri()


def uri_to_path(uri: str) -> str:
    """Convert a file:// URI to a local file system path."""
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        return uri
    # Unquote url encoded characters
    path = unquote(parsed.path)
    return path


def encode_jsonrpc_message(payload: Dict[str, Any]) -> bytes:
    """Encode a JSON-RPC dictionary into LSP framed bytes with Content-Length header."""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    return header + body


@dataclass
class Position:
    """Zero-based line and character offset in a document."""
    line: int
    character: int

    def to_dict(self) -> Dict[str, int]:
        return {"line": self.line, "character": self.character}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Position:
        return cls(line=int(data["line"]), character=int(data["character"]))

    def __str__(self) -> str:
        # User-friendly 1-based display
        return f"{self.line + 1}:{self.character + 1} (0-indexed: {self.line}:{self.character})"


@dataclass
class Range:
    """A range in a text document expressed as (start, end) positions."""
    start: Position
    end: Position

    def to_dict(self) -> Dict[str, Any]:
        return {"start": self.start.to_dict(), "end": self.end.to_dict()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Range:
        return cls(
            start=Position.from_dict(data["start"]),
            end=Position.from_dict(data["end"]),
        )


@dataclass
class Location:
    """Represents a location inside a resource, such as a line inside a text file."""
    uri: str
    range: Range

    @property
    def file_path(self) -> str:
        return uri_to_path(self.uri)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Location:
        uri = data.get("uri") or data.get("targetUri", "")
        range_data = data.get("range") or data.get("targetSelectionRange") or data.get("targetRange", {})
        return cls(
            uri=uri,
            range=Range.from_dict(range_data),
        )


@dataclass
class SymbolInformation:
    """Symbol information returned by document or workspace symbol queries."""
    name: str
    kind: int
    location: Location
    container_name: Optional[str] = None
    children: List[SymbolInformation] = field(default_factory=list)
    full_range: Optional[Range] = None
    selection_range: Optional[Range] = None

    @property
    def kind_name(self) -> str:
        # Standard LSP SymbolKind mapping
        kinds = {
            1: "File", 2: "Module", 3: "Namespace", 4: "Package", 5: "Class",
            6: "Method", 7: "Property", 8: "Field", 9: "Constructor", 10: "Enum",
            11: "Interface", 12: "Function", 13: "Variable", 14: "Constant",
            15: "String", 16: "Number", 17: "Boolean", 18: "Array", 19: "Object",
            20: "Key", 21: "Null", 22: "EnumMember", 23: "Struct", 24: "Event",
            25: "Operator", 26: "TypeParameter",
        }
        return kinds.get(self.kind, f"Unknown({self.kind})")

    @classmethod
    def from_dict(cls, data: Dict[str, Any], default_uri: str = "") -> SymbolInformation:
        name = data.get("name", "")
        kind = int(data.get("kind", 0))
        container = data.get("containerName")

        full_range = Range.from_dict(data["range"]) if "range" in data else None
        selection_range = Range.from_dict(data["selectionRange"]) if "selectionRange" in data else full_range

        if "location" in data:
            location = Location.from_dict(data["location"])
        elif selection_range:
            location = Location(uri=default_uri, range=selection_range)
        else:
            location = Location(uri=default_uri, range=Range(Position(0, 0), Position(0, 0)))

        children_data = data.get("children", [])
        children = [cls.from_dict(child, default_uri=default_uri) for child in children_data]

        return cls(
            name=name,
            kind=kind,
            location=location,
            container_name=container,
            children=children,
            full_range=full_range,
            selection_range=selection_range,
        )


DocumentSymbol = SymbolInformation


@dataclass
class Hover:
    """Hover information result."""
    contents: str
    range: Optional[Range] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Hover:
        raw_contents = data.get("contents", "")
        if isinstance(raw_contents, dict):
            contents = raw_contents.get("value", "")
        elif isinstance(raw_contents, list):
            items = []
            for item in raw_contents:
                if isinstance(item, dict):
                    items.append(item.get("value", ""))
                else:
                    items.append(str(item))
            contents = "\n\n".join(items)
        else:
            contents = str(raw_contents)

        rng = Range.from_dict(data["range"]) if "range" in data and data["range"] else None
        return cls(contents=contents, range=rng)


@dataclass
class Diagnostic:
    """Diagnostic information (error, warning, hint) published by language server."""
    range: Range
    message: str
    severity: int = 1  # 1: Error, 2: Warning, 3: Info, 4: Hint
    source: Optional[str] = None
    code: Optional[Union[int, str]] = None

    @property
    def severity_name(self) -> str:
        names = {1: "Error", 2: "Warning", 3: "Information", 4: "Hint"}
        return names.get(self.severity, "Unknown")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Diagnostic:
        return cls(
            range=Range.from_dict(data["range"]),
            message=data.get("message", ""),
            severity=int(data.get("severity", 1)),
            source=data.get("source"),
            code=data.get("code"),
        )
