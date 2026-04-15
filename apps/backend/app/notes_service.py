import json
from sqlalchemy.orm import Session
from app.models import Note
from app.schema import NoteCreate, NoteUpdate, NoteResponse
from app.redis_client import get_cached_notes, set_cached_notes, invalidate_cached_notes
from typing import List, Optional


def create_note(db: Session, note: NoteCreate, user_id: str) -> Note:
    db_note = Note(
        title=note.title,
        content=note.content,
        user_id=user_id,
        is_public=note.is_public,
    )
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    invalidate_cached_notes(user_id)
    return db_note


def get_user_notes(db: Session, user_id: str) -> List[Note]:
    cached = get_cached_notes(user_id)
    if cached:
        return cached

    notes = (
        db.query(Note)
        .filter((Note.user_id == user_id) | (Note.is_public == True))
        .all()
    )

    notes_dict = [
        {
            "id": n.id,
            "title": n.title,
            "content": n.content,
            "user_id": n.user_id,
            "is_public": n.is_public,
            "created_at": str(n.created_at),
            "updated_at": str(n.updated_at) if n.updated_at else None,
        }
        for n in notes
    ]
    set_cached_notes(user_id, json.dumps(notes_dict))

    return notes


def get_note_by_id(db: Session, note_id: int, user_id: str) -> Optional[Note]:
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        return None
    if note.user_id != user_id and not note.is_public:
        return None
    return note


def update_note(
    db: Session, note: Note, note_update: NoteUpdate, user_id: str
) -> Optional[Note]:
    if note.user_id != user_id:
        return None
    if note_update.title is not None:
        note.title = note_update.title
    if note_update.content is not None:
        note.content = note_update.content
    if note_update.is_public is not None:
        note.is_public = note_update.is_public
    db.commit()
    db.refresh(note)
    invalidate_cached_notes(user_id)
    return note


def delete_note(db: Session, note: Note, user_id: str) -> bool:
    if note.user_id != user_id:
        return False
    db.delete(note)
    db.commit()
    invalidate_cached_notes(user_id)
    return True


def get_public_notes(db: Session) -> List[Note]:
    return db.query(Note).filter(Note.is_public == True).all()
