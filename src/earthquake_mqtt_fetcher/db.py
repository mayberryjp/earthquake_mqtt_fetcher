from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from earthquake_mqtt_fetcher.config import settings
from earthquake_mqtt_fetcher.logging import get_logger

log = get_logger("db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS earthquakes (
    eid TEXT NOT NULL,
    prefecture TEXT NOT NULL,
    prefecture_code TEXT,
    intensity INTEGER,
    max_intensity INTEGER,
    magnitude TEXT,
    region TEXT,
    source TEXT,
    observed_at TEXT,
    reported_at TEXT,
    created_at TEXT,
    PRIMARY KEY (eid, prefecture)
)
"""

_INSERT = """
INSERT OR REPLACE INTO earthquakes (
    eid, prefecture, prefecture_code, intensity, max_intensity,
    magnitude, region, source, observed_at, reported_at, created_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def get_connection() -> sqlite3.Connection:
    Path(settings.database).parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(settings.database, timeout=settings.sqlite_timeout)


def initialize() -> None:
    conn = get_connection()
    try:
        with conn:
            existing = [row[1] for row in conn.execute("PRAGMA table_info(earthquakes)")]
            if existing and "prefecture" not in existing:
                log.info("Migrating earthquakes table to per-prefecture schema")
                conn.execute("DROP TABLE earthquakes")
            conn.execute(_SCHEMA)
    finally:
        conn.close()


def _row(item: dict[str, Any]) -> tuple[Any, ...]:
    return (
        item.get("jma_eid"),
        item.get("prefecture_name"),
        item.get("prefecture_code"),
        item.get("prefecture_maxi"),
        item.get("max_intensity"),
        item.get("jma_mag"),
        item.get("jma_en_anm"),
        item.get("source"),
        item.get("jma_at"),
        item.get("jma_rdt"),
        item.get("mqtt_timestamp"),
    )


def record_earthquakes(items: Iterable[dict[str, Any]]) -> None:
    rows = [_row(item) for item in items]
    if not rows:
        return
    conn = get_connection()
    try:
        with conn:
            conn.executemany(_INSERT, rows)
    finally:
        conn.close()
