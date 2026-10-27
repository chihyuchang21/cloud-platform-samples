from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class TodoIn(BaseModel):
    title: str = Field(min_length=1, max_length=200, description="待辦事項標題")


class Todo(BaseModel):
    id: str
    title: str
    done: bool = False
    created_at: datetime


class TodoStore:
    """記憶體儲存，僅供示範；正式環境請改接 Northflank 的 Postgres add-on。"""

    def __init__(self) -> None:
        self._items: dict[str, Todo] = {}

    def list(self) -> list[Todo]:
        return list(self._items.values())

    def add(self, payload: TodoIn) -> Todo:
        todo = Todo(
            id=str(uuid.uuid4()),
            title=payload.title.strip(),
            created_at=datetime.now(timezone.utc),
        )
        self._items[todo.id] = todo
        return todo

    def delete(self, todo_id: str) -> bool:
        return self._items.pop(todo_id, None) is not None
