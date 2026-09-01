"""Asynchronous LSP Client implementation over stdio."""

from __future__ import annotations
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from .protocol import (
    Diagnostic,
    Hover,
    Location,
    Position,
    Range,
    SymbolInformation,
    encode_jsonrpc_message,
    path_to_uri,
    uri_to_path,
)

logger = logging.getLogger("lsp_client")


class LspClient:
    """Async client managing Language Server subprocess and JSON-RPC protocol."""

    def __init__(
        self,
        server_command: Optional[List[str]] = None,
        workspace_root: Optional[Union[str, Path]] = None,
    ) -> None:
        if server_command is None:
            # Default to local venv pyright-langserver or global command
            venv_pyright = os.path.abspath(".venv/bin/pyright-langserver")
            if os.path.exists(venv_pyright):
                server_command = [venv_pyright, "--stdio"]
            else:
                server_command = ["pyright-langserver", "--stdio"]

        self.server_command = server_command
        self.workspace_root = os.path.abspath(workspace_root or os.getcwd())
        self.process: Optional[asyncio.subprocess.Process] = None
        self._reader_task: Optional[asyncio.Task[None]] = None

        self._request_id = 0
        self._pending_requests: Dict[int, asyncio.Future[Any]] = {}
        self._open_documents: Dict[str, int] = {}  # uri -> version
        self._diagnostics: Dict[str, List[Diagnostic]] = {}  # uri -> list of diagnostics
        self._notification_handlers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self.server_capabilities: Dict[str, Any] = {}

    async def __aenter__(self) -> LspClient:
        await self.start()
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.stop()

    async def start(self) -> None:
        """Start the language server subprocess and begin background message loop."""
        if self.process is not None:
            return

        logger.info(f"Spawning LSP server: {' '.join(self.server_command)} in {self.workspace_root}")
        self.process = await asyncio.create_subprocess_exec(
            *self.server_command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.workspace_root,
        )

        self._reader_task = asyncio.create_task(self._read_messages())
        asyncio.create_task(self._log_stderr())

    async def stop(self) -> None:
        """Gracefully shutdown and terminate the language server process."""
        if self.process is None:
            return

        try:
            await self.send_request("shutdown", {}, timeout=3.0)
            await self.send_notification("exit", {})
        except Exception as e:
            logger.debug(f"Error during graceful shutdown: {e}")

        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()

        if self.process.returncode is None:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=2.0)
            except Exception:
                self.process.kill()

        self.process = None

    async def _log_stderr(self) -> None:
        """Read and log stderr output from the server process."""
        if not self.process or not self.process.stderr:
            return
        while True:
            line = await self.process.stderr.readline()
            if not line:
                break
            logger.debug(f"[LSP stderr] {line.decode('utf-8', errors='replace').rstrip()}")

    async def _read_messages(self) -> None:
        """Message loop reading framed JSON-RPC packets from server stdout."""
        if not self.process or not self.process.stdout:
            return

        reader = self.process.stdout
        while True:
            try:
                # Read headers until empty line \r\n
                content_length = 0
                while True:
                    line = await reader.readline()
                    if not line:
                        logger.info("LSP server closed stdout.")
                        return
                    line_str = line.decode("ascii", errors="replace").strip()
                    if not line_str:
                        break
                    if line_str.lower().startswith("content-length:"):
                        content_length = int(line_str.split(":", 1)[1].strip())

                if content_length == 0:
                    continue

                # Read body of exact content_length
                body_bytes = await reader.readexactly(content_length)
                message = json.loads(body_bytes.decode("utf-8"))
                self._dispatch_message(message)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error reading LSP message: {e}", exc_info=True)
                break

    def _dispatch_message(self, message: Dict[str, Any]) -> None:
        """Route incoming JSON-RPC responses and notifications."""
        if "id" in message and ("result" in message or "error" in message):
            msg_id = message["id"]
            if msg_id in self._pending_requests:
                future = self._pending_requests.pop(msg_id)
                if not future.done():
                    if "error" in message and message["error"] is not None:
                        err = message["error"]
                        future.set_exception(RuntimeError(f"LSP error {err.get('code')}: {err.get('message')}"))
                    else:
                        future.set_result(message.get("result"))
        elif "method" in message:
            method = message["method"]
            params = message.get("params", {})
            self._handle_notification(method, params)

    def _handle_notification(self, method: str, params: Dict[str, Any]) -> None:
        """Handle server-initiated notifications such as diagnostics."""
        if method == "textDocument/publishDiagnostics":
            uri = params.get("uri", "")
            raw_diags = params.get("diagnostics", [])
            self._diagnostics[uri] = [Diagnostic.from_dict(d) for d in raw_diags]

        # Call custom handlers
        if method in self._notification_handlers:
            for handler in self._notification_handlers[method]:
                try:
                    handler(params)
                except Exception as e:
                    logger.error(f"Handler error for {method}: {e}")

    def on_notification(self, method: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback handler for server notifications."""
        self._notification_handlers.setdefault(method, []).append(handler)

    async def send_notification(self, method: str, params: Dict[str, Any]) -> None:
        """Send a notification (no response expected) to the language server."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("LSP server is not running")

        payload = {"jsonrpc": "2.0", "method": method, "params": params}
        encoded = encode_jsonrpc_message(payload)
        self.process.stdin.write(encoded)
        await self.process.stdin.drain()

    async def send_request(self, method: str, params: Dict[str, Any], timeout: float = 10.0) -> Any:
        """Send a request to the server and await matching response."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("LSP server is not running")

        self._request_id += 1
        req_id = self._request_id
        future: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        self._pending_requests[req_id] = future

        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        }
        encoded = encode_jsonrpc_message(payload)
        self.process.stdin.write(encoded)
        await self.process.stdin.drain()

        return await asyncio.wait_for(future, timeout=timeout)

    # ------------------ High-Level LSP API ------------------

    async def initialize(self) -> Dict[str, Any]:
        """Perform LSP handshake (initialize & initialized)."""
        root_uri = path_to_uri(self.workspace_root)
        params = {
            "processId": os.getpid(),
            "rootUri": root_uri,
            "rootPath": self.workspace_root,
            "workspaceFolders": [{"name": os.path.basename(self.workspace_root), "uri": root_uri}],
            "capabilities": {
                "textDocument": {
                    "synchronization": {
                        "dynamicRegistration": False,
                        "willSave": False,
                        "willSaveWaitUntil": False,
                        "didSave": True,
                    },
                    "hover": {"contentFormat": ["markdown", "plaintext"]},
                    "definition": {"linkSupport": True},
                    "references": {"dynamicRegistration": False},
                    "documentSymbol": {"hierarchicalDocumentSymbolSupport": True},
                    "typeDefinition": {"linkSupport": True},
                    "implementation": {"linkSupport": True},
                    "publishDiagnostics": {"relatedInformation": True},
                },
                "workspace": {
                    "symbol": {"symbolKind": {"valueSet": list(range(1, 27))}},
                    "workspaceFolders": True,
                },
            },
            "initializationOptions": {},
        }
        result = await self.send_request("initialize", params)
        self.server_capabilities = result.get("capabilities", {})
        await self.send_notification("initialized", {})
        return result

    async def open_document(
        self,
        file_path: Union[str, Path],
        text: Optional[str] = None,
        language_id: str = "python",
    ) -> str:
        """Open a file document with the language server via didOpen."""
        abs_path = os.path.abspath(file_path)
        uri = path_to_uri(abs_path)

        if text is None:
            with open(abs_path, "r", encoding="utf-8") as f:
                text = f.read()

        version = self._open_documents.get(uri, 0) + 1
        self._open_documents[uri] = version

        params = {
            "textDocument": {
                "uri": uri,
                "languageId": language_id,
                "version": version,
                "text": text,
            }
        }
        await self.send_notification("textDocument/didOpen", params)
        return uri

    async def ensure_document_open(self, file_path: Union[str, Path]) -> str:
        """Ensure that the given file is registered as open."""
        uri = path_to_uri(file_path)
        if uri not in self._open_documents:
            await self.open_document(file_path)
        return uri

    async def close_document(self, file_path: Union[str, Path]) -> None:
        """Notify server that document is closed."""
        uri = path_to_uri(file_path)
        if uri in self._open_documents:
            del self._open_documents[uri]
            params = {"textDocument": {"uri": uri}}
            await self.send_notification("textDocument/didClose", params)

    async def get_definition(
        self,
        file_path: Union[str, Path],
        line: int,
        character: int,
    ) -> List[Location]:
        """Find definition locations for symbol at (line, character) (0-indexed)."""
        uri = await self.ensure_document_open(file_path)
        params = {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
        }
        result = await self.send_request("textDocument/definition", params)
        if not result:
            return []
        if isinstance(result, dict):
            return [Location.from_dict(result)]
        return [Location.from_dict(loc) for loc in result]

    async def get_references(
        self,
        file_path: Union[str, Path],
        line: int,
        character: int,
        include_declaration: bool = True,
    ) -> List[Location]:
        """Find all references across the workspace for symbol at (line, character)."""
        uri = await self.ensure_document_open(file_path)
        params = {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
            "context": {"includeDeclaration": include_declaration},
        }
        result = await self.send_request("textDocument/references", params)
        if not result:
            return []
        return [Location.from_dict(loc) for loc in result]

    async def get_hover(
        self,
        file_path: Union[str, Path],
        line: int,
        character: int,
    ) -> Optional[Hover]:
        """Get type signature and docstrings at (line, character)."""
        uri = await self.ensure_document_open(file_path)
        params = {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
        }
        result = await self.send_request("textDocument/hover", params)
        if not result or not result.get("contents"):
            return None
        return Hover.from_dict(result)

    async def get_document_symbols(
        self,
        file_path: Union[str, Path],
    ) -> List[SymbolInformation]:
        """Retrieve symbol outline (classes, methods, functions) for a file."""
        uri = await self.ensure_document_open(file_path)
        params = {"textDocument": {"uri": uri}}
        result = await self.send_request("textDocument/documentSymbol", params)
        if not result:
            return []
        return [SymbolInformation.from_dict(item, default_uri=uri) for item in result]

    async def get_workspace_symbols(
        self,
        query: str,
    ) -> List[SymbolInformation]:
        """Search for symbols across the entire workspace by name query."""
        params = {"query": query}
        result = await self.send_request("workspace/symbol", params)
        if not result:
            return []
        return [SymbolInformation.from_dict(item) for item in result]

    async def get_type_definition(
        self,
        file_path: Union[str, Path],
        line: int,
        character: int,
    ) -> List[Location]:
        """Resolve the type definition for symbol at (line, character)."""
        uri = await self.ensure_document_open(file_path)
        params = {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": character},
        }
        result = await self.send_request("textDocument/typeDefinition", params)
        if not result:
            return []
        if isinstance(result, dict):
            return [Location.from_dict(result)]
        return [Location.from_dict(loc) for loc in result]

    def get_diagnostics(self, file_path: Union[str, Path]) -> List[Diagnostic]:
        """Return cached diagnostics received from language server for a given file."""
        uri = path_to_uri(file_path)
        return self._diagnostics.get(uri, [])

