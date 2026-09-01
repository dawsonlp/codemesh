"""Canonical Symbol Identifiers (CSI) for file-independent symbol addressing."""

from __future__ import annotations
from dataclasses import dataclass
import re
from typing import Optional, Tuple
from urllib.parse import urlparse


@dataclass(frozen=True)
class CanonicalSymbolId:
    """Unique, persistent, file-independent identifier for any code symbol.

    Format: csi://<package>/<namespace_path>/<symbol_name>[.<member>][(<signature>)][#<fragment>]
    Examples:
      - csi://sample_project/services/OrderService.create_order#user_id
      - csi://com.example.store/services/OrderService.findOrders(String,int)
      - csi://com.example.store/services/OrderService.findOrders(UUID)#frag
    """
    package: str
    namespace: Tuple[str, ...]
    symbol_name: str
    member_path: Tuple[str, ...] = ()
    signature_spec: Optional[Tuple[str, ...]] = None
    fragment: Optional[str] = None

    @classmethod
    def from_parts(
        cls,
        package: str,
        namespace: Tuple[str, ...] | list[str] | str,
        symbol_name: str,
        member_path: Tuple[str, ...] | list[str] | str = (),
        signature_spec: Optional[Tuple[str, ...] | list[str] | str] = None,
        fragment: Optional[str] = None,
    ) -> CanonicalSymbolId:
        if isinstance(namespace, str):
            ns_tuple = tuple(p for p in namespace.strip("/").split("/") if p)
        else:
            ns_tuple = tuple(namespace)

        if isinstance(member_path, str):
            mem_tuple = tuple(m for m in member_path.split(".") if m)
        else:
            mem_tuple = tuple(member_path)

        if signature_spec is not None:
            if isinstance(signature_spec, str):
                sig_cleaned = signature_spec.strip("()")
                sig_tuple = tuple(s.strip() for s in sig_cleaned.split(",") if s.strip()) if sig_cleaned else ()
            else:
                sig_tuple = tuple(signature_spec)
        else:
            sig_tuple = None

        return cls(
            package=package,
            namespace=ns_tuple,
            symbol_name=symbol_name,
            member_path=mem_tuple,
            signature_spec=sig_tuple,
            fragment=fragment,
        )

    @classmethod
    def parse(cls, uri_string: str) -> CanonicalSymbolId:
        """Parse a csi:// URI string into a CanonicalSymbolId."""
        parsed = urlparse(uri_string)
        if parsed.scheme != "csi":
            raise ValueError(f"Invalid CSI scheme '{parsed.scheme}': expected 'csi://'")

        package = parsed.netloc
        if not package:
            raise ValueError(f"CSI URI missing package name in netloc: '{uri_string}'")

        path = parsed.path.strip("/")
        if not path:
            return cls(package=package, namespace=(), symbol_name="")

        # Extract optional signature_spec in parentheses, e.g. OrderService.findOrders(String,int)
        sig_tuple: Optional[Tuple[str, ...]] = None
        sig_match = re.search(r"\(([^)]*)\)$", path)
        if sig_match:
            sig_content = sig_match.group(1).strip()
            sig_tuple = tuple(s.strip() for s in sig_content.split(",") if s.strip())
            path = path[: sig_match.start()]

        parts = path.split("/")
        if len(parts) == 1:
            full_symbol = parts[0]
            ns_tuple: Tuple[str, ...] = ()
        else:
            ns_tuple = tuple(parts[:-1])
            full_symbol = parts[-1]

        symbol_parts = full_symbol.split(".")
        symbol_name = symbol_parts[0]
        member_path = tuple(symbol_parts[1:]) if len(symbol_parts) > 1 else ()

        return cls(
            package=package,
            namespace=ns_tuple,
            symbol_name=symbol_name,
            member_path=member_path,
            signature_spec=sig_tuple,
            fragment=parsed.fragment or None,
        )

    @property
    def qualified_name(self) -> str:
        """Dot-separated fully qualified name (e.g., sample_project.services.OrderService.create_order)."""
        components = [self.package]
        components.extend(self.namespace)
        if self.symbol_name:
            components.append(self.symbol_name)
        components.extend(self.member_path)
        base = ".".join(components)
        if self.signature_spec is not None:
            base += f"({','.join(self.signature_spec)})"
        return base

    @property
    def parent_csi(self) -> Optional[CanonicalSymbolId]:
        """Return the parent CSI in the symbol hierarchy."""
        if self.fragment:
            return CanonicalSymbolId(
                package=self.package,
                namespace=self.namespace,
                symbol_name=self.symbol_name,
                member_path=self.member_path,
                signature_spec=self.signature_spec,
                fragment=None,
            )
        if self.signature_spec is not None:
            return CanonicalSymbolId(
                package=self.package,
                namespace=self.namespace,
                symbol_name=self.symbol_name,
                member_path=self.member_path,
                signature_spec=None,
                fragment=None,
            )
        if self.member_path:
            return CanonicalSymbolId(
                package=self.package,
                namespace=self.namespace,
                symbol_name=self.symbol_name,
                member_path=self.member_path[:-1],
                signature_spec=None,
                fragment=None,
            )
        if self.symbol_name and self.namespace:
            return CanonicalSymbolId(
                package=self.package,
                namespace=self.namespace[:-1],
                symbol_name=self.namespace[-1],
                member_path=(),
                signature_spec=None,
                fragment=None,
            )
        return None

    def child(self, member_name: str) -> CanonicalSymbolId:
        """Create a child member CSI (e.g., a method on a class)."""
        return CanonicalSymbolId(
            package=self.package,
            namespace=self.namespace,
            symbol_name=self.symbol_name,
            member_path=self.member_path + (member_name,),
            signature_spec=None,
            fragment=None,
        )

    def with_signature(self, signature_spec: Tuple[str, ...] | list[str] | str) -> CanonicalSymbolId:
        """Return a copy of this CSI with an overload signature specification."""
        if isinstance(signature_spec, str):
            sig_cleaned = signature_spec.strip("()")
            sig_tuple = tuple(s.strip() for s in sig_cleaned.split(",") if s.strip()) if sig_cleaned else ()
        else:
            sig_tuple = tuple(signature_spec)
        return CanonicalSymbolId(
            package=self.package,
            namespace=self.namespace,
            symbol_name=self.symbol_name,
            member_path=self.member_path,
            signature_spec=sig_tuple,
            fragment=self.fragment,
        )

    def without_signature(self) -> CanonicalSymbolId:
        """Return a bare copy of this CSI representing the symbol group / overload set."""
        return CanonicalSymbolId(
            package=self.package,
            namespace=self.namespace,
            symbol_name=self.symbol_name,
            member_path=self.member_path,
            signature_spec=None,
            fragment=self.fragment,
        )

    def with_fragment(self, fragment: str) -> CanonicalSymbolId:
        """Return a copy of this CSI targeting a sub-element (e.g. parameter)."""
        return CanonicalSymbolId(
            package=self.package,
            namespace=self.namespace,
            symbol_name=self.symbol_name,
            member_path=self.member_path,
            signature_spec=self.signature_spec,
            fragment=fragment,
        )

    def without_fragment(self) -> CanonicalSymbolId:
        """Return a copy of this CSI with fragment removed."""
        return CanonicalSymbolId(
            package=self.package,
            namespace=self.namespace,
            symbol_name=self.symbol_name,
            member_path=self.member_path,
            signature_spec=self.signature_spec,
            fragment=None,
        )

    def is_descendant_of(self, ancestor: CanonicalSymbolId) -> bool:
        """Check if this CSI is a member or sub-namespace of the given ancestor."""
        if self.package != ancestor.package:
            return False
        # Check namespace prefix
        if len(self.namespace) < len(ancestor.namespace):
            return False
        if self.namespace[: len(ancestor.namespace)] != ancestor.namespace:
            return False
        if ancestor.symbol_name:
            if self.symbol_name != ancestor.symbol_name:
                return False
            if len(self.member_path) < len(ancestor.member_path):
                return False
            if self.member_path[: len(ancestor.member_path)] != ancestor.member_path:
                return False
            if ancestor.signature_spec is not None:
                if self.signature_spec != ancestor.signature_spec:
                    return False
        return True

    def __str__(self) -> str:
        ns_str = "/".join(self.namespace)
        if ns_str:
            base_path = f"{ns_str}/{self.symbol_name}" if self.symbol_name else ns_str
        else:
            base_path = self.symbol_name

        if self.member_path:
            base_path = f"{base_path}.{'.'.join(self.member_path)}"

        if self.signature_spec is not None:
            base_path = f"{base_path}({','.join(self.signature_spec)})"

        uri = f"csi://{self.package}/{base_path}" if base_path else f"csi://{self.package}"
        if self.fragment:
            uri = f"{uri}#{self.fragment}"
        return uri

