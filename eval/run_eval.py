"""Run all eval questions through agent v0 and v1 and score them.

Usage:
    python eval/run_eval.py               # full eval (needs ANTHROPIC_API_KEY)
    python eval/run_eval.py --check-gold  # only run gold SQL and self-test the matcher (no API calls)

Writes eval/results.csv and eval/summary.md.
"""
import argparse
import datetime as dt
import math
import sys
from pathlib import Path

import duckdb
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agent"))
from agent import DB_PATH, answer  # noqa: E402

HERE = Path(__file__).parent
QUESTIONS = HERE / "questions.yaml"
VERSIONS = ["v0", "v1"]


# ---------- matching ----------
def _norm_col(s: pd.Series):
    """Return (kind, sorted values) for a column; kind in num/str/skip."""
    vals = s.tolist()
    if pd.api.types.is_bool_dtype(s):
        return "skip", None
    if pd.api.types.is_numeric_dtype(s):
        return "num", sorted(float(v) for v in vals if v is not None and not (isinstance(v, float) and math.isnan(v)))
    if pd.api.types.is_datetime64_any_dtype(s) or any(isinstance(v, (dt.date, pd.Timestamp)) for v in vals):
        return "str", sorted(str(v)[:10] for v in vals)
    return "str", sorted(str(v).strip().upper() for v in vals)


def _num_equal(a: list[float], b: list[float]) -> bool:
    if len(a) != len(b):
        return False
    close = lambda x, y: abs(x - y) <= max(0.011, 0.001 * abs(y))
    for scale in (1, 100, 0.01):  # accept 0.9328 vs 93.28 (rate as fraction vs percent)
        if all(close(x * scale, y) for x, y in zip(a, b)):
            return True
    return False


def results_match(pred: pd.DataFrame | None, gold: pd.DataFrame) -> bool:
    """Value-based match, ignoring column names, column order and row order.

    - Row counts must be equal.
    - Every numeric / text / date column in gold must have a column in pred with the same
      multiset of values (numbers within ±0.011 or 0.1%, fraction-vs-percent accepted).
    - Boolean gold columns (e.g. is_cross_state) are not required. Extra pred columns are fine.
    """
    if pred is None or len(pred) != len(gold):
        return False
    pred_cols = [_norm_col(pred[c]) for c in pred.columns]
    for c in gold.columns:
        kind, gvals = _norm_col(gold[c])
        if kind == "skip":
            continue
        ok = any(
            pk == kind and (_num_equal(pv, gvals) if kind == "num" else pv == gvals)
            for pk, pv in pred_cols
        )
        if not ok:
            return False
    return True


# ---------- runs ----------
def check_gold(con, questions) -> None:
    for q in questions:
        gold = con.execute(q["gold_sql"]).fetchdf()
        assert results_match(gold, gold), q["id"]
        print(f"{q['id']:4} {len(gold)} row(s) | {gold.to_dict('records')}")
    # matcher self-tests
    g = pd.DataFrame({"is_cross_state": [True, False], "late_rate_pct": [7.98, 4.48]})
    assert results_match(pd.DataFrame({"route": ["x", "y"], "r": [0.0798, 0.0448]}), g)
    assert results_match(pd.DataFrame({"r": [4.4812, 7.9789]}), g)
    assert not results_match(pd.DataFrame({"r": [7.98]}), g)
    assert not results_match(pd.DataFrame({"r": [8.5, 4.48]}), g)
    print("\nAll gold queries ran, matcher self-tests passed.")


def run(con, questions) -> pd.DataFrame:
    rows = []
    for q in questions:
        gold = con.execute(q["gold_sql"]).fetchdf()
        for v in VERSIONS:
            out = answer(q["question"], v, con=con)
            ok = out["error"] is None and results_match(out["result"], gold)
            rows.append({
                "id": q["id"], "category": q["category"], "version": v, "question": q["question"],
                "correct": ok, "error": out["error"], "pred_sql": out["sql"],
                "pred_result": None if out["result"] is None else out["result"].head(10).to_dict("records"),
                "gold_result": gold.to_dict("records"),
            })
            print(f"{q['id']:4} {v}: {'OK' if ok else 'X '}  {out['error'] or ''}")
    return pd.DataFrame(rows)


def summarise(df: pd.DataFrame) -> str:
    pivot = (df.pivot_table(index="version", columns="category", values="correct", aggfunc="sum")
               .reindex(columns=["simple", "kpi", "comparison"]))
    pivot["overall"] = df.groupby("version")["correct"].sum()
    lines = ["| Version | Simple (5) | KPI (5) | Comparison (5) | Overall (15) |", "|---|---|---|---|---|"]
    for v, r in pivot.iterrows():
        lines.append(f"| {v} | {int(r.simple)}/5 | {int(r.kpi)}/5 | {int(r.comparison)}/5 | "
                     f"{int(r.overall)}/15 ({r.overall / 15:.0%}) |")
    wrong = df[~df.correct]
    lines += ["", "## Failures", ""]
    for _, r in wrong.iterrows():
        lines += [f"### {r.id} {r.version}: {r.question}",
                  f"- error: {r.error}" if r.error else f"- predicted: `{r.pred_result}`",
                  f"- gold: `{r.gold_result}`", "```sql", r.pred_sql, "```", ""]
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--check-gold", action="store_true")
    a = p.parse_args()
    questions = yaml.safe_load(QUESTIONS.read_text())
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        if a.check_gold:
            check_gold(con, questions)
            return
        df = run(con, questions)
    finally:
        con.close()
    df.to_csv(HERE / "results.csv", index=False)
    md = summarise(df)
    (HERE / "summary.md").write_text(md)
    print("\n" + md.split("\n## Failures")[0])
    print(f"\nDetails: {HERE / 'results.csv'} and {HERE / 'summary.md'}")


if __name__ == "__main__":
    main()
