from fastapi import APIRouter, FastAPI, Request, Header, HTTPException, Depends, Form # type: ignore
from fastapi.responses import JSONResponse # type: ignore
from login.utils import send_appliction_email, send_notification_to_group
from pydantic import EmailStr  # type: ignore
from sqlalchemy.orm import Session # type: ignore
from sqlalchemy import func # type: ignore
from job_portal.routes.company import filter_empty_entries
from job_portal.schemas import CollegeEnquirySchema, Job1CreateRequest, Job1FilterParams, Job1StatusRequest, JobDetailOut, JobOut, StatusUpdatePayload
from login.database import SessionLocal
from job_portal.model import Achievements, Application1, Certification, College, Education, Experience, Job1, JobseekerResume, NewUserEnquiry, Project, Publications, Reference, Resume
from login.models import OnlineStatus, UniversityInCharge
from typing import List, Optional
from datetime import date, datetime
from sqlalchemy.exc import SQLAlchemyError # type: ignore
from fastapi.encoders import jsonable_encoder # type: ignore

app = FastAPI()

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/college-status/{university_in_charge_id}")
def college_status_counts(university_in_charge_id: int, request: Request, db: Session = Depends(get_db)):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or in an invalid format")

    token = auth_header.split(" ")[1]
    university_in_charge = db.query(UniversityInCharge).filter_by(id=university_in_charge_id, token=token).first()

    if not university_in_charge:
        raise HTTPException(status_code=404, detail="Invalid token or university in charge not found")
    
    clg_id=university_in_charge.clg_id

    enquiry_count = db.query(NewUserEnquiry).filter_by(clg_id=clg_id).count()
    total_applications = db.query(Application1).filter_by(university_in_charge_id=university_in_charge_id).count()
    shortlisted_count = db.query(Application1).filter(
        Application1.university_in_charge_id == university_in_charge_id,
        Application1.status.in_(["selected", "shortlisted"])
    ).count()
    rejected_count = db.query(Application1).filter_by(
        university_in_charge_id=university_in_charge_id,
        status="rejected"
    ).count()
    jobs_posted = db.query(Job1).filter_by(university_in_charge_id=university_in_charge_id).count()

    def get_counts_by_month(model, date_field: str, extra_filters=None):
        date_column = getattr(model, date_field)
        query = db.query(
            func.date_format(date_column, '%Y-%m').label("month"),
            func.count().label("count")
        ).filter(model.university_in_charge_id == university_in_charge_id)

        if extra_filters:
            for condition in extra_filters:
                query = query.filter(condition)

        results = query.group_by("month").order_by("month").all()
        return {r.month: r.count for r in results} if results else {}

    current_month = datetime.now().strftime("%Y-%m")

    return JSONResponse(content={
        "total_enquiries_count": enquiry_count,
        "total_applications": total_applications,
        "shortlisted_count": shortlisted_count,
        "rejected_count": rejected_count,
        "jobs_posted": jobs_posted,
        "enquiries_by_month": get_counts_by_month(NewUserEnquiry, "created_at") or {current_month: 0},
        "jobs_by_month": get_counts_by_month(Job1, "published_at") or {current_month: 0},
        "applications_by_month": get_counts_by_month(Application1, "applied_at") or {current_month: 0},
        "shortlisted_by_month": get_counts_by_month(
            Application1, "applied_at", [Application1.status.in_(["selected", "shortlisted"])]
        ) or {current_month: 0},
        "rejected_by_month": get_counts_by_month(
            Application1, "applied_at", [Application1.status == "rejected"]
        ) or {current_month: 0},
    })

def validate_college_token(token: str, university_in_charge_id: int, db: Session) -> UniversityInCharge:
    university_in_charge = db.query(UniversityInCharge).filter_by(id=university_in_charge_id, token=token).first()
    if not university_in_charge:
        raise HTTPException(status_code=404, detail="Invalid token or university in charge ID")
    return university_in_charge

