import sqlite3

DB_PATH = "pm_speeches.db"

def show(table: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    rows = cur.execute(f"SELECT * FROM {table} LIMIT 50").fetchall()
    colnames = [d[0] for d in cur.description]
    print(f"\n=== {table} ===")
    print(colnames)
    for r in rows:
        print(r)
    conn.close()

if __name__ == "__main__":
    for t in ["pm_terms", "speeches", "chunks", "chunk_metrics"]:
        show(t)