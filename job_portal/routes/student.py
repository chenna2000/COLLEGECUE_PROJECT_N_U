from job_portal.model import Achievements, Application, Application1, Certification, College, Company, Education, Experience, Job, Job1, NewUserEnquiry, Objective, Project, Publications, Reference, Resume, SavedJobForNewUser, StudentReview
from job_portal.schemas import EnquiryCreate, ResumeResponse
from login.database import SessionLocal
from login.models import UniversityInCharge, new_user
from fastapi import APIRouter, Request, Depends, HTTPException,FastAPI,Query # type: ignore
from sqlalchemy.orm import Session # type: ignore
from sqlalchemy import func, or_ # type: ignore
from fastapi.responses import JSONResponse # type: ignore
from sqlalchemy.exc import IntegrityError,OperationalError # type: ignore
import json
from pydantic import ValidationError # type: ignore
from datetime import date, datetime
from typing import List, Union, Optional
from fastapi import status # type: ignore
from itertools import chain
from uuid import UUID


app = FastAPI()

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/create/{user_id}", response_model=ResumeResponse)
async def create_user_resume(request: Request, user_id: int, db: Session = Depends(get_db)):
    auth_header: Optional[str] = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or invalid format")
    token = auth_header.split(" ")[1]
    user = db.query(new_user).filter(new_user.id == user_id, new_user.token == token).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token or user not found")

    try:
        body = await request.json()
        resume_data = body.get("resume")
        if not resume_data:
            return JSONResponse({"status":"error","message":"Resume data is required"}, status_code=400)
        if resume_data["email"] != user.email:
            return JSONResponse({"status":"error","message":"Email mismatch"}, status_code=400)

        resume = db.query(Resume).filter_by(user_id=user.id, email=user.email).first()
        if resume:
            for k,v in resume_data.items():
                setattr(resume, k, v)
        else:
            resume = Resume(**resume_data, user_id=user.id)
            db.add(resume)
        db.commit()
        db.refresh(resume)

        def upsert_single(model_class, data_dict, resume_id):
            """Update the one-and-only record for this resume, or create it."""
            if not data_dict:
                return
            obj = db.query(model_class).filter_by(resume_id=resume_id).first()
            if obj:
                for k, v in data_dict.items():
                    setattr(obj, k, v)
            else:
                obj = model_class(**data_dict, resume_id=resume_id)
                db.add(obj)
            db.commit()

        upsert_single(Objective, body.get("objective", {}), resume.id)

        single_fields = {
            'education': Education,
            'experience': Experience,
            'projects': Project,
            'references': Reference,
            'certifications': Certification,
            'achievements': Achievements,
            'publications': Publications,
        }
        for field, model_cls in single_fields.items():
            arr = body.get(field, [])
            if arr:
                upsert_single(model_cls, arr[0], resume.id)

        return JSONResponse({
            "status": "success",
            "message": "Resume and all sections created/updated successfully",
            "resume_id": resume.id
        })

    except json.JSONDecodeError:
        return JSONResponse({"status":"error","message":"Invalid JSON data"}, status_code=400)
    except ValidationError as e:
        return JSONResponse({"status":"error","message":e.errors()}, status_code=400)
    except IntegrityError as e:
        return JSONResponse({"status":"error","message":"Database integrity error","details":str(e)}, status_code=500)
    except OperationalError as e:
        return JSONResponse({"status":"error","message":"Database operational error","details":str(e)}, status_code=500)
    except Exception as e:
        return JSONResponse({"status":"error","message":str(e)}, status_code=500)

