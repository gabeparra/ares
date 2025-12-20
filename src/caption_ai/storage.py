"""SQLite storage for transcript segments."""

import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator

from caption_ai.bus import Segment
from caption_ai.config import config


class Storage:
    """SQLite storage manager for segments."""

    def __init__(self, db_path: Path | None = None) -> None:
        """Initialize storage with database path."""
        self.db_path = db_path or config.storage_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def init(self) -> None:
        """Initialize database schema."""
        async with aiosqlite.connect(self.db_path) as db:
            # Sessions metadata (chat sessions)
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT,
                    pinned INTEGER NOT NULL DEFAULT 0,
                    model TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS segments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    text TEXT NOT NULL,
                    speaker TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON segments(timestamp)
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    summary TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    message TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_conversations_session
                ON conversations(session_id, created_at)
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.commit()

    async def ensure_session(self, session_id: str) -> None:
        """Ensure a session exists in sessions table."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR IGNORE INTO sessions (session_id)
                VALUES (?)
                """,
                (session_id,),
            )
            await db.commit()

    async def update_session(
        self,
        session_id: str,
        title: str | None = None,
        pinned: bool | None = None,
        model: str | None = None,
    ) -> None:
        """Update session metadata."""
        await self.ensure_session(session_id)
        updates: list[str] = []
        params: list = []

        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if pinned is not None:
            updates.append("pinned = ?")
            params.append(1 if pinned else 0)
        if model is not None:
            updates.append("model = ?")
            params.append(model)

        if not updates:
            return

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(session_id)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                f"""
                UPDATE sessions
                SET {", ".join(updates)}
                WHERE session_id = ?
                """,
                params,
            )
            await db.commit()

    async def get_session(self, session_id: str) -> dict[str, str | int | None] | None:
        """Get session metadata."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT session_id, title, pinned, model, created_at, updated_at
                FROM sessions
                WHERE session_id = ?
                """,
                (session_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                return {
                    "session_id": row["session_id"],
                    "title": row["title"],
                    "pinned": int(row["pinned"] or 0),
                    "model": row["model"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }

    async def delete_session(self, session_id: str) -> None:
        """Delete session metadata and all conversation messages for that session."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
            await db.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            await db.commit()

    async def append(self, segment: Segment) -> None:
        """Append a segment to storage."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO segments (timestamp, text, speaker)
                VALUES (?, ?, ?)
                """
                ,
                (
                    segment.timestamp.isoformat(),
                    segment.text,
                    segment.speaker,
                ),
            )
            await db.commit()

    async def fetch_recent(
        self, limit: int = 10, since: datetime | None = None
    ) -> AsyncIterator[Segment]:
        """Fetch recent segments."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = "SELECT timestamp, text, speaker FROM segments"
            params: list = []

            if since:
                query += " WHERE timestamp >= ?"
                params.append(since.isoformat())

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            async with db.execute(query, params) as cursor:
                async for row in cursor:
                    yield Segment(
                        timestamp=datetime.fromisoformat(row["timestamp"]),
                        text=row["text"],
                        speaker=row["speaker"],
                    )

    async def append_summary(self, summary: str) -> None:
        """Append a summary to storage."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO summaries (summary)
                VALUES (?)
                """,
                (summary,),
            )
            await db.commit()

    async def get_latest_summary(self) -> str | None:
        """Get the latest summary."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT summary FROM summaries ORDER BY created_at DESC LIMIT 1"
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return row["summary"]
                return None

    async def save_conversation(
        self, session_id: str, role: str, message: str
    ) -> None:
        """Save a conversation message."""
        await self.ensure_session(session_id)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO conversations (session_id, role, message)
                VALUES (?, ?, ?)
                """,
                (session_id, role, message),
            )
            await db.execute(
                """
                UPDATE sessions
                SET updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
                """,
                (session_id,),
            )
            await db.commit()

    async def get_conversation_history(
        self, session_id: str, limit: int = 50
    ) -> list[dict[str, str]]:
        """Get conversation history for a session."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT role, message, created_at
                FROM conversations
                WHERE session_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (session_id, limit),
            ) as cursor:
                conversations = []
                async for row in cursor:
                    conversations.append({
                        "role": row["role"],
                        "message": row["message"],
                        "created_at": row["created_at"],
                    })
                return conversations

    async def get_all_conversations(
        self, limit: int = 100
    ) -> list[dict[str, str]]:
        """Get recent conversations from all sessions."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT session_id, role, message, created_at
                FROM conversations
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ) as cursor:
                conversations = []
                async for row in cursor:
                    conversations.append({
                        "session_id": row["session_id"],
                        "role": row["role"],
                        "message": row["message"],
                        "created_at": row["created_at"],
                    })
                return list(reversed(conversations))

    async def get_conversation_sessions(self) -> list[str]:
        """Get list of unique session IDs ordered by most recent message."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # Get sessions from conversations table (sessions with messages)
            async with db.execute(
                """
                SELECT session_id, MAX(created_at) as last_message
                FROM conversations
                GROUP BY session_id
                ORDER BY last_message DESC
                """
            ) as cursor:
                sessions_from_conversations = []
                async for row in cursor:
                    sessions_from_conversations.append(row["session_id"])
            
            # Also get sessions from sessions table (may not have messages yet)
            async with db.execute(
                """
                SELECT session_id FROM sessions
                WHERE session_id NOT IN (
                    SELECT DISTINCT session_id FROM conversations
                )
                ORDER BY created_at DESC
                """
            ) as cursor:
                sessions_from_metadata = []
                async for row in cursor:
                    sessions_from_metadata.append(row["session_id"])
            
            # Combine and deduplicate
            all_sessions = list(dict.fromkeys(sessions_from_conversations + sessions_from_metadata))
            return all_sessions

    async def list_sessions(self, limit: int = 100) -> list[dict[str, str | int | None]]:
        """List sessions with metadata, pinned first, then most recently updated."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT
                    s.session_id,
                    s.title,
                    s.pinned,
                    s.model,
                    s.created_at,
                    s.updated_at,
                    (
                        SELECT MAX(c.created_at)
                        FROM conversations c
                        WHERE c.session_id = s.session_id
                    ) AS last_message_at
                FROM sessions s
                ORDER BY s.pinned DESC, COALESCE(last_message_at, s.updated_at) DESC
                LIMIT ?
                """,
                (limit,),
            ) as cursor:
                rows: list[dict[str, str | int | None]] = []
                async for row in cursor:
                    rows.append({
                        "session_id": row["session_id"],
                        "title": row["title"],
                        "pinned": int(row["pinned"] or 0),
                        "model": row["model"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                        "last_message_at": row["last_message_at"],
                    })
                return rows

    async def export_session_markdown(self, session_id: str, limit: int = 1000) -> str:
        """Export a session to Markdown."""
        session = await self.get_session(session_id)
        title = (session or {}).get("title") or session_id
        conv = await self.get_conversation_history(session_id, limit=limit)
        lines = [f"# {title}", "", f"- **session_id**: `{session_id}`", ""]
        for row in conv:
            role = "User" if row["role"] == "user" else "Glup"
            lines.append(f"## {role}")
            lines.append(row["message"])
            lines.append("")
        return "\n".join(lines).strip() + "\n"

    async def get_setting(self, key: str) -> str | None:
        """Get a setting value by key."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT value FROM settings WHERE key = ?",
                (key,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return row["value"]
                return None

    async def set_setting(self, key: str, value: str) -> None:
        """Set a setting value by key."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, value),
            )
            await db.commit()

