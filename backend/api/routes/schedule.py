from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from models.database import SessionLocal
from services.posting_schedule import get_next_optimal_slot, get_schedule_preview, PLATFORM_DEFAULT_HOURS

router = APIRouter(tags=["schedule"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class NextSlotOut(BaseModel):
    platform: str
    account_id: Optional[str]
    next_slot: datetime
    is_data_driven: bool = False


class SchedulePreviewOut(BaseModel):
    platform: str
    account_id: Optional[str]
    slots: List[datetime]
    default_hours: List[int]


@router.get("/schedule/next-slot", response_model=NextSlotOut, summary="Get next optimal posting slot")
def next_slot(
    platform: str = Query("twitter", description="twitter | instagram | tiktok"),
    account_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    slot = get_next_optimal_slot(platform=platform, account_id=account_id, db=db)
    return NextSlotOut(platform=platform, account_id=account_id, next_slot=slot)


@router.get("/schedule/preview", response_model=SchedulePreviewOut, summary="Preview upcoming optimal posting slots")
def schedule_preview(
    platform: str = Query("twitter"),
    account_id: Optional[str] = Query(None),
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
):
    slots = get_schedule_preview(platform=platform, account_id=account_id, db=db, days=days)
    default_hours = PLATFORM_DEFAULT_HOURS.get(platform, [9, 12, 17, 21])
    return SchedulePreviewOut(
        platform=platform,
        account_id=account_id,
        slots=slots,
        default_hours=default_hours,
    )
