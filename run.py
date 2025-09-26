import logging
import sys
import os

from app import create_app

# Set up logging for the main application
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Main application entry point"""
    logger.info("🏠 Starting Real Estate Leasing Bot...")
    
    # Skip startup checks in production environments (Railway, Heroku, etc.)
    is_production = (
        os.getenv('FLASK_ENV') == 'production' or 
        os.getenv('RAILWAY_ENVIRONMENT') or 
        os.getenv('DYNO') or  # Heroku
        os.getenv('SKIP_STARTUP_CHECK', '').lower() == 'true'
    )
    
    if not is_production:
        logger.info("Running startup checks...")
        try:
            from startup_check import main as startup_check
            if not startup_check():
                logger.error("Startup checks failed. Exiting.")
                sys.exit(1)
        except ImportError:
            logger.warning("Startup check module not found, skipping...")
        except Exception as e:
            logger.error(f"Startup check failed with error: {e}")
            sys.exit(1)
    else:
        logger.info("🚀 Production environment detected - skipping startup checks")
    
    # Debug: Log all environment variables
    logger.info("🔍 Debug: Available environment variables:")
    logger.info(f"Total env vars: {len(os.environ)}")
    
    # Show ALL environment variables (not just our specific ones)
    for key, value in os.environ.items():
        logger.info(f"  {key}: {value[:20]}...")
    
    # Check specific variables
    logger.info("🔍 Checking specific variables:")
    for var in ['ACCESS_TOKEN', 'APP_SECRET', 'PHONE_NUMBER_ID', 'VERIFY_TOKEN', 'SUPABASE_URL', 'SUPABASE_KEY', 'GEMINI_API_KEY']:
        value = os.getenv(var)
        logger.info(f"  {var}: {'Found' if value else 'NOT FOUND'}")
    
    # Create Flask application
    try:
        app = create_app()
        logger.info("Flask application created successfully")
    except Exception as e:
        logger.error(f"Failed to create Flask application: {e}")
        sys.exit(1)
    
    # Get configuration
    port = int(os.getenv('PORT', 8080))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting server on {host}:{port} (debug={debug})")
    
    # Add a small delay to ensure all services are ready
    import time
    logger.info("Waiting 5 seconds for all services to initialize...")
    time.sleep(5)
    
    # Start the application
    try:
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application crashed: {e}")
        sys.exit(1)
    finally:
        logger.info("Application shutdown complete")


if __name__ == "__main__":
    main()
