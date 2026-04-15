from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="IMC_", case_sensitive=False)

    app_name: str = "IMC Prosperity Suite"
    data_dir: Path = Path(".data")
    session_ttl_seconds: int = 60 * 60 * 6
    max_upload_mb: int = 512
    downsample_default_points: int = 8000
    csv_separator: str = ";"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "sessions").mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
