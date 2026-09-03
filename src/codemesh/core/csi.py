"""Canonical Symbol Identifiers (CSI) for file-independent symbol addressing under Option B.

Format: csi://[tenant:][package]/<namespace_path>/<symbol_name>[.<member>][(<signature>)][@version][#fragment]
"""

from __future__ import annotations
from dataclasses import dataclass
import re
from typing import Optional, Tuple


OPTION_B_CSI_PATTERN = re.compile(
    r"^csi://"
    r"(?:(?P<tenant>[a-z0-9_-]+):)?"
    r"(?P<package>[a-zA-Z0-9_.-]+)"
    r"(?:/(?P<path>[^@#\s]+))?"
    r"(?:@(?P<version>[a-zA-Z0-9_.-]+))?"
    r"(?:#(?P<fragment>[a-zA-Z0-9_.-]+))?$"
)


@dataclass(frozen=True)
class CanonicalSymbolId:
    """Unique, persistent, file-independent identifier for any code symbol."""
    package: str
    namespace: Tuple[str, ...]
    symbol_name: str
    member_path: Tuple[str, ...] = ()
    signature_spec: Optional[Tuple[str, ...]] = None
    tenant: Optional[str] = None
    version: Optional[str] = None
    fragment: Optional[str] = None

    @classmethod
    def from_parts(
        cls,
        package: str,
        namespace: Tuple[str, ...] | list[str] | str,
        symbol_name: str,
        member_path: Tuple[str, ...] | list[str] | str = (),
        signature_spec: Optional[Tuple[str, ...] | list[str] | str] = None,
        tenant: Optional[str] = None,
        version: Optional[str] = None,
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
            tenant=tenant,
            version=version,
            fragment=fragment,
        )

    @classmethod
    def parse(cls, uri_string: str) -> CanonicalSymbolId:
        """Parse an Option B or standard csi:// URI string into a CanonicalSymbolId."""
        match = OPTION_B_CSI_PATTERN.match(uri_string.strip())
        if not match:
            raise ValueError(f"Invalid CSI scheme or format: '{uri_string}'")

        tenant = match.group("tenant")
        package = match.group("package")
        raw_path = match.group("path") or ""
        version = match.group("version")
        fragment = match.group("fragment")

        if not raw_path:
            return cls(
                package=package,
                namespace=(),
                symbol_name="",
                tenant=tenant,
                version=version,
                fragment=fragment,
            )

        # Extract optional signature_spec in parentheses
        sig_tuple: Optional[Tuple[str, ...]] = None
        sig_match = re.search(r"\(([^)]*)\)$", raw_path)
        if sig_match:
            sig_content = sig_match.group(1).strip()
            sig_tuple = tuple(s.strip() for s in sig_content.split(",") if s.strip()) if sig_content else ()
            raw_path = raw_path[: sig_match.start()]

        parts = [p for p in raw_path.split("/") if p]
        if len(parts) == 0:
            ns_tuple = ()
            symbol_name = ""
            member_path = ()
        elif len(parts) == 1:
            full_symbol = parts[0]
            ns_tuple = ()
            symbol_parts = full_symbol.split(".")
            symbol_name = symbol_parts[0]
            member_path = tuple(symbol_parts[1:]) if len(symbol_parts) > 1 else ()
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
            tenant=tenant,
            version=version,
            fragment=fragment,
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
                tenant=self.tenant,
                version=self.version,
                fragment=None,
            )
        if self.signature_spec is not None:
            return CanonicalSymbolId(
                package=self.package,
                namespace=self.namespace,
                symbol_name=self.symbol_name,
                member_path=self.member_path,
                signature_spec=None,
                tenant=self.tenant,
                version=self.version,
                fragment=None,
            )
        if self.member_path:
            return CanonicalSymbolId(
                package=self.package,
                namespace=self.namespace,
                symbol_name=self.symbol_name,
                member_path=self.member_path[:-1],
                signature_spec=None,
                tenant=self.tenant,
                version=self.version,
                fragment=None,
            )
        if self.symbol_name and self.namespace:
            return CanonicalSymbolId(
                package=self.package,
                namespace=self.namespace[:-1],
                symbol_name=self.namespace[-1],
                member_path=(),
                signature_spec=None,
                tenant=self.tenant,
                version=self.version,
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
            tenant=self.tenant,
            version=self.version,
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
            tenant=self.tenant,
            version=self.version,
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
            tenant=self.tenant,
            version=self.version,
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
            tenant=self.tenant,
            version=self.version,
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
            tenant=self.tenant,
            version=self.version,
            fragment=None,
        )

    def is_descendant_of(self, ancestor: CanonicalSymbolId) -> bool:
        """Check if this CSI is a member or sub-namespace of the given ancestor."""
        if self.package != ancestor.package:
            return False
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

    def to_canonical(self, default_tenant: str = "tripartite", default_version: Optional[str] = None) -> str:
        """Render fully qualified Option B canonical CSI."""
        tenant_prefix = f"{self.tenant or default_tenant}:"
        base = self.__str_scoped__()
        body = base[len("csi://"):]
        ver_part = f"@{self.version}" if self.version else (f"@{default_version}" if default_version else "")
        frag_part = f"#{self.fragment}" if self.fragment else ""
        return f"csi://{tenant_prefix}{body}{ver_part}{frag_part}"

    def to_coordinate_tuple(self, default_tenant: str = "tripartite") -> Tuple[str, str, str, str, str]:
        """Return 5-tuple: (scheme, tenant, solution, version, qualified_name)."""
        tenant_val = self.tenant or default_tenant
        version_val = self.version or "latest"
        return ("csi", tenant_val, self.package, version_val, self.qualified_name)

    def __str_scoped__(self) -> str:
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

    def to_coordinate_tuple(self, default_tenant: str = "tripartite") -> Tuple[str, str, str, str, str]:
        """Return 5-tuple: (scheme, tenant, solution, version, path)."""
        tenant_val = self.tenant or default_tenant
        sol_val = self.package
        version_val = self.version or "latest"
        path_parts = list(self.namespace) + ([self.symbol_name] if self.symbol_name else []) + list(self.member_path)
        path_val = "/".join(path_parts)
        return ("csi", tenant_val, sol_val, version_val, path_val)

    def to_uri(self) -> str:
        """Serialize this CSI to a canonical URI string."""
        tenant_part = f"{self.tenant}:" if self.tenant else ""
        ns_str = "/".join(self.namespace)
        symbol_str = self.symbol_name
        if self.member_path:
            symbol_str += f".{'.'.join(self.member_path)}"
        path_components = [self.package]
        if ns_str:
            path_components.append(ns_str)
        if symbol_str:
            path_components.append(symbol_str)
        uri = f"csi://{tenant_part}{'/'.join(path_components)}"
        if self.signature_spec is not None:
            uri += f"({','.join(self.signature_spec)})"
        if self.version:
            uri += f"@{self.version}"
        if self.fragment:
            uri += f"#{self.fragment}"
        return uri

    def __str__(self) -> str:
        if self.tenant or self.version:
            tenant_part = f"{self.tenant}:" if self.tenant else ""
            ns_str = "/".join(self.namespace)
            if ns_str:
                base_path = f"{ns_str}/{self.symbol_name}" if self.symbol_name else ns_str
            else:
                base_path = self.symbol_name
            if self.member_path:
                base_path = f"{base_path}.{'.'.join(self.member_path)}"
            if self.signature_spec is not None:
                base_path = f"{base_path}({','.join(self.signature_spec)})"
            ver_part = f"@{self.version}" if self.version else ""
            frag_part = f"#{self.fragment}" if self.fragment else ""
            return f"csi://{tenant_part}{self.package}/{base_path}{ver_part}{frag_part}"
        return self.__str_scoped__()
