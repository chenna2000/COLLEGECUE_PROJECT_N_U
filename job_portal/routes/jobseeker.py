from itertools import chain
from job_portal.model import Application, Application1, College, Company, Job, Job1, JobseekerAchievement, JobseekerCertification, JobseekerEducation, JobseekerExperience, JobseekerObjective, JobseekerProject, JobseekerPublication, JobseekerReference, JobseekerResume, SavedJobForNewUser1
from job_portal.schemas import JobseekerResumeResponse
from login.database import SessionLocal
from sqlalchemy.orm import Session # type: ignore
from fastapi import APIRouter, Query, Request, HTTPException, Depends, FastAPI # type: ignore
from fastapi.responses import JSONResponse # type: ignore
from sqlalchemy.exc import IntegrityError, OperationalError # type: ignore
from typing import List, Optional, Union
import json
from pydantic import ValidationError # type: ignore
from datetime import date, datetime
from login.models import JobSeeker
from sqlalchemy import UUID, func, or_ # type: ignore


router = APIRouter()

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/create/{jobseeker_id}", response_model=JobseekerResumeResponse)
async def create_jobseeker_resume(request: Request, jobseeker_id: int, db: Session = Depends(get_db)):
    auth_header: Optional[str] = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or invalid format")

    token = auth_header.split(" ")[1]

    jobseeker_obj = db.query(JobSeeker).filter(JobSeeker.id == jobseeker_id, JobSeeker.token == token).first()
    if not jobseeker_obj:
        raise HTTPException(status_code=401, detail="Invalid token or jobseeker not found")

    try:
        body = await request.json()
        resume_data = body.get("resume")
        if not resume_data:
            return JSONResponse({"status": "error", "message": "Resume data is required"}, status_code=400)

        if resume_data["email"] != jobseeker_obj.email:
            return JSONResponse({"status": "error", "message": "Email mismatch"}, status_code=400)

        resume = db.query(JobseekerResume).filter_by(job_seeker_id=jobseeker_obj.id, email=jobseeker_obj.email).first()
        if resume:
            for k, v in resume_data.items():
                setattr(resume, k, v)
        else:
            resume = JobseekerResume(**resume_data,  job_seeker_id=jobseeker_obj.id)
            db.add(resume)
        db.commit()
        db.refresh(resume)

        def upsert_single(model_class, data_dict, resume_id):
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

        upsert_single(JobseekerObjective, body.get("objective", {}), resume.id)

        section_models = {
            'education': JobseekerEducation,
            'experience': JobseekerExperience,
            'projects': JobseekerProject,
            'references': JobseekerReference,
            'certifications': JobseekerCertification,
            'achievements': JobseekerAchievement,
            'publications': JobseekerPublication,
        }

        for field_name, model_class in section_models.items():
            section_data = body.get(field_name, [])
            if section_data:
                upsert_single(model_class, section_data[0], resume.id)

        return JSONResponse({
            "status": "success",
            "message": "Jobseeker resume and sections created/updated successfully",
            "resume_id": resume.id
        })

    except json.JSONDecodeError:
        return JSONResponse({"status": "error", "message": "Invalid JSON data"}, status_code=400)
    except ValidationError as e:
        return JSONResponse({"status": "error", "message": e.errors()}, status_code=400)
    except IntegrityError as e:
        return JSONResponse({"status": "error", "message": "Database integrity error", "details": str(e)}, status_code=500)
    except OperationalError as e:
        return JSONResponse({"status": "error", "message": "Database operational error", "details": str(e)}, status_code=500)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/get/{jobseeker_id}", response_model=JobseekerResumeResponse)
async def get_jobseeker_resume(request: Request, jobseeker_id: int, db: Session = Depends(get_db)):
    auth_header: Optional[str] = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or invalid format")

    token = auth_header.split(" ", 1)[1]

    jobseeker_obj = db.query(JobSeeker).filter(JobSeeker.id == jobseeker_id, JobSeeker.token == token).first()
    if not jobseeker_obj:
        raise HTTPException(status_code=401, detail="Invalid token or jobseeker not found")

    resume = db.query(JobseekerResume).filter_by(job_seeker_id=jobseeker_obj.id, email=jobseeker_obj.email).first()
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

    objective      = db.query(JobseekerObjective).filter_by(resume_id=resume.id).first()
    education      = db.query(JobseekerEducation).filter_by(resume_id=resume.id).all()
    experience     = db.query(JobseekerExperience).filter_by(resume_id=resume.id).all()
    projects       = db.query(JobseekerProject).filter_by(resume_id=resume.id).all()
    references     = db.query(JobseekerReference).filter_by(resume_id=resume.id).all()
    certifications = db.query(JobseekerCertification).filter_by(resume_id=resume.id).all()
    achievements   = db.query(JobseekerAchievement).filter_by(resume_id=resume.id).all()
    publications   = db.query(JobseekerPublication).filter_by(resume_id=resume.id).all()

    payload = {
        "status": "success",
        "resume":         to_dict(resume, exclude=["id", "user_id"]),
        "objective":      to_dict(objective) if objective else {},
        "education":      [to_dict(e) for e in education],
        "experience":     [to_dict(e) for e in experience],
        "projects":       [to_dict(p) for p in projects],
        "references":     [to_dict(r) for r in references],
        "certifications": [to_dict(c) for c in certifications],
        "achievements":   [to_dict(a) for a in achievements],
        "publications":   [to_dict(pu) for pu in publications],
    }

    return JSONResponse(content=payload)