@router.get("/get/{user_id}", response_model=ResumeResponse)
async def get_user_resume(request: Request, user_id: int, db: Session = Depends(get_db)):
    auth_header: Optional[str] = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or invalid format")
    token = auth_header.split(" ", 1)[1]
    user = db.query(new_user).filter(new_user.id == user_id, new_user.token == token).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token or user not found")

    resume = db.query(Resume).filter_by(user_id=user.id, email=user.email).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    def to_dict(obj, exclude: list[str] = None):
        d = {}
        for col in obj.__table__.columns:
            if exclude and col.name in exclude:
                continue
            val = getattr(obj, col.name)

            if isinstance(val, (date, datetime)):
                val = val.isoformat()
            d[col.name] = val
        return d

    objective = db.query(Objective).filter_by(resume_id=resume.id).first()
    education = db.query(Education).filter_by(resume_id=resume.id).all()
    experience = db.query(Experience).filter_by(resume_id=resume.id).all()
    projects = db.query(Project).filter_by(resume_id=resume.id).all()
    references = db.query(Reference).filter_by(resume_id=resume.id).all()
    certifications = db.query(Certification).filter_by(resume_id=resume.id).all()
    achievements = db.query(Achievements).filter_by(resume_id=resume.id).all()
    publications = db.query(Publications).filter_by(resume_id=resume.id).all()

    payload = {
        "status": "success",
        "resume": to_dict(resume, exclude=["id", "user_id"]),
        "objective": to_dict(objective) if objective else {},
        "education": [to_dict(e) for e in education],
        "experience": [to_dict(e) for e in experience],
        "projects": [to_dict(p) for p in projects],
        "references": [to_dict(r) for r in references],
        "certifications":[to_dict(c) for c in certifications],
        "achievements": [to_dict(a) for a in achievements],
        "publications": [to_dict(pu) for pu in publications],
    }

    return JSONResponse(content=payload)

