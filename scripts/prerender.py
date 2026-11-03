"""Prerender public routes of the CRA build into static HTML for search engines and link previews.

Usage: python3 scripts/prerender.py <build_dir> <public_site_url>
API calls are blocked during render so only page copy and meta are baked in (live data loads in the browser).
"""
import http.server
import os
import re
import sys
import threading

from playwright.sync_api import sync_playwright

ROUTES = ["/", "/buyers", "/suppliers", "/pricing", "/trust", "/about", "/vision", "/contact", "/help",
          "/tenders/live", "/tenders/completed"]
PORT = 5055


def serve(build):
    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=build, **k)

        def log_message(self, *a):
            pass

        def send_head(self):
            p = self.translate_path(self.path.split("?")[0])
            if not os.path.exists(p) or os.path.isdir(p) and not os.path.exists(os.path.join(p, "index.html")):
                self.path = "/index.html"
            return super().send_head()

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main(build, site):
    site = site.rstrip("/")
    shell = open(os.path.join(build, "index.html"), encoding="utf-8").read()
    open(os.path.join(build, "spa-shell.html"), "w", encoding="utf-8").write(shell)
    srv = serve(build)
    origin = f"http://127.0.0.1:{PORT}"
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.route("**/api/**", lambda r: r.abort())
        for route in ROUTES:
            pg.goto(origin + route, wait_until="networkidle")
            pg.wait_for_timeout(800)
            html = pg.content().replace(origin, site)
            guard = ("<script>(function(){var p=location.pathname.replace(/\\/+$/,'')||'/';"
                     f"if(p!=='{route}')document.getElementById('root').innerHTML='';}})();</script>")
            html = re.sub(r'(<div id="root">.*?</div>)(\s*</body>)', lambda m: m.group(1) + guard + m.group(2), html, count=1, flags=re.S)
            if guard not in html:
                html = html.replace("</body>", guard + "</body>", 1)
            out[route] = html
            print("prerendered", route, len(html))
        b.close()
    srv.shutdown()
    for route, html in out.items():
        d = build if route == "/" else os.path.join(build, route.strip("/"))
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(html)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
