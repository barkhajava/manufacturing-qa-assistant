from langchain_core.tools import tool

from app.db import fetch_all, fetch_one


@tool
def list_lines() -> list[dict]:
    """List all production lines with their IDs and descriptions."""
    return fetch_all("SELECT line_id, description FROM production_lines ORDER BY line_id")


@tool
def query_metrics(line_id: str, start_date: str, end_date: str) -> dict:
    """Get total defect count, defect rate, and top defect type for a production line
    between start_date and end_date (inclusive). Dates must be YYYY-MM-DD strings."""
    row = fetch_one(
        """
        SELECT
            SUM(defect_count)                              AS defect_count,
            SUM(defect_count) * 1.0 / SUM(units_produced) AS defect_rate,
            top_defect_type
        FROM daily_metrics
        WHERE line_id = ? AND date BETWEEN ? AND ?
        GROUP BY top_defect_type
        ORDER BY COUNT(*) DESC
        LIMIT 1
        """,
        (line_id.upper(), start_date, end_date),
    )
    if not row:
        return {"error": f"No data found for line {line_id} between {start_date} and {end_date}"}

    return {
        "line_id": line_id.upper(),
        "start_date": start_date,
        "end_date": end_date,
        "defect_count": row["defect_count"],
        "defect_rate": round(row["defect_rate"], 4),
        "top_defect_type": row["top_defect_type"],
    }


@tool
def get_defect_trends(line_id: str, weeks: int) -> list[dict]:
    """Return week-over-week defect rates for a production line over the last N weeks.
    Each entry contains the ISO week label and the defect rate for that week."""
    rows = fetch_all(
        """
        SELECT
            strftime('%Y-W%W', date)                       AS week,
            SUM(defect_count) * 1.0 / SUM(units_produced) AS defect_rate
        FROM daily_metrics
        WHERE line_id = ?
          AND date >= date('now', ? || ' days')
        GROUP BY week
        ORDER BY week
        """,
        (line_id.upper(), f"-{weeks * 7}"),
    )
    return [
        {"week": r["week"], "defect_rate": round(r["defect_rate"], 4)}
        for r in rows
    ]
