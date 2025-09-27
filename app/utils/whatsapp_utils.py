import logging
from flask import current_app, jsonify
import json
import requests
import re
from app.services.lead_service import lead_service

logger = logging.getLogger(__name__)


def log_http_response(response):
    """Log HTTP response details for debugging"""
    logger.info(f"WhatsApp API Response - Status: {response.status_code}")
    logger.debug(f"Content-type: {response.headers.get('content-type')}")
    logger.debug(f"Body: {response.text}")


def get_text_message_input(recipient, text):
    """Create WhatsApp text message payload"""
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )


def send_message(data):
    """Send message via WhatsApp Business API"""
    logger.debug(f"Sending WhatsApp message: {data}")
    
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {current_app.config['ACCESS_TOKEN']}",
    }

    url = f"https://graph.facebook.com/{current_app.config['VERSION']}/{current_app.config['PHONE_NUMBER_ID']}/messages"

    try:
        response = requests.post(
            url, data=data, headers=headers, timeout=10
        )
        response.raise_for_status()
        
        logger.info("WhatsApp message sent successfully")
        log_http_response(response)
        return response
        
    except requests.Timeout:
        logger.error("Timeout occurred while sending WhatsApp message")
        return jsonify({"status": "error", "message": "Request timed out"}), 408
    except requests.RequestException as e:
        logger.error(f"Failed to send WhatsApp message: {e}")
        return jsonify({"status": "error", "message": "Failed to send message"}), 500


def send_text_message(phone_number: str, text: str):
    """Send a simple text message via WhatsApp"""
    try:
        message_data = json.dumps({
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_number,
            "type": "text",
            "text": {
                "body": text
            }
        })
        
        return send_message(message_data)
        
    except Exception as e:
        logger.error(f"Error sending text message to {phone_number}: {e}")
        return False


def process_text_for_whatsapp(text):
    """Process text for WhatsApp formatting"""
    # Remove special markdown brackets
    pattern = r"\【.*?\】"
    text = re.sub(pattern, "", text).strip()

    # Convert double asterisks to single (WhatsApp bold format)
    pattern = r"\*\*(.*?)\*\*"
    replacement = r"*\1*"
    whatsapp_style_text = re.sub(pattern, replacement, text)

    # Ensure text is not too long (WhatsApp has limits)
    if len(whatsapp_style_text) > 4096:
        whatsapp_style_text = whatsapp_style_text[:4093] + "..."
        logger.warning("Message truncated due to length limit")

    return whatsapp_style_text


def process_whatsapp_message(body):
    """Process incoming WhatsApp message through the lead service"""
    try:
        logger.info("Processing incoming WhatsApp message")
        
        # Extract message data
        contact_data = body["entry"][0]["changes"][0]["value"]["contacts"][0]
        wa_id = contact_data["wa_id"]
        name = contact_data["profile"]["name"]

        message_data = body["entry"][0]["changes"][0]["value"]["messages"][0]
        message_body = message_data["text"]["body"]
        message_id = message_data.get("id")
        
        logger.info(f"Message from {name} ({wa_id}): {message_body[:100]}...")
        
        # Process through lead service
        response = lead_service.process_lead_message(wa_id, name, message_body)
        
        if not response:
            logger.error("Lead service returned empty response")
            response = "מצטער, יש לי בעיה טכנית. אנא נסה שוב מאוחר יותר."
        
        # Format for WhatsApp
        formatted_response = process_text_for_whatsapp(response)
        
        # Send response
        data = get_text_message_input(wa_id, formatted_response)
        send_result = send_message(data)
        
        if send_result and hasattr(send_result, 'status_code') and send_result.status_code == 200:
            logger.info(f"Response sent successfully to {wa_id}")
        else:
            logger.error(f"Failed to send response to {wa_id}")
            
    except KeyError as e:
        logger.error(f"Missing required field in WhatsApp message: {e}")
        logger.debug(f"Message body: {body}")
    except Exception as e:
        logger.error(f"Error processing WhatsApp message: {e}")
        logger.debug(f"Message body: {body}")


def is_valid_whatsapp_message(body):
    """Check if the incoming webhook event has a valid WhatsApp message structure
    and is intended for this bot's phone number"""
    try:
        # Check basic structure
        if not (body.get("object") and body.get("entry")):
            return False
        
        entry = body["entry"][0]
        if not (entry.get("changes") and entry["changes"]):
            return False
        
        change = entry["changes"][0]
        if not change.get("value"):
            return False
        
        value = change["value"]
        
        # Check if it has messages
        if not (value.get("messages") and value["messages"]):
            return False
        
        # Check if it has contacts
        if not (value.get("contacts") and value["contacts"]):
            return False
        
        message = value["messages"][0]
        contact = value["contacts"][0]
        
        # Validate required fields
        if not (message.get("text") and message["text"].get("body")):
            logger.debug("Message missing text body")
            return False
        
        if not (contact.get("wa_id") and contact.get("profile", {}).get("name")):
            logger.debug("Message missing contact information")
            return False
        
        # Validate that the message is for this bot's phone number
        configured_phone_id = current_app.config.get("PHONE_NUMBER_ID")
        webhook_phone_id = value.get("metadata", {}).get("phone_number_id")
        
        if configured_phone_id and webhook_phone_id and configured_phone_id != webhook_phone_id:
            logger.info(f"Ignoring message for different phone number - configured: {configured_phone_id}, webhook: {webhook_phone_id}")
            return False
        
        logger.debug("Valid WhatsApp message structure confirmed")
        return True
        
    except (KeyError, IndexError, TypeError) as e:
        logger.debug(f"Invalid WhatsApp message structure: {e}")
        return False


def extract_message_type(body):
    """Extract the type of WhatsApp message (text, image, document, etc.)"""
    try:
        message = body["entry"][0]["changes"][0]["value"]["messages"][0]
        return message.get("type", "unknown")
    except (KeyError, IndexError):
        return "unknown"


def extract_contact_info(body):
    """Extract contact information from WhatsApp message"""
    try:
        contact = body["entry"][0]["changes"][0]["value"]["contacts"][0]
        return {
            "wa_id": contact["wa_id"],
            "name": contact["profile"]["name"]
        }
    except (KeyError, IndexError):
        return None


def handle_interactive_message(body):
    """Handle interactive messages (buttons, lists, etc.)"""
    try:
        message = body["entry"][0]["changes"][0]["value"]["messages"][0]
        
        if message.get("type") == "interactive":
            interactive = message.get("interactive", {})
            
            if interactive.get("type") == "button_reply":
                button_reply = interactive.get("button_reply", {})
                return button_reply.get("title", "")
            
            elif interactive.get("type") == "list_reply":
                list_reply = interactive.get("list_reply", {})
                return list_reply.get("title", "")
        
        return None
        
    except (KeyError, IndexError):
        return None
