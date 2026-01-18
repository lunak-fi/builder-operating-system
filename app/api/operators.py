from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.models import Operator
from app.schemas import OperatorCreate, OperatorUpdate, OperatorResponse

router = APIRouter(prefix="/operators", tags=["operators"])


@router.post("/", response_model=OperatorResponse, status_code=201)
def create_operator(operator: OperatorCreate, db: Session = Depends(get_db)):
    """Create a new operator"""
    db_operator = Operator(**operator.model_dump())
    db.add(db_operator)
    db.commit()
    db.refresh(db_operator)
    return db_operator


@router.get("/search", response_model=List[OperatorResponse])
def search_operators(q: str, db: Session = Depends(get_db)):
    """
    Search for operators by name or legal_name (case-insensitive fuzzy match).
    Returns up to 10 results for autocomplete.
    """
    search_term = f"%{q}%"
    operators = db.query(Operator).filter(
        (Operator.name.ilike(search_term)) |
        (Operator.legal_name.ilike(search_term))
    ).limit(10).all()
    return operators


@router.get("/", response_model=List[OperatorResponse])
def list_operators(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all operators with pagination"""
    operators = db.query(Operator).offset(skip).limit(limit).all()
    return operators


@router.get("/{operator_id}", response_model=OperatorResponse)
def get_operator(operator_id: UUID, db: Session = Depends(get_db)):
    """Get a specific operator by ID"""
    operator = db.query(Operator).filter(Operator.id == operator_id).first()
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")
    return operator


@router.put("/{operator_id}", response_model=OperatorResponse)
def update_operator(
    operator_id: UUID,
    operator_update: OperatorUpdate,
    db: Session = Depends(get_db)
):
    """Update an operator"""
    operator = db.query(Operator).filter(Operator.id == operator_id).first()
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")

    update_data = operator_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(operator, field, value)

    db.commit()
    db.refresh(operator)
    return operator


@router.delete("/{operator_id}", status_code=204)
def delete_operator(operator_id: UUID, db: Session = Depends(get_db)):
    """Delete an operator"""
    operator = db.query(Operator).filter(Operator.id == operator_id).first()
    if not operator:
        raise HTTPException(status_code=404, detail="Operator not found")

    db.delete(operator)
    db.commit()
    return None
