import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "nfl-big-data-bowl-2027"
DB = Path(os.environ.get("NFL_DB_PATH", str(ROOT / "data" / "curated" / "nfl.duckdb")))
STATE_DIR = Path(os.environ.get("NFL_STATE_DIR", str(ROOT / "data" / "state")))
