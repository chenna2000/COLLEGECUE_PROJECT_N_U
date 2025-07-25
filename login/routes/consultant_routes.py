import datetime, gspread, uuid, secrets # type: ignore
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

def write_consultant_to_google_sheet(consultant_data):
    try:
        scopes = [
                  'https://www.googleapis.com/auth/spreadsheets',
                  'https://www.googleapis.com/auth/drive']

        credentials = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=scopes
        )
        client = gspread.authorize(credentials)

        sheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = sheet.get_worksheet(4)

        headers = worksheet.row_values(1)
        try:
            email_index = headers.index('official_email')
        except ValueError:
            raise ValueError("No 'official_email' column found in Sheet2")

        email_column = worksheet.col_values(email_index + 1)[1:]

        if any(email.lower() == consultant_data['official_email'].lower() for email in email_column):
            return

        today_date = datetime.date.today().strftime('%Y-%m-%d')

        new_row = [
            consultant_data['consultant_name'],
            consultant_data['official_email'],
            consultant_data['country_code'],
            consultant_data['mobile_number'],
            consultant_data['designation'],
            consultant_data['password'],
            consultant_data['linkedin_profile'],
            consultant_data['consultant_person_name'],
            consultant_data['agreed_to_terms'],
            today_date
        ]

        worksheet.append_row(new_row)

    except Exception as e:
        raise RuntimeError(f"Failed to write consultant data to Google Sheet: {str(e)}")

@router.post("/register")
def register_consultant(consultant: schemas.ConsultantCreate, db: Session = Depends(get_db)):
    print("Register function called", flush=True)
    logger.info("Processing registration logic")

    errors = {}

    try:
        existing_consultant = db.query(models.Consultant).filter_by(official_email=consultant.official_email).first()
        if existing_consultant:
            if existing_consultant.consultant_name != consultant.consultant_name:
                errors['official_email'] = 'Email already registered with different consultant name'
            else:
                errors['official_email'] = 'Email already registered'

        if db.query(models.Consultant).filter_by(mobile_number=consultant.mobile_number).first():
            errors['mobile_number'] = 'Mobile number already in use'

        email_username = consultant.official_email.split('@')[0]
        if not has_two_unique_chars(email_username):
            errors['official_email'] = 'Email username must contain at least 2 unique characters'

        if consultant.password != consultant.confirm_password:
            errors['password'] = 'Passwords do not match'

        if errors:
            raise HTTPException(status_code=400, detail=errors)

        hashed_password = bcrypt.hash(consultant.password)

        db_consultant = models.Consultant(
            consultant_name=consultant.consultant_name,
            official_email=consultant.official_email,
            country_code=consultant.country_code,
            mobile_number=consultant.mobile_number,
            designation=consultant.designation,
            password=hashed_password,
            confirm_password=hashed_password,
            linkedin_profile=consultant.linkedin_profile,
            consultant_person_name=consultant.consultant_person_name,
            agreed_to_terms=consultant.agreed_to_terms,
        )

        db.add(db_consultant)
        db.commit()
        db.refresh(db_consultant)

        consultant_data = {
            'consultant_name': consultant.consultant_name,
            'official_email': consultant.official_email,
            'country_code': consultant.country_code,
            'mobile_number': consultant.mobile_number,
            'designation': consultant.designation,
            'password':hashed_password,
            'linkedin_profile': consultant.linkedin_profile,
            'consultant_person_name': consultant.consultant_person_name,
            'agreed_to_terms':consultant.agreed_to_terms
        }

        write_consultant_to_google_sheet(consultant_data)

        try:
            send_registration_email(consultant.consultant_name, consultant.official_email)
            print("Sending email...", flush=True)
            logger.info("Email sent successfully")
        except HTTPException as e:
            logger.error(f"Email failed: {e}")
            raise HTTPException(status_code=500, detail=f"Email sending failed: {str(e)}")

        return JSONResponse({'success': True, 'message': 'Registration successful'})

    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={'success': False, 'message': 'An unexpected error occurred', 'detail': str(e)}
        )

@router.post("/login")
def login_consultant(consultant_data: schemas.ConsultantLogin, db: Session = Depends(get_db)):
    try:
        consultant = db.query(models.Consultant).filter_by(official_email=consultant_data.official_email).first()
        
        if not consultant:
            raise HTTPException(status_code=404, detail="Consultant not found")

        if not bcrypt.verify(consultant_data.password, consultant.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = generate_unique_token()
        consultant.token = token
        consultant.is_online = True

        status_record = db.query(models.OnlineStatus).filter_by(email=consultant.official_email).first()
        if status_record:
            status_record.is_online = True
        else:
            db.add(models.OnlineStatus(email=consultant.official_email, is_online=True))

        db.commit()

        try:
            send_login_email(consultant.official_email, consultant.consultant_name)
            print("Sending email...", flush=True)
            logger.info("Email sent successfully")
        except HTTPException as e:
            logger.error(f"Email failed: {e}")
            raise HTTPException(status_code=500, detail=f"Email sending failed: {str(e)}")

        return {
            "success": True,
            "message": f"Login successful for {consultant.official_email}",
            "token": token,
            "official_email": consultant.official_email,
            "id": consultant.id,
            "mobile_number": consultant.mobile_number,
            "consultant_name": consultant.consultant_name,
            "model": "Consultant"
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "An unexpected error occurred", "detail": str(e)}
        )

