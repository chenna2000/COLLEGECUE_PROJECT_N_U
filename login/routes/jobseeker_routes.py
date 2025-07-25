import datetime
from fastapi import APIRouter, Depends, HTTPException, Request # type: ignore
from typing import Dict
import gspread # type: ignore
from sqlalchemy.orm import Session # type: ignore
from login import models, schemas
from login.database import SessionLocal
from passlib.hash import bcrypt # type: ignore
from fastapi.responses import JSONResponse # type: ignore
import uuid, secrets
from login.utils import send_login_email, send_otp_email, send_registration_email
from google.oauth2.service_account import Credentials # type: ignore
import logging

router = APIRouter()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_unique_token():
    return str(uuid.uuid4())

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def has_two_unique_chars(value):
    return len(set(value.replace(" ", "").lower())) >= 2

SERVICE_ACCOUNT_FILE = "D:\BHARATHTECH TASKS\collegcue-firebase-adminsdk-p63yc-498e419897.json"
SPREADSHEET_ID = '1UCiJsKfBT6eejyx07Tr7vEJylyfldVMbDyH0Au_kkdg'

def write_jobseeker_to_google_sheet(jobseeker_data):
    try:
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets', 
            'https://www.googleapis.com/auth/drive'
        ]

        credentials = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=scopes
        )
        client = gspread.authorize(credentials)

        worksheet = client.open_by_key(SPREADSHEET_ID).get_worksheet(3)

        existing_data = worksheet.get_all_records()
        headers = worksheet.row_values(1)

        email_column = 'email'

        if email_column not in headers:
            raise ValueError(f"'{email_column}' column not found in the Google Sheet")

        email_index = headers.index(email_column)

        if any(record.get(email_column) == jobseeker_data['email'] for record in existing_data):
            return

        today_date = datetime.date.today().isoformat()

        new_row = [
            jobseeker_data['firstname'],
            jobseeker_data['lastname'],
            jobseeker_data['email'],
            jobseeker_data['country_code'],
            jobseeker_data['phonenumber'],
            jobseeker_data['experience'],
            jobseeker_data['password'],
            jobseeker_data['linkedin_profile'],
            jobseeker_data['agreed_to_terms'],
            today_date
        ]

        worksheet.append_row(new_row)

    except Exception as e:
        raise RuntimeError(f"Failed to write user data to Google Sheet: {str(e)}")

@router.post("/register")
def register_jobseeker(jobseeker: schemas.JobseekerCreate, db: Session = Depends(get_db)):
    print("Register function called", flush=True)
    logger.info("Processing registration logic")

    try:
        errors: Dict[str, str] = {}

        existing_jobseeker = db.query(models.JobSeeker).filter_by(email=jobseeker.email).first()
        if existing_jobseeker:
            if existing_jobseeker.firstname != jobseeker.firstname or existing_jobseeker.lastname != jobseeker.lastname:
               errors['email'] = 'Email already registered with different name'
            else:
               errors['email'] = 'Email already registered'

        if db.query(models.JobSeeker).filter_by(phonenumber=jobseeker.phonenumber).first():
            errors['phonenumber'] = 'Mobile number already in use'

        email_username = jobseeker.email.split('@')[0]
        if not has_two_unique_chars(email_username):
            errors['email'] = 'Email username must contain at least 2 unique characters'

        if jobseeker.password != jobseeker.confirm_password:
            errors['password'] = 'Passwords do not match'

        if errors:
            raise HTTPException(status_code=400, detail=errors)

        hashed_password = bcrypt.hash(jobseeker.password)

        db_jobseeker = models.JobSeeker(
            firstname=jobseeker.firstname,
            lastname=jobseeker.lastname,
            email=jobseeker.email,
            country_code=jobseeker.country_code,
            phonenumber=jobseeker.phonenumber,
            experience=jobseeker.experience,
            linkedin_profile=jobseeker.linkedin_profile,
            password=hashed_password,
            confirm_password=hashed_password,
            agreed_to_terms=jobseeker.agreed_to_terms,
        )

        db.add(db_jobseeker)
        db.commit()
        db.refresh(db_jobseeker)

        jobseeker_data = {
           'firstname': jobseeker.firstname,
           'lastname': jobseeker.lastname,
           'email': jobseeker.email,
           'country_code': jobseeker.country_code,
           'phonenumber': jobseeker.phonenumber,
           'experience': jobseeker.experience,
           'linkedin_profile': jobseeker.linkedin_profile,
           'password': hashed_password,
           'agreed_to_terms': jobseeker.agreed_to_terms    
        }

        write_jobseeker_to_google_sheet(jobseeker_data)

        try:
            send_registration_email(jobseeker.firstname, jobseeker.email)
            print("Sending email...", flush=True)
            logger.info("Email sent successfully")
        except HTTPException as e:
            logger.error(f"Email failed: {e}")
            raise HTTPException(status_code=500, detail=f"Email sending failed: {str(e)}")

        return JSONResponse({'success': True, 'message': 'Registration successful'})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@router.post("/login")
