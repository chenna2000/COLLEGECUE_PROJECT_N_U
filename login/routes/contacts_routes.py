from fastapi import APIRouter, Depends,HTTPException # type: ignore
from fastapi.responses import JSONResponse # type: ignore
from sqlalchemy.orm import Session # type: ignore
from login.database import SessionLocal
from login.models import Contact
from login.schemas import ContactCreate

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/submit-contact/", status_code=200)
def submit_contact_form(contact: ContactCreate, db: Session = Depends(get_db)):
    try:
        new_contact = Contact(
            name=contact.name,
            email=contact.email,
            subject=contact.subject,
            website=contact.website,
            message=contact.message
        )

        db.add(new_contact)
        db.commit()
        db.refresh(new_contact)

        return JSONResponse(
            status_code=200,
            content={"message": "Contact form submitted successfully!", "contact_id": new_contact.id}
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit contact form: {str(e)}"
        )