@router.get("/user-application-status/{user_id}")
def user_application_status_counts(user_id: int, request: Request, db: Session = Depends(get_db)):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or invalid format")

    token = auth_header.split(" ")[1]
    email = request.query_params.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email parameter is required")

    user = db.query(new_user).filter_by(id=user_id, token=token, email=email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token or user not found")

    total_jobs_applied = (
        db.query(Application).filter_by(user_id=user.id).count() +
        db.query(Application1).filter_by(user_id=user.id).count()
    )

    def count_status(model, status):
        return db.query(model).filter_by(user_id=user.id, status=status).count()

    pending_count = count_status(Application, "pending") + count_status(Application1, "pending")
    interview_scheduled_count = count_status(Application, "interview_scheduled") + count_status(Application1, "interview_scheduled")
    rejected_count = count_status(Application, "rejected") + count_status(Application1, "rejected")

    college_enquiries_count = db.query(NewUserEnquiry).filter_by(email=email).count()

    def get_monthly_counts(model, date_field, status=None):
        query = db.query(
            func.date_format(getattr(model, date_field), '%Y-%m').label("month"),
            func.count().label("count")
        ).filter_by(user_id=user.id)

        if status:
            query = query.filter(model.status == status)

        return {r.month: r.count for r in query.group_by("month").order_by("month").all()}

    def merge_monthly_counts(model1, model2, date_field, status=None):
        counts1 = get_monthly_counts(model1, date_field, status)
        counts2 = get_monthly_counts(model2, date_field, status)

        combined = counts1.copy()
        for month, count in counts2.items():
            combined[month] = combined.get(month, 0) + count
        return combined

    jobs_applied_by_month = merge_monthly_counts(Application, Application1, "applied_at")
    pending_by_month = merge_monthly_counts(Application, Application1, "applied_at", "pending")
    interview_by_month = merge_monthly_counts(Application, Application1, "applied_at", "interview_scheduled")
    rejected_by_month = merge_monthly_counts(Application, Application1, "applied_at", "rejected")

    college_enquiries_by_month = {
        r.month: r.count for r in db.query(
            func.date_format(NewUserEnquiry.created_at, '%Y-%m').label("month"),
            func.count().label("count")
        ).filter_by(email=email).group_by("month").order_by("month").all()
    }

    return JSONResponse(content={
        "total_jobs_applied": total_jobs_applied,
        "pending_count": pending_count,
        "interview_scheduled": interview_scheduled_count,
        "rejected_count": rejected_count,
        "total_college_enquiries_count": college_enquiries_count,
        "jobs_applied_by_month": jobs_applied_by_month,
        "pending_by_month": pending_by_month,
        "interview_scheduled_by_month": interview_by_month,
        "rejected_by_month": rejected_by_month,
        "college_enquiries_by_month": college_enquiries_by_month
    })

@router.get("/fetch-user-skills-jobs/{user_id}")
async def fetch_jobs_by_new_user_skills(
    user_id: int,
    request: Request,
    sort_order: str = Query("latest", regex="^(latest|oldest)$"),
    db: Session = Depends(get_db),
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(400, "Token is missing or invalid format")
    token = auth_header.split(" ", 1)[1]

    user = db.query(new_user).filter_by(id=user_id, token=token).first()
    if not user:
        raise HTTPException(404, "New user not found")

    resume = db.query(Resume).filter_by(user_id=user.id).first()
    if not resume:
        raise HTTPException(404, "Resume for this user not found")

    skills_list = [s.strip().lower() for s in (resume.skills or "").split(",") if s.strip()]
    if not skills_list:
        raise HTTPException(400, "No skills found for this user")

    filters = [Job.skills.ilike(f"%{skill}%") for skill in skills_list]
    q1 = db.query(Job).filter(or_(*filters), Job.job_status != "closed")
    q2 = db.query(Job1).filter(or_(*filters), Job1.job_status != "closed")
    jobs: List[Union[Job, Job1]] = q1.all() + q2.all()

    reverse = sort_order == "latest"
    jobs.sort(key=lambda j: j.published_at or datetime.min, reverse=reverse)

    result = []
    for j in jobs:
        posted = j.published_at
        if isinstance(posted, datetime):
            posted = posted.isoformat()

        unique_id = getattr(j, "unique_job_id", None)
        job_id = unique_id or j.id

        base = {
            "job_id": job_id,
            "job_title": j.job_title,
            "location": j.location,
            "job_type": j.job_type,
            "job_posted_date": posted,
        }

        if isinstance(j, Job) and unique_id is not None:
            base["unique_job_id"] = unique_id

        if isinstance(j, Job):
            company = db.query(Company).get(j.company_id)
            base["company_name"] = company.name if company else None
        else:
            college = db.query(College).get(j.college_id)
            base["college"] = college.college_name if college else None

        result.append(base)

    return JSONResponse({"jobs": result})


@router.post("/save-job-new-user")
async def save_job_new_user(request: Request):
    try:
        db: Session = SessionLocal()

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid token format")
        token = auth_header.split(" ")[1]

        data = await request.json()
        new_user_id = data.get("new_user_id")
        job_id = data.get("job_id")

        if not new_user_id or not job_id:
            raise HTTPException(status_code=400, detail="new_user_id and job_id are required")

        user = db.query(new_user).filter_by(id=new_user_id, token=token).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found or invalid token")

        job = None
        job1 = None
        original_job_id = None

        # print(f"Received job_id: {job_id}")

        job = db.query(Job).filter_by(unique_job_id=job_id).first()
        if job:
            original_job_id = job.unique_job_id
        else:
            if str(job_id).isdigit():
                job1 = db.query(Job1).filter_by(id=int(job_id)).first()
                if job1:
                    original_job_id = job1.id
            else:
                print("Job ID is not a digit and not a valid Job1 ID")

        # print(f"Job: {job}")
        # print(f"Job1: {job1}")

        if not job and not job1:
            raise HTTPException(status_code=404, detail="Job or Job1 not found")

        existing = db.query(SavedJobForNewUser).filter_by(
            new_user_id=user.id,
            job_id=job.id if job else None,
            job1_id=job1.id if job1 else None,
            original_job_id=original_job_id
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail="Job already saved")

        saved = SavedJobForNewUser(
            new_user_id=user.id,
            job_id=job.id if job else None,
            job1_id=job1.id if job1 else None,
            original_job_id=original_job_id
        )
        db.add(saved)
        db.commit()
        db.refresh(saved)

        return JSONResponse(content={"message": "Job saved", "saved_job_id": saved.id}, status_code=201)

    except HTTPException as he:
        raise he
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})


