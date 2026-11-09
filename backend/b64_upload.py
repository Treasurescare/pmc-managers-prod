"""Rebuilds multipart uploads sent as base64 JSON (X-PMC-Upload: b64).

Production's AWS WAF (CloudFront free plan) false-positives on raw binary file
bytes (CrossSiteScripting_BODY). The browser sends files base64-encoded inside
JSON, which the WAF can inspect safely; this ASGI middleware turns the request
back into a normal multipart/form-data body so every UploadFile endpoint works
unchanged.
"""
import base64
import json
import uuid

MAX_JSON_BYTES = 40 * 1024 * 1024


def _esc(s: str) -> str:
    return str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\r", "").replace("\n", "")


def build_multipart(payload: dict) -> tuple[bytes, str]:
    boundary = f"----pmc{uuid.uuid4().hex}"
    out = bytearray()
    for f in payload.get("fields") or []:
        out += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{_esc(f['name'])}\"\r\n\r\n".encode()
        out += str(f.get("value", "")).encode() + b"\r\n"
    for f in payload.get("files") or []:
        data = base64.b64decode(f.get("b64") or "", validate=True)
        ctype = _esc(f.get("type") or "application/octet-stream")
        out += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{_esc(f['name'])}\"; "
                f"filename=\"{_esc(f.get('filename') or 'file')}\"\r\nContent-Type: {ctype}\r\n\r\n").encode()
        out += data + b"\r\n"
    out += f"--{boundary}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={boundary}"


class B64UploadMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or (dict(scope["headers"]).get(b"x-pmc-upload") or b"").lower() != b"b64":
            return await self.app(scope, receive, send)
        chunks, size, more = [], 0, True
        while more:
            msg = await receive()
            body = msg.get("body", b"")
            size += len(body)
            if size > MAX_JSON_BYTES:
                return await self._error(send, 413, "File too large")
            chunks.append(body)
            more = msg.get("more_body", False)
        try:
            new_body, ctype = build_multipart(json.loads(b"".join(chunks)))
        except Exception:
            return await self._error(send, 400, "Malformed upload")
        headers = [(k, v) for k, v in scope["headers"] if k not in (b"content-type", b"content-length", b"x-pmc-upload")]
        headers += [(b"content-type", ctype.encode()), (b"content-length", str(len(new_body)).encode())]
        sent = False

        async def new_receive():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": new_body, "more_body": False}
            return await receive()

        await self.app({**scope, "headers": headers}, new_receive, send)

    @staticmethod
    async def _error(send, status, detail):
        body = json.dumps({"detail": detail}).encode()
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})
