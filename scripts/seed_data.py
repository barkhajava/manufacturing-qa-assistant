"""
Generates 90 days of mock manufacturing quality data into SQLite.

Realistic patterns baked in:
- Line B: rising defect trend in the last 2 weeks
- Line C: 3-day spike ~6 weeks ago
- Lines A and D: stable throughout
"""

import sqlite3
import random
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "manufacturing.db"

LINES = {
    "A": "Body Assembly - North",
    "B": "Paint & Coating - East",
    "C": "Electronics Integration - West",
    "D": "Final Assembly - South",
}

DEFECT_TYPES = [
    "surface_scratch",
    "misalignment",
    "weld_crack",
    "paint_bubble",
    "connector_fault",
]

TODAY = date.today()
START = TODAY - timedelta(days=89)


def defect_rate_for(line_id: str, day: date) -> float:
    """Return a defect rate (0.0–1.0) based on the line's story."""
    days_ago = (TODAY - day).days

    if line_id == "B":
        # Stable ~3%, then rises sharply in the last 14 days
        if days_ago <= 14:
            return 0.03 + (14 - days_ago) * 0.004 + random.uniform(-0.005, 0.005)
        return 0.03 + random.uniform(-0.005, 0.005)

    if line_id == "C":
        # Spike 38–42 days ago (roughly 6 weeks back)
        if 38 <= days_ago <= 41:
            return 0.12 + random.uniform(-0.01, 0.01)
        return 0.025 + random.uniform(-0.004, 0.004)

    if line_id == "A":
        return 0.02 + random.uniform(-0.003, 0.003)

    # Line D
    return 0.018 + random.uniform(-0.003, 0.003)


def seed():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS production_lines")
    cur.execute("DROP TABLE IF EXISTS daily_metrics")

    cur.execute("""
        CREATE TABLE production_lines (
            line_id     TEXT PRIMARY KEY,
            description TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE daily_metrics (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            date            TEXT NOT NULL,
            line_id         TEXT NOT NULL,
            units_produced  INTEGER NOT NULL,
            defect_count    INTEGER NOT NULL,
            top_defect_type TEXT NOT NULL,
            FOREIGN KEY (line_id) REFERENCES production_lines(line_id)
        )
    """)

    for line_id, description in LINES.items():
        cur.execute(
            "INSERT INTO production_lines VALUES (?, ?)", (line_id, description)
        )

    rows = []
    current = START
    while current <= TODAY:
        for line_id in LINES:
            units = random.randint(800, 1200)
            rate = max(0.0, defect_rate_for(line_id, current))
            defects = round(units * rate)
            top_defect = random.choice(DEFECT_TYPES)
            rows.append((current.isoformat(), line_id, units, defects, top_defect))
        current += timedelta(days=1)

    cur.executemany(
        "INSERT INTO daily_metrics (date, line_id, units_produced, defect_count, top_defect_type) "
        "VALUES (?, ?, ?, ?, ?)",
        rows,
    )

    conn.commit()
    conn.close()
    print(f"Seeded {len(rows)} records into {DB_PATH}")


if __name__ == "__main__":
    seed()
