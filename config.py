import os
from datetime import timedelta
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))


class Config:
    """Base configuration settings with Azure and local fallback support."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'campusconnect-secret-key-development-fallbacks-9823749283')
    QR_SECRET_KEY = os.environ.get('QR_SECRET_KEY', 'campusconnect-qr-signing-key-9283749823749')
    
    # Database Configuration: Azure SQL Database with SQLite fallback
    # Azure SQL format: mssql+pyodbc:///?odbc_connect=Driver={ODBC Driver 18 for SQL Server};Server=tcp:YOUR_SERVER.database.windows.net,1433;Database=YOUR_DB;Uid=YOUR_USER;Pwd=YOUR_PASSWORD;Encrypt=yes;TrustServerCertificate=no;
    azure_db_uri = os.environ.get('AZURE_SQL_DATABASE_URL') or os.environ.get('DATABASE_URL')
    if azure_db_uri:
        SQLALCHEMY_DATABASE_URI = azure_db_uri
    else:
        # Local SQLite database in instance folder
        os.makedirs(os.path.join(basedir, 'instance'), exist_ok=True)
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(basedir, 'instance', 'campusconnect.db')}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
    }

    # Session & Security Settings
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600

    # Uploads (Azure Blob Storage with local disk fallback)
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # Azure Blob Storage Configuration
    AZURE_STORAGE_CONNECTION_STRING = os.environ.get('AZURE_STORAGE_CONNECTION_STRING', None)
    AZURE_STORAGE_CONTAINER_NAME = os.environ.get('AZURE_STORAGE_CONTAINER_NAME', 'event-media')
    AZURE_STORAGE_ACCOUNT_NAME = os.environ.get('AZURE_STORAGE_ACCOUNT_NAME', None)

    # Power BI Configuration (Documentation and Embed URLs if configured)
    POWER_BI_EMBED_URL = os.environ.get('POWER_BI_EMBED_URL', None)
    POWER_BI_REPORT_ID = os.environ.get('POWER_BI_REPORT_ID', None)


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SERVER_NAME = 'localhost.localdomain'


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