@router.post("/unsave-job-new-user")
async def unsave_job_new_user(request: Request, db: Session = Depends(get_db)):
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else None
        if not token:
            raise HTTPException(status_code=400, detail="Token is missing or invalid format")

        data = await request.json()
        new_user_id = data.get('new_user_id')
        job_id = data.get('job_id')

        if not new_user_id or not job_id:
            raise HTTPException(status_code=400, detail="New User ID and Job ID are required")

        user = db.query(new_user).filter_by(id=new_user_id, token=token).first()
        if not user:
            raise HTTPException(status_code=404, detail="Invalid token or New User not found")

        job = db.query(Job).filter_by(unique_job_id=job_id).first()
        job1 = None
        saved_job = None

        if job:
            saved_job = db.query(SavedJobForNewUser).filter_by(
                new_user_id=new_user_id,
                job_id=job.id
            ).first()
        else:
            if str(job_id).isdigit():
                job1 = db.query(Job1).filter_by(id=int(job_id)).first()
                if job1:
                    saved_job = db.query(SavedJobForNewUser).filter_by(
                        new_user_id=new_user_id,
                        job1_id=job1.id
                    ).first()

        if not saved_job:
            raise HTTPException(status_code=404, detail="Saved job not found")

        db.delete(saved_job)
        db.commit()
        return {"message": "Job unsaved successfully for New User"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fetch-saved-jobs-new-user/{new_user_id}")
def fetch_saved_jobs_new_user(new_user_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else None

        if not token:
            raise HTTPException(status_code=400, detail="Token is missing or invalid format")

        user = db.query(new_user).filter_by(id=new_user_id, token=token).first()
        if not user:
            raise HTTPException(status_code=404, detail="Invalid token or New User not found")

        saved_jobs = db.query(SavedJobForNewUser).filter_by(new_user_id=user.id).all()
        if not saved_jobs:
            return {"message": "No saved jobs found for this New User"}

        saved_jobs_data = []

        for saved_job in saved_jobs:
            job_data = None
            job1_data = None

            if saved_job.job_id:
                job = db.query(Job).filter_by(id=saved_job.job_id, job_status="active").first()
                if not job:
                    continue

                company_name = None
                if job.company_id:
                    company = db.query(Company).filter_by(id=job.company_id).first()
                    company_name = company.name if company else None

                job_data = {
                    "job_id": saved_job.original_job_id,
                    "job_title": job.job_title,
                    "company": company_name,
                    "location": job.location,
                    "job_type": job.job_type,
                    "skills": job.skills,
                    "job_status": job.job_status,
                }

            elif saved_job.job1_id:
                job1 = db.query(Job1).filter_by(id=saved_job.job1_id, job_status="active").first()
                if not job1:
                    continue

                college_name = None
                if job1.college_id:
                    college = db.query(College).filter_by(id=job1.college_id).first()
                    college_name = college.college_name if college else None

                job1_data = {
                    "job1_id": job1.id,
                    "job_title": job1.job_title,
                    "university": college_name,
                    "location": job1.location,
                    "job_type": job1.job_type,
                    "skills": job1.skills,
                    "job_status": job1.job_status,
                }

            if job_data:
                saved_jobs_data.append({"job": job_data})
            elif job1_data:
                saved_jobs_data.append({"job1": job1_data})

        return {"saved_jobs": saved_jobs_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/submit-enquiry/{clg_id}")
async def submit_enquiry(clg_id: str, data: EnquiryCreate, db: Session = Depends(get_db)):
    university_incharge = db.query(UniversityInCharge).filter_by(clg_id=clg_id).first()

    existing_enquiry = db.query(NewUserEnquiry).filter_by(clg_id=clg_id, email=data.email).first()
    if existing_enquiry:
        raise HTTPException(
            status_code=400,
            detail="An enquiry has already been submitted for this college with this email."
        )

    user = db.query(new_user).filter_by(email=data.email).first()

    if not user:
        raise HTTPException(
            status_code=400,
            detail="No user found with the provided email."
        )

    enquiry = NewUserEnquiry(
        first_name=data.firstname.strip(),
        last_name=data.lastname.strip(),
        email=data.email.strip(),
        country_code=data.country_code.strip(),
        mobile_number=data.mobile_number.strip(),
        course=data.course.strip(),
        clg_id=clg_id,
        new_user_id=user.id,
        university_in_charge_id=university_incharge.id if university_incharge else None
    )

    db.add(enquiry)
    db.commit()
    db.refresh(enquiry)

    return JSONResponse(
        content={"message": "Enquiry submitted successfully", "enquiry_id": enquiry.id},
        status_code=status.HTTP_201_CREATED
    )

@router.get("/apply/{job_id}/{user_id}")
def user_apply_for_job(job_id: str, user_id: int, request: Request, db: Session = Depends(get_db)):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or in an invalid format")

    token = auth_header.split(" ")[1]

    user = db.query(new_user).filter_by(id=user_id, token=token).first()
    if not user:
        raise HTTPException(status_code=404, detail="Invalid token or user not found")

    resume = db.query(Resume).filter_by(user_id=user_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume Not Found")

    job = db.query(Job1).filter_by(id=job_id).first()

    if job:
        application_model = Application1
        job_id_field = "job_id"
        extra_fields = {"university_in_charge_id": job.university_in_charge_id}
    else:
        try:
            uuid_job_id = UUID(job_id)
            job = db.query(Job).filter_by(unique_job_id=job_id).first()
        except ValueError:
            job = db.query(Job).filter_by(unique_job_id_as_int=job_id).first()

        if job:
            application_model = Application
            job_id_field = "job_id"
            extra_fields = {"company_in_charge_id": job.company_in_charge_id}
        else:
            raise HTTPException(status_code=404, detail=f"No job found with ID {job_id}")

    if db.query(application_model).filter_by(email=user.email, job_id=job.id).first():
        raise HTTPException(status_code=400, detail="An application with this email already exists for this job.")

    education_qs = db.query(Education).filter(Education.resume_id == resume.id).all()
    experience_qs = db.query(Experience).filter(Experience.resume_id == resume.id).all()

    education_entries = [
        {
            "course_or_degree": edu.course_or_degree,
            "school_or_university": edu.school_or_university
        } for edu in education_qs
    ]

    experience_entries = [
        {
            "company_name": exp.company_name,
            "job_title": exp.job_title,
            "start_date": exp.start_date.isoformat() if exp.start_date else None,
            "end_date": exp.end_date.isoformat() if exp.end_date else None
        } for exp in experience_qs
    ]

    application = application_model(
        user_id=user.id,
        job_id=job.id,
        first_name=user.firstname,
        last_name=user.lastname,
        email=user.email,
        phone_number=user.phonenumber,
        resume=None,
        cover_letter="No cover letter provided",
        skills=resume.skills,
        bio=resume.bio,
        education=json.dumps(education_entries),
        experience=json.dumps(experience_entries),
        **extra_fields
    )

    db.add(application)
    db.commit()
    db.refresh(application)

    return JSONResponse(
        status_code=201,
        content={"message": "Application submitted successfully", "application_id": application.id}
    )

@router.get("/filter_applied_jobs/{user_id}")
def filter_user_applied_jobs(
    user_id: int,
    request: Request,
    email: Optional[str] = Query(None),
    job_title: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Fetches the applied jobs for a specific user based on filters, including sorting.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or invalid format")

    token = auth_header.split(" ")[1]

    user = db.query(new_user).filter_by(id=user_id, token=token).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found or invalid token")

    if email and user.email != email:
        raise HTTPException(status_code=400, detail="Invalid email or email does not match")

    app1_query = db.query(Application, Job, Company).join(Job, Job.id == Application.job_id).join(Company, Company.id == Job.company_id).filter(Application.user_id == user.id)

    if job_title:
        app1_query = app1_query.filter(Job.job_title.ilike(f"%{job_title}%"))
    if job_type:
        app1_query = app1_query.filter(Job.job_type.ilike(f"%{job_type}%"))
    if status:
        app1_query = app1_query.filter(Application.status == status)

    app1_results = app1_query.all()

    app2_query = db.query(Application1, Job1, College).join(Job1, Job1.id == Application1.job_id).join(College, College.id == Job1.college_id).filter(Application1.user_id == user.id)

    if job_title:
        app2_query = app2_query.filter(Job1.job_title.ilike(f"%{job_title}%"))
    if job_type:
        app2_query = app2_query.filter(Job1.job_type.ilike(f"%{job_type}%"))
    if status:
        app2_query = app2_query.filter(Application1.status == status)

    app2_results = app2_query.all()

    applications = list(chain(app1_results, app2_results))

    seen_jobs = set()
    unique_applications = []

    for app, job, company_or_university in applications:
        job_id = job.id
        if job_id not in seen_jobs:
            seen_jobs.add(job_id)
            if isinstance(job, Job):
                unique_applications.append({
                    "job_title": job.job_title,
                    "company": company_or_university.name if company_or_university else None,
                    "job_location": job.location,
                    "job_type": job.job_type,
                    "status": app.status,
                    "applied_at": app.applied_at.isoformat() if app.applied_at else None
                })
            else:
                unique_applications.append({
                    "job_title": job.job_title,
                    "college": company_or_university.college_name if company_or_university else None,
                    "job_location": job.location,
                    "job_type": job.job_type,
                    "status": app.status,
                    "applied_at": app.applied_at.isoformat() if app.applied_at else None
                })

    if sort_by:
        if sort_by == "job_title_asc":
            unique_applications.sort(key=lambda x: x['job_title'])
        elif sort_by == "job_title_desc":
            unique_applications.sort(key=lambda x: x['job_title'], reverse=True)
        elif sort_by == "applied_at_asc":
            unique_applications.sort(key=lambda x: x['applied_at'])
        elif sort_by == "applied_at_desc":
            unique_applications.sort(key=lambda x: x['applied_at'], reverse=True)

    return JSONResponse(content=unique_applications)


@router.post("/review-student")
async def review_student(request: Request):
    try:
        db: Session = SessionLocal()

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid token format")
        token = auth_header.split(" ")[1]

        data = await request.json()
        reviewer_id = data.get("reviewer_id")
        reviewed_id = data.get("reviewed_id")
        review_text = data.get("review_text")
        liked = data.get("liked", False)
        disliked = data.get("disliked", False)
        reported = data.get("reported", False)
        original_job_id = data.get("original_job_id")

        if not reviewer_id or not reviewed_id:
            raise HTTPException(status_code=400, detail="reviewer_id and reviewed_id are required")

        if reviewer_id == reviewed_id:
            raise HTTPException(status_code=400, detail="You can't review yourself")

        user = db.query(new_user).filter_by(id=reviewer_id, token=token).first()
        if not user:
            raise HTTPException(status_code=404, detail="Reviewer not found or invalid token")

        existing_review = db.query(StudentReview).filter_by(
            reviewer_id=reviewer_id,
            reviewed_id=reviewed_id
        ).first()

        if existing_review:
            raise HTTPException(status_code=400, detail="Review already exists")

        review = StudentReview(
            reviewer_id=reviewer_id,
            reviewed_id=reviewed_id,
            review_text=review_text,
            liked=liked,
            disliked=disliked,
            reported=reported
        )

        db.add(review)
        db.commit()
        db.refresh(review)

        job_saved = False
        if original_job_id:

            if str(original_job_id).isdigit():
                saved = db.query(SavedJobForNewUser).filter_by(
                    new_user_id=reviewer_id,
                    job1_id=int(original_job_id)
                ).first()
                job_saved = saved is not None
            else:
                saved = db.query(SavedJobForNewUser).filter(
                    SavedJobForNewUser.new_user_id == reviewer_id,
                    (SavedJobForNewUser.original_job_id == str(original_job_id)) |
                    (SavedJobForNewUser.job_id != None)
                ).first()
                job_saved = saved is not None

        return JSONResponse(content={
            "message": "Review saved",
            "review_id": review.id,
            "job_saved": job_saved
        }, status_code=201)

    except HTTPException as he:
        raise he
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})
    finally:
        db.close()
