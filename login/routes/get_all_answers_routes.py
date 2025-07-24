from fastapi import APIRouter, Depends,HTTPException # type: ignore
from fastapi.responses import JSONResponse # type: ignore
from sqlalchemy.orm import Session, joinedload # type: ignore
from login.database import SessionLocal
from login.models import Question
from login.schemas import AnswerResponse

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/get-all-answers/", response_model=list[AnswerResponse])
def get_all_answers(db: Session = Depends(get_db)):
    try:
        questions = db.query(Question).options(joinedload(Question.answers)).all()

        data = []

        for q in questions:

            answer_list = [
                {
                    "id": a.id,
                    "text": a.text,
                    "created_at": str(a.created_at)
                }
                for a in q.answers
            ]

            data.append({
                "id": q.id,
                "text": q.text,
                "answers": answer_list
            })

        return JSONResponse(content={"questions": data}, status_code=200)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve answers: {str(e)}"
        )
