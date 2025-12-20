from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.db.session import get_db
from app.models import Deal
from app.schemas import DealCreate, DealUpdate, DealResponse

router = APIRouter(prefix="/deals", tags=["deals"])


@router.post("/", response_model=DealResponse, status_code=201)
def create_deal(deal: DealCreate, db: Session = Depends(get_db)):
    """Create a new deal"""
    db_deal = Deal(**deal.model_dump())
    db.add(db_deal)
    db.commit()
    db.refresh(db_deal)
    return db_deal


@router.get("/", response_model=List[DealResponse])
def list_deals(
    skip: int = 0,
    limit: int = 100,
    operator_id: Optional[UUID] = None,
    status: Optional[str] = None,
    asset_type: Optional[str] = None,
    state: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all deals with optional filters"""
    query = db.query(Deal)

    if operator_id:
        query = query.filter(Deal.operator_id == operator_id)
    if status:
        query = query.filter(Deal.status == status)
    if asset_type:
        query = query.filter(Deal.asset_type == asset_type)
    if state:
        query = query.filter(Deal.state == state)

    deals = query.offset(skip).limit(limit).all()
    return deals


@router.get("/{deal_id}", response_model=DealResponse)
def get_deal(deal_id: UUID, db: Session = Depends(get_db)):
    """Get a specific deal by ID"""
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


@router.put("/{deal_id}", response_model=DealResponse)
def update_deal(
    deal_id: UUID,
    deal_update: DealUpdate,
    db: Session = Depends(get_db)
):
    """Update a deal"""
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    update_data = deal_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(deal, field, value)

    db.commit()
    db.refresh(deal)
    return deal


@router.delete("/{deal_id}", status_code=204)
def delete_deal(deal_id: UUID, db: Session = Depends(get_db)):
    """Delete a deal"""
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    db.delete(deal)
    db.commit()
    return None


@router.post("/{deal_id}/move-next", response_model=DealResponse)
def move_deal_to_next_stage(deal_id: UUID, db: Session = Depends(get_db)):
    """Move deal to the next stage in the pipeline"""
    from app.models.deal import DEAL_STATUS_PROGRESSION, DealStatus

    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    current_status = deal.status or DealStatus.INBOX
    next_status = DEAL_STATUS_PROGRESSION.get(current_status)

    if next_status is None:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot move deal forward from status: {current_status}"
        )

    deal.status = next_status
    db.commit()
    db.refresh(deal)
    return deal


@router.post("/{deal_id}/pass", response_model=DealResponse)
def pass_deal(deal_id: UUID, db: Session = Depends(get_db)):
    """Mark a deal as passed"""
    from app.models.deal import DealStatus

    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    deal.status = DealStatus.PASSED
    db.commit()
    db.refresh(deal)
    return deal
