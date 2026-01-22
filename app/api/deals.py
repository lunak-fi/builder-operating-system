from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.db.session import get_db
from app.models import Deal, DealOperator, Operator
from app.schemas import DealCreate, DealUpdate, DealResponse, AddOperatorRequest, UpdateOperatorRequest, DealOperatorResponse

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


@router.post("/{deal_id}/operators", response_model=DealOperatorResponse, status_code=201)
def add_operator_to_deal(
    deal_id: UUID,
    request: AddOperatorRequest,
    db: Session = Depends(get_db)
):
    """Add an operator (sponsor) to a deal"""
    # Verify deal exists
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    # Verify operator exists
    operator = db.query(Operator).filter(Operator.id == request.operator_id).first()
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")

    # Check if relationship already exists
    existing = db.query(DealOperator).filter(
        DealOperator.deal_id == deal_id,
        DealOperator.operator_id == request.operator_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Operator is already associated with this deal"
        )

    # If setting as primary, unset any existing primary
    if request.is_primary:
        db.query(DealOperator).filter(
            DealOperator.deal_id == deal_id,
            DealOperator.is_primary == True
        ).update({"is_primary": False})

    # Create new relationship
    deal_operator = DealOperator(
        deal_id=deal_id,
        operator_id=request.operator_id,
        is_primary=request.is_primary
    )
    db.add(deal_operator)
    db.commit()
    db.refresh(deal_operator)
    return deal_operator


@router.delete("/{deal_id}/operators/{operator_id}", status_code=204)
def remove_operator_from_deal(
    deal_id: UUID,
    operator_id: UUID,
    db: Session = Depends(get_db)
):
    """Remove an operator (sponsor) from a deal"""
    # Verify deal exists
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    # Find the relationship
    deal_operator = db.query(DealOperator).filter(
        DealOperator.deal_id == deal_id,
        DealOperator.operator_id == operator_id
    ).first()
    if not deal_operator:
        raise HTTPException(
            status_code=404,
            detail="Operator is not associated with this deal"
        )

    # Prevent removing the last operator
    operator_count = db.query(DealOperator).filter(
        DealOperator.deal_id == deal_id
    ).count()
    if operator_count <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot remove the last operator from a deal"
        )

    # Delete the relationship
    db.delete(deal_operator)
    db.commit()
    return None


@router.put("/{deal_id}/operators/{operator_id}", response_model=DealOperatorResponse)
def update_deal_operator(
    deal_id: UUID,
    operator_id: UUID,
    request: UpdateOperatorRequest,
    db: Session = Depends(get_db)
):
    """Update an operator's relationship to a deal (e.g., set as primary)"""
    # Verify deal exists
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    # Find the relationship
    deal_operator = db.query(DealOperator).filter(
        DealOperator.deal_id == deal_id,
        DealOperator.operator_id == operator_id
    ).first()
    if not deal_operator:
        raise HTTPException(
            status_code=404,
            detail="Operator is not associated with this deal"
        )

    # If setting as primary, unset any existing primary
    if request.is_primary:
        db.query(DealOperator).filter(
            DealOperator.deal_id == deal_id,
            DealOperator.is_primary == True,
            DealOperator.id != deal_operator.id
        ).update({"is_primary": False})

    # Update the relationship
    deal_operator.is_primary = request.is_primary
    db.commit()
    db.refresh(deal_operator)
    return deal_operator


@router.post("/{deal_id}/geocode")
def geocode_deal(deal_id: UUID, db: Session = Depends(get_db)):
    """Manually trigger geocoding for a deal"""
    from app.services.geocoding import MSAGeocoder
    from datetime import datetime

    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    try:
        geocoder = MSAGeocoder()
        result = geocoder.standardize_market(
            deal.address_line1 or "",
            "",
            deal.state or "",
            deal.postal_code or ""
        )

        if result["geocoded"]:
            deal.msa = result["msa"]
            deal.latitude = result["latitude"]
            deal.longitude = result["longitude"]
            deal.geocoded_at = datetime.utcnow()
            deal.msa_source = "manual_geocode"
            db.commit()

            return {
                "success": True,
                "msa": result["msa"],
                "latitude": result["latitude"],
                "longitude": result["longitude"]
            }
        else:
            return {"success": False, "error": "Geocoding failed"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Geocoding error: {str(e)}")


@router.put("/{deal_id}/market")
def update_market(deal_id: UUID, msa: str, db: Session = Depends(get_db)):
    """Manually override MSA for a deal"""
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    deal.msa = msa
    deal.msa_source = "manual_override"
    db.commit()

    return {"success": True, "msa": msa}
