from fastapi import APIRouter, Depends,HTTPException # type: ignore
from fastapi.responses import JSONResponse # type: ignore
from sqlalchemy.orm import Session # type: ignore
from login.database import SessionLocal
from login.models import Question  # Your SQLAlchemy model
from login.schemas import QuestionCreate  # Your Pydantic schemas


router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/submit-question/")
def submit_question(question: QuestionCreate, db: Session = Depends(get_db)):
    try:
        new_question = Question(text=question.text)
        db.add(new_question)
        db.commit()
        db.refresh(new_question)

        return JSONResponse(
            status_code=201,
            content={
                "message": "Question saved successfully!",
                "question_id": new_question.id,
                "text": new_question.text
            }
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save question: {str(e)}"
        )
