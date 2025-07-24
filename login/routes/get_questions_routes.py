from fastapi import APIRouter, Depends, HTTPException # type: ignore
from sqlalchemy.orm import Session # type: ignore
from login.database import SessionLocal
from login.models import Question
from login.schemas import QuestionResponse

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/get-all-questions/", response_model=list[QuestionResponse])
def get_all_questions(db: Session = Depends(get_db)):
    try:
        questions = db.query(Question).all()

        return questions

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve questions: {str(e)}"
        )
