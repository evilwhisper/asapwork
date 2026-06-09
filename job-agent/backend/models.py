from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class UserProfile(Base):
    __tablename__ = "user_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(Text)
    target_roles: Mapped[str | None] = mapped_column(Text)           # JSON array
    target_salary_min: Mapped[int | None] = mapped_column(Integer)
    target_salary_max: Mapped[int | None] = mapped_column(Integer)
    work_types: Mapped[str | None] = mapped_column(Text)             # JSON array
    industries: Mapped[str | None] = mapped_column(Text)             # JSON array
    blacklist_keywords: Mapped[str | None] = mapped_column(Text)     # JSON array
    whitelist_companies: Mapped[str | None] = mapped_column(Text)    # JSON array
    tone_preference: Mapped[str] = mapped_column(Text, default="professional")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(Text)                         # "resume" | "cover_letter"
    filename: Mapped[str] = mapped_column(Text)
    filepath: Mapped[str] = mapped_column(Text)
    parsed_text: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ApiSettings(Base):
    __tablename__ = "api_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(Text)                     # "openai" | "anthropic" | "google" | "ollama" | "custom"
    api_key_enc: Mapped[str | None] = mapped_column(Text)
    base_url: Mapped[str | None] = mapped_column(Text)
    model_name: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_scorer_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    smtp_host: Mapped[str | None] = mapped_column(Text)
    smtp_port: Mapped[int | None] = mapped_column(Integer)
    smtp_user: Mapped[str | None] = mapped_column(Text)
    smtp_pass_enc: Mapped[str | None] = mapped_column(Text)
    notify_email: Mapped[str | None] = mapped_column(Text)
    max_submissions_per_hour: Mapped[int] = mapped_column(Integer, default=10)
    min_gap_minutes: Mapped[int] = mapped_column(Integer, default=3)
    auto_submit: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_approve_threshold: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ScraperConfig(Base):
    __tablename__ = "scraper_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(Text, unique=True)          # "seek" | "indeed_au" | "linkedin_au" | "jora"
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    keywords: Mapped[str | None] = mapped_column(Text)              # JSON array
    location: Mapped[str | None] = mapped_column(Text)
    linkedin_session_cookie: Mapped[str | None] = mapped_column(Text)  # encrypted
    schedule_hours: Mapped[int] = mapped_column(Integer, default=2)
    last_run: Mapped[datetime | None] = mapped_column(DateTime)


class JobListing(Base):
    __tablename__ = "job_listings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(Text)
    external_id: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    company: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(Text)
    work_type: Mapped[str | None] = mapped_column(Text)
    salary_text: Mapped[str | None] = mapped_column(Text)
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    match_score: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(Text, default="new")        # new | queued | skipped | applied

    applications: Mapped[list["Application"]] = relationship("Application", back_populates="job")


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("job_listings.id"))
    cover_letter: Mapped[str | None] = mapped_column(Text)
    resume_version: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="pending")    # pending | approved | rejected | submitted | failed
    submission_method: Mapped[str | None] = mapped_column(Text)     # email | seek_form | linkedin_easy_apply
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text)

    job: Mapped["JobListing"] = relationship("JobListing", back_populates="applications")
