from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request # type: ignore
from sqlalchemy.orm import Session # type: ignore
from login import models
from login.utils import send_email
from login.models import Consultant, Connection, Message, new_user
from login.database import SessionLocal
from login import schemas

app = FastAPI()
router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/send_message/{student_id}/")
def send_message(request: Request, student_id: int, msg_data: schemas.MessageRequest, db: Session = Depends(get_db)):
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=400, detail="Token is missing or invalid format")
        
        token = auth_header.removeprefix("Bearer ").strip()

        user = db.query(models.new_user).filter_by(id=student_id, token=token).first()
        if not user:
            raise HTTPException(status_code=404, detail="Invalid or expired token")

        student = db.query(new_user).get(student_id)
        expert = db.query(Consultant).filter_by(official_email=msg_data.expert_email).first()

        if not student or not expert:
            raise HTTPException(status_code=404, detail="Student or Expert not found")

        connection = db.query(Connection).filter_by(student_id=student.id, expert_id=expert.id).first()

        if not connection:
            connection = Connection(student_id=student.id, expert_id=expert.id, is_accepted=False)
            db.add(connection)
            db.commit()

            send_email(
                to_email=expert.official_email,
                subject="You have got one connection request",
                body=f"{student.firstname} ({student.email}) has sent you a connection request."
            )
            return {"message": "Connection request sent."}

        if not connection.is_accepted:
            return {"message": "Connection not yet accepted."}

        message = Message(sender_id=student.id, receiver_id=expert.id, content=msg_data.content)
        db.add(message)
        db.commit()

        send_email(
            to_email=expert.official_email,
            subject="You have a new message",
            body=f"{student.firstname} sent you a new message: \"{msg_data.content}\""
        )

        return {"message": "Message sent and expert notified."}

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.post("/accept_connection/{expert_id}")
def accept_connection(request: Request, expert_id: int, id: schemas.ConnectionRequest, db: Session = Depends(get_db)):
    
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=400, detail="Token is missing or invalid format")

        token = auth_header.removeprefix("Bearer ").strip()

        expert = db.query(models.Consultant).filter_by(id=expert_id, token=token).first()
        if not expert:
            raise HTTPException(status_code=403, detail="Invalid or expired token for this expert")

        connection = db.query(models.Connection).filter_by(student_id=id.student_id, expert_id=expert_id).first()
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")

        connection.is_accepted = True
        db.commit()

        student = db.query(models.new_user).get(id.student_id)
        if student:
            send_email(
                to_email=student.email,
                subject="Connection Accepted",
                body=f"Your connection request has been accepted by the expert. ({expert.official_email})"
            )

        return {"message": "Connection accepted and student notified."}

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")















































































































































































































































 
# @router.post("/accept_connection/{expert_id}")
# def accept_connection(expert_id: int, id: schemas.ConnectionRequest, db: Session = Depends(get_db)):

#     connection = db.query(Connection).filter_by(student_id=id.student_id, expert_id=expert_id).first()

#     if not connection:
#         raise HTTPException(status_code=404, detail="Connection not found")

#     connection.is_accepted = True
#     db.commit()

#     student = db.query(new_user).get(id.student_id)

#     send_email(
#         to_email=student.email,
#         subject="Connection Accepted",
#         body=f"Your connection request has been accepted by the expert."
#     )

#     return {"message": "Connection accepted and student notified."}