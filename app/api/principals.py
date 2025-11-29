from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.db.session import get_db
from app.models import Principal
from app.schemas import PrincipalCreate, PrincipalUpdate, PrincipalResponse

router = APIRouter(prefix="/principals", tags=["principals"])


@router.post("/", response_model=PrincipalResponse, status_code=201)
def create_principal(principal: PrincipalCreate, db: Session = Depends(get_db)):
    """Create a new principal"""
    db_principal = Principal(**principal.model_dump())
    db.add(db_principal)
    db.commit()
    db.refresh(db_principal)
    return db_principal


@router.get("/", response_model=List[PrincipalResponse])
def list_principals(
    skip: int = 0,
    limit: int = 100,
    operator_id: Optional[UUID] = None,
    db: Session = Depends(get_db)
):
    """List all principals, optionally filtered by operator"""
    query = db.query(Principal)

    if operator_id:
        query = query.filter(Principal.operator_id == operator_id)

    principals = query.offset(skip).limit(limit).all()
    return principals


@router.get("/{principal_id}", response_model=PrincipalResponse)
def get_principal(principal_id: UUID, db: Session = Depends(get_db)):
    """Get a specific principal by ID"""
    principal = db.query(Principal).filter(Principal.id == principal_id).first()
    if not principal:
        raise HTTPException(status_code=404, detail="Principal not found")
    return principal


@router.put("/{principal_id}", response_model=PrincipalResponse)
def update_principal(
    principal_id: UUID,
    principal_update: PrincipalUpdate,
    db: Session = Depends(get_db)
):
    """Update a principal"""
    principal = db.query(Principal).filter(Principal.id == principal_id).first()
    if not principal:
        raise HTTPException(status_code=404, detail="Principal not found")

    update_data = principal_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(principal, field, value)

    db.commit()
    db.refresh(principal)
    return principal


@router.delete("/{principal_id}", status_code=204)
def delete_principal(principal_id: UUID, db: Session = Depends(get_db)):
    """Delete a principal"""
    principal = db.query(Principal).filter(Principal.id == principal_id).first()
    if not principal:
        raise HTTPException(status_code=404, detail="Principal not found")

    db.delete(principal)
    db.commit()
    return None
