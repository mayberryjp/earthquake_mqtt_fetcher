from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from typing import Any


@lru_cache(maxsize=1)
def load_prefectures() -> list[dict[str, Any]]:
    raw = files("earthquake_mqtt_fetcher").joinpath("data", "prefecture.json").read_text(
        encoding="utf-8"
    )
    data: list[dict[str, Any]] = json.loads(raw)
    return data


@lru_cache(maxsize=None)
def lookup_name(code: str | None) -> str | None:
    if not code:
        return None
    for prefecture in load_prefectures():
        if prefecture["iso_code"] == code:
            return str(prefecture["name"])
    return None