def login_jobseeker(jobseeker_data: schemas.JobseekerLogin, db: Session = Depends(get_db)):
    try:
        jobseeker = db.query(models.JobSeeker).filter_by(email=jobseeker_data.email).first()

        if not jobseeker:
           raise HTTPException(status_code=404, detail="Jobseeker not found")

        if not bcrypt.verify(jobseeker_data.password, jobseeker.password):
           raise HTTPException(status_code=401, detail="Invalid credentials")

        token = generate_unique_token()
        jobseeker.token = token
        jobseeker.is_online = True

        status_record = db.query(models.OnlineStatus).filter_by(email=jobseeker.email).first()
        if status_record:
            status_record.is_online = True
        else:
            db.add(models.OnlineStatus(email=jobseeker.email, is_online=True))

        db.commit()

        try:
           send_login_email(jobseeker_data.email, jobseeker.firstname)
           print("Sending email...", flush=True)
           logger.info("Email sent successfully")
        except HTTPException as e:
           logger.error(f"Email failed: {e}")
           raise HTTPException(status_code=500, detail=f"Email sending failed: {str(e)}")

        return {
           "success": True,
           "message": f"Login successful for {jobseeker.email}",
           "token": token,
           "official_email": jobseeker.email,
           "id": jobseeker.id,
           "phone": jobseeker.phonenumber,
           "firstname": jobseeker.firstname,
           "lastname": jobseeker.lastname,
           "model": "JobSeeker"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@router.post("/logout")
async def logout_jobseeker(request: Request, db: Session = Depends(get_db)):
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=400, detail="Token is missing or invalid format")

        token = auth_header.split(" ")[1]

        job_seeker = db.query(models.JobSeeker).filter_by(token=token).first()
        if not job_seeker:
            raise HTTPException(status_code=404, detail="Invalid token")

        job_seeker.token = None
        job_seeker.is_online = False
        db.commit()

        db.query(models.OnlineStatus).filter_by(email=job_seeker.email).update({"is_online": False})
        db.commit()

        return JSONResponse({"success": True, "message": "Logout successful"}, status_code=200)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@router.post("/forgot")
def jobseeker_forgot_password(request: Request, data: schemas.ForgotRequest, db: Session = Depends(get_db)):
    try:
        jobseeker = db.query(models.JobSeeker).filter_by(email=data.email).first()
        if not jobseeker:
            raise HTTPException(status_code=404, detail="Email does not exist")

        new_otp = ''.join([str(secrets.randbelow(10)) for _ in range(4)])

        request.session['otp'] = new_otp
        request.session['email'] = data.email

        jobseeker_email = models.Forgot(
           email=data.email,

       )

        db.add(jobseeker_email)
        db.commit()
        db.refresh(jobseeker_email)

        try:
            send_otp_email(jobseeker.email, new_otp, jobseeker.firstname)
            print("Sending email...", flush=True)
            logger.info("Email sent successfully")
        except HTTPException as e:
            logger.error(f"Email failed: {e}")
            raise HTTPException(status_code=500, detail=f"Email sending failed: {str(e)}")

        return JSONResponse(content={'message': 'OTP sent successfully'}, status_code=200)

    except Exception as e:
        return JSONResponse(content={'success': False, 'error': str(e)}, status_code=500)

