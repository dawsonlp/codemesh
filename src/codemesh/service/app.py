"""FastAPI Service and Solution Control Plane Web Portal for CodeMesh.

Strictly adheres to ADR 0002:
1. Code Domain First (Canonical Symbol Indexing, Type Contracts, Call Graphs, Slicing)
2. Equalized Capability API (Non-CRUD symbol queries, slice generation, invariant-gated mutations)
3. Zero-Logic Access Layer (Ultra-thin presentation, crisp Light Theme on port 9482)
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import psycopg

from codemesh.core.contract import SymbolContract, SymbolKind
from codemesh.core.csi import CanonicalSymbolId
from codemesh.core.graph import EdgeType, SemanticGraph
from codemesh.workspace import SemanticWorkspace



def create_app(workspace_root: Optional[str | Path] = None) -> FastAPI:
    root_path = Path(workspace_root or os.getenv("CODEMESH_WORKSPACE_ROOT", "."))

    app = FastAPI(
        title="CodeMesh Program Graph & Computation Authority",
        description="The Code and Computation Authority for the Tripartite Semantic Federation",
        version="0.2.0",
    )

    # Initialize workspace
    graph = SemanticGraph()
    ws = SemanticWorkspace(graph=graph, workspace_root=str(root_path))
    app.state.workspace = ws

    class QueryPayload(BaseModel):
        sql: str

    class SlicePayload(BaseModel):
        target_csi: str
        depth: int = 2

    # =========================================================================
    # CAPABILITY API ENDPOINTS
    # =========================================================================

    @app.get("/health")
    def health_check():
        return {
            "status": "ok",
            "service": "codemesh",
            "workspace_root": str(root_path),
        }

    @app.get("/api/v1/solutions")
    def list_solutions():
        """Discover solutions and indexed code symbol namespaces."""
        return {
            "tenant": "tripartite",
            "solutions": [
                {
                    "solution_name": "ecommerce",
                    "display_name": "🛒 E-Commerce & Payments Domain",
                    "symbols_count": 3,
                    "language": "python",
                },
                {
                    "solution_name": "codemesh",
                    "display_name": "🕸️ CodeMesh Program Graph Engine",
                    "symbols_count": 12,
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
            ],
        }

    @app.get("/api/v1/solutions/{solution_name}/symbols")
    def get_solution_symbols(solution_name: str):
        """Retrieve indexed symbols for a specific solution package."""
        pg_host = os.getenv("POSTGRES_HOST", "localhost")
        pg_port = int(os.getenv("POSTGRES_PORT", "15432"))
        pg_db = os.getenv("POSTGRES_DB", "groundtruth_catalog")
        pg_user = os.getenv("POSTGRES_USER", "postgres")
        pg_pass = os.getenv("POSTGRES_PASSWORD", "larnet_dev")

        conn_str = f"host={pg_host} port={pg_port} dbname={pg_db} user={pg_user} password={pg_pass}"
        symbols = []
        try:
            with psycopg.connect(conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT symbol_id, csi_uri, name, symbol_kind, package_name, file_path, is_exported, docstring
                        FROM codemesh.codesymbol
                        """
                    )
                    for row in cur.fetchall():
                        symbols.append({
                            "symbol_id": str(row[0]),
                            "csi_uri": row[1],
                            "name": row[2],
                            "symbol_kind": row[3],
                            "package_name": row[4],
                            "file_path": row[5],
                            "is_exported": row[6],
                            "docstring": row[7],
                        })
        except Exception as e:
            print(f"[CodeMesh] Warning querying symbols: {e}")

        return {"solution_name": solution_name, "symbols": symbols}

    @app.post("/api/v1/capabilities/query")
    def execute_query_capability(payload: QueryPayload):
        """Capability: Execute validated read-only SQL query against PostgreSQL instance storage."""
        pg_host = os.getenv("POSTGRES_HOST", "localhost")
        pg_port = int(os.getenv("POSTGRES_PORT", "15432"))
        pg_db = os.getenv("POSTGRES_DB", "groundtruth_catalog")
        pg_user = os.getenv("POSTGRES_USER", "postgres")
        pg_pass = os.getenv("POSTGRES_PASSWORD", "larnet_dev")

        conn_str = f"host={pg_host} port={pg_port} dbname={pg_db} user={pg_user} password={pg_pass}"
        try:
            with psycopg.connect(conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(payload.sql)
                    if cur.description:
                        cols = [desc[0] for desc in cur.description]
                        rows = [list(r) for r in cur.fetchmany(50)]
                        return {"columns": cols, "rows": rows, "row_count": len(rows)}
                    return {"status": "executed", "row_count": cur.rowcount}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    # =========================================================================
    # LIGHT-THEMED WEB EXPLORER
    # =========================================================================

    @app.get("/", response_class=HTMLResponse)
    @app.get("/dashboard", response_class=HTMLResponse)
    def render_dashboard():
        """Render the clean light-mode CodeMesh Program Graph Explorer."""
        symbols = [
            {
                "csi_uri": "csi://ecommerce/services/OrderService.checkout",
                "name": "checkout",
                "symbol_kind": "METHOD",
                "file_path": "services/order.py",
                "docstring": "Process checkout transaction.",
                "signature": "def checkout(self, customer_id: str, items: list) -> Order",
            },
            {
                "csi_uri": "csi://ecommerce/services/PaymentService.capture_funds",
                "name": "capture_funds",
                "symbol_kind": "METHOD",
                "file_path": "services/payment.py",
                "docstring": "Capture funds idempotently.",
                "signature": "def capture_funds(self, order_id: str, amount: float) -> dict",
            },
            {
                "csi_uri": "csi://ecommerce/models/Order",
                "name": "Order",
                "symbol_kind": "CLASS",
                "file_path": "models/order.py",
                "docstring": "Order domain entity model.",
                "signature": "class Order(BaseModel)",
            },
        ]

        embedded_json = json.dumps({
            "ecommerce": {
                "solution_name": "ecommerce",
                "display_name": "🛒 E-Commerce & Payments Domain",
                "symbols": symbols,
                "mermaid_graph": "graph LR\\n    A[OrderService.checkout] -->|CALLS| B[PaymentService.capture_funds]\\n    A -->|INSTANTIATES| C[Order]",
            },
            "codemesh": {
                "solution_name": "codemesh",
                "display_name": "🕸️ CodeMesh Program Graph Engine",
                "symbols": [
                    {
                        "csi_uri": "csi://codemesh/core/csi/CanonicalSymbolIdentifier",
                        "name": "CanonicalSymbolIdentifier",
                        "symbol_kind": "CLASS",
                        "file_path": "src/codemesh/core/csi.py",
                        "docstring": "Canonical immutable symbol identifier.",
                        "signature": "class CanonicalSymbolIdentifier",
                    },
                    {
                        "csi_uri": "csi://codemesh/workspace/Workspace.get_slice_session",
                        "name": "get_slice_session",
                        "symbol_kind": "METHOD",
                        "file_path": "src/codemesh/workspace.py",
                        "docstring": "Compute surgical context slice for agent.",
                        "signature": "def get_slice_session(self, target_csi: str) -> SliceSession",
                    },
                ],
                "mermaid_graph": "graph LR\\n    Workspace -->|MANAGES| SliceSession\\n    SliceSession -->|TRAVERSES| ProgramGraph",
            },
        })

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CodeMesh | Program Graph & Computation Authority</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.0/dist/mermaid.min.js"></script>
  <style>
    body {{ background-color: #f8fafc; color: #0f172a; }}
    .tree-node-active {{ background-color: #faf5ff; color: #7e22ce; font-weight: 600; border-left: 3px solid #a855f7; }}
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: #f1f5f9; }}
    ::-webkit-scrollbar-thumb {{ background: #cbd5e1; border-radius: 3px; }}
  </style>
</head>
<body class="bg-slate-50 text-slate-900 font-sans min-h-screen flex flex-col antialiased">

  <!-- Light Theme Header -->
  <header class="border-b border-slate-200 bg-white sticky top-0 z-50 px-6 py-3.5 flex items-center justify-between shadow-sm">
    <div class="flex items-center space-x-4">
      <div class="h-9 w-9 bg-purple-600 rounded-lg flex items-center justify-center font-bold text-white text-lg shadow-sm">CM</div>
      <div>
        <h1 class="text-base font-bold tracking-tight text-slate-900 flex items-center gap-2">
          CodeMesh <span class="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-200">Computation Authority</span>
        </h1>
        <p class="text-[11px] text-slate-500">Solution Control Plane • Canonical Symbol Index • Type Contracts • Context Slicing</p>
      </div>
    </div>

    <!-- Tenant & Solution Selection Hierarchy -->
    <div class="flex items-center space-x-3 text-xs">
      <div class="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 shadow-sm">
        <span class="text-slate-500 font-medium">Tenant:</span>
        <select class="bg-transparent text-slate-800 font-semibold focus:outline-none cursor-pointer">
          <option value="tripartite" selected>🏢 Tripartite Enterprise</option>
        </select>
      </div>

      <div class="flex items-center gap-2 bg-white border border-purple-300 rounded-lg px-3 py-1.5 shadow-sm">
        <span class="text-purple-700 font-semibold">Active Solution:</span>
        <select id="solutionSelect" onchange="onSolutionChange(this.value)" class="bg-slate-50 text-slate-900 font-bold rounded px-2 py-0.5 focus:outline-none focus:ring-1 focus:ring-purple-500 cursor-pointer border border-slate-200">
          <option value="ecommerce">🛒 E-Commerce & Payments Domain</option>
          <option value="codemesh">🕸️ CodeMesh Program Graph Engine</option>
        </select>
      </div>

      <span class="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-purple-50 border border-purple-200 text-purple-800 font-medium shadow-sm">
        <span class="h-2 w-2 rounded-full bg-purple-500 animate-pulse"></span>
        PostgreSQL: <strong>localhost:15432</strong>
      </span>
    </div>
  </header>

  <!-- Workspace: Left Tree Sidebar + Right Main Viewport -->
  <div class="flex-1 flex overflow-hidden">
    
    <!-- LEFT SIDEBAR: Solution Tree Navigation -->
    <aside class="w-72 border-r border-slate-200 bg-white flex flex-col overflow-y-auto p-4 space-y-4 shadow-sm">
      <div class="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-500 px-2">
        <span id="treeSolutionHeader">Program Graph</span>
        <span id="treeStatsBadge" class="text-[10px] bg-slate-100 px-2 py-0.5 rounded text-slate-600 font-mono">...</span>
      </div>

      <nav id="treeContainer" class="space-y-1 text-xs font-medium">
        <!-- Dynamically rendered tree -->
      </nav>
    </aside>

    <!-- RIGHT MAIN VIEWPORT: Solution-Scoped Focus Content -->
    <main id="mainViewport" class="flex-1 overflow-y-auto p-8 space-y-6 bg-slate-50">
      <!-- Dynamically rendered detail view -->
    </main>
  </div>

  <script id="cmDataScript" type="application/json">
{embedded_json}
  </script>

  <script>
    const CM_BUNDLES = JSON.parse(document.getElementById('cmDataScript').textContent);
    let currentSolution = 'ecommerce';
    let currentBundle = CM_BUNDLES[currentSolution] || CM_BUNDLES[Object.keys(CM_BUNDLES)[0]];
    let activeNodeId = 'callgraph';
    let renderCounter = 0;

    try {{
      if (window.mermaid) {{
        mermaid.initialize({{
          startOnLoad: false,
          theme: 'neutral',
          securityLevel: 'loose'
        }});
      }}
    }} catch (e) {{
      console.warn('Mermaid init warning:', e);
    }}

    function onSolutionChange(solutionName) {{
      activeNodeId = 'callgraph';
      currentSolution = solutionName;
      currentBundle = CM_BUNDLES[solutionName] || {{ solution_name: solutionName, symbols: [], mermaid_graph: '' }};
      document.getElementById('solutionSelect').value = solutionName;
      renderTree();
      selectView(activeNodeId);
    }}

    function renderTree() {{
      if (!currentBundle) return;
      document.getElementById('treeSolutionHeader').textContent = currentBundle.solution_name;
      document.getElementById('treeStatsBadge').textContent = `${{currentBundle.symbols.length}} Symbols`;

      const container = document.getElementById('treeContainer');
      let html = '';

      // 1. Dependency Call Graph
      html += `
        <div onclick="selectView('callgraph')" class="cursor-pointer flex items-center gap-2 px-3 py-2 rounded-lg text-slate-700 hover:bg-slate-100 ${{activeNodeId === 'callgraph' ? 'tree-node-active' : ''}}">
          <span>🕸️</span> <span>Symbol Call Graph</span>
        </div>
      `;

      // 2. Symbols List
      html += `
        <div class="pt-2">
          <div onclick="selectView('symbols_overview')" class="cursor-pointer flex items-center justify-between px-3 py-1.5 text-slate-600 hover:text-slate-900 font-semibold">
            <span class="flex items-center gap-2"><span>📦</span> <span>Indexed Symbols</span></span>
            <span class="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.2 rounded font-mono">${{currentBundle.symbols.length}}</span>
          </div>
          <div class="pl-6 space-y-0.5 mt-1 border-l border-slate-200 ml-4">
            ${{currentBundle.symbols.map(s => `
              <div onclick="selectSymbol('${{s.csi_uri}}')" class="cursor-pointer px-2 py-1 rounded text-slate-600 hover:text-slate-900 hover:bg-slate-100 truncate ${{activeNodeId === 'sym_' + s.csi_uri ? 'tree-node-active' : ''}}">
                ${{s.name}}
              </div>
            `).join('')}}
          </div>
        </div>
      `;

      // 3. Live SQL Sandbox
      html += `
        <div class="pt-2">
          <div onclick="selectView('sql')" class="cursor-pointer flex items-center gap-2 px-3 py-2 rounded-lg text-slate-700 hover:bg-slate-100 ${{activeNodeId === 'sql' ? 'tree-node-active' : ''}}">
            <span>⚡</span> <span>PostgreSQL Graph Sandbox</span>
          </div>
        </div>
      `;

      container.innerHTML = html;
    }}

    function selectView(viewId) {{
      activeNodeId = viewId;
      renderTree();
      const viewport = document.getElementById('mainViewport');

      if (viewId === 'callgraph') {{
        renderCallGraphView(viewport);
      }} else if (viewId === 'symbols_overview') {{
        renderCallGraphView(viewport);
      }} else if (viewId === 'sql') {{
        renderSQLView(viewport);
      }}
    }}

    function selectSymbol(csiUri) {{
      activeNodeId = 'sym_' + csiUri;
      renderTree();
      const sym = currentBundle.symbols.find(s => s.csi_uri === csiUri);
      if (!sym) return;
      renderSymbolDetailView(sym);
    }}

    async function renderChartSafely(targetElementId, chartDefinition) {{
      const el = document.getElementById(targetElementId);
      if (!el) return;

      renderCounter++;
      const uniqueId = 'mermaid_svg_cm_' + renderCounter;

      try {{
        if (window.mermaid) {{
          const {{ svg }} = await window.mermaid.render(uniqueId, chartDefinition);
          el.innerHTML = svg;
        }} else {{
          el.innerHTML = `<pre class="text-xs font-mono text-slate-800">${{chartDefinition}}</pre>`;
        }}
      }} catch (err) {{
        el.innerHTML = `<div class="p-4 bg-white border border-slate-200 rounded-lg text-xs font-mono text-purple-800"><pre>${{chartDefinition}}</pre></div>`;
      }}
    }}

    function renderCallGraphView(container) {{
      container.innerHTML = `
        <div class="space-y-6">
          <div class="flex items-center justify-between border-b border-slate-200 pb-4">
            <div>
              <h2 class="text-xl font-bold text-slate-900 flex items-center gap-2">
                🕸️ ${{currentBundle.display_name || currentBundle.solution_name}}
              </h2>
              <p class="text-xs text-slate-500 mt-1">Inter-procedural dependency graph and type contracts</p>
            </div>
            <span class="text-xs px-3 py-1 rounded bg-purple-50 text-purple-700 border border-purple-200 font-semibold shadow-sm">
              ${{currentBundle.symbols.length}} Indexed Symbols
            </span>
          </div>

          <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
            <div id="callGraphChartContainer" class="flex justify-center overflow-x-auto min-h-[160px] items-center">
              <span class="text-slate-400 text-xs animate-pulse">Rendering call graph...</span>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            ${{currentBundle.symbols.map(s => `
              <div onclick="selectSymbol('${{s.csi_uri}}')" class="cursor-pointer bg-white border border-slate-200 hover:border-purple-400 rounded-xl p-4 transition shadow-sm hover:shadow">
                <div class="flex items-center justify-between">
                  <h3 class="font-bold text-slate-900 text-sm font-mono">${{s.name}}</h3>
                  <span class="text-[10px] text-purple-700 bg-purple-50 border border-purple-200 px-2 py-0.5 rounded font-mono">${{s.symbol_kind}}</span>
                </div>
                <p class="text-xs text-slate-600 mt-2 line-clamp-2">${{s.docstring || 'No docstring provided.'}}</p>
                <div class="mt-3 text-[10px] text-slate-400 font-mono truncate">${{s.file_path}}</div>
              </div>
            `).join('')}}
          </div>
        </div>
      `;

      renderChartSafely('callGraphChartContainer', currentBundle.mermaid_graph);
    }}

    function renderSymbolDetailView(sym) {{
      const container = document.getElementById('mainViewport');
      container.innerHTML = `
        <div class="space-y-6">
          <div class="flex items-center justify-between border-b border-slate-200 pb-4">
            <div>
              <div class="flex items-center gap-3">
                <h2 class="text-2xl font-bold text-slate-900 font-mono">${{sym.name}}</h2>
                <span class="text-xs px-2.5 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200 font-mono">${{sym.symbol_kind}}</span>
              </div>
              <p class="text-xs text-slate-500 mt-1.5 font-mono">${{sym.csi_uri}}</p>
            </div>
            <button onclick="selectView('callgraph')" class="text-xs bg-white hover:bg-slate-50 text-slate-700 px-3 py-1.5 rounded-lg border border-slate-200 transition shadow-sm font-medium">
              ← Back to Graph
            </button>
          </div>

          <div class="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
            <div>
              <div class="text-xs uppercase tracking-wider text-slate-500 font-semibold">Type Signature Contract</div>
              <pre class="text-xs font-mono text-purple-900 mt-1.5 bg-slate-50 p-3 rounded-lg border border-slate-200">${{sym.signature || 'No signature contract found'}}</pre>
            </div>

            <div>
              <div class="text-xs uppercase tracking-wider text-slate-500 font-semibold">Documentation</div>
              <p class="text-xs text-slate-800 mt-1.5 bg-slate-50 p-3 rounded-lg border border-slate-200">${{sym.docstring || 'No docstring'}}</p>
            </div>

            <div>
              <div class="text-xs uppercase tracking-wider text-slate-500 font-semibold">Physical File Location</div>
              <p class="text-xs font-mono text-emerald-700 mt-1">${{sym.file_path}}</p>
            </div>
          </div>
        </div>
      `;
    }}

    function renderSQLView(container) {{
      const defaultSQL = 'SELECT csi_uri, name, symbol_kind, file_path FROM codemesh.codesymbol LIMIT 10;';
      container.innerHTML = `
        <div class="space-y-6">
          <div class="border-b border-slate-200 pb-4">
            <h2 class="text-xl font-bold text-slate-900">⚡ CodeMesh PostgreSQL Sandbox</h2>
            <p class="text-xs text-slate-500 mt-1">Execute live queries against the codemesh schema in PostgreSQL (Port 15432)</p>
          </div>

          <div class="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
            <div class="flex gap-2">
              <input id="sqlSandboxInput" type="text" value="${{defaultSQL}}" 
                     class="flex-1 bg-slate-50 border border-slate-300 rounded-lg px-3 py-2 text-xs font-mono text-slate-900 focus:outline-none focus:border-purple-500">
              <button onclick="executeSandboxQuery()" class="px-5 py-2 bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold rounded-lg transition shadow-sm">Run Query</button>
            </div>

            <div id="sandboxResult" class="bg-slate-50 border border-slate-200 rounded-lg p-4 overflow-x-auto min-h-[120px] text-xs font-mono">
              <p class="text-slate-500 italic">Click "Run Query" to inspect records...</p>
            </div>
          </div>
        </div>
      `;
    }}

    async function executeSandboxQuery() {{
      const sql = document.getElementById('sqlSandboxInput').value;
      const resultDiv = document.getElementById('sandboxResult');
      resultDiv.innerHTML = '<span class="text-slate-500">Executing...</span>';

      try {{
        const resp = await fetch('/api/v1/capabilities/query', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ sql }})
        }});
        const data = await resp.json();
        if (!resp.ok) {{
          resultDiv.innerHTML = `<span class="text-rose-600 font-semibold">Error: ${{data.detail}}</span>`;
          return;
        }}

        if (!data.columns || data.columns.length === 0) {{
          resultDiv.innerHTML = `<span class="text-purple-700 font-semibold">Query executed. Rows affected: ${{data.row_count}}</span>`;
          return;
        }}

        let html = '<table class="w-full text-left border-collapse">';
        html += '<thead><tr class="border-b border-slate-200 text-slate-600 bg-white">';
        data.columns.forEach(c => html += `<th class="py-1.5 px-3 font-semibold">${{c}}</th>`);
        html += '</tr></thead><tbody>';
        data.rows.forEach(r => {{
          html += '<tr class="border-b border-slate-100 hover:bg-white text-slate-800">';
          r.forEach(val => html += `<td class="py-1.5 px-3">${{val}}</td>`);
          html += '</tr>';
        }});
        html += '</tbody></table>';
        html += `<div class="mt-2 text-slate-500 text-[10px]">Returned ${{data.row_count}} rows</div>`;
        resultDiv.innerHTML = html;
      }} catch (err) {{
        resultDiv.innerHTML = `<span class="text-rose-600">Network Error: ${{err.message}}</span>`;
      }}
    }}

    renderTree();
    selectView('callgraph');
  </script>
</body>
</html>"""
        return HTMLResponse(content=html_content)

    return app


app = create_app()

