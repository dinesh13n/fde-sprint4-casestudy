"""Loopback-only HTTP server: JSON API under /api/, static single-page UI under /.

Personas (reviewer, quality_lead, compliance, finance_read, integration, dispositioner) are demo personas sent as the X-QCC-Persona header.
They control what the UI may read, using the hub's role names. They are NOT authentication: the hub's own login (hub.web) is the real one.
"""
import datetime
import json
import mimetypes
import os
import platform
import re
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from qcc import __version__
from qcc.settings import APP_ROOT

WEB = os.path.join(APP_ROOT, "web")
PERSONAS = ("reviewer", "quality_lead", "compliance", "finance_read", "integration", "dispositioner")
CASE_ROLES = ("reviewer", "quality_lead", "compliance", "dispositioner")
ROUTE_ROLES = {
    "overview": PERSONAS, "monthend": PERSONAS, "definitions": PERSONAS, "zoneh": PERSONAS, "release": PERSONAS, "about": PERSONAS,
    "ai_status": PERSONAS, "cases": CASE_ROLES, "case": CASE_ROLES,
    "intake": ("reviewer", "quality_lead", "compliance", "integration"), "ai_ask": CASE_ROLES, "ai_key": PERSONAS,
}
CSP = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'"


class App(object):
    def __init__(self, settings, snap, hub, services, assistant):
        self.s, self.snap, self.hub, self.svc, self.ai = settings, snap, hub, services, assistant
        self.started = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        self.gate_log = os.path.join(settings.path("app.runtime_dir"), "gate-attempts.jsonl")
        self._lock = threading.Lock()

    def about(self):
        return {"app": "GxP Quality Command Centre", "version": __version__, "python": platform.python_version(), "platform": platform.platform(),
                "started": self.started, "hub_repo": self.hub.repo, "hub_head": self.hub.head, "data_snapshot": self.snap.path,
                "data_source": self.snap.source, "data_sha256": self.snap.sha256, "settings_sources": self.s.sources,
                "label": "synthetic, unvalidated", "ai": self.s.public_ai_status(), "ai_counters": self.ai.counters}

    def log_gate(self, entry):
        with self._lock:
            try:
                with open(self.gate_log, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry) + "\n")
            except OSError:
                pass


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        server_version = "QCC/" + __version__
        sys_version = ""

        def log_message(self, fmt, *args):
            sys.stderr.write("  %s %s\n" % (self.command, self.path.split("?")[0]))

        # ------------------------------------------------------------ plumbing
        def _loopback(self):
            return self.client_address[0] in ("127.0.0.1", "::1", "::ffff:127.0.0.1")

        def _send(self, code, body, ctype="application/json; charset=utf-8"):
            data = body if isinstance(body, bytes) else json.dumps(body, default=str).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", CSP)
            self.end_headers()
            self.wfile.write(data)

        def _err(self, code, ecode, msg):
            self._send(code, {"error": {"code": ecode, "message": msg}})

        def _persona(self):
            p = self.headers.get("X-QCC-Persona", "reviewer")
            return p if p in PERSONAS else "reviewer"

        def _allowed(self, route):
            return self._persona() in ROUTE_ROLES.get(route, ())

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n > 64 * 1024:
                return None
            try:
                return json.loads(self.rfile.read(n).decode("utf-8") or "{}")
            except ValueError:
                return None

        def _guard(self, route):
            if not self._allowed(route):
                self._err(403, "E-AUTH-FORBIDDEN", "Persona '%s' may not use this view (deny by default)." % self._persona())
                return False
            return True

        # ------------------------------------------------------------ GET
        def do_GET(self):
            if not self._loopback():
                return self._err(403, "E-LOOPBACK-ONLY", "This app only serves the local machine.")
            u = urllib.parse.urlparse(self.path)
            q = dict(urllib.parse.parse_qsl(u.query))
            p = u.path
            if not p.startswith("/api/"):
                return self._static(p)
            routes = {
                "/api/overview": ("overview", lambda: app.svc.overview()),
                "/api/cases": ("cases", lambda: app.svc.cases(q.get("site"), q.get("status"), q.get("severity"), q.get("q"))),
                "/api/intake": ("intake", lambda: app.svc.intake_preview(queue=q.get("queue"), reason=q.get("reason"))),
                "/api/monthend": ("monthend", lambda: app.svc.month_end(q.get("cutoff"))),
                "/api/definitions": ("definitions", lambda: app.svc.definitions()),
                "/api/zoneh": ("zoneh", lambda: app.svc.zone_h()),
                "/api/release": ("release", lambda: app.svc.release()),
                "/api/ai/status": ("ai_status", lambda: dict(app.s.public_ai_status(), counters=app.ai.counters)),
                "/api/about": ("about", lambda: app.about()),
            }
            m = re.match(r"^/api/cases/(C\d{8})$", p)
            try:
                if m:
                    if not self._guard("case"):
                        return None
                    d = app.svc.case_detail(m.group(1))
                    return self._send(200, d) if d else self._err(404, "E-NOT-FOUND", "No such case")
                if p not in routes:
                    return self._err(404, "E-NOT-FOUND", "Unknown endpoint")
                route, fn = routes[p]
                if not self._guard(route):
                    return None
                return self._send(200, fn())
            except BrokenPipeError:
                return None
            except Exception as e:  # never leak a traceback to the browser
                sys.stderr.write("  ERROR %r\n" % e)
                return self._err(500, "E-INTERNAL", "Internal error (see console).")

        def _static(self, p):
            if p in ("", "/"):
                p = "/index.html"
            full = os.path.normpath(os.path.join(WEB, p.lstrip("/")))
            if not full.startswith(WEB) or not os.path.isfile(full):
                full = os.path.join(WEB, "index.html")
            ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype in ("application/javascript",):
                ctype += "; charset=utf-8"
            with open(full, "rb") as f:
                self._send(200, f.read(), ctype)

        # ------------------------------------------------------------ POST
        def do_POST(self):
            if not self._loopback():
                return self._err(403, "E-LOOPBACK-ONLY", "This app only serves the local machine.")
            if self.headers.get("X-QCC-Request") != "1":  # simple CSRF guard: only the app's own fetch() sets this header
                return self._err(403, "E-CSRF", "Missing request header.")
            p = urllib.parse.urlparse(self.path).path
            body = self._body()
            if body is None:
                return self._err(400, "E-BAD-REQUEST", "Invalid JSON body.")
            try:
                route = {"/api/intake/replay": "intake", "/api/zoneh/attempt": "zoneh", "/api/ai/ask": "ai_ask",
                         "/api/ai/session-key": "ai_key"}.get(p)
                if route is None:
                    return self._err(404, "E-NOT-FOUND", "Unknown endpoint")
                if not self._guard(route):
                    return None
                if p == "/api/intake/replay":
                    return self._send(200, app.svc.replay())
                if p == "/api/zoneh/attempt":
                    e = app.svc.zone_h_attempt(str(body.get("action", ""))[:10], self._persona(), "human")
                    app.log_gate(e)
                    return self._send(423 if e["code"] == "E-GATE-NO-HOLDERS" else 403, e)
                if p == "/api/ai/ask":
                    r = app.ai.ask(body.get("question"), self._persona(), body.get("case_id"), body.get("feed_id"))
                    if r.get("mode") == "refused":
                        app.log_gate(app.svc.audit[-1])
                    return self._send(200, r)
                if p == "/api/ai/session-key":
                    app.s.set_session_key(body.get("api_key"))
                    return self._send(200, app.s.public_ai_status())
                return self._err(404, "E-NOT-FOUND", "Unknown endpoint")
            except Exception as e:
                sys.stderr.write("  ERROR %r\n" % e)
                return self._err(500, "E-INTERNAL", "Internal error (see console).")

    return Handler


def serve(app, host, port):
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise SystemExit("Refusing to bind %s: this app is loopback-only (ADR-015)." % host)
    httpd = ThreadingHTTPServer((host, port), make_handler(app))
    httpd.daemon_threads = True
    return httpd
