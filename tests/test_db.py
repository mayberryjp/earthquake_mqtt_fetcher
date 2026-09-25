from __future__ import annotations

from pathlib import Path

from earthquake_mqtt_fetcher import db
from earthquake_mqtt_fetcher.config import settings


def _item(prefecture: str, code: str, intensity: int) -> dict[str, object]:
    return {
        "jma_eid": "E1",
        "prefecture_name": prefecture,
        "prefecture_code": code,
        "prefecture_maxi": intensity,
        "max_intensity": 4,
        "jma_mag": "5.0",
        "jma_en_anm": "Region",
        "source": "test",
        "jma_at": "2026-01-01T00:00:00+09:00",
        "jma_rdt": "2026-01-01T00:03:00+09:00",
        "mqtt_timestamp": "2026-01-01T00:05:00+09:00",
    }


def test_record_earthquakes_persists_one_row_per_prefecture(tmp_path: Path) -> None:
    settings.database = str(tmp_path / "test.db")
    db.initialize()
    db.record_earthquakes([_item("Fukushima", "07", 3), _item("Miyagi", "04", 2)])

    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT prefecture, intensity FROM earthquakes WHERE eid = ? ORDER BY prefecture",
            ("E1",),
        ).fetchall()
    finally:
        conn.close()

    assert rows == [("Fukushima", 3), ("Miyagi", 2)]


def test_record_earthquakes_replaces_on_reprocess(tmp_path: Path) -> None:
    settings.database = str(tmp_path / "test.db")
    db.initialize()
    db.record_earthquakes([_item("Fukushima", "07", 1)])
    db.record_earthquakes([_item("Fukushima", "07", 4)])

    conn = db.get_connection()
    try:
        rows = conn.execute("SELECT intensity FROM earthquakes WHERE eid = ?", ("E1",)).fetchall()
    finally:
        conn.close()

    assert rows == [(4,)]
