from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import feedparser
import requests
import xmltodict

from earthquake_mqtt_fetcher import mqtt, prefectures
from earthquake_mqtt_fetcher.config import settings
from earthquake_mqtt_fetcher.logging import get_logger

log = get_logger("jma")

TOKYO = ZoneInfo("Asia/Tokyo")

JSON_URL = "https://www.jma.go.jp/bosai/quake/data/list.json"
ATOM_URL = "https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml"
ATOM_TITLES = {"震度速報", "震源・震度に関する情報"}

REQUEST_TIMEOUT = 10


# --- persistent state ------------------------------------------------------


def _state_path(name: str) -> Path:
    return Path(settings.data_dir) / f"{name}_state.json"


def load_state(name: str) -> dict[str, Any]:
    path = _state_path(name)
    if not path.exists():
        return {}
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return data
    except (ValueError, OSError):
        return {}


def save_state(name: str, state: dict[str, Any]) -> None:
    path = _state_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state), encoding="utf-8")


def clear_state(name: str) -> None:
    try:
        _state_path(name).unlink()
    except FileNotFoundError:
        pass


def feed_modified(url: str, state: dict[str, Any]) -> bool:
    response = requests.head(url, timeout=REQUEST_TIMEOUT)
    last_modified = response.headers.get("Last-Modified")
    if state.get("last_modified") != last_modified:
        log.info("New data available on %s (Last-Modified: %s)", url, last_modified)
        state["last_modified"] = last_modified
        return True
    return False


# --- shared parsing helpers ------------------------------------------------


def parse_intensity(value: Any) -> int | None:
    if value is None:
        return None
    digits = re.sub(r"\D", "", str(value))
    return int(digits) if digits else None


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _seconds_since(value: Any, now: datetime) -> float | None:
    parsed = _parse_datetime(value)
    return (now - parsed).total_seconds() if parsed else None


def _seconds_between(start: Any, end: Any) -> float | None:
    start_dt = _parse_datetime(start)
    end_dt = _parse_datetime(end)
    if start_dt is None or end_dt is None:
        return None
    return (end_dt - start_dt).total_seconds()


def build_item(
    *,
    eid: Any,
    magnitude: Any,
    overall_maxi: Any,
    region: Any,
    ctt: Any,
    reported_at: Any,
    observed_at: Any,
    code: Any,
    pref_maxi: Any,
    source: str,
) -> dict[str, Any]:
    now = datetime.now(TOKYO)
    return {
        "jma_eid": eid,
        "jma_mag": magnitude,
        "jma_maxi": overall_maxi,
        "jma_en_anm": region,
        "jma_ctt": ctt,
        "jma_rdt": reported_at,
        "jma_at": observed_at,
        "prefecture_code": code,
        "prefecture_name": prefectures.lookup_name(code),
        "prefecture_maxi": parse_intensity(pref_maxi),
        "max_intensity": parse_intensity(overall_maxi),
        "mqtt_timestamp": now.isoformat(),
        "mqtt_uuid": str(uuid.uuid4()),
        "source": source,
        "issued_to_mqtt_delay": _seconds_since(reported_at, now),
        "jma_observed_to_issued_delay": _seconds_between(observed_at, reported_at),
    }


# --- JSON feed -------------------------------------------------------------


def fetch_json(url: str = JSON_URL) -> list[dict[str, Any]]:
    if settings.load_file:
        raw = Path(settings.load_file_path).read_text(encoding="utf-8")
        local: list[dict[str, Any]] = json.loads(raw)
        return local
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    payload: list[dict[str, Any]] = response.json()
    return payload


def newest_json_marker(raw: list[dict[str, Any]]) -> str:
    return max((str(quake.get("ctt", "")) for quake in raw), default="")


def parse_json(raw: list[dict[str, Any]], last_seen: str) -> list[dict[str, Any]]:
    new_quakes = [quake for quake in raw if str(quake.get("ctt", "")) > str(last_seen)]
    new_quakes.sort(key=lambda quake: str(quake.get("ctt", "")))
    groups: list[dict[str, Any]] = []
    for quake in new_quakes:
        items: list[dict[str, Any]] = []
        for pref in quake.get("int") or []:
            if prefectures.lookup_name(pref.get("code")) is None:
                continue
            items.append(
                build_item(
                    eid=quake.get("eid"),
                    magnitude=quake.get("mag"),
                    overall_maxi=quake.get("maxi"),
                    region=quake.get("en_anm"),
                    ctt=quake.get("ctt"),
                    reported_at=quake.get("rdt"),
                    observed_at=quake.get("at"),
                    code=pref.get("code"),
                    pref_maxi=pref.get("maxi"),
                    source=JSON_URL,
                )
            )
        if items:
            groups.append({"marker": str(quake.get("ctt", "")), "items": items})
    return groups


