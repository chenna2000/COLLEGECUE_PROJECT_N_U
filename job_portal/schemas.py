from pydantic import BaseModel, Field, validator, HttpUrl,EmailStr # type: ignore
from typing import List, Optional
from datetime import date, datetime

class JobCreateRequest(BaseModel):
    job_title: str
    company: str
    location: Optional[str] = ""
    description: Optional[str] = ""
    requirements: Optional[str] = ""
    job_type: Optional[str] = ""
    experience: Optional[str] = ""
    experience_yr: Optional[str] = ""
    category: Optional[str] = ""
    workplaceTypes: Optional[str] = ""
    skills: Optional[str] = ""
    questions: Optional[str] = ""
    job_status: Optional[str] = "active"

    @validator("skills", pre=True, always=True)
    def deduplicate_skills(cls, value):
        if value:
            unique_skills = sorted(set(s.strip() for s in value.split(',') if s.strip()))
            return ', '.join(unique_skills)
        return ""

class JobStatusRequest(BaseModel):
    job_status: str

class JobFilterParams(BaseModel):
    name: Optional[str] = Field(None, description="Company name")
    sort_order: Optional[str] = Field(None, description="'latest' or 'oldest'")
    job_status: Optional[str] = Field(None, description="'active' or 'closed'")


# for college

class Job1CreateRequest(BaseModel):
    job_title: str
    college : int
    location: Optional[str] = ""
    description: Optional[str] = ""
    requirements: Optional[str] = ""
    job_type: Optional[str] = ""
    experience: Optional[str] = ""
    experience_yr: Optional[str] = ""
    category: Optional[str] = ""
    workplaceTypes: Optional[str] = ""
    skills: Optional[str] = ""
    questions: Optional[str] = ""
    job_status: Optional[str] = "active"

    @validator("skills", pre=True, always=True)
    def deduplicate_skills(cls, value):
        if value:
            unique_skills = sorted(set(s.strip() for s in value.split(',') if s.strip()))
            return ', '.join(unique_skills)
        return ""

class Job1StatusRequest(BaseModel):
    job_status: str

class Job1FilterParams(BaseModel):
    name: Optional[str] = Field(None, description="College name")
    sort_order: Optional[str] = Field(None, description="'latest' or 'oldest'")
    job_status: Optional[str] = Field(None, description="'active' or 'closed'")


class ObjectiveSchema(BaseModel):
    id: Optional[int]
    resume_id: Optional[int]
    text: str

    class Config:
        orm_mode = True


class EducationSchema(BaseModel):
    id: Optional[int]
    resume_id: Optional[int]
    course_or_degree: str
    school_or_university: str
    grade_or_cgpa: str
    start_date: date
    end_date: date
    description: str

    class Config:
        orm_mode = True


class ExperienceSchema(BaseModel):
    id: Optional[int]
    resume_id: Optional[int]
    job_title: Optional[str]
    company_name: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    description: Optional[str]

    class Config:
        orm_mode = True


class ProjectSchema(BaseModel):
    id: Optional[int]
    resume_id: Optional[int]
    title: Optional[str]
    description: Optional[str]
    project_link: Optional[List[HttpUrl]]

    class Config:
        orm_mode = True


class ReferenceSchema(BaseModel):
    id: Optional[int]
    resume_id: Optional[int]
    name: Optional[str]
    contact_info: Optional[str]
    relationship: Optional[str]

    class Config:
        orm_mode = True


class CertificationSchema(BaseModel):
    id: Optional[int]
    resume_id: Optional[int]
    name: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]

    class Config:
        orm_mode = True


class AchievementsSchema(BaseModel):
    id: Optional[int]
    resume_id: Optional[int]
    title: Optional[str]
    publisher: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]

    class Config:
        orm_mode = True


class PublicationsSchema(BaseModel):
    id: Optional[int]
    resume_id: Optional[int]
    title: Optional[str]
    publisher: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]

    class Config:
        orm_mode = True

