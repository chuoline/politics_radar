# scripts/doctor_env.py
import os
from pathlib import Path
from scripts._db import get_db_path

def main() -> None:
    print("POLR_DB_PATH(env) =", os.environ.get("POLR_DB_PATH"))
    db = get_db_path()
    print("DB_PATH(resolved) =", db)

    p = Path(db)
    if not p.exists():
        print("TIP: set POLR_DB_PATH or POLR_SSD_ROOT in .env, or export in shell.")
        raise SystemExit(f"ERROR: DB not found: {p}")

    print("OK: DB exists")

if __name__ == "__main__":
    main()