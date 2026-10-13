"""Bound multipart bodies before they can spool unbounded data to disk."""

from fastapi import HTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_REQUEST_BYTES = 12 * 1024 * 1024  # Includes multipart fields and overhead.


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        try:
            size = int(headers.get(b"content-length", b"0"))
            if size < 0:
                raise ValueError
        except ValueError:
            await JSONResponse({"detail": "Invalid Content-Length."}, 400)(
                scope, receive, send
            )
            return
        if size > MAX_REQUEST_BYTES:
            await JSONResponse({"detail": "Request exceeds the 12 MiB limit."}, 413)(
                scope, receive, send
            )
            return
        received = 0

        async def bounded_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > MAX_REQUEST_BYTES:
                    raise HTTPException(413, "Request exceeds the 12 MiB limit.")
            return message

        await self.app(scope, bounded_receive, send)
