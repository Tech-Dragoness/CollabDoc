import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Example: postgresql://docapp_user:password@localhost:5432/docapp
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql://docapp_user:docapp_pass@localhost:5432/docapp"
    )
    # Render/Heroku sometimes give "postgres://" — SQLAlchemy needs "postgresql://"
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgres://", "postgresql://", 1
        )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret-change-me")
    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER", os.path.join(os.path.dirname(__file__), "uploads")
    )
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB upload cap