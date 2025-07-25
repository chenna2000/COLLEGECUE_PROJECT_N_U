from email.message import EmailMessage
import os
import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from login.database import EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD
from jinja2 import Environment, FileSystemLoader  # type: ignore
from job_portal.core.ws_manager import manager

from jinja2 import Environment, FileSystemLoader, select_autoescape # type: ignore




# def send_registration_email(name: str, email: str):
#     try:
#         env = Environment(loader=FileSystemLoader("login/templates"))
#         template = env.get_template("emails/registration_successful.html")
#         html_content = template.render(name=name, email=email)

#         msg = MIMEMultipart("alternative")
#         msg["Subject"] = "Registration Successful - Collegecue"
#         msg["From"] = EMAIL_HOST_USER
#         msg["To"] = email

#         mime_html = MIMEText(html_content, "html")
#         msg.attach(mime_html)

#         with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
#             server.starttls()
#             server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
#             server.send_message(msg)
#     except Exception as e:
#         raise Exception(f"Failed to send registration email: {str(e)}")

def send_registration_email(name: str, email: str):
    try:
        env = Environment(
            loader=FileSystemLoader("login/templates"),
            autoescape=select_autoescape(['html', 'xml'])
        )
        template = env.get_template("emails/registration_successful.html")
        html_content = template.render(name=name, email=email)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Registration Successful - Collegecue"
        msg["From"] = EMAIL_HOST_USER
        msg["To"] = email

        mime_html = MIMEText(html_content, "html")
        msg.attach(mime_html)

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        raise Exception(f"Failed to send registration email: {str(e)}")


def send_login_email(email: str, name: str):
    try:
        
        env = Environment(
            loader=FileSystemLoader("login/templates"),
            autoescape=select_autoescape(['html', 'xml'])
        )
        # env = Environment(loader=FileSystemLoader("login/templates"))
        template = env.get_template("emails/login_successful.html")
        html_content = template.render(email=email, name=name)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Login Successful"
        msg["From"] = EMAIL_HOST_USER
        msg["To"] = email

        mime_html = MIMEText(html_content, "html")
        msg.attach(mime_html)

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            server.send_message(msg)
        print(f"Email sent to {email}")
    except Exception as e:
        print(f"Email send failed: {e}")
        raise Exception(f"Failed to send login email: {str(e)}")


def send_otp_email(to_email: str, otp: str, name: str):
    try:
        env = Environment(loader=FileSystemLoader("login/templates"))
        template = env.get_template("login/otp_email.html")
        html_content = template.render(email=to_email, name=name, new_otp=otp)

        plain_message = f"""Dear {name},

For security purposes, please use the following One-Time Password (OTP) to complete your authentication:

OTP: {otp}

Please enter this OTP within the next 3 minutes to ensure successful access. If you did not request this OTP, please contact our support team immediately.

Thank you for your attention to this matter.

Best regards,
Collegecue Support Team
"""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Your One-Time Password (OTP) for Secure Access"
        msg["From"] = EMAIL_HOST_USER
        msg["To"] = to_email

        mime_text = MIMEText(plain_message, "plain")
        mime_html = MIMEText(html_content, "html")

        msg.attach(mime_text)
        msg.attach(mime_html)

        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            server.send_message(msg)

        print(f"Email sent to {to_email}")
        return True

    except Exception as e:
        print(f"Email send failed: {e}")
        raise Exception(f"Failed to send OTP email: {str(e)}")

def send_appliction_email(subject, body, recipient):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = os.getenv("EMAIL_HOST_USER")
    msg['To'] = recipient
    msg.set_content(body)

    try:
        with smtplib.SMTP(os.getenv("EMAIL_HOST"), int(os.getenv("EMAIL_PORT", 587))) as server:
            server.ehlo()
            if os.getenv("EMAIL_USE_TLS", "True").lower() == "true":
                server.starttls()
                server.ehlo()

            server.login(os.getenv("EMAIL_HOST_USER"), os.getenv("EMAIL_HOST_PASSWORD"))
            server.send_message(msg)
            print("Email sent successfully")
    except Exception as e:
        print(f"Email sending failed: {e}")


async def send_notification_to_group(group: str, message: str):
    await manager.send_to_group(group, message)

def generate_referral_code(length=8):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def send_email(to_email: str, subject: str, body: str):
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = os.getenv("EMAIL_HOST_USER")
    msg['To'] = to_email

    with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
        smtp.starttls()
        smtp.login(os.getenv("EMAIL_HOST_USER"), os.getenv("EMAIL_HOST_PASSWORD"))
        smtp.send_message(msg)
