from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.auth.dependencies import get_current_user
from app.schema import NoteCreate, NoteUpdate, NoteResponse, PublicNoteResponse
from app.notes_service import (
    create_note,
    get_user_notes,
    get_note_by_id,
    update_note,
    delete_note,
    get_public_notes,
)

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("/public", response_model=list[PublicNoteResponse])
def list_public_notes(db: Session = Depends(get_db)):
    notes = get_public_notes(db)
    return [
        PublicNoteResponse(
            id=n.id,
            title=n.title,
            content=n.content,
            author="Anonymous",
            created_at=n.created_at,
            updated_at=n.updated_at,
        )
        for n in notes
    ]


@router.post("", response_model=NoteResponse)
def create(
    note: NoteCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = create_note(db, note, current_user["sub"])
    return NoteResponse.model_validate(result)


@router.get("", response_model=list[NoteResponse])
def list_notes(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    notes = get_user_notes(db, current_user["sub"])
    return [NoteResponse.model_validate(n) if hasattr(n, "id") else n for n in notes]


@router.get("/{note_id}", response_model=NoteResponse)
def get_one(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    note = get_note_by_id(db, note_id, current_user["sub"])
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return NoteResponse.model_validate(note)


@router.put("/{note_id}", response_model=NoteResponse)
def update(
    note_id: int,
    note_update: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    note = get_note_by_id(db, note_id, current_user["sub"])
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    result = update_note(db, note, note_update, current_user["sub"])
    if not result:
        raise HTTPException(status_code=403, detail="Not authorized")
    return NoteResponse.model_validate(result)


@router.delete("/{note_id}")
def delete(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    note = get_note_by_id(db, note_id, current_user["sub"])
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    delete_note(db, note, current_user["sub"])
    return {"message": "Note deleted"}
