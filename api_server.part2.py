# This file is Part 2 of 2 for api_server.py
# Run: python reassemble_v37.py
# =========================================

# ═══════════════════════════════════════════════════════════════════════════════
#  OPENAPI SPEC ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════════


def _openapi_spec() -> JsonResponse:
    """Return OpenAPI 3.0.3 specification."""
    spec = {
        "openapi": "3.0.3",
        "info": {
            "title": "Omega AI API",
            "version": "3.7.0",
            "description": "Standard-library-only REST API for Omega AI v3.7.0 (Prometheus)",
        },
        "servers": [{"url": "/api"}],
        "paths": {},
    }
    # Auto-generate from route table
    for path, info in ROUTE_TABLE.items():
        methods = info.get("methods", ["POST"])
        spec["paths"][path] = {}
        for method in methods:
            spec["paths"][path][method.lower()] = {
                "summary": info["handler"].__doc__ or "No description",
                "responses": {
                    "200": {"description": "Success"},
                    "400": {"description": "Bad Request"},
                    "401": {"description": "Unauthorized"},
                    "500": {"description": "Server Error"},
                },
            }
    return _json_response({"success": True, "spec": spec})


# ═══════════════════════════════════════════════════════════════════════════════
#  ROUTE TABLE
# ═══════════════════════════════════════════════════════════════════════════════

