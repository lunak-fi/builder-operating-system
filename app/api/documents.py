from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import uuid
import os
import shutil
from pathlib import Path
import logging

from app.db.session import get_db
from app.db.database import settings
from app.models import DealDocument
from app.schemas import DealDocumentResponse
from app.services.pdf_extractor import extract_text_from_pdf, PDFExtractionError
from app.services.llm_extractor import extract_deal_data_from_text, LLMExtractionError
from app.services.auto_populate import populate_database_from_extraction, AutoPopulationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


def process_pdf_extraction(document_id: UUID, file_path: str, db_session_maker):
    """
    Background task to extract text from uploaded PDF.
    Updates the document record with extracted text and parsing status.
    """
    # Create a new database session for background task
    db = db_session_maker()
    try:
        logger.info(f"Starting PDF extraction for document {document_id}")

        # Extract text from PDF
        extracted_text = extract_text_from_pdf(file_path)

        # Update document record
        document = db.query(DealDocument).filter(DealDocument.id == document_id).first()
        if document:
            document.parsed_text = extracted_text
            document.parsing_status = "completed"
            document.parsing_error = None
            db.commit()
            logger.info(f"Successfully extracted {len(extracted_text)} characters from document {document_id}")
        else:
            logger.error(f"Document {document_id} not found in database")

    except PDFExtractionError as e:
        logger.error(f"PDF extraction failed for document {document_id}: {str(e)}")
        # Update document with error status
        document = db.query(DealDocument).filter(DealDocument.id == document_id).first()
        if document:
            document.parsing_status = "failed"
            document.parsing_error = str(e)
            db.commit()
    except Exception as e:
        logger.error(f"Unexpected error during PDF extraction for document {document_id}: {str(e)}")
        # Update document with error status
        document = db.query(DealDocument).filter(DealDocument.id == document_id).first()
        if document:
            document.parsing_status = "failed"
            document.parsing_error = f"Unexpected error: {str(e)}"
            db.commit()
    finally:
        db.close()


@router.post("/upload", response_model=DealDocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = "pitch_deck",
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    Upload a PDF document for processing.
    No deal or operator is created until extraction is run.
    """
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Create upload directory if it doesn't exist
    upload_dir = Path(os.getenv("UPLOAD_DIR", "./uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename using UUID (no deal_id yet)
    doc_uuid = uuid.uuid4()
    filename = f"{doc_uuid}_{file.filename}"
    file_path = upload_dir / filename

    # Save file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Create database record (no deal_id - will be linked after extraction)
    db_document = DealDocument(
        id=doc_uuid,
        deal_id=None,
        document_type=document_type,
        file_name=file.filename,
        file_url=str(file_path),
        parsing_status="processing"
    )

    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    # Trigger background PDF extraction
    from app.db.database import SessionLocal
    background_tasks.add_task(
        process_pdf_extraction,
        db_document.id,
        str(file_path),
        SessionLocal
    )

    logger.info(f"Uploaded document {db_document.id}, scheduled PDF extraction")

    return db_document


@router.post("/deals/{deal_id}/upload", response_model=DealDocumentResponse, status_code=201)
async def upload_deal_document(
    deal_id: UUID,
    file: UploadFile = File(...),
    document_type: str = "pitch_deck",
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    Upload a PDF document for an existing deal.
    WARNING: Running extraction on this will overwrite existing deal data.
    Use POST /api/documents/upload instead to auto-create a new deal.
    """

    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Create upload directory if it doesn't exist
    upload_dir = Path(os.getenv("UPLOAD_DIR", "./uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
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
        parsing_status="processing"  # Changed from "pending" to "processing"
    )

    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    # Trigger background PDF extraction
    from app.db.database import SessionLocal
    background_tasks.add_task(
        process_pdf_extraction,
        db_document.id,
        str(file_path),
        SessionLocal
    )

    logger.info(f"Scheduled PDF extraction for document {db_document.id}")

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


@router.post("/{document_id}/extract")
def extract_structured_data(document_id: UUID, db: Session = Depends(get_db)):
    """
    Extract structured data from document using LLM and populate database.

    This endpoint:
    1. Retrieves the parsed text from the document
    2. Sends it to Claude AI for structured extraction
    3. Creates Operator, Deal, Principals, Underwriting records from extracted data
    4. Links the document to the newly created deal

    Returns the extracted data and IDs of created records.
    """
    # Get document
    document = db.query(DealDocument).filter(DealDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check if text extraction is complete
    if document.parsing_status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Document text extraction not completed. Status: {document.parsing_status}"
        )

    if not document.parsed_text:
        raise HTTPException(status_code=400, detail="No parsed text available")

    try:
        logger.info(f"Starting LLM extraction for document {document_id}")

        # Extract structured data using LLM
        extracted_data = extract_deal_data_from_text(document.parsed_text)

        logger.info(f"LLM extraction completed for document {document_id}")

        # Populate database with extracted data (creates Operator, Deal, etc.)
        result = populate_database_from_extraction(
            extracted_data=extracted_data,
            document_id=document_id,
            db=db
        )

        # Link document to the newly created deal
        document.deal_id = result["deal_id"]
        db.commit()

        logger.info(f"Database population completed for document {document_id}, deal_id={result['deal_id']}")

        return {
            "success": True,
            "document_id": document_id,
            "extracted_data": extracted_data,
            "populated_records": result
        }

    except LLMExtractionError as e:
        logger.error(f"LLM extraction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"LLM extraction failed: {str(e)}")
    except AutoPopulationError as e:
        logger.error(f"Database population failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database population failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during extraction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


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
