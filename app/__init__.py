from flask import Flask
from flask_cors import CORS
from app.config import load_configurations, configure_logging
from .views import webhook_blueprint
import logging
import atexit

logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)

    # Load configurations and logging settings
    load_configurations(app)
    configure_logging()
    
    # Enable CORS for development
    CORS(app)

    # Import and register blueprints
    app.register_blueprint(webhook_blueprint)
    
    # Initialize and start background scheduler
    with app.app_context():
        try:
            from app.services.scheduler_service import scheduler_service
            scheduler_service.start()
            logger.info("Background scheduler started successfully")
            
            # Register cleanup function
            atexit.register(lambda: scheduler_service.stop())
            
        except Exception as e:
            logger.error(f"Failed to start scheduler service: {e}")

    logger.info("Flask application initialized successfully")
    return app
