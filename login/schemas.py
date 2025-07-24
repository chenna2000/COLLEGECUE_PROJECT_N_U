from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, EmailStr, HttpUrl # type: ignore
from datetime import datetime
from pydantic import BaseModel, Field, validator # type: ignore
from typing import Literal

class CompanyInChargeCreate(BaseModel):
    company_name: str
    official_email: EmailStr
    country_code: str
    mobile_number: str
    designation: str
    password: str 
    confirm_password : str
    linkedin_profile:str
    company_person_name: str
    agreed_to_terms: bool

class CompanyInChargeLogin(BaseModel):
    official_email: EmailStr
    password: str

class UniversityInChargeCreate(BaseModel):
    university_name: str
    official_email: EmailStr
    country_code: str
    mobile_number: str
    designation: str
    password: str
    confirm_password: str
    linkedin_profile:str
    college_person_name: str
    agreed_to_terms: bool
    clg_id: Optional[str] = None

class UniversityInChargeLogin(BaseModel):
    official_email: EmailStr
    password: str

class OnlineStatusOut(BaseModel):
    email: EmailStr
    is_online: bool
    last_seen: datetime

class newusercreate(BaseModel):
    firstname: str
    lastname: str
    email: EmailStr
    country_code: str
    phonenumber: str
    gender : str
    password: str
    confirm_password: str
    agreed_to_terms : bool

class newusernextstep(newusercreate):
    course: str
    education: str
    percentage: str
    preferred_destination: str
    start_date: str
    mode_study: str
    entrance: bool
    passport: bool

class newuserlogin(BaseModel):
    email: EmailStr
    password: str

class JobseekerCreate(BaseModel):
    firstname: str
    lastname: str
    email: EmailStr
    country_code: str
    phonenumber: str
    experience: int
    linkedin_profile:str
    password: str
    confirm_password: str
    agreed_to_terms : bool

class JobseekerLogin(BaseModel):
    email: EmailStr
    password: str

class ForgotRequest(BaseModel):
    email: EmailStr

class VerifySchema(BaseModel):
    otp: str

class ForgotRequest2(BaseModel):
    password : str
    confirm_password : str

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    old_password: str
    new_password: str
    confirm_password: str

class DeleteAccountRequest(BaseModel):
    confirmation: bool

class ConsultantCreate(BaseModel):
    consultant_name: str
    official_email: EmailStr
    country_code: str
    mobile_number: str
    designation : str
    password: str
    confirm_password : str
    linkedin_profile:str
    consultant_person_name: str
    agreed_to_terms: bool

class ConsultantLogin(BaseModel):
    official_email: EmailStr
    password: str

class ContactCreate(BaseModel):
    name: str
    email: EmailStr
    subject: str
    website: Optional[HttpUrl] = None
    message: str

class QuestionCreate(BaseModel):
    text: str

class QuestionResponse(BaseModel):
    id: int
    text: str

    class Config:
        orm_mode = True

class AnswerCreate(BaseModel):
    text: str

class AnswerResponse(BaseModel):
    id: int
    text: str
    question_id: int

    class Config:
        orm_mode = True

class SubscriptionSchema(BaseModel):
    email: EmailStr

    class Config:
        orm_mode = True

class SubscriptionSchema1(BaseModel):
    email: EmailStr

    class Config:
        orm_mode = True

class Step1(BaseModel):
    college_name: str
    other_college_name: Optional[str]
    course_name: str
    other_course_name: Optional[str]
    student_name: str
    email: EmailStr
    country_code: str = "IN"
    phone_number: str
    gender: str
    linkedin_profile: Optional[HttpUrl]
    course_fees: Decimal
    year: int
    referral_code: Optional[str]
    apply: str = "applied"
    anvil_reservation_benefits: bool
    benefit: str = "Benefits"
    gd_pi_admission: bool
    class_size: int
    opted_hostel: bool
    college_provides_placements: bool
    hostel_fees: Optional[Decimal] = 0.00
    average_package: Optional[Decimal]

class Step2(BaseModel):
    admission_process: str
    course_curriculum_faculty: str

class Step3(BaseModel):
    fees_structure_scholarship: str

class Step4(BaseModel):
    liked_things: str
    disliked_things: str

class Step5(BaseModel):
    agree_terms: bool

class Step6(BaseModel):
    pass

class AdmissionReviewOut(BaseModel):
    id: int
    college_name: str
    other_college_name: Optional[str]
    course_name: str
    other_course_name: Optional[str]
    student_name: str
    email: EmailStr
    country_code: str = "IN"
    phone_number: str
    gender: str
    linkedin_profile: Optional[HttpUrl]
    course_fees: Decimal
    year: int
    referral_code: Optional[str]
    apply: str = "applied"
    anvil_reservation_benefits: bool
    benefit: str = "Benefits"
    gd_pi_admission: bool
    class_size: int
    opted_hostel: bool
    college_provides_placements: bool
    hostel_fees: Optional[Decimal] = 0.00
    average_package: Optional[Decimal]
    admission_process: str
    course_curriculum_faculty: str
    fees_structure_scholarship: str
    liked_things: str
    disliked_things: str
    agree_terms: bool
    profile_photo: Optional[str]
    campus_photos: Optional[str]
    certificate_id_card: Optional[str]
    graduation_certificate: Optional[str]

    class Config:
        orm_mode = True

class UnregisterCollegeCreate(BaseModel):
    university_name: str
    official_email: EmailStr
    country_code: str
    mobile_number: str
    designation: str
    password: str
    confirm_password: str
    linkedin_profile:str
    college_person_name: str
    agreed_to_terms: bool

class OptimizedReviewBase(BaseModel):
    college_name: str
    course_name: str
    stu_name: str
    email: EmailStr
    country_code: str = "IN"
    phone_number: str
    gender: str
    linkedin_profile: Optional[HttpUrl]
    year: int
    content: str
    verified: bool = False

class OptimizedReviewOut(OptimizedReviewBase):
    id: int
    profile_photo: Optional[str]

    class Config:
        orm_mode = True

class OptimizedReviewPublicOut(BaseModel):
    id: int
    college_name: str
    course_name: str
    stu_name: str
    email: EmailStr
    linkedin_profile: Optional[HttpUrl]
    content: str
    profile_photo: Optional[str]

    class Config:
        orm_mode = True

class BankDetails(BaseModel):
    pan_card: str = Field(..., min_length=10, max_length=10, pattern="^[A-Z]{5}[0-9]{4}[A-Z]{1}$")
    bank_name: str
    account_holder_name: str
    confirm_account_holder_name: str
    account_number: str = Field(..., min_length=11, max_length=11)
    confirm_account_number: str = Field(..., min_length=11, max_length=11)
    account_type: Literal["current", "personal", "savings"]
    ifsc_code: str = Field(..., min_length=11, max_length=11, pattern="^[A-Z]{4}0[A-Z0-9]{6}$")
    mobile_number: str = Field(..., min_length=10, max_length=10)

    @validator("confirm_account_holder_name")
    def match_names(cls, v, values):
        if "account_holder_name" in values and v != values["account_holder_name"]:
            raise ValueError("Account holder names do not match")
        return v

    @validator("confirm_account_number")
    def match_account_numbers(cls, v, values):
        if "account_number" in values and v != values["account_number"]:
            raise ValueError("Account numbers do not match")
        return v


class MessageRequest(BaseModel):
    expert_email: str
    content: str

class ConnectionRequest(BaseModel):
    student_id : int
