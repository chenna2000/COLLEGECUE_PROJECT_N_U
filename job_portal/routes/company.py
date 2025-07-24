from fastapi import APIRouter, FastAPI, Request, Header, HTTPException, Depends, Form # type: ignore
from fastapi.responses import JSONResponse # type: ignore
from login.utils import send_appliction_email, send_notification_to_group
from pydantic import EmailStr  # type: ignore
from sqlalchemy.orm import Session # type: ignore
from sqlalchemy import func # type: ignore
from job_portal.schemas import JobCreateRequest, JobFilterParams, JobStatusRequest, StatusUpdatePayload
from login.database import SessionLocal
from job_portal.model import Achievements, Application, Certification, Company, Education, Experience, Job, JobseekerResume, Project, Publications, Reference, Resume
from login.models import CompanyInCharge, OnlineStatus
from typing import Optional
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

@router.get("/company-status/{company_in_charge_id}")
def company_status_counts(company_in_charge_id: int, request: Request, db: Session = Depends(get_db)):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or in an invalid format")

    token = auth_header.split(" ")[1]
    company_in_charge = db.query(CompanyInCharge).filter_by(id=company_in_charge_id, token=token).first()

    if not company_in_charge:
        raise HTTPException(status_code=404, detail="Invalid token or company in charge not found")

    total_applications = db.query(Application).filter_by(company_in_charge_id=company_in_charge_id).count()
    shortlisted_count = db.query(Application).filter(
        Application.company_in_charge_id == company_in_charge_id,
        Application.status.in_(["selected", "shortlisted"])
    ).count()
    rejected_count = db.query(Application).filter_by(
        company_in_charge_id=company_in_charge_id,
        status="rejected"
    ).count()
    jobs_posted = db.query(Job).filter_by(company_in_charge_id=company_in_charge_id).count()

    def get_counts_by_month(model, date_field: str, extra_filters=None):
        date_column = getattr(model, date_field)
        query = db.query(
            func.date_format(date_column, '%Y-%m').label("month"),
            func.count().label("count")
        ).filter(model.company_in_charge_id == company_in_charge_id)

        if extra_filters:
            for condition in extra_filters:
                query = query.filter(condition)

        results = query.group_by("month").order_by("month").all()
        return {r.month: r.count for r in results} if results else {}

    current_month = datetime.now().strftime("%Y-%m")

    return JSONResponse(content={
        "total_applications": total_applications,
        "shortlisted_count": shortlisted_count,
        "rejected_count": rejected_count,
        "jobs_posted": jobs_posted,
        "jobs_by_month": get_counts_by_month(Job, "published_at") or {current_month: 0},
        "applications_by_month": get_counts_by_month(Application, "applied_at") or {current_month: 0},
        "shortlisted_by_month": get_counts_by_month(
            Application, "applied_at", [Application.status.in_(["selected", "shortlisted"])]
        ) or {current_month: 0},
        "rejected_by_month": get_counts_by_month(
            Application, "applied_at", [Application.status == "rejected"]
        ) or {current_month: 0},
    })

def validate_token(token: str, company_in_charge_id: int, db: Session) -> CompanyInCharge:
    company_in_charge = db.query(CompanyInCharge).filter_by(id=company_in_charge_id, token=token).first()
    if not company_in_charge:
        raise HTTPException(status_code=404, detail="Invalid token or company in charge ID")
    return company_in_charge

