from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.models import Fund, Deal
from app.schemas import FundCreate, FundUpdate, FundResponse
from app.schemas.deal import DealResponse

router = APIRouter(prefix="/funds", tags=["funds"])


@router.post("/", response_model=FundResponse, status_code=201)
def create_fund(fund: FundCreate, db: Session = Depends(get_db)):
    """Create a new fund"""
    db_fund = Fund(**fund.model_dump())
    db.add(db_fund)
    db.commit()
    db.refresh(db_fund)
    return db_fund


@router.get("/", response_model=List[FundResponse])
def list_funds(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all funds with pagination"""
    funds = db.query(Fund).offset(skip).limit(limit).all()
    return funds


@router.get("/{fund_id}", response_model=FundResponse)
def get_fund(fund_id: UUID, db: Session = Depends(get_db)):
    """Get a specific fund by ID"""
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    return fund


@router.get("/{fund_id}/deals", response_model=List[DealResponse])
def get_fund_deals(fund_id: UUID, db: Session = Depends(get_db)):
    """Get all deals associated with a fund"""
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")

    deals = db.query(Deal).filter(Deal.fund_id == fund_id).all()
    return deals


@router.put("/{fund_id}", response_model=FundResponse)
def update_fund(
    fund_id: UUID,
    fund_update: FundUpdate,
    db: Session = Depends(get_db)
):
    """Update a fund"""
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")

    update_data = fund_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(fund, field, value)

    db.commit()
    db.refresh(fund)
    return fund


@router.delete("/{fund_id}", status_code=204)
def delete_fund(fund_id: UUID, db: Session = Depends(get_db)):
    """Delete a fund"""
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")

    db.delete(fund)
    db.commit()
    return None
