from __future__ import annotations
from typing import Any, Iterable
from app.db import conn

async def fetch_one(query: str, params: Iterable[Any] = ()): 
    async with conn() as db:
        cur = await db.execute(query, tuple(params))
        return await cur.fetchone()

async def fetch_all(query: str, params: Iterable[Any] = ()): 
    async with conn() as db:
        cur = await db.execute(query, tuple(params))
        return await cur.fetchall()

async def execute(query: str, params: Iterable[Any] = ()): 
    async with conn() as db:
        cur = await db.execute(query, tuple(params))
        await db.commit()
        return cur.lastrowid
