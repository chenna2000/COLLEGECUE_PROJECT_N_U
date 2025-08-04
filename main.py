from fastapi import FastAPI # type: ignore
from login.routes import answer_routes, college_routes, company_routes, admission_review_routes, consultant_routes, contacts_routes, event_routes, expert_routes, get_all_answers_routes, get_questions_routes, jobseeker_routes, new_user_routes, question_routes, subscriber1_routes, subscriber_routes
from login.database import engine, Base
from starlette.middleware.sessions import SessionMiddleware # type: ignore
import secrets
from job_portal.routes.company import router as company
from job_portal.routes.college import router as college
from job_portal.routes.student import router as student
from job_portal.routes.jobseeker import router as jobseeker
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from job_portal.routes.websocket_routes import router as ws_router

Base.metadata.create_all(bind=engine)

app = FastAPI()

SECRET_KEY = secrets.token_hex(32)

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    same_site="none",
    https_only=True
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY) 

app.include_router(company_routes.router, prefix="/company")
app.include_router(new_user_routes.router, prefix="/new-user")
app.include_router(jobseeker_routes.router, prefix="/jobseeker")
app.include_router(college_routes.router, prefix="/college")
app.include_router(consultant_routes.router, prefix="/consultant")
app.include_router(contacts_routes.router, prefix="")
app.include_router(question_routes.router, prefix="")
app.include_router(answer_routes.router, prefix="")
app.include_router(get_questions_routes.router, prefix="")
app.include_router(get_all_answers_routes.router, prefix="")
app.include_router(subscriber_routes.router, prefix="")
app.include_router(subscriber1_routes.router, prefix="")
app.include_router(admission_review_routes.router, prefix="")
app.include_router(expert_routes.router, prefix="")
app.include_router(event_routes.router, prefix="")

app.include_router(company, prefix="/company", tags=["Company Jobs"])
app.include_router(college, prefix="/college", tags=["College Jobs"])
app.include_router(student, prefix="/student", tags=["student"])
app.include_router(jobseeker, prefix="/jobseeker", tags=["jobseeker"])

app.include_router(ws_router)
