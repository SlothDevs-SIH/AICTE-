"""Commands: seed | verify-audit | openapi | evaluate (python -m app.cli <command>)."""
import json
import sys
from pathlib import Path

from app.db.base import Base, get_engine, session_factory

ROOT = Path(__file__).resolve().parent.parent


def cmd_seed(reset: bool = True) -> None:
    from app import seed as s
    import app.db.models  # noqa: F401

    engine = get_engine()
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    Path(ROOT / "data").mkdir(exist_ok=True)
    with session_factory()() as db:
        truth = s.seed(db, 42, ROOT / "data" / "ground_truth.json")
    print(f"seeded: {len(truth['scenarios'])} planted scenarios; ground truth written")


def cmd_openapi() -> None:
    from app.main import app

    (ROOT / "openapi.json").write_text(json.dumps(app.openapi(), indent=2), encoding="utf-8")
    print("wrote openapi.json")


def cmd_verify() -> None:
    from app.core.audit import verify_chain

    with session_factory()() as db:
        print(json.dumps(verify_chain(db), indent=2))


def cmd_evaluate() -> None:
    from app.evaluate import run

    run()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"seed": cmd_seed, "openapi": cmd_openapi, "verify-audit": cmd_verify, "evaluate": cmd_evaluate}.get(
        cmd, lambda: print(__doc__))()
