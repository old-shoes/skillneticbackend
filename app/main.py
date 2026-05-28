from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.modules.admin_auth.router import router as admin_auth_router
from app.modules.admin_dashboard.router import router as admin_dashboard_router
from app.modules.admin_help_posts.router import router as admin_help_posts_router
from app.modules.admin_logs.router import router as admin_logs_router
from app.modules.admin_notifications.router import router as admin_notifications_router
from app.modules.admin_points.router import router as admin_points_router
from app.modules.admin_skills.router import router as admin_skills_router
from app.modules.auth.router import router as auth_router
from app.modules.admin_tutorials.router import router as admin_tutorials_router
from app.modules.admin_users.router import router as admin_users_router
from app.modules.categories.router import router as categories_router
from app.modules.homepage.router import router as homepage_router
from app.modules.me.router import router as me_router
from app.modules.skills.router import router as skills_router
from app.modules.skill_submissions.router import admin_router as admin_skill_submissions_router
from app.modules.skill_submissions.router import user_router as skill_submissions_router
from app.modules.track.router import router as track_router
from app.modules.tutorials.router import router as tutorials_router
from app.modules.upload.router import router as upload_router


app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(homepage_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(me_router, prefix="/api/v1")
app.include_router(categories_router, prefix="/api/v1")
app.include_router(skills_router, prefix="/api/v1")
app.include_router(skill_submissions_router, prefix="/api/v1")
app.include_router(tutorials_router, prefix="/api/v1")
app.include_router(track_router, prefix="/api/v1")
app.include_router(upload_router, prefix="/api/v1")
app.include_router(admin_auth_router, prefix="/api/admin/v1/auth")
app.include_router(admin_dashboard_router, prefix="/api/admin/v1/dashboard")
app.include_router(admin_skills_router, prefix="/api/admin/v1/skills")
app.include_router(admin_users_router, prefix="/api/admin/v1/users")
app.include_router(admin_points_router, prefix="/api/admin/v1/points")
app.include_router(admin_help_posts_router, prefix="/api/admin/v1/help-posts")
app.include_router(admin_notifications_router, prefix="/api/admin/v1")
app.include_router(admin_logs_router, prefix="/api/admin/v1")
app.include_router(admin_tutorials_router, prefix="/api/admin/v1")
app.include_router(admin_skill_submissions_router, prefix="/api/admin/v1")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
