import uuid
from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Boolean, BigInteger, UniqueConstraint, func # type: ignore
from sqlalchemy import Column, Integer, String, Text, Date, ForeignKey, JSON # type: ignore
from sqlalchemy.orm import relationship # type: ignore
from datetime import datetime
from login.database import Base
from sqlalchemy.dialects.postgresql import JSON # type: ignore

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    unique_job_id = Column(String(36), unique=True, default=lambda: str(uuid.uuid1()))
    unique_job_id_as_int = Column(BigInteger, unique=True, nullable=True)
    company_in_charge_id = Column(Integer, ForeignKey("company_in_charge.id"))
    company_id = Column(Integer, ForeignKey("companies.id"))
    description = Column(Text)
    requirements = Column(Text)
    published_at = Column(DateTime, default=datetime.utcnow)
    experience_yr = Column(String(10), default="0-100")
    job_title = Column(String(200))
    job_type = Column(String(50))
    experience = Column(String(50))
    category = Column(String(100))
    skills = Column(String(1000))
    workplaceTypes = Column(String(50))
    location = Column(String(100))
    questions = Column(Text, nullable=True)
    job_status = Column(String(50), default="active")
    email = Column(String(255), default="example@example.com")
    must_have_qualification = Column(Boolean, default=False)
    filter = Column(Boolean, default=False)
    source = Column(String(50), default="LinkedIn")

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    company_in_charge_id = Column(Integer, ForeignKey("company_in_charge.id"))
    name = Column(String(255))
    email = Column(String(255), default="example@example.com")
    phone = Column(String(20), default="1234567890")
    address = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100), default="India")
    zipcode = Column(String(6), default="522426")
    website = Column(String(255))
    website_urls = Column(Text)
    about_company = Column(String(2004), default="about_company")
    sector_type = Column(String(100))
    category = Column(String(100), default="Unknown")
    established_date = Column(DateTime, default=datetime.utcnow)
    employee_size = Column(Integer, default=0, nullable=True)

class Application(Base):
    __tablename__ = 'applications'

    id = Column(Integer, primary_key=True, index=True)
    company_in_charge_id = Column(Integer, ForeignKey("company_in_charge.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("new_user.id"), nullable=True)
    job_seeker_id = Column(Integer, ForeignKey("jobseeker.id"), nullable=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    first_name = Column(String(255), nullable=False, default="John")
    last_name = Column(String(255), nullable=False, default="Doe")
    email = Column(String(255), nullable=False, default="unknown@example.com")
    phone_number = Column(String(15), default="123-456-7890")
    resume = Column(String(255), nullable=True)
    cover_letter = Column(Text, default="No cover letter provided")
    applied_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default='pending')
    skills = Column(String(1000), nullable=False)
    bio = Column(Text, nullable=True)
    education = Column(Text, nullable=True)
    experience = Column(Text, nullable=True)

    job_seeker = relationship("JobSeeker", backref="applications")
    user = relationship("new_user", backref="applications")
    job = relationship("Job", backref="applications")

class Job1(Base):
    __tablename__ = "college_jobs"

    id = Column(Integer, primary_key=True, index=True)
    university_in_charge_id = Column(Integer, ForeignKey("university_in_charge.id"))
    college_id = Column(Integer, ForeignKey("colleges.id"))
    description = Column(Text)
    requirements = Column(Text)
    published_at = Column(DateTime, default=datetime.utcnow)
    experience_yr = Column(String(10), default="0-100")
    job_title = Column(String(200))
    job_type = Column(String(50))
    experience = Column(String(50))
    category = Column(String(100))
    skills = Column(String(1000))
    workplaceTypes = Column(String(50))
    location = Column(String(100))
    questions = Column(Text, nullable=True)
    job_status = Column(String(50), default="active")
    email = Column(String(255), default="example@example.com")
    must_have_qualification = Column(Boolean, default=False)
    filter = Column(Boolean, default=False)
    source = Column(String(50), default="LinkedIn")

class College(Base):
    __tablename__ = "colleges"

    id = Column(Integer, primary_key=True, index=True)
    university_in_charge_id = Column(Integer, ForeignKey("university_in_charge.id"))
    college_name = Column(String(255))
    email = Column(String(255), default="example@example.com")
    website = Column(String(255))
    phone = Column(String(20), default="1234567890")
    founded_date = Column(DateTime, default=datetime.utcnow)
    university_type = Column(String(100))
    about_college = Column(String(2004), default="about_college")
    website_urls = Column(Text)
    address = Column(String(255))
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100), default="India")
    zipcode = Column(String(6), default="522426")

