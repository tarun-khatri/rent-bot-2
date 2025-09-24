import logging
import json
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify, current_app

from .decorators.security import signature_required
from .utils.whatsapp_utils import (
    process_whatsapp_message,
    is_valid_whatsapp_message,
)
from .services.calendly_service import calendly_service
from .services.database_service import db_service

logger = logging.getLogger(__name__)

webhook_blueprint = Blueprint("webhook", __name__)


def handle_message():
    """
    Handle incoming webhook events from the WhatsApp API.

    This function processes incoming WhatsApp messages and other events,
    such as delivery statuses. If the event is a valid message, it gets
    processed through our lead management system.

    Every message send will trigger 4 HTTP requests to your webhook: message, sent, delivered, read.

    Returns:
        response: A tuple containing a JSON response and an HTTP status code.
    """
    try:
        body = request.get_json()
        logger.debug(f"WhatsApp webhook received: {json.dumps(body, indent=2)}")

        # Check if it's a WhatsApp status update
        if (
            body.get("entry", [{}])[0]
            .get("changes", [{}])[0]
            .get("value", {})
            .get("statuses")
        ):
            logger.info("Received WhatsApp status update - acknowledging")
            return jsonify({"status": "ok"}), 200

        # Process valid WhatsApp messages
        if is_valid_whatsapp_message(body):
            logger.info("Processing valid WhatsApp message")
            process_whatsapp_message(body)
            return jsonify({"status": "ok"}), 200
        else:
            logger.warning("Received invalid WhatsApp webhook payload")
            return (
                jsonify({"status": "error", "message": "Not a WhatsApp API event"}),
                404,
            )
            
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON from WhatsApp webhook: {e}")
        return jsonify({"status": "error", "message": "Invalid JSON provided"}), 400
    except Exception as e:
        logger.error(f"Unexpected error handling WhatsApp message: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500


# Required webhook verifictaion for WhatsApp
def verify():
    # Parse params from the webhook verification request
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    # Check if a token and mode were sent
    if mode and token:
        # Check the mode and token sent are correct
        if mode == "subscribe" and token == current_app.config["VERIFY_TOKEN"]:
            # Respond with 200 OK and challenge token from the request
            logging.info("WEBHOOK_VERIFIED")
            return challenge, 200
        else:
            # Responds with '403 Forbidden' if verify tokens do not match
            logging.info("VERIFICATION_FAILED")
            return jsonify({"status": "error", "message": "Verification failed"}), 403
    else:
        # Responds with '400 Bad Request' if verify tokens do not match
        logging.info("MISSING_PARAMETER")
        return jsonify({"status": "error", "message": "Missing parameters"}), 400


def handle_calendly_webhook():
    """Handle incoming Calendly webhook events"""
    try:
        body = request.get_json()
        logger.info(f"Calendly webhook received: {body.get('event', 'unknown')}")
        
        # Process through Calendly service
        result = calendly_service.process_calendly_webhook(body)
        
        if result == "OK":
            return jsonify({"status": "ok"}), 200
        else:
            logger.error(f"Calendly webhook processing failed: {result}")
            return jsonify({"status": "error"}), 400
            
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON from Calendly webhook: {e}")
        return jsonify({"status": "error", "message": "Invalid JSON provided"}), 400
    except Exception as e:
        logger.error(f"Unexpected error handling Calendly webhook: {e}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500


def get_health_status():
    """Health check endpoint"""
    try:
        # Check database connection
        db_status = "OK"
        try:
            # Simple database check
            db_service._initialize_client()
        except Exception as e:
            db_status = f"ERROR: {str(e)}"
            logger.error(f"Database health check failed: {e}")
        
        # Check scheduler status
        from app.services.scheduler_service import scheduler_service
        scheduler_status = "RUNNING" if scheduler_service.scheduler and scheduler_service.scheduler.running else "STOPPED"
        
        health_data = {
            "status": "healthy" if db_status == "OK" else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "database": db_status,
            "scheduler": scheduler_status,
            "version": "1.0.0"
        }
        
        status_code = 200 if health_data["status"] == "healthy" else 503
        return jsonify(health_data), status_code
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 503


def get_metrics():
    """Get application metrics"""
    try:
        # Get recent daily metrics
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)  # Last 7 days
        
        daily_metrics = db_service.get_daily_metrics(start_date, end_date)
        
        # Calculate totals
        totals = {
            "total_inquiries": sum(m.get("total_inquiries", 0) for m in daily_metrics),
            "qualified_leads": sum(m.get("qualified_leads", 0) for m in daily_metrics),
            "tours_scheduled": sum(m.get("tours_scheduled", 0) for m in daily_metrics),
            "tours_completed": sum(m.get("tours_completed", 0) for m in daily_metrics)
        }
        
        return jsonify({
            "daily_metrics": daily_metrics,
            "totals_last_7_days": totals,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error retrieving metrics: {e}")
        return jsonify({"error": str(e)}), 500


# WhatsApp webhook routes
@webhook_blueprint.route("/webhook", methods=["GET"])
def webhook_get():
    return verify()

@webhook_blueprint.route("/webhook", methods=["POST"])
@signature_required
def webhook_post():
    return handle_message()

# Calendly webhook route
@webhook_blueprint.route("/webhook/calendly", methods=["POST"])
def calendly_webhook_post():
    return handle_calendly_webhook()

# Health and monitoring routes
@webhook_blueprint.route("/health", methods=["GET"])
def health_check():
    return get_health_status()

@webhook_blueprint.route("/metrics", methods=["GET"])
def metrics_endpoint():
    return get_metrics()