@router.get("/jobseeker-application-status-counts/{jobseeker_id}")
async def jobseeker_application_status_counts(request: Request, jobseeker_id: int, db: Session = Depends(get_db)):
    auth_header: Optional[str] = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or invalid format")

    token = auth_header.split(" ", 1)[1]

    email = request.query_params.get('email')
    if not email:
        raise HTTPException(status_code=400, detail="Email parameter is required")

    jobseeker = db.query(JobSeeker).filter(JobSeeker.id == jobseeker_id, JobSeeker.token == token, JobSeeker.email == email).first()
    if not jobseeker:
        raise HTTPException(status_code=404, detail="Invalid token or jobseeker not found")

    def get_count(model, status=None):
        query = db.query(func.count(model.id)).filter(model.job_seeker_id == jobseeker.id)
        if status:
            query = query.filter(model.status == status)
        return query.scalar()

    total_jobs_applied_count = (
        get_count(Application) + get_count(Application1)
    )

    pending_count = (
        get_count(Application, "pending") + get_count(Application1, "pending")
    )

    interview_scheduled_count = (
        get_count(Application, "interview_scheduled") + get_count(Application1, "interview_scheduled")
    )

    rejected_count = (
        get_count(Application, "rejected") + get_count(Application1, "rejected")
    )

    def get_jobs_by_month(status: Optional[str] = None):
        query = db.query(
            func.date_format(Application.applied_at, '%Y-%m-01').label('month'),
            func.count(Application.id).label('count')
        ).filter(Application.job_seeker_id == jobseeker.id)

        if status:
            query = query.filter(Application.status == status)

        return query.group_by('month').all()

    jobs_applied_by_month = get_jobs_by_month()
    pending_by_month = get_jobs_by_month(status="pending")
    interview_scheduled_by_month = get_jobs_by_month(status="interview_scheduled")
    rejected_by_month = get_jobs_by_month(status="rejected")

    def format_counts(data):
        counts = {}
        for item in data:
            month = item[0][:7]
            counts[month] = counts.get(month, 0) + item[1]
        return counts

    response_data = {
        "total_jobs_applied": total_jobs_applied_count,
        "pending_count": pending_count,
        "interview_scheduled_count": interview_scheduled_count,
        "rejected_count": rejected_count,
        "jobs_applied_by_month": format_counts(jobs_applied_by_month),
        "pending_by_month": format_counts(pending_by_month),
        "rejected_by_month": format_counts(rejected_by_month),
        "interview_scheduled_by_month": format_counts(interview_scheduled_by_month),
    }

    return JSONResponse(content=response_data, status_code=200)

