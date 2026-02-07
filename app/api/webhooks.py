"""
Webhook endpoints for external services.

These endpoints do NOT require Clerk authentication since they're called by
external services (SendGrid, Mailgun, etc.) that can't provide JWT tokens.

Security is handled via:
- Webhook signature verification (when available)
- IP allowlisting (optional)
- Rate limiting (recommended in production)
"""

import logging
from fastapi import APIRouter, Request, Form, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.models import Deal, DealDocument
from app.services.email_parser import (
    parse_sendgrid_webhook,
    parse_mailgun_webhook,
    format_email_as_text,
    get_email_metadata,
    extract_deal_code_from_address,
    extract_deal_code_from_subject,
    EmailParserError,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])


class InboundEmailResponse(BaseModel):
    """Response for inbound email processing"""
    success: bool
    document_id: str | None = None
    deal_id: str | None = None
    deal_code: str | None = None
    message: str
    attachment_document_ids: list[str] = []


@router.post("/inbound-email", response_model=InboundEmailResponse)
async def receive_inbound_email(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    # SendGrid fields (also works for Mailgun with mapping)
    from_field: str = Form(None, alias="from"),
    to: str = Form(None),
    cc: str = Form(None),
    subject: str = Form(None),
    text: str = Form(None),
    html: str = Form(None),
    headers: str = Form(None),
    attachments: int = Form(0),
    # Provider hint (optional)
    provider: str = Form("sendgrid"),
):
    """
    Webhook endpoint for receiving forwarded emails.

    Supports SendGrid Inbound Parse and Mailgun Routes.

    Users forward emails to: deals+{deal_code}@your-domain.com
    The deal_code is extracted and used to link the email to a deal.

    If no deal code found in address, attempts to extract from subject line:
    - [DEAL-CODE] in subject
    - "Deal DEAL-CODE" in subject

    If still no deal code found, creates an unlinked email document.
    """
    try:
        # Get raw form data for attachment handling
        form_data = await request.form()

        # Build payload dict
        payload = {
            "from": from_field or form_data.get("from", ""),
            "to": to or form_data.get("to", ""),
            "cc": cc or form_data.get("cc", ""),
            "subject": subject or form_data.get("subject", "(No Subject)"),
            "text": text or form_data.get("text", ""),
            "html": html or form_data.get("html"),
            "headers": headers or form_data.get("headers", ""),
            "attachments": str(attachments) if attachments else form_data.get("attachments", "0"),
        }

        # Copy attachment fields
        for key in form_data.keys():
            if key.startswith('attachment'):
                payload[key] = form_data[key]

        logger.info(f"Received inbound email: to={payload['to']}, subject={payload['subject']}")

        # Parse email based on provider
        if provider == "mailgun":
            parsed_email = parse_mailgun_webhook(payload)
        else:
            parsed_email = parse_sendgrid_webhook(payload)

        # Extract deal code from TO address first
        deal_code = None
        for addr in parsed_email.to_addresses:
            deal_code = extract_deal_code_from_address(addr)
            if deal_code:
                break

        # Fallback: extract from subject
        if not deal_code:
            deal_code = extract_deal_code_from_subject(parsed_email.subject)

        # Look up deal if we have a code
        deal = None
        if deal_code:
            # Try exact match on internal_code first
            deal = db.query(Deal).filter(Deal.internal_code == deal_code).first()

            # Try case-insensitive match
            if not deal:
                deal = db.query(Deal).filter(
                    Deal.internal_code.ilike(deal_code)
                ).first()

            if deal:
                logger.info(f"Matched email to deal: {deal.id} ({deal.deal_name})")
            else:
                logger.warning(f"No deal found for code: {deal_code}")

        # Create the email document
        email_text = format_email_as_text(parsed_email)
        email_metadata = get_email_metadata(parsed_email)

        document = DealDocument(
            deal_id=deal.id if deal else None,
            document_type="email",
            file_name=f"Email: {parsed_email.subject[:50]}",
            file_url="",  # Emails don't have file URLs
            file_size=len(email_text.encode('utf-8')),
            parsed_text=email_text,
            metadata_json=email_metadata,
            parsing_status="completed",
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        logger.info(f"Created email document: {document.id}")

        # Process attachments as separate documents
        attachment_ids = []
        for attachment in parsed_email.attachments:
            # Skip tiny or empty attachments
            if attachment.size < 100:
                continue

            # Determine if attachment should be processed
            processable_types = [
                'application/pdf',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            ]

            attachment_doc = DealDocument(
                deal_id=deal.id if deal else None,
                document_type="attachment",
                file_name=attachment.filename,
                file_url="",  # Would need to save to storage and update
                file_size=attachment.size,
                parent_document_id=document.id,
                parsing_status="pending" if attachment.content_type in processable_types else "completed",
                metadata_json={
                    "source": "email_attachment",
                    "parent_email_id": str(document.id),
                    "original_email_subject": parsed_email.subject,
                    "content_type": attachment.content_type,
                }
            )

            db.add(attachment_doc)
            db.commit()
            db.refresh(attachment_doc)

            attachment_ids.append(str(attachment_doc.id))
            logger.info(f"Created attachment document: {attachment_doc.id} ({attachment.filename})")

        return InboundEmailResponse(
            success=True,
            document_id=str(document.id),
            deal_id=str(deal.id) if deal else None,
            deal_code=deal_code,
            message=f"Email processed successfully. {'Linked to deal.' if deal else 'No matching deal found.'}",
            attachment_document_ids=attachment_ids,
        )

    except EmailParserError as e:
        logger.error(f"Email parsing failed: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Email parsing failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error processing inbound email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process email: {str(e)}")
