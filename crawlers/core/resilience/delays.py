from __future__ import annotations
import asyncio
import random

async def human_delay(min_sec: float = 1.2, max_sec: float = 3.8) -> None:
    if max_sec < min_sec:
        min_sec, max_sec = max_sec, min_sec
    await asyncio.sleep(random.uniform(min_sec, max_sec))