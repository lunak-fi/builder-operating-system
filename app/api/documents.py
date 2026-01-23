from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
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
from app.models import DealDocument, Operator
from app.schemas import DealDocumentResponse, ActivityFeedResponse, ActivityItem
from pydantic import BaseModel
from app.services.pdf_extractor import extract_text_from_pdf, PDFExtractionError
from app.services.document_parser import parse_document, DocumentParserError
from app.services.llm_extractor import extract_deal_data_from_text, LLMExtractionError
from app.services.auto_populate import populate_database_from_extraction, AutoPopulationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


class ConfirmExtractionRequest(BaseModel):
    """Request body for confirming extraction and creating deal"""
    operator_ids: List[UUID]
    extracted_data: dict

# Mapping of file extensions to document types
ALLOWED_EXTENSIONS = {
    '.pdf': 'offer_memo',
    '.xlsx': 'financial_model',
    '.xls': 'financial_model',
    '.txt': 'transcript',
    '.md': 'transcript',
    '.eml': 'email'
}


def process_document_parsing(document_id: UUID, file_path: str, document_type: str, db_session_maker):
    """
    Background task to parse uploaded documents (PDF, Excel, text, email).
    Updates the document record with extracted text, metadata, and parsing status.
    """
    # Create a new database session for background task
    db = db_session_maker()
    try:
        logger.info(f"Starting document parsing for document {document_id}, type: {document_type}")

        # Parse document based on type
        extracted_text, metadata = parse_document(file_path, document_type)

        # Update document record
        document = db.query(DealDocument).filter(DealDocument.id == document_id).first()
        if document:
            document.parsed_text = extracted_text
            document.metadata_json = metadata
            document.parsing_status = "completed"
            document.parsing_error = None
            db.commit()
            logger.info(f"Successfully parsed document {document_id}: {len(extracted_text)} characters")

            # If transcript, trigger AI extraction
            if document_type == "transcript":
                logger.info(f"Triggering AI extraction for transcript {document_id}")
                process_transcript_ai_extraction(document_id, db_session_maker)
        else:
            logger.error(f"Document {document_id} not found in database")

    except DocumentParserError as e:
        logger.error(f"Document parsing failed for document {document_id}: {str(e)}")
        # Update document with error status
        document = db.query(DealDocument).filter(DealDocument.id == document_id).first()
        if document:
            document.parsing_status = "failed"
            document.parsing_error = str(e)
            db.commit()
    except Exception as e:
        logger.error(f"Unexpected error during document parsing for document {document_id}: {str(e)}")
        # Update document with error status
        document = db.query(DealDocument).filter(DealDocument.id == document_id).first()
        if document:
            document.parsing_status = "failed"
            document.parsing_error = f"Unexpected error: {str(e)}"
            db.commit()
    finally:
        db.close()


def process_transcript_ai_extraction(document_id: UUID, db_session_maker):
    """
    Background task: Extract AI insights from transcript.
    Called after document parsing completes for transcript documents.
    """
    db = db_session_maker()
    try:
        document = db.query(DealDocument).filter(DealDocument.id == document_id).first()

        if not document or document.document_type != "transcript":
            return

        if document.parsing_status != "completed" or not document.parsed_text:
            logger.warning(f"Cannot extract insights - parsing not complete for {document_id}")
            return

        # Extract metadata
        metadata = document.metadata_json or {}
        transcript_metadata = metadata.get("transcript", {})

        # Call transcript extractor
        from app.services.transcript_extractor import extract_transcript_insights, TranscriptExtractionError
        from datetime import datetime

        try:
            insights = extract_transcript_insights(document.parsed_text, transcript_metadata)

            # Store insights in metadata_json
            if "ai_insights" not in metadata:
                metadata["ai_insights"] = {}
            metadata["ai_insights"] = insights

            document.metadata_json = metadata

            # Force SQLAlchemy to detect the JSONB field change
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(document, "metadata_json")

            db.commit()

            logger.info(f"Successfully extracted insights for transcript {document_id}")

        except TranscriptExtractionError as e:
            logger.error(f"Transcript extraction failed for {document_id}: {str(e)}")
            # Store error in metadata
            metadata["ai_insights"] = {
                "error": str(e),
                "extracted_at": datetime.utcnow().isoformat()
            }
            document.metadata_json = metadata

            # Force SQLAlchemy to detect the JSONB field change
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(document, "metadata_json")

            db.commit()

    finally:
        db.close()


