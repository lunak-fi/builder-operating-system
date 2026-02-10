"""
Webhook endpoints for external services.

These endpoints do NOT require Clerk authentication since they're called by
external services (SendGrid, Mailgun, Postmark, etc.) that can't provide JWT tokens.

Security is handled via:
- Webhook signature verification (when available)
- IP allowlisting (optional)
- Rate limiting (recommended in production)
"""

import logging
import os
import uuid
from pathlib import Path
from fastapi import APIRouter, Request, Form, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.db.database import SessionLocal
from app.models import Deal, DealDocument, PendingEmail, PendingEmailAttachment
from app.services.email_parser import (
    parse_sendgrid_webhook,
    parse_mailgun_webhook,
    format_email_as_text,
    get_email_metadata,
    extract_deal_code_from_address,
    extract_deal_code_from_subject,
    EmailParserError,
)
from app.api.pending_emails import process_pending_email_extraction

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])

# Upload directory for attachments
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


class InboundEmailResponse(BaseModel):
    """Response for inbound email processing"""
    success: bool
    pending_email_id: str | None = None
    organization_id: str | None = None
    message: str
    attachment_count: int = 0


def extract_org_id_from_address(email_address: str) -> str | None:
    """
    Extract organization ID from email address using +tag convention.

    Examples:
        deals+org123@buildingpartnership.co -> org123
        inbox@buildingpartnership.co -> None
    """
    import re
    match = re.search(r'\+([^@]+)@', email_address)
    if match:
        return match.group(1)
    return None


@router.post("/inbound-email", response_model=InboundEmailResponse)
async def receive_inbound_email(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    # SendGrid/Postmark fields (also works for Mailgun with mapping)
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

    Supports SendGrid Inbound Parse, Mailgun Routes, and Postmark.

    Users forward emails to: deals+{org_id}@buildingpartnership.co
    The org_id is extracted and used to associate the email with an organization.

    The email is stored as a PendingEmail for user review before deal creation.
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

        # Extract organization ID from TO address
        org_id = None
        for addr in parsed_email.to_addresses:
            org_id = extract_org_id_from_address(addr)
            if org_id:
                break

        # If no org_id found, use a default or reject
        if not org_id:
            # Check if this is an email to an existing deal (legacy behavior)
            deal_code = None
            for addr in parsed_email.to_addresses:
                deal_code = extract_deal_code_from_address(addr)
                if deal_code:
                    break

            if not deal_code:
                deal_code = extract_deal_code_from_subject(parsed_email.subject)

            if deal_code:
                # Legacy: link to existing deal
                deal = db.query(Deal).filter(Deal.internal_code.ilike(deal_code)).first()
                if deal:
                    # Create document linked to existing deal (old behavior)
                    email_text = format_email_as_text(parsed_email)
                    email_metadata = get_email_metadata(parsed_email)

                    document = DealDocument(
                        deal_id=deal.id,
                        document_type="email",
                        file_name=f"Email: {parsed_email.subject[:50]}",
                        file_url="",
                        file_size=len(email_text.encode('utf-8')),
                        parsed_text=email_text,
                        metadata_json=email_metadata,
                        parsing_status="completed",
                    )
                    db.add(document)
                    db.commit()

                    return InboundEmailResponse(
                        success=True,
                        pending_email_id=None,
                        organization_id=None,
                        message=f"Email linked to existing deal: {deal.deal_name}",
                        attachment_count=len(parsed_email.attachments),
                    )

            # Use 'default' org_id for emails without org identifier
            org_id = "default"
            logger.warning(f"No organization ID found in email address, using default")

        # Create PendingEmail record
        pending_email = PendingEmail(
            organization_id=org_id,
            status="received",
            from_address=parsed_email.from_address,
            from_name=parsed_email.from_name,
            subject=parsed_email.subject,
            body_text=parsed_email.body_text,
            body_html=parsed_email.body_html,
            to_addresses=parsed_email.to_addresses,
            cc_addresses=parsed_email.cc_addresses,
            email_date=parsed_email.date,
            message_id=parsed_email.message_id,
            in_reply_to=parsed_email.in_reply_to,
            raw_headers=parsed_email.raw_headers,
        )

        db.add(pending_email)
        db.commit()
        db.refresh(pending_email)

        logger.info(f"Created pending email: {pending_email.id} for org {org_id}")

        # Process and save attachments
        attachment_count = 0
        for attachment in parsed_email.attachments:
            # Skip tiny or empty attachments
            if attachment.size < 100:
                continue

            # Save attachment to disk
            file_id = str(uuid.uuid4())
            safe_filename = f"{file_id}_{attachment.filename}"
            file_path = UPLOAD_DIR / safe_filename

            with open(file_path, 'wb') as f:
                f.write(attachment.content)

            # Determine if attachment should be parsed
            parseable_types = [
                'application/pdf',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            ]

            pending_attachment = PendingEmailAttachment(
                pending_email_id=pending_email.id,
                file_name=attachment.filename,
                content_type=attachment.content_type,
                file_size=attachment.size,
                storage_url=str(file_path),
                parsing_status="pending" if attachment.content_type in parseable_types else "completed",
            )

            db.add(pending_attachment)
            attachment_count += 1

            logger.info(f"Saved attachment: {attachment.filename} ({attachment.size} bytes)")

        db.commit()

        # Trigger background task for AI extraction
        background_tasks.add_task(
            process_pending_email_extraction,
            pending_email.id,
            SessionLocal
        )

        return InboundEmailResponse(
            success=True,
            pending_email_id=str(pending_email.id),
            organization_id=org_id,
            message="Email received and queued for processing",
            attachment_count=attachment_count,
        )

    except EmailParserError as e:
        logger.error(f"Email parsing failed: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Email parsing failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error processing inbound email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process email: {str(e)}")