# --- Atom feed -------------------------------------------------------------


def fetch_atom(url: str = ATOM_URL) -> Any:
    return feedparser.parse(url)


def fetch_atom_entry(url: str) -> bytes:
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.content


def newest_atom_marker(feed: Any) -> str:
    return max(
        (
            str(entry.get("updated", ""))
            for entry in feed.entries
            if entry.get("title") in ATOM_TITLES
        ),
        default="",
    )


def _get_in(data: Any, *keys: str) -> Any:
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _atom_magnitude(body: dict[str, Any]) -> Any:
    magnitude = _get_in(body, "Earthquake", "jmx_eb:Magnitude")
    if isinstance(magnitude, dict):
        return magnitude.get("#text")
    return magnitude


def parse_atom_xml(xml_text: str | bytes) -> list[dict[str, Any]]:
    document = xmltodict.parse(xml_text, force_list={"Pref"})
    head = _get_in(document, "Report", "Head") or {}
    body = _get_in(document, "Report", "Body") or {}
    observation = _get_in(body, "Intensity", "Observation") or {}
    prefs = observation.get("Pref")
    if not prefs:
        return []
    region = _get_in(body, "Earthquake", "Hypocenter", "Area", "Name")
    items: list[dict[str, Any]] = []
    for pref in prefs:
        if prefectures.lookup_name(pref.get("Code")) is None:
            continue
        items.append(
            build_item(
                eid=head.get("EventID"),
                magnitude=_atom_magnitude(body),
                overall_maxi=observation.get("MaxInt"),
                region=region,
                ctt=None,
                reported_at=head.get("ReportDateTime"),
                observed_at=head.get("TargetDateTime"),
                code=pref.get("Code"),
                pref_maxi=pref.get("MaxInt"),
                source=ATOM_URL,
            )
        )
    return items


def parse_atom(feed: Any, last_seen: str) -> list[dict[str, Any]]:
    entries = [
        entry
        for entry in feed.entries
        if entry.get("title") in ATOM_TITLES and str(entry.get("updated", "")) > str(last_seen)
    ]
    entries.sort(key=lambda entry: str(entry.get("updated", "")))
    groups: list[dict[str, Any]] = []
    for entry in entries:
        try:
            xml_text = fetch_atom_entry(entry.get("id"))
            items = parse_atom_xml(xml_text)
        except (requests.RequestException, ValueError):
            log.exception("Failed to fetch or parse atom entry %s", entry.get("id"))
            continue
        if items:
            groups.append({"marker": str(entry.get("updated", "")), "items": items})
    return groups


# --- publishing ------------------------------------------------------------


def _state_topic(name: str) -> str:
    return f"homeassistant/sensor/japan_earthquake_{name.lower()}/state"


def publish_quake(item: dict[str, Any]) -> None:
    name = item["prefecture_name"]
    messages: list[mqtt.Message] = [(f"earthquake/{name.lower()}", json.dumps(item), False)]
    if item.get("prefecture_maxi") is not None:
        messages.append((_state_topic(name), item["prefecture_maxi"], False))
    log.info("Earthquake %s in %s intensity %s", item.get("jma_eid"), name, item.get("prefecture_maxi"))
    mqtt.publish(messages)


def publish_any(items: list[dict[str, Any]]) -> None:
    intensities = [item["prefecture_maxi"] for item in items if item.get("prefecture_maxi") is not None]
    if not intensities:
        return
    highest = max(intensities)
    log.info("Publishing max intensity (Any) -> %s", highest)
    mqtt.publish([(_state_topic("Any"), highest, False)])


def reset_all_to_zero() -> None:
    messages: list[mqtt.Message] = [
        (_state_topic(pref["name"]), 0, False) for pref in prefectures.load_prefectures()
    ]
    messages.append((_state_topic("Any"), 0, False))
    mqtt.publish(messages)
