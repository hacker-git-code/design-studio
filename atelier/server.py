"""Local web studio (stdlib only): `atelier serve` then open http://127.0.0.1:8765"""

from __future__ import annotations

import json
import threading
import traceback
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WEB = Path(__file__).parent / "web"
_lock = threading.Lock()


class Handler(SimpleHTTPRequestHandler):
    out_root: Path = Path("out")
    taste = None

    def log_message(self, fmt, *args):  # quieter
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = (WEB / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith("/out/"):
            rel = self.path[5:].split("?")[0]
            target = (self.out_root / rel).resolve()
            if self.out_root.resolve() not in target.parents or not target.is_file():
                self.send_error(404)
                return
            ctype = {".html": "text/html; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png", ".json": "application/json",
                     ".css": "text/css", ".js": "text/javascript"}.get(target.suffix, "application/octet-stream")
            data = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self.send_error(404)

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(n) or b"{}")
            if self.path == "/api/dna":
                from .brief import parse

                dna = parse(req.get("brief", ""), req.get("name") or None, req.get("llm") or None)
                return self._json(200, dna.to_dict())
            if self.path == "/api/generate":
                from .dna import BrandDNA
                from .studio import run

                dna = BrandDNA.from_dict(req["dna"])
                with _lock:
                    out = run(dna, self.out_root, n=int(req.get("n", 24)), k=int(req.get("k", 3)), taste=self.taste,
                              png=bool(req.get("png", False)), verbose=True)
                return self._json(200, _listing(out, self.out_root))
            if self.path == "/api/remix":
                from argparse import Namespace

                from .cli import cmd_remix

                spec = (self.out_root / req["spec"]).resolve()
                if self.out_root.resolve() not in spec.parents:
                    return self._json(400, {"error": "bad path"})
                out = spec.parent.parent / f"remix-{req.get('vary', 'all')}"
                with _lock:
                    cmd_remix(Namespace(spec=str(spec), vary=req.get("vary", "all"), n=12, k=3, out=str(out), taste=None, no_png=True))
                return self._json(200, _listing(out, self.out_root, prefix="remix-"))
            self.send_error(404)
        except Exception as e:
            traceback.print_exc()
            self._json(500, {"error": str(e)})


def _listing(out: Path, root: Path, prefix="direction-"):
    dirs = []
    for d in sorted(out.glob(f"{prefix}*")):
        spec = json.loads((d / "brand.json").read_text())
        dirs.append({"name": d.name, "book": f"/out/{d.relative_to(root)}/brandbook.html",
                     "board": f"/out/{d.relative_to(root)}/logo/lockup-stacked.svg",
                     "board2": f"/out/{d.relative_to(root)}/logo/lockup-stacked-reversed.svg",
                     "spec": str((d / 'brand.json').relative_to(root)),
                     "palette": [v["hex"] for k, v in spec["palette"].items() if not k.startswith("_")],
                     "family": spec["mark"]["family"], "font": spec["type"]["display"], "score": spec["score"]})
    return {"out": str(out), "directions": dirs}


def serve(host="127.0.0.1", port=8765, out_root=Path("out"), taste_path=None):
    out_root.mkdir(parents=True, exist_ok=True)
    Handler.out_root = out_root
    if taste_path:
        from .taste import TasteModel

        Handler.taste = TasteModel.load(taste_path)
    srv = ThreadingHTTPServer((host, port), partial(Handler))
    print(f"Atelier studio on http://{host}:{port}  (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
