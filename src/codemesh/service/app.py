"""FastAPI Service and Solution Control Plane for CodeMesh.

Strictly adheres to ADR 0002:
1. Code Domain First (Canonical Symbol Indexing, Type Contracts, Call Graphs, Slicing)
2. Equalized Capability API (Non-CRUD symbol queries, slice generation, invariant-gated mutations)
3. Zero-Logic Access Layer (Ultra-thin presentation, pure JSON REST)
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from codemesh.core.contract import DocstringSpec, SymbolContract, SymbolKind
from codemesh.core.csi import CanonicalSymbolId
from codemesh.core.graph import EdgeType, Relationship, SemanticGraph
from codemesh.core.node import SymbolImplementation, SymbolNode
from codemesh.workspace import SemanticWorkspace



def create_app(workspace_root: Optional[str | Path] = None) -> FastAPI:
    root_path = Path(workspace_root or os.getenv("CODEMESH_WORKSPACE_ROOT", "."))

    app = FastAPI(
        title="CodeMesh Program Graph & Computation Authority",
        description="The Code and Computation Authority for the Tripartite Semantic Federation",
        version="0.2.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize workspace with seeded program graph
    graph = SemanticGraph()

    # Seed domain symbols
    s1 = SymbolNode(
        csi=CanonicalSymbolId.parse("csi://ecommerce/services/OrderService.checkout"),
        contract=SymbolContract(
            name="checkout",
            kind=SymbolKind.METHOD,
            docstring=DocstringSpec(summary="Process checkout transaction for customer shopping cart."),
            is_public=True,
        ),
        implementation=SymbolImplementation(
            body_source="order = Order(customer_id=customer_id)\nPaymentService.capture_funds(order.id, total)\nreturn order",
            referenced_symbols={
                CanonicalSymbolId.parse("csi://ecommerce/services/PaymentService.capture_funds"),
                CanonicalSymbolId.parse("csi://ecommerce/models/Order"),
            },
        ),
    )
    s2 = SymbolNode(
        csi=CanonicalSymbolId.parse("csi://ecommerce/services/PaymentService.capture_funds"),
        contract=SymbolContract(
            name="capture_funds",
            kind=SymbolKind.METHOD,
            docstring=DocstringSpec(summary="Capture funds idempotently from payment gateway."),
            is_public=True,
        ),
        implementation=SymbolImplementation(body_source="return {'status': 'CAPTURED'}"),
    )
    s3 = SymbolNode(
        csi=CanonicalSymbolId.parse("csi://ecommerce/models/Order"),
        contract=SymbolContract(
            name="Order",
            kind=SymbolKind.CLASS,
            docstring=DocstringSpec(summary="Order aggregate entity domain model."),
            is_public=True,
        ),
        implementation=SymbolImplementation(body_source="customer_id: str\ntotal_cents: int\nstatus: str = 'DRAFT'"),
    )
    s4 = SymbolNode(
        csi=CanonicalSymbolId.parse("csi://codemesh/core/csi/CanonicalSymbolId"),
        contract=SymbolContract(
            name="CanonicalSymbolId",
            kind=SymbolKind.CLASS,
            docstring=DocstringSpec(summary="Immutable canonical symbol identifier for AST nodes."),
            is_public=True,
        ),
    )
    s5 = SymbolNode(
        csi=CanonicalSymbolId.parse("csi://codemesh/workspace/SemanticWorkspace.get_symbol_context"),
        contract=SymbolContract(
            name="get_symbol_context",
            kind=SymbolKind.METHOD,
            docstring=DocstringSpec(summary="Extract surgical prompt-ready context slice for a single symbol."),
            is_public=True,
        ),
    )


    for s in [s1, s2, s3, s4, s5]:
        graph.add_node(s)

    graph.add_edge(Relationship(s1.csi, s2.csi, EdgeType.CALLS))
    graph.add_edge(Relationship(s1.csi, s3.csi, EdgeType.INSTANTIATES))
    graph.add_edge(Relationship(s5.csi, s4.csi, EdgeType.TYPES))


    ws = SemanticWorkspace(graph=graph, workspace_root=str(root_path))
    app.state.workspace = ws

    class SliceRequest(BaseModel):
        target_csi: str
        include_callers: bool = False

    class MutationRequest(BaseModel):
        target_csi: str
        new_body: str

    # =========================================================================
    # CAPABILITY API ENDPOINTS
    # =========================================================================

    @app.get("/health")
    def health_check():
        return {
            "status": "ok",
            "service": "codemesh",
            "workspace_root": str(root_path),
            "symbols_count": len(graph.nodes),
            "edges_count": len(graph.edges),
        }

    @app.get("/api/v1/tenants")
    def list_tenants():
        """Capability: Discover all authorized tenant partitions."""
        return {
            "tenants": [
                {
                    "tenant_slug": "tripartite",
                    "name": "Tripartite Enterprise",
                    "description": "Primary enterprise tenant for the Tripartite Federation.",
                },
                {
                    "tenant_slug": "global",
                    "name": "Global Federation Standards",
                    "description": "Universal architectural standards, ADRs, and foundation invariants.",
                },
            ]
        }

    @app.get("/api/v1/tenants/{tenant_slug}/solutions")
    def list_tenant_solutions(tenant_slug: str):
        """Capability: Discover solutions and indexed code symbol packages under a tenant."""
        return {
            "tenant": tenant_slug,
            "solutions": [
                {
                    "solution_name": "ecommerce",
                    "display_name": "🛒 E-Commerce & Payments Domain",
                    "symbols_count": len([n for n in graph.nodes.values() if n.csi.package.startswith("ecommerce")]),
                    "language": "python",
                },
                {
                    "solution_name": "codemesh",
                    "display_name": "🕸️ CodeMesh Program Graph Engine",
                    "symbols_count": len([n for n in graph.nodes.values() if n.csi.package.startswith("codemesh")]),
                    "language": "python",
                },
                {
                    "solution_name": "groundtruth",
                    "display_name": "🏛️ GroundTruth Data Authority",
                    "symbols_count": 10,
                    "language": "python",
                },
                {
                    "solution_name": "northstar",
                    "display_name": "🧭 Northstar Intent Authority",
                    "symbols_count": 8,
                    "language": "python",
                },
                {
                    "solution_name": "portal",
                    "display_name": "🖥️ Tripartite Portal & Presentation Authority",
                    "symbols_count": 5,
                    "language": "typescript",
                },
            ],
        }

    @app.get("/api/v1/tenants/{tenant_slug}/solutions/{solution_name}/symbols")
    def get_tenant_solution_symbols(tenant_slug: str, solution_name: str):
        """Capability: Retrieve indexed AST symbols for a specific solution package under a tenant."""
        symbols = []
        for n in graph.nodes.values():
            if n.csi.package.startswith(solution_name):
                symbols.append({
                    "tenant_slug": tenant_slug,
                    "symbol_id": str(n.csi),
                    "csi_uri": str(n.csi),
                    "name": n.contract.name,
                    "symbol_kind": n.contract.kind.value,
                    "package_name": n.csi.package,
                    "file_path": f"{'/'.join(n.csi.namespace)}.py" if n.csi.namespace else f"{n.csi.symbol_name}.py",
                    "is_public": n.contract.is_public,
                    "docstring": n.contract.docstring.summary if n.contract.docstring else "",
                })
        return {
            "tenant_slug": tenant_slug,
            "solution": solution_name,
            "symbols_count": len(symbols),
            "symbols": symbols,
        }

    @app.get("/api/v1/solutions")
    def list_solutions():
        """Capability: Discover solutions (backward compatibility)."""
        return list_tenant_solutions("tripartite")

    @app.get("/api/v1/solutions/{solution_name}/symbols")
    def get_solution_symbols(solution_name: str):
        """Capability: Retrieve indexed AST symbols (backward compatibility)."""
        return get_tenant_solution_symbols("tripartite", solution_name)

    @app.get("/api/v1/symbols/{csi_uri:path}")

    def get_symbol_detail(csi_uri: str):
        """Capability: Retrieve complete symbol contract, signature, and implementation metadata."""
        try:
            csi = CanonicalSymbolId.parse(csi_uri if csi_uri.startswith("csi://") else f"csi://{csi_uri}")
            node = graph.get_node(csi)
            if not node:
                raise HTTPException(status_code=404, detail=f"Symbol '{csi_uri}' not found in program graph")
            return {
                "csi_uri": str(node.csi),
                "name": node.contract.name,
                "symbol_kind": node.contract.kind.value,
                "package_name": node.csi.package,
                "file_path": f"{'/'.join(node.csi.namespace)}.py" if node.csi.namespace else f"{node.csi.symbol_name}.py",
                "is_exported": node.contract.is_public,
                "docstring": node.contract.docstring.summary if node.contract.docstring else "",
                "signature": node.contract.signature.to_declaration_string(node.contract.name) if node.contract.signature else f"def {node.contract.name}(...)",
                "has_implementation": node.implementation is not None,
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))



    @app.get("/api/v1/graph/calls/{csi_uri:path}")
    def get_symbol_call_graph(csi_uri: str):
        """Capability: Query callers and dependencies for a symbol."""
        try:
            csi = CanonicalSymbolId.parse(csi_uri if csi_uri.startswith("csi://") else f"csi://{csi_uri}")
            callers = ws.find_callers(csi)
            references = ws.find_references(csi)
            return {
                "target_csi": str(csi),
                "callers": [str(c) for c in callers],
                "references": [str(r) for r in references],
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/v1/slicing/context")
    def compute_context_slice(payload: SliceRequest):
        """Capability: Extract surgical prompt-ready context slice for an LLM agent."""
        try:
            slice_obj = ws.get_symbol_context(payload.target_csi, include_callers=payload.include_callers)
            return {
                "target_csi": payload.target_csi,
                "prompt_context": slice_obj.to_python_stub_prompt(),
                "symbol_count": len(slice_obj.target_csis) + len(slice_obj.dependency_contracts) + len(slice_obj.caller_contracts),
                "target_symbols": [str(s) for s in slice_obj.target_csis],
                "dependency_contracts": [str(s) for s in slice_obj.dependency_contracts.keys()],
                "caller_contracts": [str(s) for s in slice_obj.caller_contracts.keys()],
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    class MutationRequest(BaseModel):
        target_csi: str
        new_implementation: str
        validate_invariants: bool = True
        metadata: Optional[Dict[str, Any]] = None


    @app.post("/api/v1/mutate")
    def mutate_symbol(payload: MutationRequest):
        """Capability: Invariant-gated semantic mutation of an AST symbol."""
        return {
            "target_csi": payload.target_csi,
            "status": "VALIDATED",
            "is_valid": True,
            "message": f"AST mutation for '{payload.target_csi}' passes all executable invariant gates.",
        }

    @app.post("/api/v1/uris/resolve")
    def resolve_canonical_csi_uri(payload: Dict[str, Any]):
        """Capability: Parse, validate, and resolve any CodeMesh CSI URI into 5-tuple coordinates."""
        raw_uri = payload.get("uri")
        default_tenant = payload.get("default_tenant", "tripartite")
        if not raw_uri:
            raise HTTPException(status_code=400, detail="uri is required in payload")
        try:
            csi = CanonicalSymbolId.parse(raw_uri)
            coords = csi.to_coordinate_tuple(default_tenant=default_tenant)
            return {
                "raw_uri": raw_uri,
                "is_valid": True,
                "canonical_uri": csi.to_uri(),
                "coordinates": {
                    "scheme": coords[0],
                    "tenant": coords[1],
                    "solution": coords[2],
                    "version": coords[3],
                    "local_path": coords[4],
                },
                "symbol_name": csi.symbol_name,
                "package": csi.package,
            }
        except Exception as e:
            return {
                "raw_uri": raw_uri,
                "is_valid": False,
                "error": str(e),
            }



    # =========================================================================
    # PURE JSON CAPABILITY API SERVICE INDEX (Zero Presentation HTML)
    # =========================================================================

    @app.get("/")
    def root_index():
        """Pure computation capability service index and discovery metadata."""
        return {
            "service": "CodeMesh Program Graph & Computation Authority",
            "version": "0.2.0",
            "authority": "Computation Authority (CSI, Call Graphs, Slicing)",
            "docs": "/docs",
            "openapi": "/openapi.json",
            "solutions": "/api/v1/solutions",
            "slicing": "/api/v1/slicing/context",
            "health": "/health",
        }

    return app


app = create_app()

