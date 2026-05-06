from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from models.database import get_db
from models.orm import Account
from models.schemas import AccountCreate, AccountOut

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/", response_model=List[AccountOut])
def list_accounts(db: Session = Depends(get_db)):
    return db.query(Account).filter(Account.is_active == True).all()


@router.post("/", response_model=AccountOut, status_code=201)
def create_account(data: AccountCreate, db: Session = Depends(get_db)):
    account = Account(
        name=data.name,
        platform=data.platform,
        handle=data.handle,
        credentials=data.credentials,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}")
def deactivate_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(404, "Account not found")
    account.is_active = False
    db.commit()
    return {"deactivated": account_id}
