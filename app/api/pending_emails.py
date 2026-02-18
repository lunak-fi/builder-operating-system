"""
Pending Emails API Router

Endpoints for managing pending emails in the inbox before deal creation.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from uuid import UUID

from app.db.session import get_db
from app.db.database import SessionLocal
from app.models import PendingEmail, PendingEmailAttachment, Operator, DealDocument
from app.schemas.pending_email import (
    PendingEmailResponse,
    PendingEmailListResponse,
    PendingEmailConfirmRequest,
    PendingEmailConfirmResponse,
    PendingEmailCountResponse,
)
from app.services.llm_extractor import extract_deal_data_from_text, LLMExtractionError
from app.services.auto_populate import populate_database_from_extraction
from app.services.document_parser import parse_document, DocumentParserError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pending-emails", tags=["pending-emails"])


def process_pending_email_attachment_parsing(
    attachment_id: UUID,
    file_path: str,
    content_type: str,
    db_session_maker
):
    """
    Background task to parse a single attachment (PDF/Excel).
    After parsing, checks if all attachments are done and triggers AI extraction.
    """
    db = db_session_maker()
    try:
        attachment = db.query(PendingEmailAttachment).filter(
            PendingEmailAttachment.id == attachment_id
        ).first()

        if not attachment:
            logger.error(f"Attachment {attachment_id} not found")
            return

        logger.info(f"Parsing attachment {attachment_id}: {attachment.file_name}")

        # Determine doc type from content type
        if content_type == "application/pdf":
            doc_type = "offer_memo"
        elif content_type in [
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ]:
            doc_type = "financial_model"
        else:
            doc_type = "other"

        try:
            parsed_text, metadata = parse_document(file_path, doc_type)
            attachment.parsed_text = parsed_text
            attachment.parsing_status = "completed"
            attachment.parsing_error = None
            logger.info(f"Successfully parsed attachment {attachment_id}: {len(parsed_text)} chars")
        except DocumentParserError as e:
            attachment.parsing_status = "failed"
            attachment.parsing_error = str(e)
            logger.error(f"Failed to parse attachment {attachment_id}: {e}")

        db.commit()

        # Check if ALL attachments for this email are done parsing
        pending_email_id = attachment.pending_email_id
        pending_attachments = db.query(PendingEmailAttachment).filter(
            PendingEmailAttachment.pending_email_id == pending_email_id,
            PendingEmailAttachment.parsing_status == "pending"
        ).count()

        if pending_attachments == 0:
            # All attachments parsed - trigger AI extraction
            logger.info(f"All attachments parsed for email {pending_email_id}, triggering AI extraction")
            process_pending_email_extraction(pending_email_id, db_session_maker)
        else:
            logger.info(f"Waiting for {pending_attachments} more attachment(s) to parse for email {pending_email_id}")

    except Exception as e:
        logger.error(f"Error parsing attachment {attachment_id}: {e}")
        try:
            attachment = db.query(PendingEmailAttachment).filter(
                PendingEmailAttachment.id == attachment_id
            ).first()
            if attachment:
                attachment.parsing_status = "failed"
                attachment.parsing_error = str(e)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def process_pending_email_extraction(pending_email_id: UUID, db_session_maker):
    """
    Background task to run AI extraction on pending email content.
    Updates the pending email with extracted data and operator matches.
    """
    db = db_session_maker()
    try:
        pending_email = db.query(PendingEmail).filter(PendingEmail.id == pending_email_id).first()
        if not pending_email:
            logger.error(f"Pending email {pending_email_id} not found")
            return

        logger.info(f"Processing pending email {pending_email_id}: {pending_email.subject}")

        # Update status to processing
        pending_email.status = "processing"
        db.commit()

        # Gather text content from email body and attachments
        text_content = []

        # Add email body
        if pending_email.body_text:
            text_content.append(f"Email Subject: {pending_email.subject}")
            text_content.append(f"From: {pending_email.from_name or ''} <{pending_email.from_address}>")
            text_content.append("")
            text_content.append(pending_email.body_text)

        # Add parsed text from attachments (PDFs, etc.)
        for attachment in pending_email.attachments:
            if attachment.parsing_status == "completed" and attachment.parsed_text:
                text_content.append(f"\n\n--- Attachment: {attachment.file_name} ---")
                text_content.append(attachment.parsed_text)

        combined_text = "\n".join(text_content)

        if not combined_text.strip():
            pending_email.status = "failed"
            pending_email.error_message = "No content available for extraction"
            db.commit()
            return

        # Run AI extraction
        try:
            extracted_data = extract_deal_data_from_text(combined_text)
        except LLMExtractionError as e:
            pending_email.status = "failed"
            pending_email.error_message = f"AI extraction failed: {str(e)}"
            db.commit()
            return

        # Search for matching operators
        operator_matches = []
        if "operators" in extracted_data:
            for idx, op_data in enumerate(extracted_data.get("operators", [])):
                op_name = op_data.get("name", "")
                if op_name:
                    # Search for matches
                    matches = db.query(Operator).filter(
                        Operator.name.ilike(f"%{op_name}%")
                    ).limit(5).all()

                    operator_matches.append({
                        "extracted_name": op_name,
                        "is_primary": idx == 0,
                        "matches": [
                            {
                                "id": str(m.id),
                                "name": m.name,
                                "legal_name": m.legal_name,
                                "hq_city": m.hq_city,
                                "hq_state": m.hq_state,
                            }
                            for m in matches
                        ]
                    })

        # Update pending email with extraction results
        pending_email.extracted_data = extracted_data
        pending_email.operator_matches = operator_matches
        pending_email.status = "ready_for_review"
        pending_email.error_message = None
        db.commit()

        logger.info(f"Successfully processed pending email {pending_email_id}")

    except Exception as e:
        logger.error(f"Error processing pending email {pending_email_id}: {str(e)}")
        try:
            pending_email = db.query(PendingEmail).filter(PendingEmail.id == pending_email_id).first()
            if pending_email:
                pending_email.status = "failed"
                pending_email.error_message = f"Processing error: {str(e)}"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.get("/", response_model=List[PendingEmailListResponse])
def list_pending_emails(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all pending emails for the organization.

    Optionally filter by status: received, processing, ready_for_review, confirmed, failed
    """
    query = db.query(PendingEmail)

    if status:
        query = query.filter(PendingEmail.status == status)

    # Order by most recent first
    pending_emails = query.order_by(PendingEmail.created_at.desc()).all()

    return pending_emails


