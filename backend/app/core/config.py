"""Application configuration module."""
import os
from pathlib import Path
from typing import Optional

try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for older pydantic versions
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "Certificate Generation Backend"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # Paths (can be overridden by env vars)
    BASE_DIR: Path = Path(__file__).parent.parent.parent
    
    # Path settings from environment or defaults
    TEMPLATE_PATH: Path = Path(os.getenv("TEMPLATE_PATH", str(BASE_DIR / "data" / "template.png")))
    FIELDS_CONFIG_PATH: Path = Path(os.getenv("FIELDS_CONFIG_PATH", str(BASE_DIR / "fields_config.json")))
    FONTS_DIR: Path = Path(os.getenv("FONTS_DIR", str(BASE_DIR / "fonts")))
    
    # Derived paths
    DATA_DIR: Path = TEMPLATE_PATH.parent if TEMPLATE_PATH.name == "template.png" else BASE_DIR / "data"
    LOGS_DIR: Path = BASE_DIR / "logs"
    
    # Template settings
    MAX_TEMPLATE_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # SMTP Email settings (for sending to students)
    SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "465"))
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER")
    SMTP_PASS: Optional[str] = os.getenv("SMTP_PASS")
    SMTP_USE_SSL: bool = os.getenv("SMTP_USE_SSL", "true").lower() == "true"
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "False").lower() == "true"
    
    # Email defaults
    EMAIL_FROM: Optional[str] = os.getenv("EMAIL_FROM")
    ADMIN_RESULTS_EMAIL: Optional[str] = os.getenv("ADMIN_RESULTS_EMAIL")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Frontend URL - SINGLE SOURCE OF TRUTH (SSOT)
    # This is the ONLY place where the frontend URL should be defined
    # Set via environment variable FRONTEND_URL
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "https://jabanes.github.io/Auto-Certificate-Frontend/")
    
    # CORS origins - can be explicitly set, otherwise derived from FRONTEND_URL (SSOT)
    # If CORS_ORIGINS env var is set, use it (comma-separated list)
    # Otherwise, CORS will use FRONTEND_URL automatically in get_cors_origins()
    CORS_ORIGINS: Optional[str] = os.getenv("CORS_ORIGINS")
    
    def get_cors_origins(self) -> list[str]:
        """
        Get CORS origins as a list.
        
        SSOT Logic:
        - If CORS_ORIGINS env var is explicitly set, use it (comma-separated)
        - Otherwise, use FRONTEND_URL (SSOT) as the single origin
        """
        # If CORS_ORIGINS was explicitly set, use it
        if self.CORS_ORIGINS:
            origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        else:
            # Otherwise, use FRONTEND_URL (SSOT) as the single origin
            origins = [self.FRONTEND_URL] if self.FRONTEND_URL else []
        
        # Remove duplicates while preserving order
        seen = set()
        unique_origins = []
        for origin in origins:
            if origin and origin not in seen:
                seen.add(origin)
                unique_origins.append(origin)
        return unique_origins
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        # Ensure template path parent exists
        self.TEMPLATE_PATH.parent.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()