@router.get("/colleges/{university_in_charge_id}")
def get_colleges(
    university_in_charge_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or invalid format")

    token = auth_header.split(" ")[1]

    try:
        university_in_charge = db.query(UniversityInCharge).filter_by(id=university_in_charge_id, token=token).first()
        if not university_in_charge:
            raise HTTPException(status_code=404, detail="Invalid token or university in charge ID")

        colleges = db.query(UniversityInCharge).filter_by(university_in_charge_id=university_in_charge.id).all()
        if not colleges:
            raise HTTPException(status_code=404, detail="No colleges found for this university in charge")

        colleges_data = [
            {
                "id": college.id,
                "name": college.college_name,
                "email": college.email,
                "phone": college.phone,
                "address": college.address,
                "city": college.city,
                "state": college.state,
                "country": college.country,
                "zipcode": college.zipcode,
                "website": college.website,
                "website_urls": college.website_urls,
                "about_college": college.about_college,
                "university_type": college.university_type,
                "founded_date": str(college.founded_date) if college.founded_date else None,
            }
            for college in colleges
        ]
        return {"status": "success", "colleges": colleges_data}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.post("/colleges/{university_in_charge_id}")
def create_or_update_college(
    university_in_charge_id: int,
    email: EmailStr = Form(...),
    college_name: str = Form(...),
    phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    zipcode: Optional[str] = Form(None),
    website: Optional[str] = Form(None),
    website_urls: Optional[str] = Form(None),
    about_college: Optional[str] = Form(None),
    university_type: Optional[str] = Form(None),
    founded_date: Optional[date] = Form(None),
    request: Request = None,
    db: Session = Depends(get_db),
):
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=400, detail="Token is missing or invalid format")
        token = auth_header.split(" ")[1]

        university_in_charge = validate_college_token(token, university_in_charge_id, db)
        if not university_in_charge:
            raise HTTPException(status_code=404, detail="University in charge not found or token invalid")

        if email != university_in_charge.official_email:
            raise HTTPException(status_code=400, detail="Email does not match the email of the university in charge")

        college = db.query(College).filter_by(email=email, university_in_charge_id=university_in_charge.id).first()
        if not college:
            college = College(email=email, university_in_charge_id=university_in_charge.id)

        college.college_name = college_name
        college.phone = phone
        college.address = address
        college.city = city
        college.state = state
        college.country = country
        college.zipcode = zipcode
        college.website = website
        college.website_urls = website_urls
        college.about_college = about_college
        college.university_type = university_type
        college.founded_date = founded_date

        db.add(college)
        db.commit()
        db.refresh(college)

        return {
            "status": "success",
            "message": "College created/updated successfully",
            "college_id": college.id,
        }

    except HTTPException as http_exc:
        raise http_exc
    except SQLAlchemyError as db_err:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(db_err)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.delete("/colleges/{university_in_charge_id}/{college_id}")