@router.get("/fetch-jobseeker-skills-jobs/{jobseeker_id}")
async def fetch_jobs_by_jobseeker_skills(
    jobseeker_id: int,
    request: Request,
    sort_order: str = Query("latest", regex="^(latest|oldest)$"),
    db: Session = Depends(get_db),
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or invalid format")

    token = auth_header.split(" ", 1)[1]

    jobseeker = db.query(JobSeeker).filter_by(id=jobseeker_id, token=token).first()
    if not jobseeker:
        raise HTTPException(status_code=404, detail="Jobseeker not found or invalid token")

    resume = db.query(JobseekerResume).filter_by(job_seeker_id=jobseeker.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume for this jobseeker not found")

    skills_list = [s.strip().lower() for s in (resume.skills or "").split(",") if s.strip()]
    if not skills_list:
        raise HTTPException(status_code=400, detail="No skills found for this jobseeker")

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

        job_data = {
            "job_id": job_id,
            "job_title": j.job_title,
            "location": j.location,
            "job_type": j.job_type,
            "job_posted_date": posted,
        }

        if isinstance(j, Job) and unique_id is not None:
            job_data["unique_job_id"] = unique_id

        if isinstance(j, Job):
            company = db.query(Company).get(j.company_id)
            job_data["company_name"] = company.name if company else None
        else:
            college = db.query(College).get(j.college_id)
            job_data["college"] = college.college_name if college else None

        result.append(job_data)

    return JSONResponse(content={"jobs": result})


@router.post("/save-job-jobseeker")
async def save_job_job_seeker(request: Request):
    try:
        db: Session = SessionLocal()

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid token format")
        token = auth_header.split(" ")[1]

        data = await request.json()
        job_seeker_id = data.get("job_seeker_id")
        job_id = data.get("job_id")

        if not job_seeker_id or not job_id:
            raise HTTPException(status_code=400, detail="job_seeker_id and job_id are required")

        user = db.query(JobSeeker).filter_by(id=job_seeker_id, token=token).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found or invalid token")

        job = None
        job1 = None
        original_job_id = None

        print(f"Received job_id: {job_id}")

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

        existing = db.query(SavedJobForNewUser1).filter_by(
            job_seeker_id=user.id,
            job_id=job.id if job else None,
            job1_id=job1.id if job1 else None,
            original_job_id=original_job_id
        ).first()

        if existing:
            raise HTTPException(status_code=400, detail="Job already saved")

        saved = SavedJobForNewUser1(
            job_seeker_id=user.id,
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
        job_seeker_id = data.get('job_seeker_id')
        job_id = data.get('job_id')

        if not job_seeker_id or not job_id:
            raise HTTPException(status_code=400, detail="JOBSEEKER ID and Job ID are required")

        user = db.query(JobSeeker).filter_by(id=job_seeker_id, token=token).first()
        if not user:
            raise HTTPException(status_code=404, detail="Invalid token or New User not found")

        job = db.query(Job).filter_by(unique_job_id=job_id).first()
        job1 = None
        saved_job = None

        if job:
            saved_job = db.query(SavedJobForNewUser1).filter_by(
                job_seeker_id=job_seeker_id,
                job_id=job.id
            ).first()
        else:
            if str(job_id).isdigit():
                job1 = db.query(Job1).filter_by(id=int(job_id)).first()
                if job1:
                    saved_job = db.query(SavedJobForNewUser1).filter_by(
                        job_seeker_id=job_seeker_id,
                        job1_id=job1.id
                    ).first()

        if not saved_job:
            raise HTTPException(status_code=404, detail="Saved job not found")

        db.delete(saved_job)
        db.commit()
        return {"message": "Job unsaved successfully for Jobseeker"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/fetch-saved-jobs-job_seeker/{job_seeker_id}")
def fetch_saved_jobs_job_seeker(job_seeker_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        auth_header = request.headers.get('Authorization', '')
        token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else None

        if not token:
            raise HTTPException(status_code=400, detail="Token is missing or invalid format")

        user = db.query(JobSeeker).filter_by(id=job_seeker_id, token=token).first()
        if not user:
            raise HTTPException(status_code=404, detail="Invalid token or New User not found")

        saved_jobs = db.query(SavedJobForNewUser1).filter_by(job_seeker_id=user.id).all()
        if not saved_jobs:
            return {"message": "No saved jobs found for this Job seeker"}

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

@router.get("/apply/{job_id}/{user_id}")
def jobseeker_apply_for_job(job_id: str, user_id: int, request: Request, db: Session = Depends(get_db)):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or in an invalid format")

    token = auth_header.split(" ")[1]

    user = db.query(JobSeeker).filter_by(id=user_id, token=token).first()

    if not user:
        raise HTTPException(status_code=404, detail="Invalid token or user not found")

    # print(f"User found: {user}")
    # print(f"User ID: {user.id}")

    resume = db.query(JobseekerResume).filter_by(job_seeker_id=user_id).first()

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

    existing_application = db.query(application_model).filter_by(email=user.email, job_id=job.id).first()
    if existing_application:
        raise HTTPException(status_code=400, detail="An application with this email already exists for this job.")

    education_qs = db.query(JobseekerEducation).filter(JobseekerEducation.resume_id == resume.id).all()
    experience_qs = db.query(JobseekerExperience).filter(JobseekerExperience.resume_id == resume.id).all()

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
        job_id=job.id,
        job_seeker_id=user.id,
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
def filter_jobseeker_applied_jobs(
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

    user = db.query(JobSeeker).filter_by(id=user_id, token=token).first()
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
