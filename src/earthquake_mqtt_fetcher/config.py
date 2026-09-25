from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="EARTHQUAKE_", extra="ignore")

    mqtt_host: str = Field("earthquake.mayberry.farm", validation_alias="MQTT_HOST")
    mqtt_port: int = Field(1883, validation_alias="MQTT_PORT")
    mqtt_username: str = Field("japan", validation_alias="MQTT_USERNAME")
    mqtt_password: str = Field("earthquake", validation_alias="MQTT_PASSWORD")

    database: str = Field("/data/earthquake.db", validation_alias="DATABASE")
    data_dir: str = Field("/data", validation_alias="DATA_DIR")
    sqlite_timeout: int = Field(20, validation_alias="SQLITE_TIMEOUT")

    send_mqtt: bool = Field(True, validation_alias="SEND_MQTT")
    load_file: bool = Field(False, validation_alias="LOAD_FILE")
    load_file_path: str = Field("test.json", validation_alias="LOAD_FILE_PATH")
    reset_every_run: bool = Field(False, validation_alias="RESET_EVERY_RUN")

    poll_interval_min: int = Field(30, validation_alias="POLL_INTERVAL_MIN")
    poll_interval_max: int = Field(60, validation_alias="POLL_INTERVAL_MAX")

    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")


settings = Settings()