class Application1(Base):
    __tablename__ = 'colleges_applications'

    id = Column(Integer, primary_key=True, index=True)
    university_in_charge_id = Column(Integer, ForeignKey("university_in_charge.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("new_user.id"), nullable=True)
    job_seeker_id = Column(Integer, ForeignKey("jobseeker.id"), nullable=True)
    job_id = Column(Integer, ForeignKey("college_jobs.id"), nullable=False)
    first_name = Column(String(255), nullable=False, default="John")
    last_name = Column(String(255), nullable=False, default="Doe")
    email = Column(String(255), nullable=False, default="unknown@example.com")
    phone_number = Column(String(15), default="123-456-7890")
    resume = Column(String(255), nullable=True)
    cover_letter = Column(Text, default="No cover letter provided")
    applied_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default='pending')
    skills = Column(String(1000), nullable=False)
    bio = Column(Text, nullable=True)
    education = Column(Text, nullable=True)
    experience = Column(Text, nullable=True)

    job_seeker = relationship("JobSeeker", backref="colleges_applications")
    user = relationship("new_user", backref="colleges_applications")
    job = relationship("Job1", backref="colleges_applications")


class NewUserEnquiry(Base):
    __tablename__ = "new_user_enquiry"

    id = Column(Integer, primary_key=True, index=True)
    university_in_charge_id = Column(Integer, ForeignKey("university_in_charge.id"), nullable=True)
    clg_id = Column(String(400), nullable=True, default="Null")
    new_user_id = Column(Integer, ForeignKey("new_user.id"), nullable=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(254), nullable=False)
    country_code = Column(String(3), default="+91")
    mobile_number = Column(String(15), nullable=False)
    course = Column(String(128), default="N/A")
    status = Column(String(20), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SavedJobForNewUser(Base):
    __tablename__ = 'saved_job_for_new_user'

    id = Column(Integer, primary_key=True, index=True)
    new_user_id = Column(Integer, ForeignKey('new_user.id'))
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=True)
    job1_id = Column(Integer, ForeignKey('college_jobs.id'), nullable=True)
    saved_at = Column(DateTime, server_default=func.now())
    original_job_id = Column(String(255), nullable=True, default=None)


    class Meta:
        __table_args__ = (
            UniqueConstraint('new_user_id', 'job_id', 'job1_id', name='uix_new_user_job_job1'),
        )

class SavedJobForNewUser1(Base):
    __tablename__ = 'saved_job_for_new_user1'

    id = Column(Integer, primary_key=True, index=True)
    # new_user_id = Column(Integer, ForeignKey('new_user.id'))
    job_seeker_id = Column(Integer, ForeignKey("jobseeker.id"), nullable=True)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=True)
    job1_id = Column(Integer, ForeignKey('college_jobs.id'), nullable=True)
    saved_at = Column(DateTime, server_default=func.now())
    original_job_id = Column(String(255), nullable=True, default=None)


    class Meta:
        __table_args__ = (
            UniqueConstraint('job_seeker_id', 'job_id', 'job1_id', name='uix_jobseeker_job_job1'),
        )

class Resume(Base):
    __tablename__ = 'resumes'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('new_user.id'))
    first_name = Column(String(50))
    last_name = Column(String(50))
    email = Column(String(100))
    phone = Column(String(20))
    address = Column(Text)
    date_of_birth = Column(Date)
    website_urls = Column(JSON)
    skills = Column(Text)
    activities = Column(Text, nullable=True)
    interests = Column(Text, nullable=True)
    languages = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))
    zipcode = Column(String(20))


class Objective(Base):
    __tablename__ = 'objectives'

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey('resumes.id'))
    text = Column(Text)


class Education(Base):
    __tablename__ = 'educations'

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey('resumes.id'))
    course_or_degree = Column(String(100))
    school_or_university = Column(String(100))
    grade_or_cgpa = Column(String(20))
    start_date = Column(Date)
    end_date = Column(Date)
    description = Column(Text)


