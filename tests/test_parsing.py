from __future__ import annotations

from earthquake_mqtt_fetcher import jma

SAMPLE: list[dict[str, object]] = [
    {
        "ctt": "20260925084932",
        "eid": "20260925084652",
        "rdt": "2026-09-25T08:49:00+09:00",
        "at": "2026-09-25T08:46:00+09:00",
        "mag": "2.9",
        "maxi": "2",
        "en_anm": "Aizu, Fukushima Prefecture",
        "int": [
            {"code": "07", "maxi": "1", "city": [{"code": "0736800", "maxi": "1"}]},
            {"code": "04", "maxi": "2", "city": []},
        ],
    }
]


def test_parse_json_expands_every_prefecture() -> None:
    groups = jma.parse_json(SAMPLE, last_seen="20260101000000")
    assert len(groups) == 1
    names = {item["prefecture_name"] for item in groups[0]["items"]}
    assert names == {"Fukushima", "Miyagi"}


def test_parse_json_captures_intensity_and_magnitude() -> None:
    groups = jma.parse_json(SAMPLE, last_seen="0")
    fukushima = next(i for i in groups[0]["items"] if i["prefecture_name"] == "Fukushima")
    assert fukushima["prefecture_maxi"] == 1
    assert fukushima["max_intensity"] == 2
    assert fukushima["jma_mag"] == "2.9"
    assert fukushima["jma_en_anm"] == "Aizu, Fukushima Prefecture"


def test_parse_json_skips_already_seen() -> None:
    assert jma.parse_json(SAMPLE, last_seen="20260925084932") == []


def test_newest_json_marker() -> None:
    assert jma.newest_json_marker(SAMPLE) == "20260925084932"


def test_parse_intensity_handles_scale_suffixes() -> None:
    assert jma.parse_intensity("5+") == 5
    assert jma.parse_intensity("5-") == 5
    assert jma.parse_intensity("") is None
    assert jma.parse_intensity(None) is None
