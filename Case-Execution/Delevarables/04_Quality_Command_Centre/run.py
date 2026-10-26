"""Start the GxP Quality Command Centre.

    python run.py                 # serves http://127.0.0.1:8090 and opens the browser
    python run.py --port 8091     # another port
    python run.py --check         # start-up checks only (data checksum, hub import, settings), then exit

Requires Python 3.10+ (tested on 3.10 and 3.14). Standard library only; no pip install needed.
"""
import argparse
import json
import os
import sys
import threading
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

from qcc import settings as settings_mod  # noqa: E402
from qcc.ai.assistant import Assistant  # noqa: E402
from qcc.data import Snapshot, SnapshotError  # noqa: E402
from qcc.hubbridge import Hub, HubUnavailable  # noqa: E402
from qcc.server import App, serve  # noqa: E402
from qcc.services import Services  # noqa: E402


def build(s):
    runtime = s.path("app.runtime_dir")
    snap = Snapshot(s.path("paths.data_source"), s.get("paths.data_source_sha256"), runtime)
    hub = Hub(s.path("paths.hub_repo"))
    with open(s.path("paths.semantic_layer_json"), encoding="utf-8") as f:
        sem = json.load(f)
    svc = Services(snap, hub, sem)
    ai = Assistant(s, svc, sem, runtime)
    return App(s, snap, hub, svc, ai)


def main(argv=None):
    ap = argparse.ArgumentParser(description="GxP Quality Command Centre (synthetic, loopback only)")
    ap.add_argument("--port", type=int)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    if sys.version_info < (3, 10):
        raise SystemExit("Python 3.10 or newer is required (found %s)." % sys.version.split()[0])
    s = settings_mod.load()
    try:
        app = build(s)
    except (SnapshotError, HubUnavailable, OSError) as e:
        raise SystemExit("Start-up check failed: %s" % e)
    info = app.about()
    print("GxP Quality Command Centre %s  |  Python %s" % (info["version"], info["python"]))
    print("  hub        %s (HEAD %s)" % (info["hub_repo"], info["hub_head"]))
    print("  data       %s (sha256 %s..., read-only snapshot)" % (info["data_source"], info["data_sha256"][:12]))
    ai = info["ai"]
    print("  assistant  %s | provider %s | model %s | key %s" % (ai["mode"], ai["provider"], ai["model"],
                                                               ai["key_source"] or "not set"))
    if a.check:
        ov = app.svc.overview()
        print("  checks     cases=%d backlog(D-OPS)=%d month-end hub=%s legacy=%s exception-queue=%d" % (
            ov["cases"], ov["backlog_d_ops"]["value"], ov["month_end"]["hub"]["value"], ov["month_end"]["legacy"]["value"],
            ov["intake"]["exception_queue_total"]))
        return 0
    host, port = s.get("app.host", "127.0.0.1"), a.port or int(s.get("app.port", 8090))
    httpd = serve(app, host, port)
    url = "http://%s:%d/" % (host, port)
    print("  serving    %s   (Ctrl+C to stop)" % url)
    threading.Thread(target=app.svc.intake_preview, kwargs={"summary_only": True}, daemon=True).start()
    if s.get("app.open_browser", True) and not a.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