@router.get("/count", response_model=PendingEmailCountResponse)
def get_pending_email_count(
    db: Session = Depends(get_db)
):
    """
    Get count of pending emails needing review (for inbox badge).
    Only counts emails with status 'ready_for_review'.
    """
    count = db.query(func.count(PendingEmail.id)).filter(
        PendingEmail.status == "ready_for_review"
    ).scalar()

    return PendingEmailCountResponse(count=count or 0)


@router.get("/{pending_email_id}", response_model=PendingEmailResponse)
def get_pending_email(
    pending_email_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get a single pending email with full details including attachments.
    """
    pending_email = db.query(PendingEmail).filter(
        PendingEmail.id == pending_email_id
    ).first()

    if not pending_email:
        raise HTTPException(status_code=404, detail="Pending email not found")

    return pending_email


@router.post("/{pending_email_id}/confirm", response_model=PendingEmailConfirmResponse)
def confirm_pending_email(
    pending_email_id: UUID,
    request: PendingEmailConfirmRequest,
    db: Session = Depends(get_db)
):
    """
    Confirm a pending email and create a deal.

    This endpoint:
    1. Validates the selected operators exist
    2. Creates deal records using the extraction data and operator_ids
    3. Links any attachments as deal documents
    4. Updates pending email status to 'confirmed'
    """
    pending_email = db.query(PendingEmail).filter(
        PendingEmail.id == pending_email_id
    ).first()

    if not pending_email:
        raise HTTPException(status_code=404, detail="Pending email not found")

    if pending_email.status != "ready_for_review":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot confirm email with status '{pending_email.status}'. Must be 'ready_for_review'."
        )

    # Validate operators only if creating a new deal
    if not request.deal_id and not request.operator_ids:
        raise HTTPException(status_code=400, detail="At least one operator required when creating a new deal")

    # Validate all operators exist (if provided)
    operator_uuids = [UUID(oid) for oid in request.operator_ids] if request.operator_ids else []
    for operator_id in operator_uuids:
        operator = db.query(Operator).filter(Operator.id == operator_id).first()
        if not operator:
            raise HTTPException(status_code=404, detail=f"Operator {operator_id} not found")

    try:
        if request.deal_id:
            # Link to existing deal
            deal_id = UUID(request.deal_id)
            from app.models import Deal
            deal = db.query(Deal).filter(Deal.id == deal_id).first()
            if not deal:
                raise HTTPException(status_code=404, detail="Deal not found")
            logger.info(f"Linking pending email {pending_email_id} to existing deal {deal_id}")
        else:
            # Create new deal
            # Use the provided extracted_data or fall back to stored extraction
            extracted_data = request.extracted_data or pending_email.extracted_data

            if not extracted_data:
                raise HTTPException(status_code=400, detail="No extracted data available")

            logger.info(f"Creating deal from pending email {pending_email_id}")

            # Create deal using the auto_populate service
            result = populate_database_from_extraction(
                extracted_data=extracted_data,
                document_id=None,  # No source document yet
                operator_ids=operator_uuids,
                db=db
            )

            deal_id = result["deal_id"]

        # Create email document linked to the deal
        email_document = DealDocument(
            deal_id=deal_id,
            document_type="email",
            file_name=f"Email: {pending_email.subject[:50]}",
            file_url="",
            file_size=len((pending_email.body_text or "").encode('utf-8')),
            parsed_text=pending_email.body_text,
            metadata_json={
                "email": {
                    "from_address": pending_email.from_address,
                    "from_name": pending_email.from_name,
                    "to_addresses": pending_email.to_addresses or [],
                    "cc_addresses": pending_email.cc_addresses or [],
                    "subject": pending_email.subject,
                    "date": pending_email.email_date.isoformat() if pending_email.email_date else None,
                    "message_id": pending_email.message_id,
                    "in_reply_to": pending_email.in_reply_to,
                    "has_attachments": len(pending_email.attachments) > 0,
                    "attachment_count": len(pending_email.attachments),
                    "attachment_names": [a.file_name for a in pending_email.attachments],
                }
            },
            parsing_status="completed",
        )
        db.add(email_document)

        # Create document records for attachments and link to deal
        for attachment in pending_email.attachments:
            # Determine document type based on content type
            doc_type = "attachment"
            if attachment.content_type == "application/pdf":
                doc_type = "offer_memo"
            elif attachment.content_type in [
                "application/vnd.ms-excel",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ]:
                doc_type = "financial_model"

            attachment_doc = DealDocument(
                deal_id=deal_id,
                document_type=doc_type,
                file_name=attachment.file_name,
                file_url=attachment.storage_url,
                file_size=attachment.file_size,
                parsed_text=attachment.parsed_text,
                parsing_status=attachment.parsing_status,
                metadata_json={
                    "source": "pending_email_attachment",
                    "pending_email_id": str(pending_email_id),
                    "content_type": attachment.content_type,
                }
            )
            db.add(attachment_doc)

        # Update pending email status
        pending_email.status = "confirmed"
        pending_email.deal_id = deal_id
        db.commit()

        logger.info(f"Successfully created deal {deal_id} from pending email {pending_email_id}")

        return PendingEmailConfirmResponse(
            success=True,
            deal_id=str(deal_id),
            pending_email_id=str(pending_email_id),
            message="Deal created successfully"
        )

    except Exception as e:
        logger.error(f"Error confirming pending email {pending_email_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create deal: {str(e)}")


@router.delete("/{pending_email_id}")
def delete_pending_email(
    pending_email_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Delete/reject a pending email.
    This permanently removes the email and its attachments.
    """
    pending_email = db.query(PendingEmail).filter(
        PendingEmail.id == pending_email_id
    ).first()

    if not pending_email:
        raise HTTPException(status_code=404, detail="Pending email not found")

    # Delete the pending email (cascade will delete attachments)
    db.delete(pending_email)
    db.commit()

    return {"success": True, "message": "Pending email deleted"}


@router.post("/{pending_email_id}/reprocess")
def reprocess_pending_email(
    pending_email_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Reprocess a failed pending email (retry AI extraction).
    """
    pending_email = db.query(PendingEmail).filter(
        PendingEmail.id == pending_email_id
    ).first()

    if not pending_email:
        raise HTTPException(status_code=404, detail="Pending email not found")

    if pending_email.status not in ["failed", "received"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reprocess email with status '{pending_email.status}'"
        )

    # Reset status and trigger background processing
    pending_email.status = "received"
    pending_email.error_message = None
    db.commit()

    background_tasks.add_task(
        process_pending_email_extraction,
        pending_email_id,
        SessionLocal
    )

    return {"success": True, "message": "Reprocessing started"}