@router.post("/logout")
async def consultant_logout(request: Request, db: Session = Depends(get_db)):
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=400, detail="Token is missing or invalid format")

        token = auth_header.split(" ")[1]

        consultant = db.query(models.Consultant).filter_by(token=token).first()
        if not consultant:
            raise HTTPException(status_code=404, detail="Invalid token")

        consultant.token = None
        consultant.is_online = False
        db.commit()

        db.query(models.OnlineStatus).filter_by(email=consultant.official_email).update({"is_online": False})
        db.commit()

        return JSONResponse({"success": True, "message": "Logout successful"}, status_code=200)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@router.post("/forgot")
def consultant_forgot_password(request: Request, data: schemas.ForgotRequest, db: Session = Depends(get_db)):
    try:
        consultant = db.query(models.Consultant).filter_by(official_email=data.email).first()
        if not consultant:
            raise HTTPException(status_code=404, detail="Email does not exist")

        new_otp = ''.join([str(secrets.randbelow(10)) for _ in range(4)])

        request.session['otp'] = new_otp
        request.session['email'] = data.email
        
        consultant_email = models.Forgot(
           email=data.email,

       )

        db.add(consultant_email)
        db.commit()
        db.refresh(consultant_email)

        try:
            send_otp_email(consultant.official_email, new_otp, consultant.consultant_name)
            print("Sending email...", flush=True)
            logger.info("Email sent successfully")
        except HTTPException as e:
            logger.error(f"Email failed: {e}")
            raise HTTPException(status_code=500, detail=f"Email sending failed: {str(e)}")

        return JSONResponse(content={'message': 'OTP sent successfully'}, status_code=200)

    except Exception as e:
        return JSONResponse(content={'success': False, 'error': str(e)}, status_code=500)

@router.post("/verify")
def consultant_verify_otp(request: Request, data: schemas.VerifySchema, db: Session = Depends(get_db)):
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
def consultant_resend_otp(request: Request, db: Session = Depends(get_db)):
    try:
        stored_email = request.session.get("email")
        if not stored_email:
            raise HTTPException(status_code=400, detail="Session data not found")

        consultant = db.query(models.Consultant).filter_by(official_email=stored_email).first()
        if not consultant:
            raise HTTPException(status_code=404, detail="Consultant not found")

        new_otp = ''.join([str(secrets.randbelow(10)) for _ in range(4)])

        request.session["otp"] = new_otp

        if not send_otp_email(consultant.official_email, new_otp, consultant.consultant_name):
            raise HTTPException(status_code=500, detail="Failed to send OTP email")

        return JSONResponse(content={"message": "OTP sent successfully"}, status_code=200)

    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

@router.post("/forgot2")
def consultant_forgot2(request: Request, data: schemas.ForgotRequest2, db: Session = Depends(get_db)):
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

        consultant = db.query(models.Consultant).filter_by(official_email=stored_email).first()
        if not consultant:
            raise HTTPException(status_code=404, detail="Consultant not found")

        if bcrypt.verify(password, consultant.password):
            raise HTTPException(
                status_code=400,
                detail="New password cannot be the same as the current password"
            )

        consultant.password = bcrypt.hash(password)
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
def consultant_reset_password(request: Request, data: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
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

        consultant = db.query(models.Consultant).filter_by(official_email=email, token=token).first()
        if not consultant:
            raise HTTPException(status_code=404, detail="consultant not found or invalid token")

        if not bcrypt.verify(old_password, consultant.password):
            raise HTTPException(status_code=400, detail="Old password is incorrect")

        consultant.password = bcrypt.hash(new_password)
        db.commit()

        return {"success": True, "message": "Password has been reset successfully"}

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@router.post("/delete-account")
def consultant_delete_account(request: Request, request_data: schemas.DeleteAccountRequest, db: Session = Depends(get_db)):
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=400, detail="Token is missing or invalid format")

        token = auth_header.split(" ")[1]

        consultant = db.query(models.Consultant).filter_by(token=token).first()
        if not consultant:
            raise HTTPException(status_code=404, detail="Invalid token")

        if request_data.confirmation:
            db.delete(consultant)
            db.commit()
            return {"success": True, "message": "Account deleted successfully"}
        else:
            return {"success": False, "message": "Account deletion canceled by user"}

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)