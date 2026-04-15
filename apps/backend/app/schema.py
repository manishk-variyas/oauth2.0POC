from sqlalchemy.orm import Session
from app.models import Note
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# Common Base Model for notes (shared structure)
class NoteBase(BaseModel):
    title: str
    content: Optional[str] = None
    is_public: bool = False


# Model used when creating a note
# Inherits all fields from NoteBase
class NoteCreate(NoteBase):
    pass


# Model used when updating a note
# All fields are optional because user may update only some fields
class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    is_public: Optional[bool] = None


# Model used when sending data back to the user
class NoteResponse(NoteBase):
    id: int
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PublicNoteResponse(BaseModel):
    id: int
    title: str
    content: Optional[str] = None
    author: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
