from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import os
import shutil
from pathlib import Path

from app.db.session import get_db
from app.db.database import settings
from app.models import DealDocument
from app.schemas import DealDocumentResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/deals/{deal_id}/upload", response_model=DealDocumentResponse, status_code=201)
async def upload_deal_document(
    deal_id: UUID,
    file: UploadFile = File(...),
    document_type: str = "pitch_deck",
    db: Session = Depends(get_db)
):
    """Upload a PDF document for a deal"""

    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Create upload directory if it doesn't exist
    upload_dir = Path(os.getenv("UPLOAD_DIR", "/tmp/builder-os/uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    file_id = str(UUID(int=0).int)  # Temporary, will be replaced with actual UUID
    filename = f"{deal_id}_{file.filename}"
    file_path = upload_dir / filename

    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Create database record
    db_document = DealDocument(
        deal_id=deal_id,
        document_type=document_type,
        file_name=file.filename,
        file_url=str(file_path),
        parsing_status="pending"
    )

    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    return db_document


@router.get("/deals/{deal_id}/documents", response_model=List[DealDocumentResponse])
def list_deal_documents(deal_id: UUID, db: Session = Depends(get_db)):
    """List all documents for a deal"""
    documents = db.query(DealDocument).filter(DealDocument.deal_id == deal_id).all()
    return documents


@router.get("/{document_id}", response_model=DealDocumentResponse)
def get_document(document_id: UUID, db: Session = Depends(get_db)):
    """Get a specific document by ID"""
    document = db.query(DealDocument).filter(DealDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get("/{document_id}/status")
def get_document_status(document_id: UUID, db: Session = Depends(get_db)):
    """Get the parsing status of a document"""
    document = db.query(DealDocument).filter(DealDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "document_id": document.id,
        "parsing_status": document.parsing_status,
        "parsing_error": document.parsing_error,
        "has_parsed_text": document.parsed_text is not None
    }


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: UUID, db: Session = Depends(get_db)):
    """Delete a document"""
    document = db.query(DealDocument).filter(DealDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete file from disk
    try:
        if os.path.exists(document.file_url):
            os.remove(document.file_url)
    except Exception:
        pass  # Continue even if file deletion fails

    db.delete(document)
    db.commit()
    return None
