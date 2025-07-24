from fastapi import APIRouter, Depends, HTTPException # type: ignore
from fastapi.responses import JSONResponse # type: ignore
from sqlalchemy.orm import Session # type: ignore
from login.database import SessionLocal
from login.models import Question, Answer
from login.schemas import AnswerCreate


router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/submit-answer/{question_id}/")
def submit_answer(question_id: int, answer: AnswerCreate, db: Session = Depends(get_db)):
    try:
        question = db.query(Question).filter_by(id=question_id).first()
        
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        new_answer = Answer(text=answer.text, question_id=question.id)
        db.add(new_answer)
        db.commit()
        db.refresh(new_answer)

        return JSONResponse(
            status_code=201,
            content={
                "message": "Answer saved successfully!",
                "answer_id": new_answer.id,
                "question_id": question.id,
                "text": new_answer.text
            }
        )

    except Exception as e:
        db.rollback()
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save answer: {str(e)}"
        )
