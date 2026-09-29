import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./data/test_hybrid.db"
os.environ["JWT_SECRET"] = "test-secret-key-with-32-bytes-min"
os.environ["DISABLE_SCHEDULER"] = "true"
os.environ["DATA_SOURCE"] = "synthetic"

# Settings are instantiated at import, so wipe a previous test database first.
db_path = Path(__file__).resolve().parents[1] / "data" / "test_hybrid.db"
if db_path.exists():
    db_path.unlink()
