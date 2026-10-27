"""Routes that are planned but not built answer 501 with their planned phase.

Every route in BACKEND_PLAN section 5 is now built, so the list is empty. The mechanism stays so that a
future route can be declared honestly before it exists.
"""
from fastapi import APIRouter, Request

from app.core.errors import envelope

router = APIRouter(tags=["planned"])

# (method, path, planned_phase)
PLANNED: list[tuple[str, str, str]] = []


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
