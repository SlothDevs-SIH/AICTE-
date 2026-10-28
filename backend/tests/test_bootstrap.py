import os
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent


def test_fresh_database_is_created_and_seeded_once():
    with tempfile.TemporaryDirectory() as d:
        env = {**os.environ, "DATABASE_URL": f"sqlite:///{Path(d, 'fresh.db').as_posix()}",
               "SECRET_KEY": "x" * 20, "PII_ENCRYPTION_KEY": "y" * 20}
        code = f"import sys; sys.path.insert(0, r'{BACKEND}'); from app.bootstrap import ensure_database as e; print(e()); print(e())"
        out = subprocess.run([sys.executable, "-I", "-c", code], env=env, cwd=d, capture_output=True, text=True, timeout=300)
        assert out.returncode == 0, out.stderr[-800:]
        assert out.stdout.split() == ["seeded", "existing"]
