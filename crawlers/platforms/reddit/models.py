"""Reddit-local intermediate structures."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class RawRedditPost(BaseModel):
    post_id: str
    title: str
    content: str = ""
    author: str = "[deleted]"
    score: Optional[int] = 0
    num_comments: int = 0
    url: str = ""
    permalink: str
    created_at: Optional[str] = None