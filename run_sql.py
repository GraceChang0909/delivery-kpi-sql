"""Run the SQL files in sql/ in order against a local DuckDB file.

Usage:
    python run_sql.py              # run all sql/*.sql in order
    python run_sql.py 01 02        # run only files starting with these prefixes

Set DELIVERY_DB to use a different database file (default: delivery.duckdb).
Note: DuckDB allows one writer at a time — close the notebook connection first.
"""
import os
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("DELIVERY_DB", ROOT / "delivery.duckdb"))
SQL_DIR = ROOT / "sql"
RAW_DIR = ROOT / "data" / "raw"


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(DB_PATH), read_only=read_only)
    con.execute(f"SET file_search_path = '{RAW_DIR.as_posix()}'")
    return con


def split_statements(sql: str) -> list[str]:
    """Split a file on ';' (ignoring ';' inside comment lines) and drop comment-only chunks."""
    lines = [l.replace(";", ",") if l.strip().startswith("--") else l for l in sql.splitlines()]
    out = []
    for stmt in "\n".join(lines).split(";"):
        body = "\n".join(l for l in stmt.splitlines() if not l.strip().startswith("--")).strip()
        if body:
            out.append(stmt.strip())
    return out


def _body(stmt: str) -> str:
    return "\n".join(l for l in stmt.splitlines() if not l.strip().startswith("--")).strip()


def run_file(con, path: Path, verbose: bool = True) -> None:
    """Execute every statement in a .sql file. SELECT results are printed, DDL runs silently."""
    print(f"\n=== {path.name} ===")
    title = ""
    for stmt in split_statements(path.read_text()):
        comments = [l.strip("- ").strip() for l in stmt.splitlines() if l.strip().startswith("--")]
        if comments:
            title = comments[-1]
        body = _body(stmt)
        if body.upper().startswith(("SELECT", "WITH", "FROM")):
            if verbose:
                print(f"\n-- {title}")
                print(con.sql(body))
        else:
            con.execute(body)


def main(prefixes: list[str]) -> None:
    files = sorted(SQL_DIR.glob("*.sql"))
    if prefixes:
        files = [f for f in files if any(f.name.startswith(p) for p in prefixes)]
    con = connect()
    try:
        for f in files:
            run_file(con, f)
    finally:
        con.close()


if __name__ == "__main__":
    main(sys.argv[1:])
