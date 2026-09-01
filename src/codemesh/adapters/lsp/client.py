"""Asynchronous LSP Client implementation over stdio."""

from __future__ import annotations
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from codemesh.adapters.lsp.protocol import (
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

logger = logging.getLogger("codemesh.lsp_client")


class LspClient:
    """Asynchronous client that communicates with an LSP server over stdio."""

    def __init__(
        self,
        command: Optional[List[str]] = None,
        workspace_root: Optional[Union[str, Path]] = None,
        timeout: float = 10.0,
    ) -> None:
        if command is None:
            venv_bin = Path(__file__).resolve().parents[4] / ".venv" / "bin" / "pyright-langserver"
            if venv_bin.exists():
                command = [str(venv_bin), "--stdio"]
            else:
                command = ["pyright-langserver", "--stdio"]

        self.command = command
        self.workspace_root = str(Path(workspace_root or ".").resolve())
        self.timeout = timeout

        self.process: Optional[asyncio.subprocess.Process] = None
        self._reader_task: Optional[asyncio.Task] = None
        self._request_id = 0
        self._pending_requests: Dict[int, asyncio.Future[Any]] = {}
        self._notification_handlers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self.diagnostics: Dict[str, List[Diagnostic]] = {}
        self._open_documents: set[str] = set()

    async def start(self) -> None:
        """Spawn the language server process and start the message reader loop."""
        if self.process is not None:
            return

        logger.info(f"Starting LSP server with command: {' '.join(self.command)}")
        self.process = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        self._reader_task = asyncio.create_task(self._read_messages())

    async def stop(self) -> None:
        """Gracefully shutdown and terminate the language server."""
        if self.process is None:
            return

        try:
            await self.shutdown()
            await self.exit()
        except Exception as e:
            logger.warning(f"Error during graceful LSP shutdown: {e}")

        if self._reader_task and not self._reader_task.done():
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

        if self.process.returncode is None:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=2.0)
            except (asyncio.TimeoutError, ProcessLookupError):
                self.process.kill()

        self.process = None
        logger.info("LSP server stopped.")

    async def __aenter__(self) -> LspClient:
        await self.start()
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.stop()

    async def _send_payload(self, payload: Dict[str, Any]) -> None:
        if self.process is None or self.process.stdin is None:
            raise RuntimeError("LSP server is not running")
        msg_bytes = encode_jsonrpc_message(payload)
        self.process.stdin.write(msg_bytes)
        await self.process.stdin.drain()

    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        self._request_id += 1
        req_id = self._request_id
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {},
        }

        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self._pending_requests[req_id] = fut

        await self._send_payload(payload)
        try:
            return await asyncio.wait_for(fut, timeout=self.timeout)
        except asyncio.TimeoutError:
            self._pending_requests.pop(req_id, None)
            raise TimeoutError(f"LSP request '{method}' (id={req_id}) timed out after {self.timeout}s")

    async def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }
        await self._send_payload(payload)

    async def _read_messages(self) -> None:
        if not self.process or not self.process.stdout:
            return

        reader = self.process.stdout
        while True:
            try:
                header_bytes = bytearray()
                while b"\r\n\r\n" not in header_bytes:
                    line = await reader.readline()
                    if not line:
                        return
                    header_bytes.extend(line)

                headers_text = header_bytes.decode("ascii", errors="replace")
                content_length = 0
                for line in headers_text.split("\r\n"):
                    if line.lower().startswith("content-length:"):
                        content_length = int(line.split(":", 1)[1].strip())

                if content_length <= 0:
                    continue

                body_bytes = await reader.readexactly(content_length)
                message = json.loads(body_bytes.decode("utf-8"))
                self._handle_incoming_message(message)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error reading LSP message: {e}")
                break

    def _handle_incoming_message(self, message: Dict[str, Any]) -> None:
        if "id" in message and message["id"] in self._pending_requests:
            req_id = message["id"]
            fut = self._pending_requests.pop(req_id)
            if not fut.done():
                if "error" in message:
                    fut.set_exception(RuntimeError(f"LSP error: {message['error']}"))
                else:
                    fut.set_result(message.get("result"))

        elif "method" in message:
            method = message["method"]
            params = message.get("params", {})
            if method == "textDocument/publishDiagnostics":
                self._handle_diagnostics(params)

            handlers = self._notification_handlers.get(method, [])
            for handler in handlers:
                try:
                    handler(params)
                except Exception as e:
                    logger.error(f"Error in notification handler for {method}: {e}")

    def _handle_diagnostics(self, params: Dict[str, Any]) -> None:
        uri = params.get("uri", "")
        file_path = uri_to_path(uri)
        raw_diags = params.get("diagnostics", [])
        self.diagnostics[file_path] = [Diagnostic.from_dict(d) for d in raw_diags]

    async def initialize(self) -> Dict[str, Any]:
        workspace_uri = path_to_uri(self.workspace_root)
        params = {
            "processId": os.getpid(),
            "rootUri": workspace_uri,
            "rootPath": self.workspace_root,
            "capabilities": {
                "textDocument": {
                    "hover": {"contentFormat": ["markdown", "plaintext"]},
                    "definition": {"dynamicRegistration": True},
                    "references": {"dynamicRegistration": True},
                    "documentSymbol": {
                        "hierarchicalDocumentSymbolSupport": True,
                        "symbolKind": {"valueSet": list(range(1, 27))},
                    },
                },
                "workspace": {
                    "symbol": {"symbolKind": {"valueSet": list(range(1, 27))}},
                    "workspaceFolders": True,
                },
            },
            "workspaceFolders": [{"uri": workspace_uri, "name": "workspace"}],
        }
        result = await self.send_request("initialize", params)
        await self.send_notification("initialized", {})
        return result

    async def shutdown(self) -> Any:
        return await self.send_request("shutdown", None)

    async def exit(self) -> None:
        await self.send_notification("exit", None)

    async def open_document(self, file_path: Union[str, Path], language_id: str = "python") -> None:
        resolved_path = str(Path(file_path).resolve())
        uri = path_to_uri(resolved_path)
        with open(resolved_path, "r", encoding="utf-8") as f:
            text = f.read()

        params = {
            "textDocument": {
                "uri": uri,
                "languageId": language_id,
                "version": 1,
                "text": text,
            }
        }
        await self.send_notification("textDocument/didOpen", params)
        self._open_documents.add(resolved_path)

    async def ensure_document_open(self, file_path: Union[str, Path]) -> None:
        resolved = str(Path(file_path).resolve())
        if resolved not in self._open_documents:
            await self.open_document(resolved)

    async def get_hover(self, file_path: Union[str, Path], line: int, character: int) -> Optional[Hover]:
        await self.ensure_document_open(file_path)
        params = {
            "textDocument": {"uri": path_to_uri(file_path)},
            "position": Position(line=line, character=character).to_dict(),
        }
        res = await self.send_request("textDocument/hover", params)
        return Hover.from_dict(res) if res else None

    async def get_definitions(self, file_path: Union[str, Path], line: int, character: int) -> List[Location]:
        await self.ensure_document_open(file_path)
        params = {
            "textDocument": {"uri": path_to_uri(file_path)},
            "position": Position(line=line, character=character).to_dict(),
        }
        res = await self.send_request("textDocument/definition", params)
        if not res:
            return []
        if isinstance(res, list):
            return [Location.from_dict(item) for item in res]
        return [Location.from_dict(res)]

    async def get_references(
        self,
        file_path: Union[str, Path],
        line: int,
        character: int,
        include_declaration: bool = False,
    ) -> List[Location]:
        await self.ensure_document_open(file_path)
        params = {
            "textDocument": {"uri": path_to_uri(file_path)},
            "position": Position(line=line, character=character).to_dict(),
            "context": {"includeDeclaration": include_declaration},
        }
        res = await self.send_request("textDocument/references", params)
        if not res or not isinstance(res, list):
            return []
        return [Location.from_dict(item) for item in res]

    async def get_document_symbols(self, file_path: Union[str, Path]) -> List[SymbolInformation]:
        await self.ensure_document_open(file_path)
        uri = path_to_uri(file_path)
        params = {"textDocument": {"uri": uri}}
        res = await self.send_request("textDocument/documentSymbol", params)
        if not res or not isinstance(res, list):
            return []
        return [SymbolInformation.from_dict(item, default_uri=uri) for item in res]

