"""Prerender public routes of the CRA build into static HTML for search engines and link previews.

Usage: python3 scripts/prerender.py <build_dir> <public_site_url>
API calls are blocked during render so only page copy and meta are baked in (live data loads in the browser).
"""
import http.server
import json
import os
import re
import sys
import threading

from playwright.sync_api import sync_playwright

ROUTES = ["/", "/buyers", "/suppliers", "/trust", "/about", "/vision", "/contact", "/help",
          "/tenders/live", "/tenders/completed"]
URL_LANGS = ["ru", "kk", "zh-Hans", "zh-Hant", "es", "fr", "de", "hi", "ms", "id", "ko", "ja", "ar"]
SEED = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend", "seed", "i18n_cache.json")
PORT = 5055
REDIRECTS = {"/pricing": "/contact"}


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


def load_dicts():
    dicts = {}
    if os.path.exists(SEED):
        for r in json.load(open(SEED, encoding="utf-8")):
            dicts.setdefault(r["lang"], {})[r["src"]] = r["out"]
    return dicts


def api_handler(dicts):
    def handle(r):
        url = r.request.url
        m = re.search(r"/api/v1/i18n/dict/([\w-]+)", url)
        if m:
            return r.fulfill(status=200, content_type="application/json", body=json.dumps({"map": dicts.get(m.group(1), {})}))
        if "/api/v1/i18n/translate" in url:
            body = json.loads(r.request.post_data or "{}")
            d = dicts.get(body.get("lang"), {})
            return r.fulfill(status=200, content_type="application/json",
                             body=json.dumps({"map": {t: d[t] for t in body.get("texts", []) if t in d}}))
        return r.abort()
    return handle


def main(build, site):
    site = site.rstrip("/")
    shell = open(os.path.join(build, "index.html"), encoding="utf-8").read()
    open(os.path.join(build, "spa-shell.html"), "w", encoding="utf-8").write(shell)
    srv = serve(build)
    origin = f"http://127.0.0.1:{PORT}"
    out = {}
    pages = [(r, None) for r in ROUTES] + [((f"/{lg}" if r == "/" else f"/{lg}{r}"), lg) for lg in URL_LANGS for r in ROUTES]
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.add_init_script("try{localStorage.removeItem('pmc_lang')}catch(e){}")
        pg.route("**/api/**", api_handler(load_dicts()))
        for route, lg in pages:
            pg.goto(origin + route, wait_until="networkidle")
            pg.wait_for_timeout(1500 if lg else 800)
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
    for old, to in REDIRECTS.items():
        d = os.path.join(build, old.strip("/"))
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(
            f'<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex">'
            f'<link rel="canonical" href="{site}{to}"><meta http-equiv="refresh" content="0;url={to}">'
            f'<script>location.replace("{to}")</script>')


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
