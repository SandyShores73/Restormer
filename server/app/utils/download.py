from __future__ import annotations

import asyncio
from pathlib import Path

import httpx


async def download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        await asyncio.get_running_loop().run_in_executor(
            None, destination.write_bytes, response.content
        )
