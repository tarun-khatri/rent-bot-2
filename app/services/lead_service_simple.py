"""
Simplified AI-powered lead management service.
New flow: name → project → rooms → show units → guarantees → calendly
Ultra-short, direct responses.
"""

import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional
from flask import current_app
from app.services.database_service import db_service
from app.services.gemini_service_simple import gemini_service_simple
from app.config import get_current_time

logger = logging.getLogger(__name__)


class LeadServiceSimple:
    """Simplified service for managing leads with new flow"""
    
    def __init__(self):
        """Initialize the simplified lead service"""
        # Properties will be fetched from database dynamically
        self._properties_cache = None
        self._properties_cache_time = None
    
    def process_lead_message(self, phone_number: str, name: str, message: str) -> str:
        """Main entry point for processing lead messages"""
        try:
            logger.info(f"Processing message from {name} ({phone_number}): {message[:50]}...")
            
            # Get or create lead
            lead = db_service.get_lead_by_phone(phone_number)
            if not lead:
                lead = db_service.create_lead(phone_number, name)
                logger.info(f"New lead created: {lead['id']}")
            
            # Check for duplicate message
            recent_messages = db_service.get_conversation_history(lead['id'], limit=3)
            if recent_messages:
                last_user_message = None
                for msg in reversed(recent_messages):
                    if msg.get('message_type') == 'user':
                        last_user_message = msg.get('content', '').strip()
                        break
                
                if last_user_message and last_user_message == message.strip():
                    logger.info(f"Duplicate message detected for lead {lead['id']}, skipping")
                    return "קיבלתי את ההודעה."
            
            # Log user message
            db_service.log_conversation(lead['id'], 'user', message)
            
            # Process based on stage
            response = self._process_by_stage(lead, message)
            
            # Log bot response
            db_service.log_conversation(lead['id'], 'bot', response)
            
            logger.info(f"Response generated for lead {lead['id']}, length: {len(response)}")
            return response
            
        except Exception as e:
            logger.error(f"Error processing lead message: {e}")
            return "מצטער, יש בעיה טכנית. נסה שוב."
    
    def _process_by_stage(self, lead: Dict, message: str) -> str:
        """Process message based on current stage"""
        stage = lead.get('stage', 'new')
        conversation_history = db_service.get_conversation_history(lead['id'], limit=10)
        
        logger.info(f"Processing stage '{stage}' for lead {lead['id']}")
        
        # AI will naturally handle preference changes through conversation flow
        # No need for explicit detection
        
        # Route to appropriate handler
        if stage == 'new':
            return self._handle_new_lead(lead, message, conversation_history)
        elif stage == 'collecting_profile':
            return self._handle_collecting_profile(lead, message, conversation_history)
        elif stage == 'qualified':
            return self._handle_qualified(lead, message, conversation_history)
        elif stage == 'scheduling_in_progress':
            return self._handle_scheduling(lead, message, conversation_history)
        elif stage == 'tour_scheduled':
            return self._handle_tour_scheduled(lead, message, conversation_history)
        else:
            # Default to collecting profile for unknown stages
            return self._handle_collecting_profile(lead, message, conversation_history)
    
    def _handle_new_lead(self, lead: Dict, message: str, conversation_history: List[Dict]) -> str:
        """Handle new lead - ask for name"""
        logger.info(f"Handling new lead {lead['id']}")
        
        # Move to collecting profile stage
        db_service.update_lead(lead['id'], {'stage': 'collecting_profile'})
        
        # Generate welcome and ask for name using AI
        lead_refreshed = db_service.get_lead_by_phone(lead['phone_number'])
        return gemini_service_simple.generate_response('new', lead_refreshed, conversation_history, message)
    
    def _handle_collecting_profile(self, lead: Dict, message: str, conversation_history: List[Dict]) -> str:
        """Handle profile collection - collect project and rooms"""
        logger.info(f"Collecting profile for lead {lead['id']}")
        
        # Handle edge cases
        if not message or len(message.strip()) < 1:
            return "אני לא הבנתי. תוכל לחזור על זה?"
        
        # Try to extract information from message
        extracted = self._extract_profile_info(message, lead)
        logger.info(f"Extracted info: {extracted}")
        
        if extracted:
            logger.info(f"Updating lead {lead['id']} with: {extracted}")
            db_service.update_lead(lead['id'], extracted)
            lead = db_service.get_lead_by_phone(lead['phone_number'])
            logger.info(f"Updated lead data: {lead}")
        
        # Check what's missing
        missing = self._get_missing_profile_fields(lead)
        
        if not missing:
            # Profile complete - search for properties
            return self._search_and_show_properties(lead, conversation_history)
        
        # If asking for project, pass available projects to AI
        if 'project' in missing:
            properties = self._get_available_properties()
            property_names = [p.get('name', '') for p in properties if p.get('name')]
            # Add property names to lead data for AI context
            lead_with_properties = lead.copy()
            lead_with_properties['available_properties'] = property_names
            return gemini_service_simple.generate_response('collecting_profile', lead_with_properties, conversation_history, message)
        
        # Generate response asking for missing info
        return gemini_service_simple.generate_response('collecting_profile', lead, conversation_history, message)
    
    def _handle_qualified(self, lead: Dict, message: str, conversation_history: List[Dict]) -> str:
        """Handle qualified lead - already showed properties"""
        logger.info(f"Handling qualified lead {lead['id']}")
        
        # Check if they want to schedule
        is_scheduling = self._is_scheduling_request(message)
        logger.info(f"Scheduling request detection for '{message}': {is_scheduling}")
        
        if is_scheduling:
            logger.info(f"Calling _start_scheduling for lead {lead['id']}")
            return self._start_scheduling(lead, conversation_history)
        
        # Check if they're asking about guarantees
        if any(word in message.lower() for word in ['ערבות', 'guarantee', 'דרישות', 'תלוש', 'payslip']):
            return self._explain_guarantees_and_schedule(lead, conversation_history)
        
        # Default - ask if they want to schedule or need more info
        return gemini_service_simple.generate_response('qualified', lead, conversation_history, message)
    
    def _handle_scheduling(self, lead: Dict, message: str, conversation_history: List[Dict]) -> str:
        """Handle scheduling in progress"""
        logger.info(f"Handling scheduling for lead {lead['id']}")
        
        # Check if they confirmed booking
        if self._is_booking_confirmation(message):
            db_service.update_lead(lead['id'], {'stage': 'tour_scheduled'})
            lead_refreshed = db_service.get_lead_by_phone(lead['phone_number'])
            return gemini_service_simple.generate_response('tour_scheduled', lead_refreshed, conversation_history, message)
        
        return gemini_service_simple.generate_response('scheduling_in_progress', lead, conversation_history, message)
    
    def _handle_tour_scheduled(self, lead: Dict, message: str, conversation_history: List[Dict]) -> str:
        """Handle tour already scheduled"""
        logger.info(f"Handling tour scheduled for lead {lead['id']}")
        return gemini_service_simple.generate_response('tour_scheduled', lead, conversation_history, message)
    
    def _search_and_show_properties(self, lead: Dict, conversation_history: List[Dict]) -> str:
        """Search for properties and show them to the lead"""
        logger.info(f"Searching properties for lead {lead['id']}")
        
        # Build search criteria
        search_criteria = {}
        if lead.get('rooms'):
            search_criteria['min_rooms'] = lead['rooms']
            search_criteria['max_rooms'] = lead['rooms']
        
        # Search for units
        units = db_service.get_available_units(search_criteria)
        
        # Filter by project if specified
        if lead.get('preferred_area'):
            logger.info(f"Filtering units by preferred_area: {lead.get('preferred_area')}")
            filtered_units = []
            for u in units:
                matches = self._matches_project(u, lead.get('preferred_area'))
                property_info = u.get('properties', {})
                property_name = property_info.get('name', '') if isinstance(property_info, dict) else ''
                logger.info(f"Unit property: '{property_name}', matches: {matches}")
                if matches:
                    filtered_units.append(u)
            units = filtered_units
        
        logger.info(f"Found {len(units)} units for lead {lead['id']}")
        
        if units:
            # Update stage to qualified
            db_service.update_lead(lead['id'], {'stage': 'qualified'})
            
            # Generate property message
            property_msg = gemini_service_simple.generate_property_message(lead, units)
            
            # Send property images
            try:
                from app.services.messaging_service import messaging_service
                messaging_service.send_property_images(lead['id'], units)
                logger.info(f"Sent property images for lead {lead['id']}")
            except Exception as e:
                logger.error(f"Failed to send property images: {e}")
            
            return property_msg
        else:
            # No properties found - allow preference changes
            db_service.update_lead(lead['id'], {'stage': 'collecting_profile'})  # Allow changes
            no_props_msg = gemini_service_simple.generate_no_properties_message(lead)
            return no_props_msg
    
    def _explain_guarantees_and_schedule(self, lead: Dict, conversation_history: List[Dict]) -> str:
        """Explain guarantee requirements and offer to schedule"""
        logger.info(f"Explaining guarantees for lead {lead['id']}")
        
        # Generate guarantee explanation using AI
        guarantee_stage_data = {**lead, 'stage': 'asking_guarantees'}
        response = gemini_service_simple.generate_response('asking_guarantees', guarantee_stage_data, conversation_history, "")
        
        # Add calendly link
        calendly_link = os.getenv('CALENDLY_LINK', '')
        if calendly_link:
            response += f"\n\n📅 קישור לתיאום ביקור:\n{calendly_link}"
            db_service.update_lead(lead['id'], {'stage': 'scheduling_in_progress'})
        
        return response
    
    def _start_scheduling(self, lead: Dict, conversation_history: List[Dict]) -> str:
        """Start the scheduling process"""
        logger.info(f"Starting scheduling for lead {lead['id']}")
        
        # First explain guarantees briefly
        guarantee_msg = gemini_service_simple.generate_response('asking_guarantees', lead, conversation_history, "")
        
        # Then send calendly link
        calendly_link = os.getenv('CALENDLY_LINK', '')
        logger.info(f"CALENDLY_LINK environment variable: {'SET' if calendly_link else 'NOT SET'}")
        
        if calendly_link:
            logger.info(f"Using Calendly link: {calendly_link}")
            db_service.update_lead(lead['id'], {'stage': 'scheduling_in_progress'})
            return f"{guarantee_msg}\n\n📅 קישור לתיאום:\n{calendly_link}\n\nאחרי שתקבע, תאשר לי כאן."
        else:
            logger.info("No Calendly link found, using manual scheduling")
            return "אתאם איתך ידנית. איזה יום ושעה נוחים לך?"
    
    def _get_available_properties(self) -> List[Dict]:
        """Get available properties from database with caching"""
        from datetime import datetime, timedelta
        
        # Cache for 5 minutes
        if self._properties_cache and self._properties_cache_time:
            if datetime.now() - self._properties_cache_time < timedelta(minutes=5):
                return self._properties_cache
        
        # Fetch from database
        properties = db_service.get_all_properties()
        self._properties_cache = properties
        self._properties_cache_time = datetime.now()
        return properties
    
    def _match_property_with_ai(self, user_message: str, properties: List[Dict]) -> Optional[str]:
        """Use AI to match user's message to a property name"""
        if not properties:
            return None
        
        # Build a simple prompt for AI to match
        property_names = [p.get('name', '') for p in properties if p.get('name')]
        if not property_names:
            return None
        
        # Also try simple string matching first (faster)
        user_lower = user_message.lower().strip()
        for prop_name in property_names:
            if prop_name.lower() in user_lower or user_lower in prop_name.lower():
                logger.info(f"Directly matched '{user_message}' to property: {prop_name}")
                return prop_name
        
        # If no direct match, use AI
        try:
            from app.services.gemini_service_simple import gemini_service_simple
            
            prompt = f"""Match the user's message to a property name.

User said: "{user_message}"

Available properties:
{chr(10).join(f"- {name}" for name in property_names)}

Reply with ONLY the exact property name that best matches, or "NONE" if no match.
Example replies: "{property_names[0]}" or "NONE"
"""
            
            response = gemini_service_simple.generate_response('collecting_profile', {}, [], prompt)
            matched_property = response.strip().strip('"').strip("'")
            
            logger.info(f"AI response for '{user_message}': '{matched_property}'")
            
            # Verify the matched property exists in our list
            if matched_property in property_names:
                logger.info(f"AI matched '{user_message}' to property: {matched_property}")
                return matched_property
            elif matched_property.upper() != "NONE":
                logger.warning(f"AI returned invalid property: {matched_property}, trying fuzzy match")
                # Try fuzzy matching
                for prop_name in property_names:
                    if matched_property.lower() in prop_name.lower():
                        logger.info(f"Fuzzy matched to: {prop_name}")
                        return prop_name
            
        except Exception as e:
            logger.error(f"Error matching property with AI: {e}")
        
        return None
    
    def _extract_profile_info(self, message: str, lead: Dict) -> Dict:
        """Extract profile information from message using AI and database"""
        updates = {}
        message_lower = message.lower().strip()
        
        # Extract name (if not already set and looks like a name)
        if not lead.get('name') or lead.get('name') in ['Unknown', '...', None, '']:
            words = message.split()
            if 1 <= len(words) <= 3 and not any(char.isdigit() for char in message) and '?' not in message:
                updates['name'] = message.strip()
                logger.info(f"Extracted name: {message.strip()}")
        
        # Extract project using AI - match against actual database properties
        properties = self._get_available_properties()
        matched_property = self._match_property_with_ai(message, properties)
        
        if matched_property:
            updates['preferred_area'] = matched_property
            if lead.get('preferred_area') and lead.get('preferred_area') != matched_property:
                logger.info(f"Changed project from {lead.get('preferred_area')} to {matched_property}")
            else:
                logger.info(f"Extracted project: {matched_property}")
        
        # Extract number of rooms - allow updates anytime user mentions a number
        rooms = self._extract_number(message)
        if rooms and 1 <= rooms <= 10:
            updates['rooms'] = rooms
            if lead.get('preferred_area') and lead.get('rooms') != rooms:
                logger.info(f"Changed rooms from {lead.get('rooms')} to {rooms}")
            else:
                logger.info(f"Extracted rooms: {rooms}")
        
        return updates
    
    def _get_missing_profile_fields(self, lead: Dict) -> List[str]:
        """Get list of missing required fields"""
        missing = []
        
        if not lead.get('name') or lead.get('name') in ['Unknown', '...', None, '']:
            missing.append('name')
        if not lead.get('preferred_area'):
            missing.append('project')
        if not lead.get('rooms'):
            missing.append('rooms')
        
        logger.info(f"Missing fields for lead {lead.get('id')}: {missing}")
        return missing
    
    def _extract_number(self, message: str) -> Optional[int]:
        """Extract number from message"""
        # Hebrew numbers
        hebrew_numbers = {
            'אחד': 1, 'אחת': 1, 'שני': 2, 'שתיים': 2, 'שניים': 2,
            'שלוש': 3, 'שלושה': 3, 'ארבע': 4, 'ארבעה': 4,
            'חמש': 5, 'חמישה': 5, 'שש': 6, 'שישה': 6,
            'שבע': 7, 'שבעה': 7, 'שמונה': 8, 'תשע': 9, 'עשר': 10
        }
        
        message_lower = message.lower()
        for word, num in hebrew_numbers.items():
            if word in message_lower:
                return num
        
        # Extract digits
        numbers = re.findall(r'\d+', message)
        if numbers:
            return int(numbers[0])
        
        return None
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        return text.lower().replace(' ', '').replace('-', '').replace('_', '')
    
    def _matches_project(self, unit: Dict, preferred_area: str) -> bool:
        """Check if unit matches preferred project"""
        if not preferred_area:
            return True
        
        property_info = unit.get('properties', {})
        if isinstance(property_info, dict):
            property_name = property_info.get('name', '')
            property_address = property_info.get('address', '')
            
            # Normalize for comparison
            pref_norm = self._normalize_text(preferred_area)
            name_norm = self._normalize_text(property_name)
            addr_norm = self._normalize_text(property_address)
            
            return pref_norm in name_norm or pref_norm in addr_norm
        
        return True
    
    def _is_scheduling_request(self, message: str) -> bool:
        """Check if message is requesting to schedule using AI"""
        try:
            from app.services.gemini_service_simple import gemini_service_simple
            
            # Use AI to understand if user wants to schedule
            prompt = f"""Does this message indicate the user wants to schedule a visit/tour?

User message: "{message}"

Reply with ONLY "YES" or "NO"."""
            
            response = gemini_service_simple.generate_response('collecting_profile', {}, [], prompt)
            result = response.strip().upper()
            
            logger.info(f"AI scheduling detection for '{message}': {result}")
            return result == "YES"
            
        except Exception as e:
            logger.error(f"Error in AI scheduling detection: {e}")
            # Fallback to simple detection
            message_lower = message.lower()
            return any(word in message_lower for word in ['yes', 'כן', 'רוצה', 'want', 'schedule', 'visit', 'tour'])
    
    def _is_booking_confirmation(self, message: str) -> bool:
        """Check if message confirms booking"""
        message_lower = message.lower()
        
        confirmation_keywords = [
            'קבעתי', 'הזמנתי', 'תיאמתי', 'booked', 'scheduled',
            'confirmed', 'done', 'קיבלתי אישור', 'סידרתי'
        ]
        
        return any(keyword in message_lower for keyword in confirmation_keywords)
    
    def _is_preference_change_request(self, message: str) -> bool:
        """Check if user wants to change preferences"""
        message_lower = message.lower()
        
        change_keywords = [
            'change', 'שינוי', 'אחר', 'different', 'other', 
            'גמיש', 'flexible', 'לא מתאים', 'not suitable',
            'אפשר אחר', 'can change', 'לשנות'
        ]
        
        return any(keyword in message_lower for keyword in change_keywords)
    
    def _handle_preference_change(self, lead: Dict, message: str, conversation_history: List[Dict]) -> str:
        """Handle when user wants to change preferences"""
        logger.info(f"Handling preference change for lead {lead['id']}")
        
        # Reset to collecting profile stage
        db_service.update_lead(lead['id'], {'stage': 'collecting_profile'})
        
        # Extract new preferences
        updates = self._extract_profile_info(message, lead)
        
        if updates:
            # Update lead with new preferences
            db_service.update_lead(lead['id'], updates)
            logger.info(f"Updated preferences for lead {lead['id']}: {updates}")
        
        # Generate response asking for missing info
        missing_fields = self._get_missing_profile_fields(lead)
        
        if missing_fields:
            return gemini_service_simple.generate_response('collecting_profile', lead, conversation_history, message)
        else:
            # All info collected, search for properties
            return self._search_and_show_properties(lead, conversation_history)


# Global instance
lead_service_simple = LeadServiceSimple()

