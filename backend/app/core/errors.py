from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, **details):
        self.status, self.code, self.message, self.details = status, code, message, details


def envelope(request: Request, status: int, code: str, message: str, **details) -> JSONResponse:
    rid = getattr(request.state, "request_id", None)
    body = {"error": {"code": code, "message": message, "details": details, "request_id": rid}}
    return JSONResponse(body, status_code=status)
