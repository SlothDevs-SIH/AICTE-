"""Every route in BACKEND_PLAN section 5 that is not built yet answers 501 with its planned phase."""
from fastapi import APIRouter, Request

from app.core.errors import envelope

router = APIRouter(tags=["planned"])

# (method, path, planned_phase)
PLANNED: list[tuple[str, str, str]] = [
    ("GET", "/stream", "B2"),
    ("POST", "/institutions", "B2"),
    ("PATCH", "/institutions/{id}", "B2"),
    ("DELETE", "/institutions/{id}/aliases/{alias_id}", "B2"),
    ("GET", "/institutions/{id}/risk", "B5"),
    ("PATCH", "/complaints/{id}", "B2"),
    ("POST", "/complaints/{id}/attachments", "B2"),
    ("GET", "/complaints/{id}/overlaps", "B3"),
    ("POST", "/overlaps/{id}/summary", "B5"),
    ("GET", "/overlaps/{id}/brief.pdf", "B5"),
    ("GET", "/coordination", "B4"),
    ("POST", "/coordination", "B4"),
    ("GET", "/coordination/{id}", "B4"),
    ("POST", "/coordination/{id}/messages", "B4"),
    ("POST", "/coordination/{id}/resolve", "B4"),
    ("GET", "/notifications", "B4"),
    ("POST", "/notifications/{id}/read", "B4"),
    ("GET", "/clusters", "B5"),
    ("GET", "/risk/ranking", "B5"),
    ("POST", "/ask", "B5"),
    ("POST", "/imports", "B2"),
    ("POST", "/imports/{id}/map", "B2"),
    ("POST", "/imports/{id}/dry-run", "B2"),
    ("POST", "/imports/{id}/commit", "B2"),
    ("GET", "/imports/{id}", "B2"),
    ("GET", "/admin/settings", "B4"),
    ("PUT", "/admin/settings/{key}", "B4"),
    ("GET", "/admin/users", "B4"),
    ("POST", "/admin/users", "B4"),
    ("PATCH", "/admin/users/{id}", "B4"),
    ("GET", "/admin/scenarios", "B5"),
    ("POST", "/admin/scenarios/{id}/load", "B5"),
    ("POST", "/admin/ai/{feature}", "B4"),
]


def _make(phase: str):
    async def handler(request: Request):
        return envelope(
            request, 501, "not_implemented",
            f"This endpoint is planned for phase {phase}.", planned_phase=phase,
        )

    return handler


for _method, _path, _phase in PLANNED:
    router.add_api_route(
        _path, _make(_phase), methods=[_method],
        summary=f"[planned {_phase}] {_method} {_path}",
    )
