from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
import logging

from app.db.session import get_db
from app.models import DealNote, Deal
from app.schemas.deal_note import (
    DealNoteCreate,
    DealNoteUpdate,
    DealNoteResponse,
    ThreadExtractionRequest,
    ThreadExtractionResponse,
)
from app.services.text_thread_parser import extract_thread_insights, ThreadExtractionError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("/", response_model=DealNoteResponse, status_code=201)
def create_note(
    deal_id: UUID,
    note_data: DealNoteCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new note for a deal.
    """
    # Verify deal exists
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    note = DealNote(
        deal_id=deal_id,
        author_name=note_data.author_name,
        note_type=note_data.note_type,
        content=note_data.content,
        metadata_json=note_data.metadata_json,
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    logger.info(f"Created note {note.id} for deal {deal_id}")
    return note


@router.get("/deals/{deal_id}", response_model=list[DealNoteResponse])
def get_notes_by_deal(deal_id: UUID, db: Session = Depends(get_db)):
    """
    Get all notes for a specific deal, ordered by most recent first.
    """
    # Verify deal exists
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    notes = (
        db.query(DealNote)
        .filter(DealNote.deal_id == deal_id)
        .order_by(DealNote.created_at.desc())
        .all()
    )
    return notes


@router.get("/{note_id}", response_model=DealNoteResponse)
def get_note(note_id: UUID, db: Session = Depends(get_db)):
    """
    Get a single note by ID.
    """
    note = db.query(DealNote).filter(DealNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.patch("/{note_id}", response_model=DealNoteResponse)
def update_note(
    note_id: UUID,
    note_data: DealNoteUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a note.
    """
    note = db.query(DealNote).filter(DealNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Update fields if provided
    if note_data.author_name is not None:
        note.author_name = note_data.author_name
    if note_data.content is not None:
        note.content = note_data.content
    if note_data.metadata_json is not None:
        note.metadata_json = note_data.metadata_json

    db.commit()
    db.refresh(note)

    logger.info(f"Updated note {note_id}")
    return note


@router.delete("/{note_id}", status_code=204)
def delete_note(note_id: UUID, db: Session = Depends(get_db)):
    """
    Delete a note.
    """
    note = db.query(DealNote).filter(DealNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    db.delete(note)
    db.commit()

    logger.info(f"Deleted note {note_id}")
    return None


@router.post("/extract-thread", response_model=ThreadExtractionResponse)
def extract_and_create_thread_note(
    request: ThreadExtractionRequest,
    db: Session = Depends(get_db)
):
    """
    Extract insights from a pasted text/SMS thread and create a note with the insights.
    Uses Claude AI to parse the thread and extract:
    - Participants
    - Key topics
    - Action items
    - Concerns/risks
    - Key decisions
    - Sentiment
    - Summary
    """
    # Verify deal exists
    deal = db.query(Deal).filter(Deal.id == request.deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    try:
        # Extract insights using AI
        logger.info(f"Extracting insights from text thread for deal {request.deal_id}")
        insights = extract_thread_insights(request.thread_content)

        # Create note with extracted insights
        note = DealNote(
            deal_id=request.deal_id,
            author_name=request.author_name,
            note_type="thread_summary",
            content=request.thread_content,
            metadata_json={"ai_insights": insights},
        )
        db.add(note)
        db.commit()
        db.refresh(note)

        logger.info(f"Created thread summary note {note.id} for deal {request.deal_id}")

        return ThreadExtractionResponse(
            note=DealNoteResponse.model_validate(note),
            insights=insights,
        )

    except ThreadExtractionError as e:
        logger.error(f"Thread extraction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during thread extraction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Thread extraction failed: {str(e)}")
