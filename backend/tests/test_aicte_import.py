from sqlalchemy import select

from app.aicte_import import load_rows
from app.db.models import Institution
from app.db.base import session_factory

# Same field order the public AICTE endpoint returns. Names here are invented for the test, not real records.
ROWS = [["1-100000001", "Test Institute of Engineering, Pune", "Some Road", "Pune", "Private", "No", "No", "9"],
        ["", "No id", "", "", "", "", "", ""]]


def test_rows_load_idempotently_and_are_marked_real():
    with session_factory()() as db:
        first = load_rows(db, ROWS, "Maharashtra")
        second = load_rows(db, ROWS, "Maharashtra")
        inst = db.scalar(select(Institution).where(Institution.aicte_id == "1-100000001"))
        assert first == {"added": 1, "updated": 0, "skipped": 1}
        assert second == {"added": 0, "updated": 1, "skipped": 1}
        assert inst.is_synthetic is False and inst.state == "Maharashtra" and inst.region_id
        db.delete(inst)
        db.commit()
