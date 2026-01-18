from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
import logging

from app.db.session import get_db
from app.models import Memo
from app.schemas import MemoResponse
from app.services.memo_generator import generate_memo_for_deal, MemoGenerationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memos", tags=["memos"])


@router.get("/deal/{deal_id}", response_model=MemoResponse)
def get_memo_by_deal(deal_id: UUID, db: Session = Depends(get_db)):
    """
    Get the memo for a specific deal.
    Returns 404 if no memo exists for the deal.
    """
    memo = db.query(Memo).filter(Memo.deal_id == deal_id).first()

    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found for this deal")

    return memo


@router.post("/generate/{deal_id}", response_model=MemoResponse, status_code=201)
def generate_memo(deal_id: UUID, db: Session = Depends(get_db)):
    """
    Manually trigger memo generation for a deal.
    Deletes any existing memo and generates a fresh one.
    """
    try:
        logger.info(f"Manual memo generation requested for deal {deal_id}")
        memo = generate_memo_for_deal(deal_id, db)
        return memo

    except MemoGenerationError as e:
        logger.error(f"Memo generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during memo generation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Memo generation failed: {str(e)}")


@router.delete("/{memo_id}", status_code=204)
def delete_memo(memo_id: UUID, db: Session = Depends(get_db)):
    """Delete a memo"""
    memo = db.query(Memo).filter(Memo.id == memo_id).first()

    if not memo:
        raise HTTPException(status_code=404, detail="Memo not found")

    db.delete(memo)
    db.commit()
    return None