@router.post("/upload", response_model=DealDocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form("pitch_deck"),
    document_date: str | None = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    Upload a document for processing.
    Supports: PDF, Excel (.xlsx, .xls), Text (.txt, .md), Email (.eml)
    No deal is created until extraction is run.

    Optionally provide:
    - document_date: ISO 8601 date string for the document's event date (e.g., "2025-12-15T00:00:00Z")
                     If not provided, defaults to upload time (created_at)
    """
    # Get file extension
    file_extension = Path(file.filename).suffix.lower()

    # Validate file type
    if file_extension not in ALLOWED_EXTENSIONS:
        allowed = ', '.join(ALLOWED_EXTENSIONS.keys())
        raise HTTPException(
            status_code=400,
            detail=f"File type not supported. Allowed: {allowed}"
        )

    # Auto-detect document type from extension
    detected_type = ALLOWED_EXTENSIONS[file_extension]

    # Create upload directory if it doesn't exist
    upload_dir = Path(os.getenv("UPLOAD_DIR", "./uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename using UUID (no deal_id yet)
    doc_uuid = uuid.uuid4()
    filename = f"{doc_uuid}_{file.filename}"
    file_path = upload_dir / filename

    # Save file and get file size
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_size = file_path.stat().st_size
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Create database record (no deal_id - will be linked after extraction)
    db_document = DealDocument(
        id=doc_uuid,
        deal_id=None,
        document_type=detected_type,
        file_name=file.filename,
        file_url=str(file_path),
        file_size=file_size,
        parsing_status="processing"
    )

    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    # Set document_date
    # Priority: user-provided > upload time
    if document_date:
        try:
            from datetime import datetime
            db_document.document_date = datetime.fromisoformat(document_date.replace('Z', '+00:00'))
        except ValueError:
            logger.warning(f"Invalid document_date format: {document_date}, using upload time")
            db_document.document_date = db_document.created_at
    else:
        # Default to upload time (will be updated if parser extracts a better date, e.g., email date)
        db_document.document_date = db_document.created_at
    db.commit()

    # Trigger background document parsing
    from app.db.database import SessionLocal
    background_tasks.add_task(
        process_document_parsing,
        db_document.id,
        str(file_path),
        detected_type,
        SessionLocal
    )

    logger.info(f"Uploaded document {db_document.id} ({detected_type}), scheduled parsing")

    return db_document


@router.post("/deals/{deal_id}/upload", response_model=DealDocumentResponse, status_code=201)
async def upload_deal_document(
    deal_id: UUID,
    file: UploadFile = File(...),
    document_type: str = Form("pitch_deck"),
    topic: str | None = Form(None),
    conversation_date: str | None = Form(None),
    document_date: str | None = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    Upload a document for an existing deal.
    Supports: PDF, Excel (.xlsx, .xls), Text (.txt, .md), Email (.eml)
    WARNING: Running extraction on PDFs will overwrite existing deal data.

    For transcripts, optionally provide:
    - topic: Conversation topic (e.g., "Sponsor Call - Q3 Review")
    - conversation_date: ISO 8601 date string (e.g., "2026-01-15T14:30:00Z")

    For all documents, optionally provide:
    - document_date: ISO 8601 date string for the document's event date (e.g., "2025-12-15T00:00:00Z")
                     If not provided, defaults to upload time (created_at)
    """
    # Get file extension
    file_extension = Path(file.filename).suffix.lower()

    # Validate file type
    if file_extension not in ALLOWED_EXTENSIONS:
        allowed = ', '.join(ALLOWED_EXTENSIONS.keys())
        raise HTTPException(
            status_code=400,
            detail=f"File type not supported. Allowed: {allowed}"
        )

    # Auto-detect document type from extension
    detected_type = ALLOWED_EXTENSIONS[file_extension]

    # Create upload directory if it doesn't exist
    upload_dir = Path(os.getenv("UPLOAD_DIR", "./uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    filename = f"{deal_id}_{file.filename}"
    file_path = upload_dir / filename

    # Save file and get file size
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_size = file_path.stat().st_size
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Create database record
    db_document = DealDocument(
        deal_id=deal_id,
        document_type=detected_type,
        file_name=file.filename,
        file_url=str(file_path),
        file_size=file_size,
        parsing_status="processing"
    )

    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    # Set document_date
    # Priority: user-provided > conversation_date (for transcripts) > upload time
    if document_date:
        try:
            from datetime import datetime
            db_document.document_date = datetime.fromisoformat(document_date.replace('Z', '+00:00'))
        except ValueError:
            logger.warning(f"Invalid document_date format: {document_date}, using upload time")
            db_document.document_date = db_document.created_at
    elif detected_type == "transcript" and conversation_date:
        # For transcripts, use conversation_date as document_date
        try:
            from datetime import datetime
            db_document.document_date = datetime.fromisoformat(conversation_date.replace('Z', '+00:00'))
        except ValueError:
            logger.warning(f"Invalid conversation_date format: {conversation_date}, using upload time")
            db_document.document_date = db_document.created_at
    else:
        # Default to upload time
        db_document.document_date = db_document.created_at

    db.commit()
    logger.info(f"Set document_date for document {db_document.id}")

    # Store transcript metadata if provided
    if detected_type == "transcript" and (topic or conversation_date):
        transcript_metadata = {}
        if topic:
            transcript_metadata["topic"] = topic
        if conversation_date:
            transcript_metadata["conversation_date"] = conversation_date

        db_document.metadata_json = {"transcript": transcript_metadata}

        # Force SQLAlchemy to detect the JSONB field change
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(db_document, "metadata_json")

        db.commit()
        logger.info(f"Stored transcript metadata for document {db_document.id}")

    # Trigger background document parsing
    from app.db.database import SessionLocal
    background_tasks.add_task(
        process_document_parsing,
        db_document.id,
        str(file_path),
        detected_type,
        SessionLocal
    )

    logger.info(f"Scheduled document parsing for document {db_document.id} ({detected_type})")

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


@router.get("/deals/{deal_id}/activity", response_model=ActivityFeedResponse)
def get_deal_activity(deal_id: UUID, db: Session = Depends(get_db)):
    """
    Get activity feed for a deal.
    Returns a timeline of all activities (document uploads, versions) sorted chronologically.
    """
    activities = []

    # Get all documents for this deal
    documents = db.query(DealDocument).filter(
        DealDocument.deal_id == deal_id
    ).order_by(DealDocument.created_at.desc()).all()

    for doc in documents:
        # Determine activity type
        if doc.parent_document_id:
            activity_type = "document_version_uploaded"
        else:
            activity_type = "document_uploaded"

        activities.append(ActivityItem(
            id=str(doc.id),
            type=activity_type,
            timestamp=doc.created_at,
            data={
                "document_id": str(doc.id),
                "document_type": doc.document_type,
                "file_name": doc.file_name,
                "file_size": doc.file_size,
                "version_number": doc.version_number,
                "parent_document_id": str(doc.parent_document_id) if doc.parent_document_id else None,
                "parsing_status": doc.parsing_status,
                "metadata_json": doc.metadata_json
            }
        ))

    return ActivityFeedResponse(activities=activities)


@router.post("/{document_id}/extract")
def extract_structured_data(document_id: UUID, db: Session = Depends(get_db)):
    """
    Extract structured data from document using LLM (preview only).

    This endpoint:
    1. Retrieves the parsed text from the document
    2. Sends it to Claude AI for structured extraction
    3. Searches for matching operators by extracted sponsor name
    4. Returns extraction preview WITHOUT creating deal records

    Returns extracted data and operator matches for user confirmation.
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
        # Extract deal data from parsed text
        logger.info(f"Starting deal LLM extraction for document {document_id}")
        extracted_data = extract_deal_data_from_text(document.parsed_text)
        logger.info(f"Deal LLM extraction completed for document {document_id}")

        # Search for matching operators for EACH extracted sponsor
        operator_matches_by_extracted = []
        operators_data = extracted_data.get("operators", [])

        for operator_data in operators_data:
            if operator_data and operator_data.get("name"):
                extracted_name = operator_data.get("name")
                search_term = f"%{extracted_name}%"

                matching_operators = db.query(Operator).filter(
                    (Operator.name.ilike(search_term)) |
                    (Operator.legal_name.ilike(search_term))
                ).limit(10).all()

                operator_matches_by_extracted.append({
                    "extracted_name": extracted_name,
                    "is_primary": operator_data.get("is_primary", False),
                    "matches": [
                        {
                            "id": str(op.id),
                            "name": op.name,
                            "legal_name": op.legal_name,
                            "hq_city": op.hq_city,
                            "hq_state": op.hq_state
                        }
                        for op in matching_operators
                    ]
                })

                logger.info(f"Found {len(matching_operators)} matching operators for '{extracted_name}'")

        return {
            "success": True,
            "document_id": str(document_id),
            "extracted_data": extracted_data,
            "operator_matches": operator_matches_by_extracted
        }

    except LLMExtractionError as e:
        logger.error(f"LLM extraction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"LLM extraction failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during extraction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")


@router.post("/{document_id}/confirm")
def confirm_extraction(
    document_id: UUID,
    request: ConfirmExtractionRequest,
    db: Session = Depends(get_db)
):
    """
    Confirm sponsor selection(s) and create deal from extracted data.

    This endpoint:
    1. Validates the selected operators exist
    2. Creates deal records using the confirmed operator_ids
    3. Links the document to the newly created deal

    Returns the created deal data and record IDs.
    """
    # Get document
    document = db.query(DealDocument).filter(DealDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Validate at least one operator
    if not request.operator_ids:
        raise HTTPException(status_code=400, detail="At least one operator required")

    # Validate all operators exist
    from app.models import Operator
    for operator_id in request.operator_ids:
        operator = db.query(Operator).filter(Operator.id == operator_id).first()
        if not operator:
            raise HTTPException(status_code=404, detail=f"Operator {operator_id} not found")

    try:
        # Create deal with confirmed operators
        logger.info(f"Creating deal for document {document_id} with {len(request.operator_ids)} operator(s)")
        result = populate_database_from_extraction(
            extracted_data=request.extracted_data,
            document_id=document_id,
            operator_ids=request.operator_ids,
            db=db
        )

        # Link document to the newly created deal
        document.deal_id = result["deal_id"]
        db.commit()

        logger.info(f"Deal created successfully: deal_id={result['deal_id']}")

        return {
            "success": True,
            "document_id": str(document_id),
            "classification": "deal",
            "extracted_data": request.extracted_data,
            "populated_records": result
        }

    except AutoPopulationError as e:
        logger.error(f"Database population failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database population failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during deal creation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Deal creation failed: {str(e)}")


@router.post("/{document_id}/new-version", response_model=DealDocumentResponse, status_code=201)
async def upload_document_version(
    document_id: UUID,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    """
    Upload a new version of an existing document.
    The new version will be linked to the original document via parent_document_id.
    """
    # Get the parent document
    parent_document = db.query(DealDocument).filter(DealDocument.id == document_id).first()
    if not parent_document:
        raise HTTPException(status_code=404, detail="Parent document not found")

    # Get file extension
    file_extension = Path(file.filename).suffix.lower()

    # Validate file type matches parent document type
    if file_extension not in ALLOWED_EXTENSIONS:
        allowed = ', '.join(ALLOWED_EXTENSIONS.keys())
        raise HTTPException(
            status_code=400,
            detail=f"File type not supported. Allowed: {allowed}"
        )

    detected_type = ALLOWED_EXTENSIONS[file_extension]

    # Create upload directory if it doesn't exist
    upload_dir = Path(os.getenv("UPLOAD_DIR", "./uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    doc_uuid = uuid.uuid4()
    filename = f"{doc_uuid}_{file.filename}"
    file_path = upload_dir / filename

    # Save file and get file size
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_size = file_path.stat().st_size
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    # Calculate new version number
    # Find the highest version number among the parent and its versions
    if parent_document.parent_document_id is None:
        # Parent is the original document
        original_doc_id = parent_document.id
        current_max_version = parent_document.version_number
    else:
        # Parent is already a version, find the original
        original_doc_id = parent_document.parent_document_id
        current_max_version = parent_document.version_number

    # Find all versions of the original document
    all_versions = db.query(DealDocument).filter(
        (DealDocument.id == original_doc_id) |
        (DealDocument.parent_document_id == original_doc_id)
    ).all()

    max_version = max([v.version_number for v in all_versions]) if all_versions else 0
    new_version_number = max_version + 1

    # Create database record for new version
    db_document = DealDocument(
        id=doc_uuid,
        deal_id=parent_document.deal_id,  # Inherit deal_id from parent
        document_type=detected_type,
        file_name=file.filename,
        file_url=str(file_path),
        file_size=file_size,
        parent_document_id=original_doc_id,  # Link to original document
        version_number=new_version_number,
        parsing_status="processing"
    )

    db.add(db_document)
    db.commit()
    db.refresh(db_document)

    # Trigger background document parsing
    from app.db.database import SessionLocal
    background_tasks.add_task(
        process_document_parsing,
        db_document.id,
        str(file_path),
        detected_type,
        SessionLocal
    )

    logger.info(f"Uploaded version {new_version_number} of document {original_doc_id}")

    return db_document


@router.patch("/{document_id}/transcript-metadata", response_model=DealDocumentResponse)
async def update_transcript_metadata(
    document_id: UUID,
    topic: str | None = None,
    conversation_date: str | None = None,
    db: Session = Depends(get_db)
):
    """
    Update transcript metadata (topic and/or conversation date).
    """
    document = db.query(DealDocument).filter(DealDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.document_type != "transcript":
        raise HTTPException(status_code=400, detail="Document is not a transcript")

    # Update metadata
    metadata = document.metadata_json or {}
    transcript_metadata = metadata.get("transcript", {})

    if topic:
        transcript_metadata["topic"] = topic
    if conversation_date:
        transcript_metadata["conversation_date"] = conversation_date

    metadata["transcript"] = transcript_metadata
    document.metadata_json = metadata

    # Force SQLAlchemy to detect the JSONB field change
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(document, "metadata_json")

    db.commit()
    db.refresh(document)

    logger.info(f"Updated transcript metadata for document {document_id}")

    return document


@router.post("/{document_id}/regenerate-insights")
async def regenerate_transcript_insights(
    document_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Manually trigger AI insight regeneration for a transcript.
    """
    document = db.query(DealDocument).filter(DealDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.document_type != "transcript":
        raise HTTPException(status_code=400, detail="Document is not a transcript")

    if document.parsing_status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Document parsing not complete: {document.parsing_status}"
        )

    # Trigger background extraction
    from app.db.database import SessionLocal
    background_tasks.add_task(
        process_transcript_ai_extraction,
        document_id,
        SessionLocal
    )

    logger.info(f"Triggered insights regeneration for transcript {document_id}")

    return {"success": True, "message": "Insights regeneration triggered"}


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