@router.post("/verify")
def jobseeker_verify_otp(request: Request, data: schemas.VerifySchema, db: Session = Depends(get_db)):
    try:
        stored_otp = request.session.get("otp")
        if not stored_otp:
            raise HTTPException(status_code=400, detail="Session data not found")

        if str(stored_otp) != str(data.otp):
            raise HTTPException(status_code=400, detail="Invalid OTP")

        otp = models.Verify(
            otp=data.otp
        )

        db.add(otp)
        db.commit()
        db.refresh(otp)

        del request.session["otp"]

        return {"message": "OTP verification successful"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/resend-otp")
def jobseeker_resend_otp(request: Request, db: Session = Depends(get_db)):
    try:
        stored_email = request.session.get("email")
        if not stored_email:
            raise HTTPException(status_code=400, detail="Session data not found")

        jobseeker = db.query(models.JobSeeker).filter_by(email=stored_email).first()
        if not jobseeker:
            raise HTTPException(status_code=404, detail="Jobseeker not found")

        new_otp = ''.join([str(secrets.randbelow(10)) for _ in range(4)])

        request.session["otp"] = new_otp

        if not send_otp_email(jobseeker.email, new_otp, jobseeker.firstname):
            raise HTTPException(status_code=500, detail="Failed to send OTP email")

        return JSONResponse(content={"message": "OTP sent successfully"}, status_code=200)

    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@router.post("/forgot2")
def jobseeker_forgot2(request: Request, data: schemas.ForgotRequest2, db: Session = Depends(get_db)):

    password = data.password
    confirm_password = data.confirm_password

    if not password or not confirm_password:
        raise HTTPException(status_code=400, detail="Password and confirm_password are required")

    if password != confirm_password:
        return JSONResponse(content={'error': 'Passwords did not match'}, status_code=400)

    stored_email = request.session.get("email")
    if not stored_email:
        raise HTTPException(status_code=400, detail="Session expired or not found")

    jobseeker = db.query(models.JobSeeker).filter_by(email=stored_email).first()
    if not jobseeker:
        raise HTTPException(status_code=404, detail="Jobseeker not found")

    if bcrypt.verify(password, jobseeker.password):
        raise HTTPException(
            status_code=400,
            detail="New password cannot be the same as the current password"
        )

    jobseeker.password = bcrypt.hash(password)
    db.commit()

    del request.session["email"]

    return JSONResponse(content={"message": "Password updated successfully"}, status_code=200)

@router.post("/reset-password")
def jobseeker_reset_password(request: Request, data: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=400, detail="Token is missing or invalid format")

        token = auth_header.split(" ")[1]

        email = data.email
        old_password = data.old_password
        new_password = data.new_password
        confirm_password = data.confirm_password

        if new_password != confirm_password:
            raise HTTPException(status_code=400, detail="Passwords do not match")

        if old_password == new_password:
            raise HTTPException(status_code=400, detail="New password cannot be the same as the old password")

        jobseeker = db.query(models.JobSeeker).filter_by(email=email, token=token).first()
        if not jobseeker:
            raise HTTPException(status_code=404, detail="jobseeker not found or invalid token")

        if not bcrypt.verify(old_password, jobseeker.password):
            raise HTTPException(status_code=400, detail="Old password is incorrect")

        jobseeker.password = bcrypt.hash(new_password)
        db.commit()

        return {"success": True, "message": "Password has been reset successfully"}

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.post("/delete-account")
def jobseeker_delete_account(request: Request, request_data: schemas.DeleteAccountRequest, db: Session = Depends(get_db)):
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=400, detail="Token is missing or invalid format")

        token = auth_header.split(" ")[1]

        jobseeker = db.query(models.JobSeeker).filter_by(token=token).first()
        if not jobseeker:
            raise HTTPException(status_code=404, detail="Invalid token")

        if request_data.confirmation:
            db.delete(jobseeker)
            db.commit()
            return {"success": True, "message": "Account deleted successfully"}
        else:
            return {"success": False, "message": "Account deletion canceled by user"}

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
