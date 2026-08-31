"""Shared core models."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class CrawlTask(BaseModel):
    platform: str
    keyword: str
    baseline_since: str

    @field_validator("keyword")
    @classmethod
    def keyword_not_empty(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("keyword must not be empty")
        return v


class CleanPost(BaseModel):
    post_id: str
    platform: str
    keyword: str
    title: str
    content: str = ""
    author: str = "[unknown]"
    created_at: Optional[str] = None
    url: str = ""
    permalink: str
    score: Optional[int] = 0
    num_comments: int = 0
    fetched_at: str

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class CrawlOutcome(BaseModel):
    success: bool
    platform: str
    keyword: str
    crawl_type: Literal["initial", "incremental"] = "initial"
    baseline_since: Optional[str] = None
    until: Optional[str] = None
    checkpoint_found: bool = False
    checkpoint_updated: bool = False
    last_post_id: Optional[str] = None
    count: int = 0
    posts: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None
    debug_file: Optional[str] = None