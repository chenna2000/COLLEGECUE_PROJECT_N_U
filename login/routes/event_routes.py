from datetime import datetime
import os
from typing import Optional
from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, UploadFile # type: ignore
from fastapi import APIRouter, Depends, HTTPException, Query # type: ignore
from sqlalchemy.orm import Session # type: ignore
from login import models
from login.models import Event_Hoster 
from login.database import SessionLocal
from fastapi import Request # type: ignore

app = FastAPI()
router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/create-event/")
def create_event(
    request: Request,
    logo: UploadFile = File(...),
    opportunity_type: str = Form(...),
    opportunity_sub_type: str = Form(...),
    visibility: str = Form(...),
    opportunity_title: str = Form(...),
    organization_name: str = Form(...),
    website: str = Form(...),
    mode_of_event: str = Form(...),
    category: str = Form(...),
    skills: str = Form(...),
    about_opportunity: str = Form(...),
    participant_type: str = Form(...),
    festival_name: Optional[str] = Form(None),
    min_member: Optional[int] = Form(None),
    max_member: Optional[int] = Form(None),
    start_date: Optional[datetime] = Form(None),
    end_date: Optional[datetime] = Form(None),
    db: Session = Depends(get_db)
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or invalid format")

    token = auth_header.removeprefix("Bearer ").strip()

    company = db.query(models.CompanyInCharge).filter_by(token=token).first()
    college = db.query(models.UniversityInCharge).filter_by(token=token).first()
    consultant = db.query(models.Consultant).filter_by(token=token).first()

    if not (company or college or consultant):
        raise HTTPException(status_code=401, detail="Invalid token")

    if participant_type.lower() == "team":
        if min_member is None or max_member is None:
            raise HTTPException(status_code=400, detail="min_member and max_member are required for team participation")
    else:
        min_member = None
        max_member = None

    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_location = os.path.join(upload_dir, logo.filename)

    with open(file_location, "wb") as buffer:
        buffer.write(logo.file.read())

    company_id = company.id if company else None
    university_id = college.id if college else None
    consultant_id = consultant.id if consultant else None

    new_event = Event_Hoster(
        logo=file_location,
        opportunity_type=opportunity_type,
        opportunity_sub_type=opportunity_sub_type,
        visibility=visibility,
        opportunity_title=opportunity_title,
        organization_name=organization_name,
        website=website,
        festival_name=festival_name,
        mode_of_event=mode_of_event,
        category=category,
        skills=skills,
        about_opportunity=about_opportunity,
        participant_type=participant_type,
        min_member=min_member,
        max_member=max_member,
        start_date=start_date,
        end_date=end_date,
        company_id=company_id,
        university_id=university_id,
        consultant_id=consultant_id
    )

    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    return {"message": "Event created successfully", "event_id": new_event.id}


@router.get("/get-events/")
def get_events(
    event_id: Optional[int] = Query(None, description="Fetch a specific event by ID"),
    opportunity_type: Optional[str] = Query(None, description="Filter by opportunity type"),
    db: Session = Depends(get_db)
):
    query = db.query(Event_Hoster)

    if event_id is not None and opportunity_type:
        event = query.filter(
            Event_Hoster.id == event_id,
            Event_Hoster.opportunity_type.ilike(f"%{opportunity_type}%")
        ).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found with given ID and opportunity type")
        return event

    if event_id is not None:
        event = query.filter(Event_Hoster.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found with given ID")
        return event

    if opportunity_type:
        events = query.filter(Event_Hoster.opportunity_type.ilike(f"%{opportunity_type}%")).all()
        return events

    return query.all()
