import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from models.database import SessionLocal
from models.orm import SystemConfig
from models.schemas import SystemConfigOut, SystemConfigUpdate

logger = logging.getLogger(__name__)

router = APIRouter(tags=["config"])

# Default values seeded when not yet persisted
_DEFAULTS = {
    "autopilot_enabled": False,
    "autopilot_confidence_threshold": 0.75,
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_or_default(db: Session, key: str):
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    return row.value if row else _DEFAULTS[key]


def _upsert(db: Session, key: str, value) -> None:
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if row:
        row.value = value
    else:
        db.add(SystemConfig(key=key, value=value))


@router.get("/config", response_model=SystemConfigOut, summary="Get system config")
def get_config(db: Session = Depends(get_db)):
    return SystemConfigOut(
        autopilot_enabled=_get_or_default(db, "autopilot_enabled"),
        autopilot_confidence_threshold=_get_or_default(db, "autopilot_confidence_threshold"),
    )


@router.patch("/config", response_model=SystemConfigOut, summary="Update system config")
def update_config(payload: SystemConfigUpdate, db: Session = Depends(get_db)):
    if payload.autopilot_enabled is not None:
        _upsert(db, "autopilot_enabled", payload.autopilot_enabled)

    if payload.autopilot_confidence_threshold is not None:
        threshold = payload.autopilot_confidence_threshold
        if not (0.0 <= threshold <= 1.0):
            raise HTTPException(status_code=422, detail="threshold must be between 0 and 1")
        _upsert(db, "autopilot_confidence_threshold", threshold)

    db.commit()
    return SystemConfigOut(
        autopilot_enabled=_get_or_default(db, "autopilot_enabled"),
        autopilot_confidence_threshold=_get_or_default(db, "autopilot_confidence_threshold"),
    )