@router.get("/companies/{company_in_charge_id}")
def get_companies(
    company_in_charge_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or invalid format")

    token = auth_header.split(" ")[1]

    try:
        company_in_charge = db.query(CompanyInCharge).filter_by(id=company_in_charge_id, token=token).first()
        if not company_in_charge:
            raise HTTPException(status_code=404, detail="Invalid token or company in charge ID")

        companies = db.query(Company).filter_by(company_in_charge_id=company_in_charge.id).all()
        if not companies:
            raise HTTPException(status_code=404, detail="No companies found for this company in charge")

        companies_data = [
            {
                "id": company.id,
                "name": company.name,
                "email": company.email,
                "phone": company.phone,
                "address": company.address,
                "city": company.city,
                "state": company.state,
                "country": company.country,
                "zipcode": company.zipcode,
                "website": company.website,
                "website_urls": company.website_urls,
                "about_company": company.about_company,
                "sector_type": company.sector_type,
                "category": company.category,
                "established_date": str(company.established_date) if company.established_date else None,
                "employee_size": company.employee_size,
            }
            for company in companies
        ]
        return {"status": "success", "companies": companies_data}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.post("/companies/{company_in_charge_id}")
def create_or_update_company(
    company_in_charge_id: int,
    email: EmailStr = Form(...),
    name: str = Form(...),
    phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    country: Optional[str] = Form(None),
    zipcode: Optional[str] = Form(None),
    website: Optional[str] = Form(None),
    website_urls: Optional[str] = Form(None),
    about_company: Optional[str] = Form(None),
    sector_type: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    established_date: Optional[date] = Form(None),
    employee_size: Optional[int] = Form(None),
    request: Request = None,
    db: Session = Depends(get_db),
):
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=400, detail="Token is missing or invalid format")
        token = auth_header.split(" ")[1]

        company_in_charge = validate_token(token, company_in_charge_id, db)
        if not company_in_charge:
            raise HTTPException(status_code=404, detail="Company in charge not found or token invalid")

        if email != company_in_charge.official_email:
            raise HTTPException(status_code=400, detail="Email does not match the email of the company in charge")

        company = db.query(Company).filter_by(email=email, company_in_charge_id=company_in_charge.id).first()
        if not company:
            company = Company(email=email, company_in_charge_id=company_in_charge.id)

        company.name = name
        company.phone = phone
        company.address = address
        company.city = city
        company.state = state
        company.country = country
        company.zipcode = zipcode
        company.website = website
        company.website_urls = website_urls
        company.about_company = about_company
        company.sector_type = sector_type
        company.category = category
        company.established_date = established_date
        company.employee_size = employee_size

        db.add(company)
        db.commit()
        db.refresh(company)

        return {
            "status": "success",
            "message": "Company created/updated successfully",
            "company_id": company.id,
        }

    except HTTPException as http_exc:
        raise http_exc
    except SQLAlchemyError as db_err:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(db_err)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.delete("/companies/{company_in_charge_id}/{company_id}")
