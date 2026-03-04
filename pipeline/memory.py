"""
memory.py -- Conversation Memory
Persistent chat history stored in a JSON file so conversations
survive between sessions.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MEMORY_FILE = Path(".autochain_memory.json")
MAX_HISTORY = 50  # max messages to keep per session


class ConversationMemory:
    """
    Stores and retrieves chat history.

    Structure on disk:
    {
      "sessions": {
        "session_id": {
          "created": "2025-01-01T00:00:00",
          "title": "First message preview...",
          "messages": [
            {"role": "user", "content": "...", "ts": "..."},
            {"role": "assistant", "content": "...", "ts": "..."}
          ]
        }
      }
    }
    """

    def __init__(self, memory_file: Path = MEMORY_FILE):
        self.memory_file = memory_file
        self._data = self._load()

    # ── Persistence ───────────────────────────────────────────────────

    def _load(self) -> dict:
        if self.memory_file.exists():
            try:
                return json.loads(self.memory_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Could not load memory file: %s", e)
        return {"sessions": {}}

    def _save(self) -> None:
        try:
            self.memory_file.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("Could not save memory file: %s", e)

    # ── Session management ────────────────────────────────────────────

    def new_session(self) -> str:
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._data["sessions"][session_id] = {
            "created": datetime.now().isoformat(),
            "title": "New conversation",
            "messages": [],
        }
        self._save()
        return session_id

    def list_sessions(self) -> list[dict]:
        """Return sessions sorted newest first."""
        sessions = []
        for sid, data in self._data["sessions"].items():
            sessions.append({
                "id": sid,
                "created": data.get("created", ""),
                "title": data.get("title", "Untitled"),
                "message_count": len(data.get("messages", [])),
            })
        return sorted(sessions, key=lambda x: x["created"], reverse=True)

    def delete_session(self, session_id: str) -> None:
        self._data["sessions"].pop(session_id, None)
        self._save()

    def clear_all(self) -> None:
        self._data = {"sessions": {}}
        self._save()

    # ── Message management ────────────────────────────────────────────

    def add_message(self, session_id: str, role: str, content: str) -> None:
        if session_id not in self._data["sessions"]:
            return
        session = self._data["sessions"][session_id]
        msg = {
            "role": role,
            "content": content,
            "ts": datetime.now().isoformat(),
        }
        session["messages"].append(msg)

        # Update session title from first user message
        if role == "user" and session["title"] == "New conversation":
            session["title"] = content[:60] + ("..." if len(content) > 60 else "")

        # Trim to max history (keep system message integrity)
        if len(session["messages"]) > MAX_HISTORY:
            session["messages"] = session["messages"][-MAX_HISTORY:]

        self._save()

    def get_messages(self, session_id: str) -> list[dict]:
        if session_id not in self._data["sessions"]:
            return []
        return self._data["sessions"][session_id].get("messages", [])

    def get_session_title(self, session_id: str) -> str:
        if session_id not in self._data["sessions"]:
            return "Unknown"
        return self._data["sessions"][session_id].get("title", "Untitled")

    def to_langchain_messages(self, session_id: str) -> list:
        """Convert stored history to LangChain message objects."""
        from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

        lc_messages = [
            SystemMessage(content=(
                "You are AutoChain — a sharp, friendly, and occasionally witty AI assistant. "
                "You're warm and approachable but always professional and accurate. "
                "You give clear, direct answers. You help with finance, coding, "
                "reasoning, research, and anything else the user needs. "
                "You remember the full conversation history and refer back to it naturally."
            ))
        ]
        for msg in self.get_messages(session_id):
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_messages.append(AIMessage(content=msg["content"]))
        return lc_messages