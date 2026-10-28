import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import auth, extras, records, stubs, system
from app.bootstrap import ensure_database
from app.core.errors import ApiError, envelope


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_database()
    if os.environ.get("AICTE_AUTO_IMPORT", "").lower() in ("1", "true", "yes"):
        from app import aicte_import  # the disk of a free host is wiped on deploy, so load them again each start

        aicte_import.start_job()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="SAMANVAY API", version="0.1.0",
        docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=lifespan,
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError):
        return envelope(request, exc.status, exc.code, exc.message, **exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        fields = [{"loc": [str(p) for p in e["loc"]], "msg": e["msg"]} for e in exc.errors()]
        return envelope(request, 422, "validation_error", "Request is invalid.", fields=fields)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        code = "not_found" if exc.status_code == 404 else "http_error"
        return envelope(request, exc.status_code, code, str(exc.detail))

    for r in (system.router, auth.router, extras.router, records.router, stubs.router):
        app.include_router(r, prefix="/api/v1")
    dist = Path(__file__).resolve().parents[2] / 'frontend' / 'app' / 'dist'
    if dist.exists():  # one-process demo: serve the built single-page app
        app.mount('/assets', StaticFiles(directory=dist / 'assets'), name='assets')

        @app.get('/{path:path}', include_in_schema=False)
        async def spa(path: str):
            f = (dist / path).resolve()
            if path and f.is_file() and dist in f.parents:
                return FileResponse(f)
            return FileResponse(dist / 'index.html')

    return app


app = create_app()
