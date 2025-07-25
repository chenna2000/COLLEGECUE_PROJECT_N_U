import datetime, secrets, gspread, uuid # type: ignore
from fastapi import APIRouter, Depends, HTTPException, Request # type: ignore
from sqlalchemy.orm import Session # type: ignore
from login import models, schemas
from login.database import SessionLocal
from passlib.hash import bcrypt # type: ignore
from fastapi.responses import JSONResponse # type: ignore
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


def write_data_to_google_sheet(college_data: dict, sheet_name: str):
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

        sheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = sheet.worksheet(sheet_name)

        headers = worksheet.row_values(1)
        try:
            email_index = headers.index('official_email')
        except ValueError:
            raise ValueError(f"No 'official_email' column found in '{sheet_name}'")

        existing_emails = [
            email.lower() for email in worksheet.col_values(email_index + 1)[1:]
        ]

        if college_data['official_email'].lower() in existing_emails:
            return 

        today_date = datetime.date.today().strftime('%Y-%m-%d')

        new_row = [
            college_data.get('university_name', ''),
            college_data.get('official_email', ''),
            college_data.get('country_code', ''),
            college_data.get('mobile_number', ''),
            college_data.get('designation', ''),
            college_data.get('password', ''),
            college_data.get('linkedin_profile', ''),
            college_data.get('college_person_name', ''),
            college_data.get('agreed_to_terms', ''),
            today_date
        ]

        worksheet.append_row(new_row)

    except Exception as e:
        raise RuntimeError(f"Failed to write data to Google Sheet '{sheet_name}': {str(e)}")

## College
@router.post("/register")
def register_college(college: schemas.UniversityInChargeCreate, db: Session = Depends(get_db)):
    errors = {}

    try:
        existing = db.query(models.UniversityInCharge).filter_by(official_email=college.official_email).first()
        if existing:
            if existing.university_name != college.university_name:
                errors['official_email'] = 'Email already registered with different university name'
            else:
                errors['official_email'] = 'Email already registered'

        if db.query(models.UniversityInCharge).filter_by(mobile_number=college.mobile_number).first():
            errors['mobile_number'] = 'Mobile number already in use'

        email_username = college.official_email.split('@')[0]
        if not has_two_unique_chars(email_username):
            errors['official_email'] = 'Email username must contain at least 2 unique characters'

        if college.password != college.confirm_password:
            errors['password'] = 'Passwords do not match'

        if errors:
            raise HTTPException(status_code=400, detail=errors)

        hashed_password = bcrypt.hash(college.password)

        db_college = models.UniversityInCharge(
            university_name=college.university_name,
            official_email=college.official_email,
            country_code=college.country_code,
            mobile_number=college.mobile_number,
            designation=college.designation,
            password=hashed_password,
            confirm_password=hashed_password,
            linkedin_profile=college.linkedin_profile,
            college_person_name=college.college_person_name,
            agreed_to_terms=college.agreed_to_terms,
            clg_id=college.clg_id
        )
        db.add(db_college)
        db.commit()
        db.refresh(db_college)

        college_data = {
            'university_name': college.university_name,
            'official_email': college.official_email,
            'country_code': college.country_code,
            'mobile_number': college.mobile_number,
            'designation': college.designation,
            'password': hashed_password,
            'linkedin_profile': college.linkedin_profile,
            'college_person_name': college.college_person_name,
            'agreed_to_terms': college.agreed_to_terms
        }

        try:
            write_data_to_google_sheet(college_data, sheet_name='Sheet3')
        except Exception as e:
            logger.error(f"Failed to write to Google Sheet: {e}")

        try:
            send_registration_email(college.university_name, college.official_email)
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise HTTPException(status_code=500, detail="Email sending failed")

        if not college.clg_id or college.clg_id == "None":
            unregistered_college = models.Unregister_Colleges(
                university_name=college.university_name,
                official_email=college.official_email,
                country_code=college.country_code,
                mobile_number=college.mobile_number,
                password=hashed_password,
                linkedin_profile=college.linkedin_profile,
                college_person_name=college.college_person_name,
                agreed_to_terms=college.agreed_to_terms
            )
            db.add(unregistered_college)
            db.commit()
            db.refresh(unregistered_college)

            try:
                write_data_to_google_sheet(college_data, sheet_name='Sheet6')
            except Exception as e:
                logger.error(f"Failed to write unregistered college to Google Sheet: {e}")

        return JSONResponse({'success': True, 'message': 'Registration successful'})

    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"error": "An unexpected error occurred", "detail": str(e)}
        )

@router.post("/login")
def login_college(college_data: schemas.UniversityInChargeLogin, db: Session = Depends(get_db)):
    try:
        college = db.query(models.UniversityInCharge).filter_by(official_email=college_data.official_email).first()

        if not college:
            raise HTTPException(status_code=404, detail="College not found")

        if not bcrypt.verify(college_data.password, college.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = generate_unique_token()
        college.token = token
        college.is_online = True

        status_record = db.query(models.OnlineStatus).filter_by(email=college.official_email).first()
        if status_record:
            status_record.is_online = True
        else:
            db.add(models.OnlineStatus(email=college.official_email, is_online=True))

        db.commit()

        try:
            send_login_email(college.official_email, college.university_name)
            print("Sending email...", flush=True)
            logger.info("Email sent successfully")
        except HTTPException as e:
            logger.error(f"Email failed: {e}")
            raise HTTPException(status_code=500, detail=f"Email sending failed: {str(e)}")

        return {
            "success": True,
            "message": f"Login successful for {college.official_email}",
            "token": token,
            "official_email": college.official_email,
            "id": college.id,
            "mobile_number": college.mobile_number,
            "university_name": college.university_name,
            "model": "UniversityInCharge"
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"error": "An unexpected error occurred", "detail": str(e)}
        )