def delete_college(
    university_in_charge_id: int,
    college_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or invalid format")

    token = auth_header.split(" ")[1]

    try:
        university_in_charge = db.query(UniversityInCharge).filter_by(id=university_in_charge_id, token=token).first()
        if not university_in_charge:
            raise HTTPException(status_code=404, detail="Invalid token or university in charge ID")

        college = db.query(College).filter_by(id=college_id, university_in_charge_id=university_in_charge.id).first()
        if not college:
            raise HTTPException(status_code=404, detail="College not found or does not belong to this university in charge")

        db.delete(college)
        db.commit()

        return {"status": "success", "message": f"College with ID {college_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.post("/create-college-jobs/{university_in_charge_id}/")
def create_college_job(
    university_in_charge_id: int,
    request: Request,
    job_data: Job1CreateRequest,
    db: Session = Depends(get_db)
):

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or in an invalid format")
    token = auth_header.split(" ")[1]

    university_in_charge = db.query(UniversityInCharge).filter_by(id=university_in_charge_id, token=token).first()
    if not university_in_charge:
        raise HTTPException(status_code=401, detail="Invalid token or university in charge not found")

    college = db.query(College).filter_by(id=job_data.college, university_in_charge_id=university_in_charge.id).first()
    if not college:
        raise HTTPException(status_code=404, detail=f'College with id "{job_data.college}" does not exist')

    if db.query(Job1).filter_by(college_id=college.id).count() >= 100:
        return JSONResponse(content={"message": "Limit exceeded for job postings by this college"}, status_code=200)

    try:
        new_job = Job1(
            job_title=job_data.job_title.strip(),
            location=job_data.location,
            description=job_data.description,
            requirements=job_data.requirements,
            job_type=job_data.job_type,
            experience=job_data.experience,
            experience_yr=job_data.experience_yr,
            category=job_data.category,
            workplaceTypes=job_data.workplaceTypes,
            skills=job_data.skills,
            questions=job_data.questions,
            job_status=job_data.job_status,
            college_id=college.id,
            university_in_charge_id=university_in_charge.id,
        )
        db.add(new_job)
        db.commit()
        return JSONResponse(content={"message": "Job created successfully"}, status_code=201)

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving job: {str(e)}")

@router.get("/jobs-college/{university_in_charge_id}/")
def jobs_by_college(
    university_in_charge_id: int,
    request: Request,
    filters: Job1FilterParams = Depends(),
    db: Session = Depends(get_db)
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or in an invalid format")

    token = auth_header.split(" ")[1]

    university_in_charge = db.query(UniversityInCharge).filter_by(id=university_in_charge_id, token=token).first()
    if not university_in_charge:
        raise HTTPException(status_code=401, detail="Invalid token or university in charge not found")

    if not (filters.name or filters.sort_order or filters.job_status):
        raise HTTPException(status_code=400, detail="Select at least one parameter")

    jobs_query = db.query(Job1)

    if filters.name:
        college = db.query(College).filter_by(college_name=filters.name, university_in_charge_id=university_in_charge.id).first()
        if not college:
            raise HTTPException(status_code=404, detail="College not found")
        jobs_query = jobs_query.filter(Job1.college_id == college.id)

    if filters.job_status:
        if filters.job_status.lower() not in {"active", "closed"}:
            raise HTTPException(status_code=400, detail="Invalid job status")
        jobs_query = jobs_query.filter(Job1.job_status == filters.job_status.lower())

    if filters.sort_order:
        if filters.sort_order == "latest":
            jobs_query = jobs_query.order_by(Job1.published_at.desc())
        elif filters.sort_order == "oldest":
            jobs_query = jobs_query.order_by(Job1.published_at.asc())
        else:
            raise HTTPException(status_code=400, detail="Invalid sort order")

    jobs = jobs_query.all()

    jobs_list = [{
        "id": job.id,
        "university_in_charge": str(university_in_charge.university_name),
        "job_title": job.job_title,
        "location": job.location,
        "description": job.description,
        "requirements": job.requirements,
        "job_type": job.job_type,
        "experience": job.experience,
        "category": job.category,
        "published_at": job.published_at,
        "status": job.job_status,
    } for job in jobs]

    return JSONResponse(content=jsonable_encoder(jobs_list), status_code=200)

@router.api_route("/update-college-job/{university_in_charge_id}/{job_id}/", methods=["GET", "PUT", "DELETE"])
def update_college_job(
    university_in_charge_id: int,
    job_id: str,
    request: Request,
    job_data: Job1CreateRequest, 
    db: Session = Depends(get_db), 
):

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or in an invalid format")
    token = auth_header.split(" ")[1]

    university_in_charge = db.query(UniversityInCharge).filter_by(id=university_in_charge_id, token=token).first()
    if not university_in_charge:
        raise HTTPException(status_code=401, detail="Invalid token or university in charge not found")

    job = db.query(Job1).filter_by(id=job_id, university_in_charge_id=university_in_charge.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if request.method == "GET":
        return {
            "id": job.id,
            "job_title": job.job_title,
            "college": job.college_id,
            "location": job.location,
            "requirements": job.requirements,
            "job_type": job.job_type,
            "experience": job.experience,
            "category": job.category,
            "skills": job.skills,
            "workplaceTypes": job.workplaceTypes,
            "description": job.description,
            "experience_yr": job.experience_yr,
            "source": job.source,
        }

    elif request.method == "DELETE":
        db.delete(job)
        db.commit()
        return JSONResponse(content={"message": "Job deleted successfully"}, status_code=200)

    elif request.method == "PUT":
        if not job_data:
            raise HTTPException(status_code=400, detail="Missing JSON body")

        if not job_data.college:
            raise HTTPException(status_code=400, detail="College name is required")
        college = db.query(College).filter_by(id=job_data.college, university_in_charge_id=university_in_charge.id).first()
        if not college:
            raise HTTPException(status_code=404, detail=f'College with id "{job_data.college}" does not exist')

        try:
            for key, value in job_data.dict(exclude_unset=True).items():
                setattr(job, key, value)
            job.college_id = college.id
            job.university_in_charge_id = university_in_charge.id
            db.commit()
            return JSONResponse(content={"message": "Job updated successfully"}, status_code=200)

        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Error updating job: {str(e)}")

@router.post("/change-college-job-status/{university_in_charge_id}/{job_id}/")
def change_college_job_status(
    university_in_charge_id: int,
    job_id: str,
    job_status_request: Job1StatusRequest,
    request: Request,
    db: Session = Depends(get_db),
):

    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=400, detail="Token is missing or in an invalid format")

    token = auth_header.split(' ')[1]

    university_in_charge = db.query(UniversityInCharge).filter_by(id=university_in_charge_id, token=token).first()
    if not university_in_charge:
        raise HTTPException(status_code=401, detail="Invalid token or university in charge not found")

    if job_status_request.job_status not in {"active", "closed"}:
        raise HTTPException(status_code=400, detail="Valid job_status is required")

    job = db.query(Job1).filter_by(id=job_id, university_in_charge_id=university_in_charge.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        job.job_status = job_status_request.job_status
        db.commit()
        return JSONResponse(
            content={"message": "Job status updated successfully", "job_id": job_id, "status": job.job_status},
            status_code=200,
        )
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating job status: {str(e)}")


def fetch_applications_for_college(job, db: Session):
    applications = db.query(Application1).filter_by(job_id=job.id).all()
    applications_list = []

    for app in applications:
        resume = None
        if app.user_id:
            resume = db.query(Resume).filter_by(user_id=app.user_id).first()
        elif app.job_seeker_id:
            resume = db.query(JobseekerResume).filter_by(job_seeker_id=app.job_seeker_id).first()

        resume_data = {}
        if resume:
            education_entries = db.query(Education).filter_by(resume_id=resume.id).all()
            experience_entries = db.query(Experience).filter_by(resume_id=resume.id).all()
            projects = db.query(Project).filter_by(resume_id=resume.id).all()
            references = db.query(Reference).filter_by(resume_id=resume.id).all()
            certifications = db.query(Certification).filter_by(resume_id=resume.id).all()
            achievements = db.query(Achievements).filter_by(resume_id=resume.id).all()
            publications = db.query(Publications).filter_by(resume_id=resume.id).all()

            resume_data = {
                "address": resume.address,
                "date_of_birth": resume.date_of_birth,
                "website_urls": resume.website_urls,
                "skills": resume.skills,
                "activities": resume.activities,
                "interests": resume.interests,
                "languages": resume.languages,
                "bio": resume.bio,
                "city": resume.city,
                "state": resume.state,
                "country": resume.country,
                "zipcode": resume.zipcode,
                "objective": getattr(resume.objective, 'text', 'Not specified') if hasattr(resume, 'objective') else 'Not specified',
                "education": [
                    {
                        "course_or_degree": edu.course_or_degree,
                        "school_or_university": edu.school_or_university,
                        "grade_or_cgpa": edu.grade_or_cgpa,
                        "start_date": edu.start_date,
                        "end_date": edu.end_date,
                        "description": edu.description
                    } for edu in education_entries
                ],
                "experience": filter_empty_entries([
                    {
                        "job_title": exp.job_title,
                        "company_name": exp.company_name,
                        "start_date": exp.start_date,
                        "end_date": exp.end_date,
                        "description": exp.description,
                    } for exp in experience_entries
                ]),
                "projects": filter_empty_entries([
                    {
                        "title": p.title,
                        "description": p.description,
                        "project_link": p.project_link
                    } for p in projects
                ]),
                "references": filter_empty_entries([
                    {
                        "name": r.name,
                        "contact_info": r.contact_info,
                        "relationship": r.relationship,
                    } for r in references
                ]),
                "certifications": filter_empty_entries([
                    {
                        "name": c.name,
                        "start_date": c.start_date,
                        "end_date": c.end_date,
                    } for c in certifications
                ]),
                "achievements": filter_empty_entries([
                    {
                        "title": a.title,
                        "publisher": a.publisher,
                        "start_date": a.start_date,
                        "end_date": a.end_date,
                    } for a in achievements
                ]),
                "publications": filter_empty_entries([
                    {
                        "title": pub.title,
                        "start_date": pub.start_date,
                        "end_date": pub.end_date,
                    } for pub in publications
                ]),
            }

        model_name = "new_user" if app.user_id else "JobSeeker"

        applications_list.append({
            "id": app.id,
            "first_name": app.first_name,
            "last_name": app.last_name,
            "email": app.email,
            "phone_number": app.phone_number,
            "status": app.status,
            "applied_at": app.applied_at.isoformat() if app.applied_at else None,
            "model_name": model_name,
            "resume_details": resume_data,
        })

    # return applications_list
    return {
        "applications": applications_list,
        "application_count": len(applications_list)
    }

@router.get("/college-job-applications/{university_in_charge_id}/{job_id}")
def fetch_college_job_applications(
    university_in_charge_id: int,
    job_id: int,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or not in the correct format")

    token = authorization.split(" ")[1]

    university_in_charge = db.query(UniversityInCharge).filter_by(id=university_in_charge_id, token=token).first()
    if not university_in_charge:
        raise HTTPException(status_code=401, detail="Invalid token or university in charge not found")

    job = db.query(Job1).filter_by(id=job_id, university_in_charge_id=university_in_charge.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="No Jobs Found")

    applications_list = fetch_applications_for_college(job, db)

    job_details = {
        'job_title': job.job_title,
        # 'college': job.college.college_name,
        'description': job.description,
        'requirements': job.requirements,
        'published_at': job.published_at.isoformat() if job.published_at else None,
        'experience_yr': job.experience_yr,
        'job_type': job.job_type,
        'experience': job.experience,
        'category': job.category,
        'skills': job.skills,
        'workplaceTypes': job.workplaceTypes,
        'location': job.location,
        'questions': job.questions,
        'job_status': job.job_status,
        'must_have_qualification': job.must_have_qualification,
    }

    return JSONResponse(content=jsonable_encoder({
    "jobdetails": job_details,
    "applicants": applications_list,
}))


@router.get("/college_jobs/{college_id}/{university_in_charge_id}", response_model=List[JobOut])
async def college_jobs_api(
    college_id: int,
    university_in_charge_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or invalid format")

    token = auth_header.split(" ")[1]

    university_in_charge = db.query(UniversityInCharge).filter_by(id=university_in_charge_id, token=token).first()
    if not university_in_charge:
        raise HTTPException(status_code=404, detail="Invalid token or university in charge not found")

    try:
        jobs = db.query(Job1).filter_by(college_id=college_id, university_in_charge_id=university_in_charge_id).all()
        if not jobs:
            raise HTTPException(status_code=404, detail="No jobs found.")

        return jobs

    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/job-detail/{college_id}/{university_in_charge_id}/{job_id}", response_model=JobDetailOut)
async def job_detail_api(
    college_id: int,
    university_in_charge_id: int,
    job_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or invalid format")

    token = auth_header.split(" ")[1]

    university_in_charge = db.query(UniversityInCharge).filter_by(id=university_in_charge_id, token=token).first()
    if not university_in_charge:
        raise HTTPException(status_code=404, detail="Invalid token or university in charge not found")

    job = db.query(Job1).filter_by(
        id=job_id,
        college_id=college_id,
        university_in_charge_id=university_in_charge_id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@router.get("/fetch-student-enquiries/{university_in_charge_id}/", response_model=List[CollegeEnquirySchema])
def get_student_enquiries_for_college(
    university_in_charge_id: int,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or invalid format")

    token = authorization.split(" ")[1]

    university = db.query(UniversityInCharge).filter_by(id=university_in_charge_id, token=token).first()
    if not university:
        raise HTTPException(status_code=404, detail="Invalid token or university in charge not found")

    enquiries = db.query(NewUserEnquiry).filter_by(university_in_charge_id=university.id).all()

    return enquiries

@router.put("/update-college-application-status/{university_in_charge_id}/{application_id}/")
async def update_college_application_status(
    university_in_charge_id: int,
    application_id: int,
    payload: StatusUpdatePayload,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or invalid format")
    token = authorization.split(" ")[1]

    university_in_charge = db.query(UniversityInCharge).filter_by(id=university_in_charge_id, token=token).first()
    if not university_in_charge:
        raise HTTPException(status_code=401, detail="Invalid token or university in charge not found")

    application = db.query(Application1).filter_by(id=application_id, university_in_charge_id=university_in_charge_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    application.status = payload.application_status
    db.commit()

    message = (
        f"Your application for {application.job.job_title} has been updated "
        f"to {application.status} by {university_in_charge.university_name}"
    )

    if application.job_seeker:
        job_seeker = application.job_seeker
        recipient_status = db.query(OnlineStatus).filter_by(email=job_seeker.email).first()
        group_name = job_seeker.email.replace("@", "_at_").replace(".", "_dot_")
        group_name = f"notifications_{group_name}"

        if recipient_status and recipient_status.is_online:
            await send_notification_to_group(group_name, message)
            print("Notification was send in a dashboard")
        else:
            send_appliction_email(
                subject="Application Status Update",
                body=f"Dear {job_seeker.first_name} {job_seeker.last_name},\n\n{message}\n\nHR Team\n{university_in_charge.university_name}",
                recipient=job_seeker.email,
            )

    if application.user:
        user = application.user
        recipient_status = db.query(OnlineStatus).filter_by(email=user.email).first()
        group_name = user.email.replace("@", "_at_").replace(".", "_dot_")
        group_name = f"notifications_{group_name}"

        if recipient_status and recipient_status.is_online:
            await send_notification_to_group(group_name, message)
            print("Notification was send in a dashboard")
        else:
            send_appliction_email(
                subject="Application Status Update",
                body=f"Dear {user.firstname} {user.lastname},\n\n{message}\n\nHR Team\n{university_in_charge.university_name}",
                recipient=user.email,
            )

    return JSONResponse(status_code=200, content={"message": "Application status updated successfully"})