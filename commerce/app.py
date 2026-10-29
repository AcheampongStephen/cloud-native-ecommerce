import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from commerce.basic_routes import identity_routes, notification_routes, product_routes
from commerce.config import Settings
from commerce.db import database
from commerce.operations import inventory_routes, payment_routes
from commerce.orders import order_routes
from commerce.security import hash_password

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("commerce")


def create_app(settings=None, client=None):
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app):
        yield
        if client is None:
            app.state.client.close()
        app.state.engine.dispose()

    app = FastAPI(title=f"Commerce {settings.service}", version="1.0.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.engine, app.state.sessions = database(settings.database_url)
    app.state.client = client or httpx.Client(follow_redirects=False)
    if settings.service == "identity":
        app.state.dummy_password = hash_password("dummy-account-password")

    @app.middleware("http")
    async def request_log(request: Request, call_next):
        started = time.perf_counter()
        request_id = uuid.uuid4().hex
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
        )
        logger.info(
            json.dumps(
                {
                    "service": settings.service,
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                }
            )
        )
        return response

    @app.exception_handler(OperationalError)
    async def database_error(request, error):
        logger.error(json.dumps({"service": settings.service, "event": "database_unavailable"}))
        return JSONResponse({"detail": "Database unavailable; retry safely"}, status_code=503)

    @app.get("/health/live")
    def live():
        return {"status": "ok", "service": settings.service}

    @app.get("/health/ready")
    def ready():
        with app.state.engine.connect() as connection:
            connection.execute(text("SELECT 1 FROM records LIMIT 1"))
        return {"status": "ready", "service": settings.service}

    routes = {
        "identity": identity_routes,
        "product": product_routes,
        "inventory": inventory_routes,
        "payment": payment_routes,
        "order": order_routes,
        "notification": notification_routes,
    }
    if settings.service in routes:
        routes[settings.service](app)
    else:
        gateway_routes(app)
    return app


def gateway_routes(app):
    prefixes = {
        "auth": "identity",
        "products": "product",
        "inventory": "inventory",
        "orders": "order",
        "notifications": "notification",
    }

    @app.api_route("/api/v1/{path:path}", methods=["GET", "POST", "PUT"])
    async def proxy(path: str, request: Request):
        service = prefixes.get(path.split("/")[0])
        if not service:
            raise HTTPException(404, "Unknown API route")
        # Only allow known public paths; never proxy internal service credentials.
        if any(part in ("..", ".") for part in path.split("/")) or "\\" in path:
            raise HTTPException(400, "Invalid path")
        content = await request.body()
        if len(content) > 64_000:
            raise HTTPException(413, "Request too large")
        headers = {
            key: request.headers[key]
            for key in ("authorization", "content-type", "idempotency-key")
            if key in request.headers
        }
        try:
            # Async client keeps the gateway event loop free during upstream calls.
            async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
                result = await client.request(
                    request.method,
                    app.state.settings.urls[service] + "/api/v1/" + path,
                    params=request.query_params,
                    content=content,
                    headers=headers,
                )
        except httpx.RequestError:
            raise HTTPException(503, "Upstream unavailable; retain your checkout retry key") from None
        return Response(
            content=result.content,
            status_code=result.status_code,
            media_type=result.headers.get("content-type", "application/json"),
        )

    app.mount(
        "/",
        StaticFiles(directory=Path(__file__).resolve().parent.parent / "frontend", html=True),
        name="frontend",
    )