def delete_company(
    company_in_charge_id: int,
    company_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or invalid format")

    token = auth_header.split(" ")[1]

    try:
        company_in_charge = db.query(CompanyInCharge).filter_by(id=company_in_charge_id, token=token).first()
        if not company_in_charge:
            raise HTTPException(status_code=404, detail="Invalid token or company in charge ID")

        company = db.query(Company).filter_by(id=company_id, company_in_charge_id=company_in_charge.id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found or does not belong to this company in charge")

        db.delete(company)
        db.commit()

        return {"status": "success", "message": f"Company with ID {company_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.get("/get-all-jobs/")
def get_all_jobs(db: Session = Depends(get_db)):
    try:
        jobs = db.query(Job).all()
        if not jobs:
            raise HTTPException(status_code=404, detail="No jobs found")
        return jobs  
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving jobs: {str(e)}")

@router.post("/create-company-jobs/{company_in_charge_id}/")
def create_company_job(
    company_in_charge_id: int,
    request: Request,
    job_data: JobCreateRequest,
    db: Session = Depends(get_db)
):

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or in an invalid format")
    token = auth_header.split(" ")[1]

    company_in_charge = db.query(CompanyInCharge).filter_by(id=company_in_charge_id, token=token).first()
    if not company_in_charge:
        raise HTTPException(status_code=401, detail="Invalid token or company in charge not found")

    company = db.query(Company).filter_by(name=job_data.company, company_in_charge_id=company_in_charge.id).first()
    if not company:
        raise HTTPException(status_code=404, detail=f'Company with name "{job_data.company}" does not exist')

    if db.query(Job).filter_by(company_id=company.id).count() >= 100:
        return JSONResponse(content={"message": "Limit exceeded for job postings by this company"}, status_code=200)

    try:
        new_job = Job(
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
            company_id=company.id,
            company_in_charge_id=company_in_charge.id,
        )
        db.add(new_job)
        db.commit()
        return JSONResponse(content={"message": "Job created successfully"}, status_code=201)

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving job: {str(e)}")

@router.api_route("/update-company-job/{company_in_charge_id}/{job_id}/", methods=["GET", "PUT", "DELETE"])
def update_company_job(
    company_in_charge_id: int,
    job_id: str,
    request: Request,
    job_data: JobCreateRequest, 
    db: Session = Depends(get_db), 
):

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or in an invalid format")
    token = auth_header.split(" ")[1]

    company_in_charge = db.query(CompanyInCharge).filter_by(id=company_in_charge_id, token=token).first()
    if not company_in_charge:
        raise HTTPException(status_code=401, detail="Invalid token or company in charge not found")

    job = db.query(Job).filter_by(unique_job_id=job_id, company_in_charge_id=company_in_charge.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if request.method == "GET":
        return {
            "id": job.id,
            "job_title": job.job_title,
            "company": job.company_id,
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

        if not job_data.company:
            raise HTTPException(status_code=400, detail="Company name is required")
        company = db.query(Company).filter_by(name=job_data.company, company_in_charge_id=company_in_charge.id).first()
        if not company:
            raise HTTPException(status_code=404, detail=f'Company with name "{job_data.company}" does not exist')

        try:
            for key, value in job_data.dict(exclude_unset=True).items():
                setattr(job, key, value)
            job.company_id = company.id
            job.company_in_charge_id = company_in_charge.id
            db.commit()
            return JSONResponse(content={"message": "Job updated successfully"}, status_code=200)

        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Error updating job: {str(e)}")

@router.post("/change-job-status/{company_in_charge_id}/{job_id}/")
def change_company_job_status(
    company_in_charge_id: int,
    job_id: str,
    job_status_request: JobStatusRequest,
    request: Request,
    db: Session = Depends(get_db),
):

    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=400, detail="Token is missing or in an invalid format")

    token = auth_header.split(' ')[1]

    company_in_charge = db.query(CompanyInCharge).filter_by(id=company_in_charge_id, token=token).first()
    if not company_in_charge:
        raise HTTPException(status_code=401, detail="Invalid token or company in charge not found")

    if job_status_request.job_status not in {"active", "closed"}:
        raise HTTPException(status_code=400, detail="Valid job_status is required")

    job = db.query(Job).filter_by(unique_job_id=job_id, company_in_charge_id=company_in_charge.id).first()
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

@router.get("/jobs-company/{company_in_charge_id}/")
def jobs_by_company(
    company_in_charge_id: int,
    request: Request,
    filters: JobFilterParams = Depends(),
    db: Session = Depends(get_db)
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or in an invalid format")

    token = auth_header.split(" ")[1]

    company_in_charge = db.query(CompanyInCharge).filter_by(id=company_in_charge_id, token=token).first()
    if not company_in_charge:
        raise HTTPException(status_code=401, detail="Invalid token or company in charge not found")

    if not (filters.name or filters.sort_order or filters.job_status):
        raise HTTPException(status_code=400, detail="Select at least one parameter")

    jobs_query = db.query(Job)

    if filters.name:
        company = db.query(Company).filter_by(name=filters.name, company_in_charge_id=company_in_charge.id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        jobs_query = jobs_query.filter(Job.company_id == company.id)

    if filters.job_status:
        if filters.job_status.lower() not in {"active", "closed"}:
            raise HTTPException(status_code=400, detail="Invalid job status")
        jobs_query = jobs_query.filter(Job.job_status == filters.job_status.lower())

    if filters.sort_order:
        if filters.sort_order == "latest":
            jobs_query = jobs_query.order_by(Job.published_at.desc())
        elif filters.sort_order == "oldest":
            jobs_query = jobs_query.order_by(Job.published_at.asc())
        else:
            raise HTTPException(status_code=400, detail="Invalid sort order")

    jobs = jobs_query.all()

    jobs_list = [{
        "id": job.unique_job_id,
        "company_in_charge": str(company_in_charge.company_name),
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

@router.get("/company-applicants-count/{company_in_charge_id}/")
def fetch_company_applicants_count(
    company_in_charge_id: int,
    request: Request,
    job_title: str,
    db: Session = Depends(get_db)
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or invalid format")

    token = auth_header.split(" ")[1]

    company_in_charge = db.query(CompanyInCharge).filter_by(id=company_in_charge_id, token=token).first()
    if not company_in_charge:
        raise HTTPException(status_code=404, detail="company in charge not found")

    company = db.query(Company).filter_by(company_in_charge_id=company_in_charge.id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    job = db.query(Job).filter_by(job_title=job_title, company_id=company.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    applicants_count = db.query(Application).filter_by(job_id=job.id).count()

    return JSONResponse(content={"applicants_count": applicants_count})

@router.get("/job-summary/{company_in_charge_id}/")
def get_job_application_summary(
    company_in_charge_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or invalid format")

    token = auth_header.split(" ")[1]

    company_in_charge = (
        db.query(CompanyInCharge)
        .filter_by(id=company_in_charge_id, token=token)
        .first()
    )
    if not company_in_charge:
        raise HTTPException(status_code=401, detail="Invalid token or company in charge not found")

    job_data = (
        db.query(
            Job.job_title,
            Job.location,
            func.count(Application.id).label("applied_candidates")
        )
        .outerjoin(Application, Job.id == Application.job_id)
        .filter(Job.company_in_charge_id == company_in_charge_id)
        .group_by(Job.job_title, Job.location)
        .all()
    )

    job_summary = [
        {
            "job_title": job.job_title,
            "location": job.location,
            "applied_candidates": job.applied_candidates
        }
        for job in job_data
    ]

    return JSONResponse(content={"Posted_Jobs": job_summary})

@router.get("/application-details/{company_in_charge_id}/")
def get_application_details(
    company_in_charge_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or invalid format")

    token = auth_header.split(" ")[1]

    company_in_charge = (
        db.query(CompanyInCharge)
        .filter_by(id=company_in_charge_id, token=token)
        .first()
    )
    if not company_in_charge:
        raise HTTPException(status_code=401, detail="Invalid token or company in charge not found")

    applications = (
        db.query(Application, Job.job_title)
        .join(Job, Application.job_id == Job.id)
        .filter(Application.company_in_charge_id == company_in_charge_id)
        .all()
    )

    application_details = [
        {
            "first_name": app.first_name,
            "last_name": app.last_name,
            "job_title": job_title,
            "status": app.status
        }
        for app, job_title in applications
    ]

    return JSONResponse(content={"Candidates Applied": application_details})


def filter_empty_entries(entries):
    def remove_empty_fields(data):
        if isinstance(data, dict):
            return {key: remove_empty_fields(value) for key, value in data.items() if value not in [None, '', [], {}]}
        elif isinstance(data, list):
            return [remove_empty_fields(item) for item in data if item not in [None, '', [], {}]]
        else:
            return data

    filtered_entries = []
    for entry in entries:
        cleaned_entry = remove_empty_fields(entry)
        if cleaned_entry:
            filtered_entries.append(cleaned_entry)
    return filtered_entries


def fetch_applications_for_company(job, db: Session):
    applications = db.query(Application).filter_by(job_id=job.id).all()
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
                        "description": exp.description
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


@router.get("/company-job-applications/{company_in_charge_id}/{job_id}/")
def fetch_company_job_applications(
    company_in_charge_id: int,
    job_id: str,
    request: Request,
    db: Session = Depends(get_db)
):

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or not in the correct format")
    token = auth_header.split(" ")[1]

    company_in_charge = (
        db.query(CompanyInCharge)
        .filter_by(id=company_in_charge_id, token=token)
        .first()
    )
    if not company_in_charge:
        raise HTTPException(status_code=401, detail="Invalid token or company in charge not found")

    job = (
        db.query(Job)
        .filter_by(company_in_charge_id=company_in_charge_id, unique_job_id=job_id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="No Jobs Found")

    applications_list = fetch_applications_for_company(job, db)

    job_details = {
        "job_title": job.job_title,
        # "company": job.company.name,
        "description": job.description,
        "requirements": job.requirements,
        "published_at": job.published_at,
        "experience_yr": job.experience_yr,
        "job_type": job.job_type,
        "experience": job.experience,
        "category": job.category,
        "skills": job.skills,
        "workplaceTypes": job.workplaceTypes,
        "location": job.location,
        "questions": job.questions,
        "job_status": job.job_status,
        "must_have_qualification": job.must_have_qualification,
    }

    return JSONResponse(content=jsonable_encoder({
    "jobdetails": job_details,
    "applicants": applications_list,
}))


@router.put("/update-company-application-status/{company_in_charge_id}/{application_id}/")
async def update_company_application_status(
    company_in_charge_id: int,
    application_id: int,
    payload: StatusUpdatePayload,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Token is missing or invalid format")
    token = authorization.split(" ")[1]

    company_in_charge = db.query(CompanyInCharge).filter_by(id=company_in_charge_id, token=token).first()
    if not company_in_charge:
        raise HTTPException(status_code=401, detail="Invalid token or company in charge not found")

    application = db.query(Application).filter_by(id=application_id, company_in_charge_id=company_in_charge_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    application.status = payload.application_status
    db.commit()

    message = (
        f"Your application for {application.job.job_title} has been updated "
        f"to {application.status} by {company_in_charge.company_name}"
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
                body=f"Dear {job_seeker.first_name} {job_seeker.last_name},\n\n{message}\n\nHR Team\n{company_in_charge.company_name}",
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
                body=f"Dear {user.firstname} {user.lastname},\n\n{message}\n\nHR Team\n{company_in_charge.company_name}",
                recipient=user.email,
            )

    return JSONResponse(status_code=200, content={"message": "Application status updated successfully"})