class ResumeBase(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    address: str
    date_of_birth: date
    website_urls: Optional[List[HttpUrl]] = []
    skills: str
    activities: Optional[str] = None
    interests: Optional[str] = None
    languages: Optional[str] = None
    bio: Optional[str] = None
    city: str
    state: str
    country: str
    zipcode: str

    class Config:
        orm_mode = True


class ResumeCreate(ResumeBase):
    pass


class ResumeResponse(ResumeBase):
    id: int
    objective: Optional[ObjectiveSchema] = None
    education_entries: Optional[List[EducationSchema]] = []
    experience_entries: Optional[List[ExperienceSchema]] = []
    projects: Optional[List[ProjectSchema]] = []
    references: Optional[List[ReferenceSchema]] = []
    certifications: Optional[List[CertificationSchema]] = []
    achievements: Optional[List[AchievementsSchema]] = []
    publications: Optional[List[PublicationsSchema]] = []

    class Config:
        orm_mode = True


class SaveJobRequest(BaseModel):
    new_user_id: int
    job_id: int


class EnquiryCreate(BaseModel):
    firstname: str
    lastname: str
    email: EmailStr
    country_code: str
    mobile_number: str
    course: str


from pydantic import BaseModel, EmailStr, HttpUrl # type: ignore
from typing import Optional, List
from datetime import date


class JobseekerObjective(BaseModel):
    id: Optional[int]
    resume_id: Optional[int]
    text: str

    class Config:
        orm_mode = True


class JobseekerEducation(BaseModel):
    id: Optional[int]
    resume_id: Optional[int]
    course_or_degree: str
    school_or_university: str
    grade_or_cgpa: str
    start_date: date
    end_date: date
    description: str

    class Config:
        orm_mode = True


class JobseekerExperience(BaseModel):
    id: Optional[int]
    resume_id: Optional[int]
    job_title: Optional[str]
    company_name: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]
    description: Optional[str]

    class Config:
        orm_mode = True


class JobseekerProject(BaseModel):
    id: Optional[int]
    resume_id: Optional[int]
    title: Optional[str]
    description: Optional[str]
    project_link: Optional[List[HttpUrl]]

    class Config:
        orm_mode = True


class JobseekerReference(BaseModel):
    id: Optional[int]
    resume_id: Optional[int]
    name: Optional[str]
    contact_info: Optional[str]
    relationship: Optional[str]

    class Config:
        orm_mode = True


class JobseekerCertification(BaseModel):
    id: Optional[int]
    resume_id: Optional[int]
    name: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]

    class Config:
        orm_mode = True


class JobseekerAchievement(BaseModel):
    id: Optional[int]
    resume_id: Optional[int]
    title: Optional[str]
    publisher: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]

    class Config:
        orm_mode = True


class JobseekerPublication(BaseModel):
    id: Optional[int]
    resume_id: Optional[int]
    title: Optional[str]
    publisher: Optional[str]
    start_date: Optional[date]
    end_date: Optional[date]

    class Config:
        orm_mode = True


class JobseekerResumeBase(BaseModel):
    user_id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    address: str
    date_of_birth: date
    website_urls: Optional[List[HttpUrl]] = []
    skills: str
    activities: Optional[str] = None
    interests: Optional[str] = None
    languages: Optional[str] = None
    bio: Optional[str] = None
    city: str
    state: str
    country: str
    zipcode: str

    class Config:
        orm_mode = True


class JobseekerResumeCreate(JobseekerResumeBase):
    pass


class JobseekerResumeResponse(JobseekerResumeBase):
    id: int
    objective: Optional[JobseekerObjective] = None
    education_entries: Optional[List[JobseekerEducation]] = []
    experience_entries: Optional[List[JobseekerExperience]] = []
    projects: Optional[List[JobseekerProject]] = []
    references: Optional[List[JobseekerReference]] = []
    certifications: Optional[List[JobseekerCertification]] = []
    achievements: Optional[List[JobseekerAchievement]] = []
    publications: Optional[List[JobseekerPublication]] = []

    class Config:
        orm_mode = True

class JobOut(BaseModel):
    id: int
    job_title: str
    location: str
    job_status: str
    published_at: Optional[datetime]

class JobDetailOut(BaseModel):
    id: int
    job_title: str
    description: str
    requirements: str
    location: str
    experience_yr: str
    job_type: str
    experience: str
    category: str
    skills: str
    workplaceTypes: str
    published_at: Optional[datetime]
    job_status: str
    email: str
    source: str

class CollegeEnquirySchema(BaseModel):
    first_name: str
    last_name: str
    email: str
    course: str
    status: str

    class Config:
        orm_mode = True

class StatusUpdatePayload(BaseModel):
    application_status: str
