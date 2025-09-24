"""
Messaging service for handling WhatsApp communications.
Centralizes all message sending and formatting logic.
"""

import logging
import json
import requests
from typing import Dict, Optional
from flask import current_app
from app.services.database_service import db_service
from app.utils.whatsapp_utils import send_message, get_text_message_input, process_text_for_whatsapp

logger = logging.getLogger(__name__)


class MessagingService:
    """Service for managing WhatsApp messaging"""
    
    def send_message_to_lead(self, lead_id: int, message: str) -> bool:
        """Send WhatsApp message to a lead"""
        try:
            logger.info(f"Sending message to lead {lead_id}")
            
            # Get lead information
            lead = db_service.get_lead_by_id(lead_id)
            if not lead:
                logger.error(f"Lead {lead_id} not found")
                return False
            
            # Process message for WhatsApp formatting
            formatted_message = process_text_for_whatsapp(message)
            
            # Prepare message data
            message_data = get_text_message_input(lead['phone_number'], formatted_message)
            
            # Send message
            response = send_message(message_data)
            
            if response and response.status_code == 200:
                logger.info(f"Message sent successfully to lead {lead_id}")
                
                # Log the message
                db_service.log_conversation(lead_id, 'bot', formatted_message)
                
                return True
            else:
                logger.error(f"Failed to send message to lead {lead_id}: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending message to lead {lead_id}: {e}")
            return False
    
    def send_message_to_phone(self, phone_number: str, message: str) -> bool:
        """Send WhatsApp message to a phone number"""
        try:
            logger.info(f"Sending message to phone {phone_number}")
            
            # Process message for WhatsApp formatting
            formatted_message = process_text_for_whatsapp(message)
            
            # Prepare message data
            message_data = get_text_message_input(phone_number, formatted_message)
            
            # Send message
            response = send_message(message_data)
            
            if response and response.status_code == 200:
                logger.info(f"Message sent successfully to {phone_number}")
                return True
            else:
                logger.error(f"Failed to send message to {phone_number}: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending message to phone {phone_number}: {e}")
            return False
    
    def send_property_images(self, lead_id: int, units: list) -> bool:
        """Send property images to a lead with captions"""
        try:
            logger.info(f"Sending property images to lead {lead_id}")
            
            # Get lead information
            lead = db_service.get_lead_by_id(lead_id)
            if not lead:
                logger.error(f"Lead {lead_id} not found")
                return False
            
            success_count = 0
            
            for i, unit in enumerate(units[:3], 1):  # Send up to 3 properties
                property_info = unit.get('properties', {}) if isinstance(unit.get('properties'), dict) else {}
                
                logger.info(f"Processing unit {i}: {unit.get('id')} with image_url: {unit.get('image_url')}")
                
                # Create caption for the property
                caption = f"""🏠 דירה {i}: {unit.get('rooms')} חדרים
📍 {property_info.get('address', 'כתובת לא זמינה')}
💰 {unit.get('price', 0):,.0f} ש"ח/חודש
🚗 חניה: {'כן' if unit.get('has_parking') else 'לא'}
📏 {unit.get('area_sqm', 'לא צוין')} מ"ר"""
                
                # Send main property image with caption
                if unit.get('image_url') and not unit.get('image_url').startswith('https://example.com'):
                    logger.info(f"Attempting to send image with caption for unit {unit.get('id')}")
                    if self._send_image_message_with_caption(lead['phone_number'], unit['image_url'], caption):
                        success_count += 1
                        logger.info(f"Successfully sent image with caption for unit {unit.get('id')}")
                    else:
                        # Fallback: send image without caption
                        logger.warning(f"Failed to send image with caption, trying without caption for unit {unit.get('id')}")
                        if self._send_image_message(lead['phone_number'], unit['image_url']):
                            success_count += 1
                            logger.info(f"Successfully sent image without caption for unit {unit.get('id')}")
                else:
                    # No valid image URL, send caption as text message
                    logger.warning(f"Invalid or placeholder image URL for unit {unit.get('id')}: {unit.get('image_url')}")
                    from app.utils.whatsapp_utils import send_text_message
                    send_text_message(lead['phone_number'], caption)
                    logger.info(f"Sent property details as text for unit {unit.get('id')}")
                
                # Send floorplan if available (without caption to avoid spam)
                if unit.get('floorplan_url') and not unit.get('floorplan_url').startswith('https://example.com'):
                    logger.info(f"Attempting to send floorplan for unit {unit.get('id')}")
                    if self._send_image_message(lead['phone_number'], unit['floorplan_url']):
                        success_count += 1
                        logger.info(f"Successfully sent floorplan for unit {unit.get('id')}")
                    else:
                        logger.warning(f"Failed to send floorplan for unit {unit.get('id')}")
            
            logger.info(f"Sent {success_count} images to lead {lead_id}")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error sending property images to lead {lead_id}: {e}")
            return False
    
    def _send_image_message(self, phone_number: str, image_url: str) -> bool:
        """Send an image message via WhatsApp"""
        try:
            message_data = json.dumps({
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": phone_number,
                "type": "image",
                "image": {
                    "link": image_url
                }
            })
            
            response = send_message(message_data)
            
            if response and response.status_code == 200:
                logger.debug(f"Image sent successfully to {phone_number}")
                return True
            else:
                logger.error(f"Failed to send image to {phone_number}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending image to {phone_number}: {e}")
            return False
    
    def _send_image_message_with_caption(self, phone_number: str, image_url: str, caption: str) -> bool:
        """Send an image message with caption via WhatsApp"""
        try:
            message_data = json.dumps({
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": phone_number,
                "type": "image",
                "image": {
                    "link": image_url,
                    "caption": caption
                }
            })
            
            response = send_message(message_data)
            
            if response and response.status_code == 200:
                logger.debug(f"Image with caption sent successfully to {phone_number}")
                return True
            else:
                logger.error(f"Failed to send image with caption to {phone_number}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending image with caption to {phone_number}: {e}")
            return False
    
    def send_document(self, lead_id: int, document_url: str, filename: str) -> bool:
        """Send a document to a lead"""
        try:
            logger.info(f"Sending document to lead {lead_id}")
            
            # Get lead information
            lead = db_service.get_lead_by_id(lead_id)
            if not lead:
                logger.error(f"Lead {lead_id} not found")
                return False
            
            message_data = json.dumps({
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": lead['phone_number'],
                "type": "document",
                "document": {
                    "link": document_url,
                    "filename": filename
                }
            })
            
            response = send_message(message_data)
            
            if response and response.status_code == 200:
                logger.info(f"Document sent successfully to lead {lead_id}")
                return True
            else:
                logger.error(f"Failed to send document to lead {lead_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending document to lead {lead_id}: {e}")
            return False
    
    def send_location(self, lead_id: int, latitude: float, longitude: float, name: str, address: str) -> bool:
        """Send a location to a lead"""
        try:
            logger.info(f"Sending location to lead {lead_id}")
            
            # Get lead information
            lead = db_service.get_lead_by_id(lead_id)
            if not lead:
                logger.error(f"Lead {lead_id} not found")
                return False
            
            message_data = json.dumps({
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": lead['phone_number'],
                "type": "location",
                "location": {
                    "latitude": latitude,
                    "longitude": longitude,
                    "name": name,
                    "address": address
                }
            })
            
            response = send_message(message_data)
            
            if response and response.status_code == 200:
                logger.info(f"Location sent successfully to lead {lead_id}")
                return True
            else:
                logger.error(f"Failed to send location to lead {lead_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending location to lead {lead_id}: {e}")
            return False
    
    def send_quick_replies(self, lead_id: int, message: str, options: list) -> bool:
        """Send a message with quick reply buttons"""
        try:
            logger.info(f"Sending quick replies to lead {lead_id}")
            
            # Get lead information
            lead = db_service.get_lead_by_id(lead_id)
            if not lead:
                logger.error(f"Lead {lead_id} not found")
                return False
            
            # WhatsApp interactive button message
            buttons = []
            for i, option in enumerate(options[:3]):  # Max 3 buttons
                buttons.append({
                    "type": "reply",
                    "reply": {
                        "id": f"option_{i}",
                        "title": option[:20]  # Max 20 chars for button title
                    }
                })
            
            message_data = json.dumps({
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": lead['phone_number'],
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {
                        "text": message
                    },
                    "action": {
                        "buttons": buttons
                    }
                }
            })
            
            response = send_message(message_data)
            
            if response and response.status_code == 200:
                logger.info(f"Quick replies sent successfully to lead {lead_id}")
                return True
            else:
                logger.error(f"Failed to send quick replies to lead {lead_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending quick replies to lead {lead_id}: {e}")
            return False


# Global messaging service instance
messaging_service = MessagingService()
