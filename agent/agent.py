"""Mini text-to-SQL agent: question -> LLM writes SQL -> run on DuckDB -> answer.

Versions:
    v0: prompt contains the fct_orders schema only
    v1: prompt contains schema + metric_definitions.md

Requires ANTHROPIC_API_KEY in .env (see .env.example).

Usage:
    python agent/agent.py "What is the overall on-time rate?" --version v1
    python agent/agent.py "..." --version v0 --explain      # also ask the LLM to explain the result
"""
import argparse
import os
import re
import sys
from pathlib import Path

import duckdb
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from run_sql import DB_PATH  # noqa: E402  (respects DELIVERY_DB)

METRICS_PATH = Path(__file__).parent / "metric_definitions.md"
MODEL = os.environ.get("AGENT_MODEL", "claude-sonnet-5-5")

load_dotenv(ROOT / ".env")
_client = None


def client():
    global _client
    if _client is None:
        from anthropic import Anthropic
        if not os.environ.get("ANTHROPIC_API_KEY"):
            sys.exit("ANTHROPIC_API_KEY not set — copy .env.example to .env and add your key.")
        _client = Anthropic()
    return _client


BASE_INSTRUCTIONS = """You are a data analyst who writes DuckDB SQL to answer business questions
about e-commerce deliveries in Brazil.

Rules:
- Query only the table described below.
- Return exactly one SQL query inside a ```sql``` code block and nothing else.
- Return only the columns needed to answer the question.
"""


def get_schema(con) -> str:
    rows = con.execute("DESCRIBE fct_orders").fetchall()
    return "Table fct_orders:\n" + "\n".join(f"- {r[0]} ({r[1]})" for r in rows)


def build_system_prompt(con, version: str) -> str:
    prompt = BASE_INSTRUCTIONS + "\n" + get_schema(con)
    if version == "v1":
        prompt += "\n\n# Business metric definitions\n" + METRICS_PATH.read_text()
    return prompt


def extract_sql(text: str) -> str:
    m = re.search(r"```(?:sql)?\s*(.*?)```", text, re.S | re.I)
    return (m.group(1) if m else text).strip().rstrip(";")


def call_llm(user: str, system: str | None = None, max_tokens: int = 4096) -> str:
    kwargs = {"system": system} if system else {}
    resp = client().messages.create(
        model=MODEL, max_tokens=max_tokens,
        messages=[{"role": "user", "content": user}], **kwargs,
    )
    # the response may start with a thinking block — keep only the text blocks
    return "".join(b.text for b in resp.content if b.type == "text")


def generate_sql(question: str, system: str) -> str:
    return extract_sql(call_llm(question, system))


def explain(question: str, sql: str, df) -> str:
    return call_llm(
        f"Question: {question}\n\nSQL:\n{sql}\n\nResult:\n{df.head(30).to_string()}\n\n"
        "Answer the question in 1-3 sentences using the result.",
        max_tokens=2048,
    )


def answer(question: str, version: str = "v1", con=None) -> dict:
    own = con is None
    con = con or duckdb.connect(str(DB_PATH), read_only=True)
    try:
        sql = generate_sql(question, build_system_prompt(con, version))
        try:
            df, error = con.execute(sql).fetchdf(), None
        except Exception as e:  # keep failures for the eval error analysis
            df, error = None, f"{type(e).__name__}: {e}"
        return {"question": question, "version": version, "sql": sql, "result": df, "error": error}
    finally:
        if own:
            con.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("question")
    p.add_argument("--version", choices=["v0", "v1"], default="v1")
    p.add_argument("--explain", action="store_true")
    a = p.parse_args()
    out = answer(a.question, a.version)
    print(out["sql"], "\n")
    if out["error"]:
        print(out["error"])
    else:
        print(out["result"])
        if a.explain:
            print("\n" + explain(a.question, out["sql"], out["result"]))
