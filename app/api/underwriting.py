from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.models import DealUnderwriting
from app.schemas import DealUnderwritingCreate, DealUnderwritingUpdate, DealUnderwritingResponse

router = APIRouter(prefix="/underwriting", tags=["underwriting"])


@router.post("/", response_model=DealUnderwritingResponse, status_code=201)
def create_underwriting(
    underwriting: DealUnderwritingCreate,
    db: Session = Depends(get_db)
):
    """Create a new deal underwriting record"""
    # Check if underwriting already exists for this deal (unique constraint)
    existing = db.query(DealUnderwriting).filter(
        DealUnderwriting.deal_id == underwriting.deal_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Underwriting already exists for deal {underwriting.deal_id}"
        )

    db_underwriting = DealUnderwriting(**underwriting.model_dump())
    db.add(db_underwriting)
    db.commit()
    db.refresh(db_underwriting)
    return db_underwriting


@router.get("/", response_model=List[DealUnderwritingResponse])
def list_underwriting(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """List all underwriting records"""
    underwriting = db.query(DealUnderwriting).offset(skip).limit(limit).all()
    return underwriting


@router.get("/{underwriting_id}", response_model=DealUnderwritingResponse)
def get_underwriting(underwriting_id: UUID, db: Session = Depends(get_db)):
    """Get a specific underwriting record by ID"""
    underwriting = db.query(DealUnderwriting).filter(
        DealUnderwriting.id == underwriting_id
    ).first()

    if not underwriting:
        raise HTTPException(status_code=404, detail="Underwriting not found")

    return underwriting


@router.get("/deal/{deal_id}", response_model=DealUnderwritingResponse)
def get_underwriting_by_deal(deal_id: UUID, db: Session = Depends(get_db)):
    """Get underwriting record for a specific deal"""
    underwriting = db.query(DealUnderwriting).filter(
        DealUnderwriting.deal_id == deal_id
    ).first()

    if not underwriting:
        raise HTTPException(
            status_code=404,
            detail=f"No underwriting found for deal {deal_id}"
        )

    return underwriting


@router.put("/{underwriting_id}", response_model=DealUnderwritingResponse)
def update_underwriting(
    underwriting_id: UUID,
    underwriting_update: DealUnderwritingUpdate,
    db: Session = Depends(get_db)
):
    """Update an underwriting record"""
    underwriting = db.query(DealUnderwriting).filter(
        DealUnderwriting.id == underwriting_id
    ).first()

    if not underwriting:
        raise HTTPException(status_code=404, detail="Underwriting not found")

    update_data = underwriting_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(underwriting, field, value)

    db.commit()
    db.refresh(underwriting)
    return underwriting


@router.delete("/{underwriting_id}", status_code=204)
def delete_underwriting(underwriting_id: UUID, db: Session = Depends(get_db)):
    """Delete an underwriting record"""
    underwriting = db.query(DealUnderwriting).filter(
        DealUnderwriting.id == underwriting_id
    ).first()

    if not underwriting:
        raise HTTPException(status_code=404, detail="Underwriting not found")

    db.delete(underwriting)
    db.commit()
    return None
