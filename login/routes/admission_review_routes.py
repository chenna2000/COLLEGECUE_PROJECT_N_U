from fastapi import APIRouter, Form, File, UploadFile, Depends, HTTPException # type: ignore
from fastapi.responses import JSONResponse # type: ignore
from sqlalchemy.orm import Session # type: ignore
import os, shutil
from typing import Optional
from typing import List
from login.database import SessionLocal
from login.models import OptimizedReview
from login.schemas import OptimizedReviewOut,OptimizedReviewPublicOut

router = APIRouter()
UPLOAD_DIR = "uploads_optimized"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def save_file(upload_file: UploadFile, subfolder: str) -> str:
    folder_path = os.path.join(UPLOAD_DIR, subfolder)
    os.makedirs(folder_path, exist_ok=True)

    file_path = os.path.join(folder_path, upload_file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return file_path

@router.post("/optimized-review/", response_model=OptimizedReviewOut)
async def submit_optimized_review(
    college_name: str = Form(...),
    course_name: str = Form(...),
    stu_name: str = Form(...),
    email: str = Form(...),
    country_code: str = Form("IN"),
    phone_number: str = Form(...),
    gender: str = Form(...),
    linkedin_profile: Optional[str] = Form(None),
    year: int = Form(...),
    content: str = Form(...),
    verified: bool = Form(False),
    profile_photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    try:
        existing = db.query(OptimizedReview).filter(OptimizedReview.email == email).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Hi, this email ({email}) has already submitted a review."
            )

        review = OptimizedReview(
            college_name=college_name,
            course_name=course_name,
            stu_name=stu_name,
            email=email,
            country_code=country_code,
            phone_number=phone_number,
            gender=gender,
            linkedin_profile=linkedin_profile,
            year=year,
            content=content,
            verified=verified,
        )

        if profile_photo:
            review.profile_photo = save_file(profile_photo, "profile_photos")

        db.add(review)
        db.commit()
        db.refresh(review)

        return JSONResponse({'message': 'Submitted Review Successfully.'}, status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to submit: {str(e)}")


@router.get("/optimized-reviews/", response_model=List[OptimizedReviewPublicOut])
def get_all_reviews(db: Session = Depends(get_db)):
    reviews = db.query(OptimizedReview).all()
    return reviews


# from fastapi import APIRouter, Form, File, UploadFile, Depends,HTTPException # type: ignore
# from fastapi.responses import JSONResponse # type: ignore
# from sqlalchemy.orm import Session # type: ignore
# from typing import Optional
# import os, shutil
# from login.database import SessionLocal
# from login.models import AdmissionReview
# from login.schemas import AdmissionReviewOut

# router = APIRouter()

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# UPLOAD_DIR = "uploads"

# def save_file(upload_file: UploadFile, subfolder: str) -> str:
#     folder_path = os.path.join(UPLOAD_DIR, subfolder)
#     os.makedirs(folder_path, exist_ok=True)

#     file_path = os.path.join(folder_path, upload_file.filename)
#     with open(file_path, "wb") as buffer:
#         shutil.copyfileobj(upload_file.file, buffer)
#     return file_path


# @router.post("/submit-review/", response_model=AdmissionReviewOut)
# async def submit_review(
#     college_name: str = Form(...),
#     other_college_name: Optional[str] = Form(None),
#     course_name: str = Form(...),
#     other_course_name: Optional[str] = Form(None),
#     student_name: str = Form(...),
#     email: str = Form(...),
#     country_code: str = Form("IN"),
#     phone_number: str = Form(...),
#     gender: str = Form(...),
#     linkedin_profile: Optional[str] = Form(None),
#     course_fees: float = Form(...),
#     year: int = Form(...),
#     referral_code: Optional[str] = Form(None),
#     apply: str = Form("applied"),
#     anvil_reservation_benefits: bool = Form(...),
#     benefit: str = Form("Benefits"),
#     gd_pi_admission: bool = Form(...),
#     class_size: int = Form(...),
#     opted_hostel: bool = Form(...),
#     college_provides_placements: bool = Form(...),
#     hostel_fees: Optional[float] = Form(0.00),
#     average_package: Optional[float] = Form(...),
#     admission_process: str = Form(...),
#     course_curriculum_faculty: str = Form(...),
#     fees_structure_scholarship: str = Form(...),
#     liked_things: str = Form(...),
#     disliked_things: str = Form(...),
#     agree_terms: bool = Form(...),
#     profile_photo: Optional[UploadFile] = File(None),
#     campus_photos: Optional[UploadFile] = File(None),
#     certificate_id_card: Optional[UploadFile] = File(None),
#     graduation_certificate: Optional[UploadFile] = File(None),
#     db: Session = Depends(get_db),
# ):
#     try:
#         review = AdmissionReview(
#             college_name=college_name,
#             other_college_name=other_college_name,
#             course_name=course_name,
#             other_course_name=other_course_name,
#             student_name=student_name,
#             email=email,
#             country_code=country_code,
#             phone_number=phone_number,
#             gender=gender,
#             linkedin_profile=linkedin_profile,
#             course_fees=course_fees,
#             year=year,
#             referral_code=referral_code,
#             apply=apply,
#             anvil_reservation_benefits=anvil_reservation_benefits,
#             benefit=benefit,
#             gd_pi_admission=gd_pi_admission,
#             class_size=class_size,
#             opted_hostel=opted_hostel,
#             college_provides_placements=college_provides_placements,
#             hostel_fees=hostel_fees,
#             average_package=average_package,
#             admission_process=admission_process,
#             course_curriculum_faculty=course_curriculum_faculty,
#             fees_structure_scholarship=fees_structure_scholarship,
#             liked_things=liked_things,
#             disliked_things=disliked_things,
#             agree_terms=agree_terms
#         )

#         if profile_photo:
#             review.profile_photo = save_file(profile_photo, "profile_photos")
#         if campus_photos:
#             review.campus_photos = save_file(campus_photos, "campus_photos")
#         if certificate_id_card:
#             review.certificate_id_card = save_file(certificate_id_card, "certificates")
#         if graduation_certificate:
#             review.graduation_certificate = save_file(graduation_certificate, "graduation_certificates")

#         db.add(review)
#         db.commit()
#         db.refresh(review)

#         return JSONResponse({'message': 'Submitted Review Successfully.'}, status_code=200)

#     except Exception as e:
#         db.rollback()
#         raise HTTPException(status_code=500, detail=f"Failed to submit review: {str(e)}")