"""Centralized configuration from environment variables."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_group_id: str = "crawler-group"
    kafka_task_topic_prefix: str = "crawl-tasks"
    kafka_result_topic: str = "social.posts.raw"
    kafka_max_poll_interval_ms: int = 900_000

    redis_url: str = "redis://localhost:6379/0"
    redis_checkpoint_prefix: str = "crawler:checkpoint"
    redis_seen_prefix: str = "crawler:seen"
    redis_seen_ttl_seconds: int = 60 * 60 * 24 * 7

    browser_headless: bool = True
    navigation_timeout_ms: int = 45_000
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    )

    human_delay_min: float = 1.2
    human_delay_max: float = 3.8

    max_no_progress_attempts: int = 5
    max_pages_per_task: int = 200

    max_initial_lookback_hours: int = 2
    since_policy: Literal["reject", "clamp"] = "reject"

    max_retries: int = 3
    initial_backoff: float = 1.0
    max_backoff: float = 30.0

    platform: str = "reddit"
    debug_dir: str = "output/debug"

    @property
    def task_topic(self) -> str:
        return f"{self.kafka_task_topic_prefix}.{self.platform}"

    @property
    def debug_path(self) -> Path:
        return Path(self.debug_dir)


settings = Settings()