@router.post("/logout")
async def college_logout(request: Request, db: Session = Depends(get_db)):
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=400, detail="Token is missing or invalid format")

        token = auth_header.split(" ")[1]

        college = db.query(models.UniversityInCharge).filter_by(token=token).first()
        if not college:
            raise HTTPException(status_code=404, detail="Invalid token")

        college.token = None
        college.is_online = False
        db.commit()

        db.query(models.OnlineStatus).filter_by(email=college.official_email).update({"is_online": False})
        db.commit()

        return JSONResponse({"success": True, "message": "Logout successful"}, status_code=200)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@router.post("/forgot")
def college_forgot_password(request: Request, data: schemas.ForgotRequest, db: Session = Depends(get_db)):
    try:
        college = db.query(models.UniversityInCharge).filter_by(official_email=data.email).first()
        if not college:
            raise HTTPException(status_code=404, detail="Email does not exist")

        new_otp = ''.join([str(secrets.randbelow(10)) for _ in range(4)])

        request.session['otp'] = new_otp
        request.session['email'] = data.email

        college_email = models.Forgot(
           email=data.email,
       
       )

        db.add(college_email)
        db.commit()
        db.refresh(college_email)

        try:
            send_otp_email(college.official_email, new_otp, college.university_name)
            print("Sending email...", flush=True)
            logger.info("Email sent successfully")
        except HTTPException as e:
            logger.error(f"Email failed: {e}")
            raise HTTPException(status_code=500, detail=f"Email sending failed: {str(e)}")

        return JSONResponse(content={'message': 'OTP sent successfully'}, status_code=200)

    except Exception as e:
        return JSONResponse(content={'success': False, 'error': str(e)}, status_code=500)

@router.post("/verify")
def college_verify_otp(request: Request, data: schemas.VerifySchema, db: Session = Depends(get_db)):
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
def college_resend_otp(request: Request, db: Session = Depends(get_db)):
    try:
        stored_email = request.session.get("email")
        if not stored_email:
            raise HTTPException(status_code=400, detail="Session data not found")

        college = db.query(models.UniversityInCharge).filter_by(official_email=stored_email).first()
        if not college:
            raise HTTPException(status_code=404, detail="College not found")

        new_otp = ''.join([str(secrets.randbelow(10)) for _ in range(4)])

        request.session["otp"] = new_otp

        if not send_otp_email(college.official_email, new_otp, college.university_name):
            raise HTTPException(status_code=500, detail="Failed to send OTP email")

        return JSONResponse(content={"message": "OTP sent successfully"}, status_code=200)

    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@router.post("/forgot2")
def college_forgot2(request: Request, data: schemas.ForgotRequest2, db: Session = Depends(get_db)):
    try:
        password = data.password
        confirm_password = data.confirm_password

        if not password or not confirm_password:
            raise HTTPException(status_code=400, detail="Password and confirm_password are required")

        if password != confirm_password:
            return JSONResponse(content={'error': 'Passwords did not match'}, status_code=400)

        stored_email = request.session.get("email")
        if not stored_email:
            raise HTTPException(status_code=400, detail="Session expired or not found")

        college = db.query(models.UniversityInCharge).filter_by(official_email=stored_email).first()
        if not college:
            raise HTTPException(status_code=404, detail="College not found")

        if bcrypt.verify(password, college.password):
            raise HTTPException(
                status_code=400,
                detail="New password cannot be the same as the current password"
            )

        college.password = bcrypt.hash(password)
        db.commit()

        del request.session["email"]

        return JSONResponse(content={"message": "Password updated successfully"}, status_code=200)

    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"error": "An unexpected error occurred", "detail": str(e)}
        )

@router.post("/reset-password")
def college_reset_password(request: Request, data: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
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

        college = db.query(models.UniversityInCharge).filter_by(official_email=email, token=token).first()
        if not college:
            raise HTTPException(status_code=404, detail="college not found or invalid token")

        if not bcrypt.verify(old_password, college.password):
            raise HTTPException(status_code=400, detail="Old password is incorrect")

        college.password = bcrypt.hash(new_password)
        db.commit()

        return {"success": True, "message": "Password has been reset successfully"}

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.post("/delete-account")
def college_delete_account(request: Request, request_data: schemas.DeleteAccountRequest, db: Session = Depends(get_db)):
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=400, detail="Token is missing or invalid format")

        token = auth_header.split(" ")[1]

        college = db.query(models.UniversityInCharge).filter_by(token=token).first()
        if not college:
            raise HTTPException(status_code=404, detail="Invalid token")

        if request_data.confirmation:
            db.delete(college)
            db.commit()
            return {"success": True, "message": "Account deleted successfully"}
        else:
            return {"success": False, "message": "Account deletion canceled by user"}

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
