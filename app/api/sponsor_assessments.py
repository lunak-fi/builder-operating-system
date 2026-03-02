from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
import logging

from app.db.session import get_db
from app.models import SponsorAssessment, Operator
from app.schemas.sponsor_assessment import (
    SponsorAssessmentUpsert,
    SponsorAssessmentResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sponsor-assessments", tags=["sponsor-assessments"])


@router.get("/operators/{operator_id}", response_model=SponsorAssessmentResponse | None)
def get_assessment_by_operator(operator_id: UUID, db: Session = Depends(get_db)):
    """Get the assessment for a specific sponsor, or null if none exists."""
    operator = db.query(Operator).filter(Operator.id == operator_id).first()
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")

    assessment = (
        db.query(SponsorAssessment)
        .filter(SponsorAssessment.operator_id == operator_id)
        .first()
    )
    return assessment


@router.put("/operators/{operator_id}", response_model=SponsorAssessmentResponse)
def upsert_assessment(
    operator_id: UUID,
    data: SponsorAssessmentUpsert,
    db: Session = Depends(get_db),
):
    """Create or replace the assessment for a sponsor."""
    operator = db.query(Operator).filter(Operator.id == operator_id).first()
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")

    assessment = (
        db.query(SponsorAssessment)
        .filter(SponsorAssessment.operator_id == operator_id)
        .first()
    )

    # Serialize dimensions to plain dicts for JSONB storage
    dimensions_dict = {k: v.model_dump() for k, v in data.dimensions.items()}

    if assessment:
        assessment.dimensions = dimensions_dict
    else:
        assessment = SponsorAssessment(
            operator_id=operator_id,
            dimensions=dimensions_dict,
        )
        db.add(assessment)

    db.commit()
    db.refresh(assessment)

    logger.info(f"Upserted sponsor assessment for operator {operator_id}")
    return assessment
