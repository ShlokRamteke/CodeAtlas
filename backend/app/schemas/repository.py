from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.repository import RepositoryStatus


class RepositoryBase(BaseModel):
    owner: str
    name: str
    full_name: str
    default_branch: str = "main"


class RepositoryCreate(RepositoryBase):
    pass


class RepositoryRead(RepositoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: RepositoryStatus
    indexed_at: Optional[datetime] = None
    file_count: int = 0
    symbol_count: int = 0
    commit_count: int = 0
    created_at: datetime
    updated_at: datetime