class Experience(Base):
    __tablename__ = 'experiences'

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey('resumes.id'))
    job_title = Column(String(100), nullable=True)
    company_name = Column(String(100), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)


class Project(Base):
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey('resumes.id'))
    title = Column(String(150), nullable=True)
    description = Column(Text, nullable=True)
    project_link = Column(Text, nullable=True)


class Reference(Base):
    __tablename__ = 'references'

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey('resumes.id'))
    name = Column(String(100), nullable=True)
    contact_info = Column(String(150), nullable=True)
    relationship = Column(String(100), nullable=True)


class Certification(Base):
    __tablename__ = 'certifications'

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey('resumes.id'))
    name = Column(String(100), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)


class Achievements(Base):
    __tablename__ = 'achievements'

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey('resumes.id'))
    title = Column(String(150), nullable=True)
    publisher = Column(String(100), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)


class Publications(Base):
    __tablename__ = 'publications'

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey('resumes.id'))
    title = Column(String(150), nullable=True)
    publisher = Column(String(100), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)


from sqlalchemy import Column, Integer, String, Date, ForeignKey, Text, JSON # type: ignore


class JobseekerResume(Base):
    __tablename__ = 'resumes1'

    id = Column(Integer, primary_key=True, index=True)
    # user_id = Column(Integer, ForeignKey('jobseeker.id'))
    job_seeker_id = Column(Integer, ForeignKey("jobseeker.id"), nullable=True)
    first_name = Column(String(50))
    last_name = Column(String(50))
    email = Column(String(100))
    phone = Column(String(20))
    address = Column(Text)
    date_of_birth = Column(Date)
    website_urls = Column(JSON)
    skills = Column(Text)
    activities = Column(Text, nullable=True)
    interests = Column(Text, nullable=True)
    languages = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100))
    zipcode = Column(String(20))


class JobseekerObjective(Base):
    __tablename__ = 'objectives1'

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey('resumes1.id'))
    text = Column(Text)


class JobseekerEducation(Base):
    __tablename__ = 'educations1'

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey('resumes1.id'))
    course_or_degree = Column(String(100))
    school_or_university = Column(String(100))
    grade_or_cgpa = Column(String(20))
    start_date = Column(Date)
    end_date = Column(Date)
    description = Column(Text)


class JobseekerExperience(Base):
    __tablename__ = 'experiences1'

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey('resumes1.id'))
    job_title = Column(String(100), nullable=True)
    company_name = Column(String(100), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)


class JobseekerProject(Base):
    __tablename__ = 'projects1'

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey('resumes1.id'))
    title = Column(String(150), nullable=True)
    description = Column(Text, nullable=True)
    project_link = Column(Text, nullable=True)


class JobseekerReference(Base):
    __tablename__ = 'references1'

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey('resumes1.id'))
    name = Column(String(100), nullable=True)
    contact_info = Column(String(150), nullable=True)
    relationship = Column(String(100), nullable=True)


class JobseekerCertification(Base):
    __tablename__ = 'certifications1'

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey('resumes1.id'))
    name = Column(String(100), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)


class JobseekerAchievement(Base):
    __tablename__ = 'achievements1'

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey('resumes1.id'))
    title = Column(String(150), nullable=True)
    publisher = Column(String(100), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)


class JobseekerPublication(Base):
    __tablename__ = 'publications1'

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey('resumes1.id'))
    title = Column(String(150), nullable=True)
    publisher = Column(String(100), nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)


class StudentReview(Base):
    __tablename__ = 'student_review'

    id = Column(Integer, primary_key=True, index=True)
    reviewer_id = Column(Integer, ForeignKey('new_user.id'))
    reviewed_id = Column(Integer, ForeignKey('new_user.id'))
    review_text = Column(Text, nullable=True)
    liked = Column(Boolean, default=False)
    disliked = Column(Boolean, default=False)
    reported = Column(Boolean, default=False)
    reviewed_at = Column(DateTime, server_default=func.now())

    class Meta:
        __table_args__ = (
            UniqueConstraint('reviewer_id', 'reviewed_id', name='uix_reviewer_reviewed'),
        )
