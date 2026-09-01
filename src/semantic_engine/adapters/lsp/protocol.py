"""LSP protocol data structures and JSON-RPC message framing."""

from __future__ import annotations
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import unquote, urlparse


def path_to_uri(file_path: Union[str, Path]) -> str:
    """Convert a file system path to a standard file:// URI."""
    return Path(file_path).resolve().as_uri()


def uri_to_path(uri: str) -> str:
    """Convert a file:// URI to a local file system path."""
    parsed = urlparse(uri)
    return unquote(parsed.path)


def encode_jsonrpc_message(payload: Dict[str, Any]) -> bytes:
    """Encode a dictionary payload into a JSON-RPC wire-format byte string with Content-Length header."""
    body = json.dumps(payload, ensure_ascii=False)
    encoded_body = body.encode("utf-8")
    header = f"Content-Length: {len(encoded_body)}\r\n\r\n"
    return header.encode("ascii") + encoded_body


@dataclass
class Position:
    """Zero-indexed line and character offset in a text document."""
    line: int
    character: int

    def to_dict(self) -> Dict[str, int]:
        return {"line": self.line, "character": self.character}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Position:
        return cls(line=int(data["line"]), character=int(data["character"]))


@dataclass
class Range:
    """Range in a document expressed as start and end positions."""
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
    """Location inside a resource defined by URI and Range."""
    uri: str
    range: Range

    @property
    def file_path(self) -> str:
        return uri_to_path(self.uri)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Location:
        if "uri" in data:
            uri = data["uri"]
        elif "targetUri" in data:
            uri = data["targetUri"]
        else:
            uri = ""

        if "range" in data:
            range_obj = Range.from_dict(data["range"])
        elif "targetSelectionRange" in data:
            range_obj = Range.from_dict(data["targetSelectionRange"])
        elif "targetRange" in data:
            range_obj = Range.from_dict(data["targetRange"])
        else:
            range_obj = Range(Position(0, 0), Position(0, 0))

        return cls(uri=uri, range=range_obj)


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
        contents_raw = data.get("contents", "")
        if isinstance(contents_raw, str):
            contents = contents_raw
        elif isinstance(contents_raw, dict):
            contents = contents_raw.get("value", "")
        elif isinstance(contents_raw, list):
            parts = []
            for item in contents_raw:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(item.get("value", ""))
            contents = "\n".join(parts)
        else:
            contents = str(contents_raw)

        range_obj = Range.from_dict(data["range"]) if "range" in data and data["range"] else None
        return cls(contents=contents, range=range_obj)


@dataclass
class Diagnostic:
    """Diagnostic information (errors, warnings, lints)."""
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

