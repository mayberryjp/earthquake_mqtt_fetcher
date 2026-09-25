# Earthquake MQTT Fetcher

Fetches recent earthquake information from the Japan Meteorological Agency (JMA)
and publishes per-prefecture seismic intensity to MQTT for Home Assistant.

Two feeds are polled by two workers that run together in a single container,
managed by `supervisord`:

- **json worker** — `https://www.jma.go.jp/bosai/quake/data/list.json`
- **atom worker** — `https://www.data.jma.go.jp/developer/xml/feed/eqvol.xml`

## Layout

```
src/earthquake_mqtt_fetcher/
  config.py        Pydantic settings (env-driven)
  logging.py       Logging helper
  db.py            SQLite connection + schema (one row per eid + prefecture)
  mqtt.py          MQTT transport
  prefectures.py   Prefecture ISO-code lookup
  jma.py           Feed fetch/parse + earthquake publishing
  discovery.py     Home Assistant MQTT discovery (runs once at startup)
  workers/
    json_worker.py
    atom_worker.py
data/prefecture.json
supervisord.conf
Dockerfile
docker-compose.yml
```

## Configuration

All configuration comes from environment variables (defined in
`docker-compose.yml`, no `.env` file):

| Variable | Default | Description |
| --- | --- | --- |
| `MQTT_HOST` | `earthquake.mayberry.farm` | MQTT broker host |
| `MQTT_PORT` | `1883` | MQTT broker port |
| `MQTT_USERNAME` / `MQTT_PASSWORD` | `japan` / `earthquake` | MQTT credentials |
| `DATABASE` | `/data/earthquake.db` | SQLite database path |
| `DATA_DIR` | `/data` | Directory for the DB and per-feed state |
| `SEND_MQTT` | `1` | Publish to MQTT (`0` to disable) |
| `LOAD_FILE` | `0` | Read `LOAD_FILE_PATH` instead of the live JSON feed |
| `RESET_EVERY_RUN` | `0` | Clear saved state on startup |
| `POLL_INTERVAL_MIN` / `POLL_INTERVAL_MAX` | `30` / `60` | Poll sleep range (seconds) |
| `LOG_LEVEL` | `INFO` | Log level |

## What gets stored

The `earthquakes` table keeps **one row per (earthquake, prefecture)** so every
affected prefecture is recorded:

`eid, prefecture, prefecture_code, intensity, max_intensity, magnitude, region,
source, observed_at, reported_at, created_at`

On first start against an old database, the previous single-row-per-`eid` table
is dropped and recreated automatically.

## Home Assistant

`discovery.py` publishes retained MQTT discovery configs for all 47 prefectures
plus an `Any` aggregate. Entities are named `Japan Earthquake <Prefecture>` and
grouped under a single `Japan Earthquake Intensity` device. Topics and
`unique_id`s are unchanged from previous versions, so existing entities are not
duplicated.

## Local development

No virtualenv is used; install into the global interpreter.

```
pip install .[dev]     # or: make install
ruff check .           # make lint
mypy src               # make typecheck
pytest -q              # make test
bandit -r src
```

## Run in Docker

```
docker build -t earthquake-mqtt-fetcher:dev .
docker compose up
```

The container runs as a non-root user (`appuser`), so the host directory bound
to `/data` must be writable by it (uid 1000), e.g.
`sudo chown -R 1000:1000 /earthquake_mqtt_fetcher`.

v2.0.0
