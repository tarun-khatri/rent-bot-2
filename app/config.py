import sys
import os
from dotenv import load_dotenv
import logging
import pytz
from datetime import datetime


def load_configurations(app):
    """Load all configuration variables from environment"""
    load_dotenv()
    
    # WhatsApp API Configuration
    app.config["ACCESS_TOKEN"] = os.getenv("ACCESS_TOKEN")
    app.config["YOUR_PHONE_NUMBER"] = os.getenv("YOUR_PHONE_NUMBER")
    app.config["APP_ID"] = os.getenv("APP_ID")
    app.config["APP_SECRET"] = os.getenv("APP_SECRET")
    app.config["RECIPIENT_WAID"] = os.getenv("RECIPIENT_WAID")
    app.config["VERSION"] = os.getenv("VERSION", "v18.0")
    app.config["PHONE_NUMBER_ID"] = os.getenv("PHONE_NUMBER_ID")
    app.config["VERIFY_TOKEN"] = os.getenv("VERIFY_TOKEN")
    
    # Supabase Configuration
    app.config["SUPABASE_URL"] = os.getenv("SUPABASE_URL")
    app.config["SUPABASE_KEY"] = os.getenv("SUPABASE_KEY")
    
    # Gemini AI Configuration
    app.config["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY")
    app.config["GEMINI_MODEL"] = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    # Calendly Configuration
    app.config["CALENDLY_ACCESS_TOKEN"] = os.getenv("CALENDLY_ACCESS_TOKEN")
    app.config["CALENDLY_ORGANIZATION_URI"] = os.getenv("CALENDLY_ORGANIZATION_URI")
    app.config["CALENDLY_MORNING_LINK"] = os.getenv("CALENDLY_MORNING_LINK")
    app.config["CALENDLY_AFTERNOON_LINK"] = os.getenv("CALENDLY_AFTERNOON_LINK")
    app.config["CALENDLY_EVENING_LINK"] = os.getenv("CALENDLY_EVENING_LINK")
    
    # Application Settings
    app.config["FLASK_ENV"] = os.getenv("FLASK_ENV", "production")
    app.config["FLASK_DEBUG"] = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.config["LOG_LEVEL"] = os.getenv("LOG_LEVEL", "INFO")
    app.config["TIMEZONE"] = os.getenv("TIMEZONE", "Asia/Jerusalem")
    
    # Business Rules Configuration
    app.config["MAX_BUDGET_THRESHOLD"] = int(os.getenv("MAX_BUDGET_THRESHOLD", "8000"))
    app.config["MAX_MOVE_IN_DAYS"] = int(os.getenv("MAX_MOVE_IN_DAYS", "60"))
    app.config["ABANDONED_LEAD_HOURS"] = int(os.getenv("ABANDONED_LEAD_HOURS", "4"))
    app.config["MAX_PROPERTY_RECOMMENDATIONS"] = int(os.getenv("MAX_PROPERTY_RECOMMENDATIONS", "3"))
    
    # Validate critical configurations
    _validate_critical_config(app.config)


def _validate_critical_config(config):
    """Validate that critical configuration variables are set"""
    critical_vars = [
        "ACCESS_TOKEN", "APP_SECRET", "PHONE_NUMBER_ID", "VERIFY_TOKEN",
        "SUPABASE_URL", "SUPABASE_KEY", "GEMINI_API_KEY"
    ]
    
    missing_vars = []
    for var in critical_vars:
        if not config.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing critical configuration variables: {', '.join(missing_vars)}")


def configure_logging():
    """Configure production-level logging with detailed format"""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Create detailed formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Set specific logger levels
    logging.getLogger("supabase").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    logging.info(f"Logging configured with level: {log_level}")


def get_timezone():
    """Get the configured timezone"""
    return pytz.timezone(os.getenv("TIMEZONE", "Asia/Jerusalem"))


def get_current_time():
    """Get current time in the configured timezone"""
    tz = get_timezone()
    return datetime.now(tz)