ROUTE_TABLE: dict[str, dict[str, Any]] = {
    # Public
    "/api/health":   {"handler": _health,   "methods": ["GET"],  "auth": False},
    "/api/version":  {"handler": _version,  "methods": ["GET"],  "auth": False},
    "/api/status":   {"handler": _status,   "methods": ["GET"],  "auth": False},
    "/api/openapi.json": {"handler": _openapi_spec, "methods": ["GET"], "auth": False},
    # Core
    "/api/process":  {"handler": _process,  "methods": ["POST"], "auth": True},
    "/api/chat":     {"handler": _chat,     "methods": ["POST"], "auth": True},
    "/api/learn":    {"handler": _learn,    "methods": ["POST"], "auth": True},
    "/api/predict":  {"handler": _predict,  "methods": ["POST"], "auth": True},
    # Memory
    "/api/memory/search":  {"handler": _memory_search,  "methods": ["POST"], "auth": True},
    "/api/memory/store":   {"handler": _memory_store,   "methods": ["POST"], "auth": True},
    "/api/memory/delete":  {"handler": _memory_delete,  "methods": ["POST"], "auth": True},
    # Analytics & Data
    "/api/analytics":      {"handler": _analytics,      "methods": ["GET"],  "auth": True},
    "/api/export":         {"handler": _export_data,    "methods": ["POST"], "auth": True},
    "/api/import":         {"handler": _import_data,    "methods": ["POST"], "auth": True},
    # Plugins
    "/api/plugins":            {"handler": _plugins_list,       "methods": ["GET"],  "auth": True},
    "/api/plugins/install":    {"handler": _plugins_install,    "methods": ["POST"], "auth": True},
    "/api/plugins/uninstall":  {"handler": _plugins_uninstall,  "methods": ["POST"], "auth": True},
    # Config
    "/api/config":        {"handler": _config_get,     "methods": ["GET"],  "auth": True},
    "/api/config/update": {"handler": _config_update,  "methods": ["POST"], "auth": True},
    # System
    "/api/system/stats":   {"handler": _system_stats,   "methods": ["GET"],  "auth": True},
    "/api/system/logs":    {"handler": _system_logs,    "methods": ["GET"],  "auth": True},
    "/api/system/restart": {"handler": _system_restart, "methods": ["POST"], "auth": True},
    # Wisdom (v3.5.0)
    "/api/wisdom":         {"handler": _wisdom,         "methods": ["POST"], "auth": True},
    # Error Repair (v3.6.1)
    "/api/error-repair/stats": {"handler": _error_repair_stats, "methods": ["GET"],  "auth": True},
    "/api/error-repair/heal":  {"handler": _error_repair_heal,  "methods": ["POST"], "auth": True},
    "/api/error-repair/clear": {"handler": _error_repair_clear, "methods": ["POST"], "auth": True},
    # Memory Manager (v3.6.2)
    "/api/memory-manager/stats":          {"handler": _memory_mgr_stats,          "methods": ["GET"],  "auth": True},
    "/api/memory-manager/entries":        {"handler": _memory_mgr_entries,        "methods": ["GET"],  "auth": True},
    "/api/memory-manager/cleanup":        {"handler": _memory_mgr_cleanup,        "methods": ["POST"], "auth": True},
    "/api/memory-manager/purge-proposals": {"handler": _memory_mgr_purge_proposals, "methods": ["GET"],  "auth": True},
    "/api/memory-manager/approve-purge":  {"handler": _memory_mgr_approve_purge,  "methods": ["POST"], "auth": True},
    "/api/memory-manager/reject-purge":   {"handler": _memory_mgr_reject_purge,   "methods": ["POST"], "auth": True},
    "/api/memory-manager/recover":        {"handler": _memory_mgr_recover,        "methods": ["POST"], "auth": True},
    # Pedagogical (v3.6.3)
    "/api/pedagogical/diagnostic": {"handler": _pedagogical_diagnostic, "methods": ["POST"], "auth": True},
    "/api/pedagogical/progress":   {"handler": _pedagogical_progress,   "methods": ["GET"],  "auth": True},
    # Crypto (v3.7.0)
    "/api/crypto/encrypt": {"handler": _crypto_encrypt, "methods": ["POST"], "auth": True},
    "/api/crypto/decrypt": {"handler": _crypto_decrypt, "methods": ["POST"], "auth": True},
    "/api/crypto/hash":    {"handler": _crypto_hash,    "methods": ["POST"], "auth": True},
    # Key Rotation (v3.7.0)
    "/api/keys/rotate":    {"handler": _keys_rotate,    "methods": ["POST"], "auth": True},
    # Rate Limiter (v3.7.0)
    "/api/rate-limit/status": {"handler": _rate_limit_status, "methods": ["GET"], "auth": True},
    # WebSocket (v3.7.0)
    "/api/ws/connect":     {"handler": _ws_connect,     "methods": ["GET"],  "auth": True},
    # Vector DB (v3.7.0)
    "/api/vector/search":  {"handler": _vector_search,  "methods": ["POST"], "auth": True},
    "/api/vector/store":   {"handler": _vector_store,   "methods": ["POST"], "auth": True},
    # Multi-Tenant (v3.7.0)
    "/api/tenant/stats":   {"handler": _tenant_stats,   "methods": ["GET"],  "auth": True},
    # Plugin Marketplace (v3.7.0)
    "/api/marketplace/plugins": {"handler": _marketplace_plugins, "methods": ["GET"],  "auth": True},
    "/api/marketplace/install": {"handler": _marketplace_install, "methods": ["POST"], "auth": True},
    # Realtime Prices (v3.7.0)
    "/api/prices/realtime": {"handler": _prices_realtime, "methods": ["POST"], "auth": True},
    # Metrics (v3.7.0)
    "/api/metrics":        {"handler": _metrics_export, "methods": ["GET"],  "auth": True},
    # Email (v3.7.0)
    "/api/notify/email":   {"handler": _notify_email,   "methods": ["POST"], "auth": True},
    # Telegram (v3.7.0)
    "/api/telegram/send":  {"handler": _telegram_send,  "methods": ["POST"], "auth": True},
    # PDF (v3.7.0)
    "/api/pdf/generate":   {"handler": _pdf_generate,   "methods": ["POST"], "auth": True},
    # Backup (v3.7.0)
    "/api/backup/create":  {"handler": _backup_create,  "methods": ["POST"], "auth": True},
    "/api/backup/restore": {"handler": _backup_restore, "methods": ["POST"], "auth": True},
    "/api/backup/list":    {"handler": _backup_list,    "methods": ["GET"],  "auth": True},
    # Local LLM (v3.7.0)
    "/api/llm/local/status": {"handler": _llm_status,   "methods": ["GET"],  "auth": True},
    "/api/llm/local/query":  {"handler": _llm_query,    "methods": ["POST"], "auth": True},
    # Agent Mesh (v3.7.0)
    "/api/mesh/agents":    {"handler": _mesh_agents,    "methods": ["GET"],  "auth": True},
    "/api/mesh/tasks":     {"handler": _mesh_tasks,     "methods": ["GET"],  "auth": True},
    # Blockchain (v3.7.0)
    "/api/blockchain/audit": {"handler": _blockchain_audit, "methods": ["GET"], "auth": True},
    # Federated Learning (v3.7.0)
    "/api/federated/model-status": {"handler": _federated_status, "methods": ["GET"], "auth": True},
}


# ═══════════════════════════════════════════════════════════════════════════════
#  HTTP REQUEST HANDLER
# ═══════════════════════════════════════════════════════════════════════════════

_shutdown_requested = False


class OmegaHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Omega AI API."""

    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        """Suppress default logging — we log to database."""
        pass

    def _send_json(self, response: JsonResponse):
        """Send a JSON response with CORS headers."""
        body = response.to_bytes()
        self.send_response(response.status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for key, value in CORS_HEADERS.items():
            self.send_header(key, value)
        for key, value in response.headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def _send_options(self):
        """Handle CORS preflight."""
        self.send_response(204)
        for key, value in CORS_HEADERS.items():
            self.send_header(key, value)
        self.end_headers()

    def _read_body(self) -> bytes:
        """Safely read request body with size limit."""
        content_length = self.headers.get("Content-Length")
        if not content_length:
            return b""
        size = int(content_length)
        if size > MAX_REQUEST_SIZE:
            return b""
        return self.rfile.read(size)

    def _get_headers(self) -> dict[str, str]:
        """Extract relevant headers."""
        return {
            "Authorization": self.headers.get("Authorization", ""),
            "Content-Type": self.headers.get("Content-Type", ""),
        }

    def do_OPTIONS(self):
        self._send_options()

    def do_GET(self):
        self._handle_request("GET")

    def do_POST(self):
        self._handle_request("POST")

    def do_PUT(self):
        self._handle_request("PUT")

    def do_DELETE(self):
        self._handle_request("DELETE")

    def _handle_request(self, method: str):
        """Main request router."""
        start = time.time()
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # Read body
        body_bytes = self._read_body()
        headers = self._get_headers()
        body = _parse_body(body_bytes, headers)

        # Merge query params into body
        for key, values in query.items():
            if key not in body:
                body[key] = values[0] if len(values) == 1 else values

        # Route lookup
        route_info = ROUTE_TABLE.get(path)
        if route_info is None:
            self._send_json(_error(f"Not found: {path}", 404))
            _log_request(method, path, 404, (time.time() - start) * 1000)
            return

        # Auth check
        if route_info.get("auth", True) and path not in PUBLIC_ENDPOINTS:
            if not _check_auth(headers):
                self._send_json(_error("Unauthorized — provide Bearer token", 401))
                _log_request(method, path, 401, (time.time() - start) * 1000)
                return

        # Method check
        if method not in route_info.get("methods", ["GET"]):
            self._send_json(_error(f"Method not allowed: {method}", 405))
            _log_request(method, path, 405, (time.time() - start) * 1000)
            return

        # Execute handler
        try:
            handler = route_info["handler"]
            sig = handler.__code__.co_argcount
            if sig >= 1:
                response = handler(body)
            else:
                response = handler()
            if not isinstance(response, JsonResponse):
                response = _json_response({"success": True, "data": response})
        except Exception as e:
            traceback.print_exc()
            response = _error(str(e), 500)

        duration_ms = (time.time() - start) * 1000
        self._send_json(response)
        _log_request(method, path, response.status, duration_ms)


# ═══════════════════════════════════════════════════════════════════════════════
#  SERVER LIFECYCLE
# ═══════════════════════════════════════════════════════════════════════════════

_server_instance: HTTPServer | None = None


def _signal_handler(signum, frame):
    """Graceful shutdown on SIGTERM/SIGINT."""
    global _shutdown_requested
    _shutdown_requested = True
    if _server_instance:
        _server_instance.shutdown()


def start_server(port: int | None = None, blocking: bool = True):
    """Start the HTTP API server.

    Args:
        port: Port number (default from OMEGA_PORT env or 8080)
        blocking: If True, blocks until shutdown
    """
    global _server_instance
    port = port or DEFAULT_PORT
    _server_instance = HTTPServer(("0.0.0.0", port), OmegaHandler)
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
    print(f"[API] Omega AI v3.7.0 serving on http://0.0.0.0:{port}")
    print(f"[API] {len(ROUTE_TABLE)} endpoints registered")
    print(f"[API] Public: {len(PUBLIC_ENDPOINTS)}, Auth-required: {len(AUTH_ENDPOINTS)}")
    if blocking:
        try:
            _server_instance.serve_forever()
        except Exception as e:
            print(f"[API] Server error: {e}")
        finally:
            print("[API] Server stopped")
    else:
        thread = threading.Thread(target=_server_instance.serve_forever, daemon=True)
        thread.start()
        return _server_instance


def stop_server():
    """Stop the running server."""
    global _server_instance
    if _server_instance:
        _server_instance.shutdown()
        _server_instance.server_close()
        _server_instance = None


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN (for direct execution)
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Omega AI API Server v3.7.0")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port number")
    parser.add_argument("--background", action="store_true", help="Run in background thread")
    args = parser.parse_args()
    start_server(port=args.port, blocking=not args.background)
