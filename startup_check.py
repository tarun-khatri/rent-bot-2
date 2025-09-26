#!/usr/bin/env python3
"""
Startup Check Script for Real Estate Leasing Bot
Validates configuration and dependencies before starting the application.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Configure basic logging for startup check
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_environment_variables():
    """Check if all required environment variables are set"""
    logger.info("🔍 Checking environment variables...")
    
    required_vars = [
        # WhatsApp API
        'ACCESS_TOKEN',
        'APP_SECRET', 
        'PHONE_NUMBER_ID',
        'VERIFY_TOKEN',
        
        # Supabase
        'SUPABASE_URL',
        'SUPABASE_KEY',
        
        # Gemini AI
        'GEMINI_API_KEY',
        
 
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables:")
        for var in missing_vars:
            logger.error(f"   - {var}")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True


def check_dependencies():
    """Check if all required Python packages are installed"""
    logger.info("📦 Checking Python dependencies...")
    
    # Map package names to their import names
    required_packages = {
        'flask': 'flask',
        'python-dotenv': 'dotenv',
        'requests': 'requests',
        'google-genai': 'google.genai',
        'supabase': 'supabase',
        'apscheduler': 'apscheduler',
        'pytz': 'pytz',
        'flask-cors': 'flask_cors'
    }
    
    missing_packages = []
    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        logger.error(f"❌ Missing required packages:")
        for package in missing_packages:
            logger.error(f"   - {package}")
        logger.error("Run: pip install -r requirements.txt")
        return False
    
    logger.info("✅ All required packages are installed")
    return True


def test_database_connection():
    """Test Supabase database connection"""
    logger.info("🗄️ Testing database connection...")
    
    try:
        from supabase import create_client
        
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        
        if not url or not key:
            logger.error("❌ Supabase credentials not configured")
            return False
        
        client = create_client(url, key)
        
        # Test simple query
        response = client.table('leads').select('id').limit(1).execute()
        
        logger.info("✅ Database connection successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


def test_gemini_api():
    """Test Google Gemini API connection"""
    logger.info("🤖 Testing Gemini AI API...")
    
    try:
        from google import genai
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            logger.error("❌ Gemini API key not configured")
            return False
        
        # Initialize client with new API
        client = genai.Client(api_key=api_key)
        
        # Test simple generation
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents="שלום"
        )
        
        # Check response
        response_text = ""
        if hasattr(response, 'text') and response.text:
            response_text = response.text.strip()
        elif hasattr(response, 'candidates') and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'text') and part.text:
                            response_text += part.text
        
        if response_text:
            logger.info("✅ Gemini AI API connection successful")
            return True
        else:
            logger.error("❌ Gemini AI API returned empty response")
            return False
            
    except Exception as e:
        logger.error(f"❌ Gemini AI API test failed: {e}")
        return False


def check_port_availability(port=8080):
    """Check if the specified port is available"""
    logger.info(f"🔌 Checking port {port} availability...")
    
    import socket
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
        logger.info(f"✅ Port {port} is available")
        return True
    except OSError:
        logger.error(f"❌ Port {port} is already in use")
        return False


def validate_configuration():
    """Validate configuration values"""
    logger.info("⚙️ Validating configuration...")
    
    issues = []
    
    # Check timezone
    timezone = os.getenv('TIMEZONE', 'Asia/Jerusalem')
    try:
        import pytz
        pytz.timezone(timezone)
    except Exception:
        issues.append(f"Invalid timezone: {timezone}")
    
    # Check numeric configurations
    try:
        max_budget = int(os.getenv('MAX_BUDGET_THRESHOLD', '8000'))
        if max_budget <= 0:
            issues.append("MAX_BUDGET_THRESHOLD must be positive")
    except ValueError:
        issues.append("MAX_BUDGET_THRESHOLD must be a number")
    
    try:
        max_days = int(os.getenv('MAX_MOVE_IN_DAYS', '60'))
        if max_days <= 0:
            issues.append("MAX_MOVE_IN_DAYS must be positive")
    except ValueError:
        issues.append("MAX_MOVE_IN_DAYS must be a number")
    
    if issues:
        logger.error("❌ Configuration validation failed:")
        for issue in issues:
            logger.error(f"   - {issue}")
        return False
    
    logger.info("✅ Configuration validation passed")
    return True


def print_startup_summary():
    """Print startup summary and instructions"""
    logger.info("📋 Startup Summary:")
    logger.info("   • WhatsApp webhook URL: http://your-domain.com/webhook")
    logger.info("   • Calendly webhook URL: http://your-domain.com/webhook/calendly")
    logger.info("   • Health check: http://your-domain.com/health")
    logger.info("   • Metrics endpoint: http://your-domain.com/metrics")
    logger.info("")
    logger.info("🚀 Starting application...")


def main():
    """Main startup check function"""
    logger.info("=" * 60)
    logger.info("🏠 REAL ESTATE LEASING BOT - STARTUP CHECK")
    logger.info("=" * 60)
    
    # Load environment variables
    load_dotenv()
    
    checks = [
        ("Environment Variables", check_environment_variables),
        ("Python Dependencies", check_dependencies),
        ("Database Connection", test_database_connection),
        ("Gemini AI API", test_gemini_api),
        ("Port Availability", check_port_availability),
        ("Configuration", validate_configuration)
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        try:
            if not check_func():
                all_passed = False
        except Exception as e:
            logger.error(f"❌ {check_name} check failed with exception: {e}")
            all_passed = False
        
        logger.info("")  # Add spacing between checks
    
    if all_passed:
        logger.info("=" * 60)
        logger.info("✅ ALL CHECKS PASSED - SYSTEM READY!")
        logger.info("=" * 60)
        print_startup_summary()
        return True
    else:
        logger.error("=" * 60)
        logger.error("❌ STARTUP CHECKS FAILED")
        logger.error("=" * 60)
        logger.error("Please fix the issues above before starting the application.")
        return False


if __name__ == "__main__":
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
