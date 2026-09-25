from __future__ import annotations

import time
from random import randrange
from typing import Any

from earthquake_mqtt_fetcher import __version__, db, jma
from earthquake_mqtt_fetcher.config import settings
from earthquake_mqtt_fetcher.logging import configure_logging, get_logger

log = get_logger("worker.atom")
NAME = "atom"


def run_once() -> None:
    state = jma.load_state(NAME)
    if not jma.feed_modified(jma.ATOM_URL, state):
        return
    feed = jma.fetch_atom()
    last_seen = state.get("last_seen")
    if not last_seen:
        state["last_seen"] = jma.newest_atom_marker(feed)
        jma.save_state(NAME, state)
        log.info("Baseline established; skipping historical earthquakes")
        return
    groups = jma.parse_atom(feed, last_seen)
    if not groups:
        jma.save_state(NAME, state)
        return
    published: list[dict[str, Any]] = []
    for group in groups:
        if settings.send_mqtt:
            for item in group["items"]:
                jma.publish_quake(item)
        db.record_earthquakes(group["items"])
        published.extend(group["items"])
        state["last_seen"] = group["marker"]
        jma.save_state(NAME, state)
    if settings.send_mqtt:
        jma.publish_any(published)


def main() -> None:
    configure_logging(settings.log_level)
    if settings.reset_every_run:
        jma.clear_state(NAME)
    db.initialize()
    log.info("Starting Atom worker version %s", __version__)
    while True:
        try:
            run_once()
        except Exception:
            log.exception("worker iteration failed")
        # randrange only staggers polling; it is not security-sensitive
        sleep_for = randrange(  # nosec B311
            settings.poll_interval_min, settings.poll_interval_max
        )
        log.info("Sleeping for %s seconds", sleep_for)
        time.sleep(sleep_for)
        if settings.send_mqtt:
            jma.reset_all_to_zero()


if __name__ == "__main__":
    main()
