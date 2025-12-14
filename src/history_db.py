# ==============================================================================
# Agentic Health Agent - History Database
# ==============================================================================
# Manages the SQLite database for logging all session history.
# This ensures that a permanent record of all user interactions and generated
# artifacts is kept, separate from the graph state checkpoints.
#
# Created by: Human Developer
# Last Updated: 2025
# ==============================================================================

import aiosqlite
import json
from datetime import datetime

import os
DB_NAME = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "history.sqlite")

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS history (
                thread_id TEXT PRIMARY KEY,
                user_intent TEXT,
                status TEXT,
                created_at TEXT,
                updated_at TEXT,
                final_artifact JSON
            )
        """)
        await db.commit()

async def create_history_entry(thread_id: str, intent: str):
    async with aiosqlite.connect(DB_NAME) as db:
        now = datetime.now().isoformat()
        await db.execute(
            "INSERT INTO history (thread_id, user_intent, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (thread_id, intent, "started", now, now)
        )
        await db.commit()

async def update_history_status(thread_id: str, status: str, artifact: dict = None):
    async with aiosqlite.connect(DB_NAME) as db:
        now = datetime.now().isoformat()
        if artifact:
            await db.execute(
                "UPDATE history SET status = ?, updated_at = ?, final_artifact = ? WHERE thread_id = ?",
                (status, now, json.dumps(artifact), thread_id)
            )
        else:
            await db.execute(
                "UPDATE history SET status = ?, updated_at = ? WHERE thread_id = ?",
                (status, now, thread_id)
            )
        await db.commit()

async def get_all_history():
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM history ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

