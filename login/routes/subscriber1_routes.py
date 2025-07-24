from fastapi import APIRouter, Depends, HTTPException # type: ignore
from fastapi.responses import JSONResponse # type: ignore
from sqlalchemy.orm import Session # type: ignore
from login.models import Subscriber1
from login.schemas import SubscriptionSchema1
from login.database import SessionLocal

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/subscriber1")
async def subscribe(subscriber: SubscriptionSchema1, db: Session = Depends(get_db)):
    try:
        existing_subscriber = db.query(Subscriber1).filter_by(email=subscriber.email).first()

        if existing_subscriber:
            return JSONResponse(
                status_code=200,
                content={"message": f"You are already subscribed at {existing_subscriber.subscribed_at}"}
            )

        new_subscriber = Subscriber1(email=subscriber.email)
        db.add(new_subscriber)
        db.commit()
        db.refresh(new_subscriber)

        return JSONResponse(
            status_code=201,
            content={"message": f"You have successfully subscribed at {new_subscriber.subscribed_at}"}
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Subscription failed: {str(e)}")
