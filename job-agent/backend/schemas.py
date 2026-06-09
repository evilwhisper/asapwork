from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserProfileSchema(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    target_roles: Optional[list[str]] = None
    target_salary_min: Optional[int] = None
    target_salary_max: Optional[int] = None
    work_types: Optional[list[str]] = None
    industries: Optional[list[str]] = None
    blacklist_keywords: Optional[list[str]] = None
    whitelist_companies: Optional[list[str]] = None
    tone_preference: str = "professional"

    class Config:
        from_attributes = True


class DocumentSchema(BaseModel):
    id: Optional[int] = None
    type: str
    filename: str
    filepath: str
    parsed_text: Optional[str] = None
    is_active: bool = True
    uploaded_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApiSettingsSchema(BaseModel):
    id: Optional[int] = None
    provider: str
    api_key: Optional[str] = None          # plaintext on write, masked on read
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    is_active: bool = True
    ai_scorer_enabled: bool = False
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_pass: Optional[str] = None
    notify_email: Optional[str] = None
    max_submissions_per_hour: int = 10
    min_gap_minutes: int = 3
    auto_submit: bool = False
    auto_approve_threshold: Optional[float] = None

    class Config:
        from_attributes = True


class ScraperConfigSchema(BaseModel):
    id: Optional[int] = None
    source: str
    enabled: bool = False
    keywords: Optional[list[str]] = None
    location: Optional[str] = None
    linkedin_session_cookie: Optional[str] = None
    schedule_hours: int = 2
    last_run: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobListingSchema(BaseModel):
    id: Optional[int] = None
    source: str
    external_id: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    work_type: Optional[str] = None
    salary_text: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    description: Optional[str] = None
    url: Optional[str] = None
    posted_at: Optional[datetime] = None
    scraped_at: Optional[datetime] = None
    match_score: Optional[float] = None
    status: str = "new"

    class Config:
        from_attributes = True


class ApplicationSchema(BaseModel):
    id: Optional[int] = None
    job_id: int
    cover_letter: Optional[str] = None
    resume_version: Optional[str] = None
    status: str = "pending"
    submission_method: Optional[str] = None
    submitted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    notes: Optional[str] = None
    job: Optional[JobListingSchema] = None

    class Config:
        from_attributes = True


class HealthResponse(BaseModel):
    status: str
    mode: str
    version: str
    db_connected: bool


class TestConnectionResponse(BaseModel):
    success: bool
    message: str
    latency_ms: int
