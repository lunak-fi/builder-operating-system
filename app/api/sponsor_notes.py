from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
import logging

from app.db.session import get_db
from app.models import SponsorNote, Operator
from app.schemas.sponsor_note import (
    SponsorNoteCreate,
    SponsorNoteUpdate,
    SponsorNoteResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sponsor-notes", tags=["sponsor-notes"])


@router.post("/", response_model=SponsorNoteResponse, status_code=201)
def create_sponsor_note(
    operator_id: UUID,
    note_data: SponsorNoteCreate,
    db: Session = Depends(get_db)
):
    """Create a new note for a sponsor."""
    operator = db.query(Operator).filter(Operator.id == operator_id).first()
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")

    note = SponsorNote(
        operator_id=operator_id,
        author_name=note_data.author_name,
        note_type=note_data.note_type,
        content=note_data.content,
        interaction_date=note_data.interaction_date,
        metadata_json=note_data.metadata_json,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    logger.info(f"Created sponsor note {note.id} for operator {operator_id}")
    return note


@router.get("/operators/{operator_id}", response_model=list[SponsorNoteResponse])
def get_notes_by_operator(operator_id: UUID, db: Session = Depends(get_db)):
    """Get all notes for a specific sponsor, ordered by most recent first."""
    operator = db.query(Operator).filter(Operator.id == operator_id).first()
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")

    notes = (
        db.query(SponsorNote)
        .filter(SponsorNote.operator_id == operator_id)
        .order_by(SponsorNote.created_at.desc())
        .all()
    )
    return notes


@router.patch("/{note_id}", response_model=SponsorNoteResponse)
def update_sponsor_note(
    note_id: UUID,
    note_data: SponsorNoteUpdate,
    db: Session = Depends(get_db)
):
    """Update a sponsor note."""
    note = db.query(SponsorNote).filter(SponsorNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if note_data.author_name is not None:
        note.author_name = note_data.author_name
    if note_data.content is not None:
        note.content = note_data.content
    if note_data.note_type is not None:
        note.note_type = note_data.note_type
    if note_data.interaction_date is not None:
        note.interaction_date = note_data.interaction_date
    if note_data.metadata_json is not None:
        note.metadata_json = note_data.metadata_json

    db.commit()
    db.refresh(note)

    logger.info(f"Updated sponsor note {note_id}")
    return note


@router.delete("/{note_id}", status_code=204)
def delete_sponsor_note(note_id: UUID, db: Session = Depends(get_db)):
    """Delete a sponsor note."""
    note = db.query(SponsorNote).filter(SponsorNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    db.delete(note)
    db.commit()

    logger.info(f"Deleted sponsor note {note_id}")
    return None
