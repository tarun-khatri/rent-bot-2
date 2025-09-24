"""
Calendly integration service for managing tour scheduling.
Handles webhook processing and followup scheduling.
"""

import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional
from flask import current_app
from app.services.database_service import db_service
from app.config import get_current_time, get_timezone

logger = logging.getLogger(__name__)


class CalendlyService:
    """Service for managing Calendly integration and tour scheduling"""
    
    def __init__(self):
        self.calendly_links = {}
        self._initialized = False
    
    def _load_calendly_links(self):
        """Load Calendly scheduling links from configuration (lazy initialization)"""
        if self._initialized:
            return
            
        try:
            from flask import current_app
            self.calendly_links = {
                'morning': current_app.config.get('CALENDLY_MORNING_LINK'),
                'afternoon': current_app.config.get('CALENDLY_AFTERNOON_LINK'),
                'evening': current_app.config.get('CALENDLY_EVENING_LINK')
            }
            self._initialized = True
            logger.info("Calendly links loaded from configuration")
        except Exception as e:
            logger.error(f"Failed to load Calendly configuration: {e}")
            raise
    
    def _ensure_initialized(self):
        """Ensure the service is initialized before use"""
        if not self._initialized:
            self._load_calendly_links()
    
    def process_scheduling_request(self, lead_id: int, time_preference: str) -> str:
        """Process tour scheduling request and return Calendly link"""
        try:
            self._ensure_initialized()
            logger.info(f"Processing scheduling request for lead {lead_id}, preference: {time_preference}")
            
            # Normalize time preference
            time_pref = self._normalize_time_preference(time_preference)
            
            if not time_pref:
                return self._get_time_preference_clarification()
            
            # Get appropriate Calendly link
            calendly_link = self.calendly_links.get(time_pref)
            
            if not calendly_link:
                logger.error(f"No Calendly link configured for {time_pref}")
                return "מצטער, יש בעיה טכנית עם מערכת התיאומים. אנא נסה שוב מאוחר יותר."
            
            # Update lead stage
            db_service.update_lead(lead_id, {'stage': 'scheduling_in_progress'})
            
            # Generate scheduling message
            return self._generate_scheduling_message(time_pref, calendly_link)
            
        except Exception as e:
            logger.error(f"Error processing scheduling request for lead {lead_id}: {e}")
            return "מצטער, יש בעיה טכנית עם התיאום. אנא נסה שוב מאוחר יותר."
    
    def process_calendly_webhook(self, webhook_data: Dict) -> str:
        """Process incoming Calendly webhook"""
        try:
            logger.info(f"Processing Calendly webhook: {webhook_data.get('event')}")
            
            event_type = webhook_data.get('event')
            payload = webhook_data.get('payload', {})
            
            if event_type == 'invitee.created':
                return self._handle_appointment_created(payload)
            elif event_type == 'invitee.canceled':
                return self._handle_appointment_canceled(payload)
            else:
                logger.info(f"Unhandled Calendly event type: {event_type}")
                return "OK"
                
        except Exception as e:
            logger.error(f"Error processing Calendly webhook: {e}")
            return "ERROR"
    
    def _handle_appointment_created(self, payload: Dict) -> str:
        """Handle appointment creation webhook"""
        try:
            # Extract appointment data
            appointment_data = self._extract_appointment_data(payload)
            
            if not appointment_data:
                logger.error("Failed to extract appointment data from webhook")
                return "ERROR"
            
            # Find lead by email
            lead = self._find_lead_by_email(appointment_data['attendee_email'])
            
            if not lead:
                logger.warning(f"No lead found for email: {appointment_data['attendee_email']}")
                return "OK"  # Still return OK to Calendly
            
            logger.info(f"Appointment created for lead {lead['id']}")
            
            # Create appointment record
            appointment = db_service.create_appointment(
                lead_id=lead['id'],
                unit_id=None,  # Will be determined later
                calendly_data=appointment_data
            )
            
            # Update lead status
            db_service.update_lead(lead['id'], {'stage': 'tour_scheduled'})
            
            # Schedule reminder messages
            self._schedule_reminder_messages(lead, appointment_data)
            
            # Send confirmation via WhatsApp
            self._send_appointment_confirmation(lead, appointment_data)
            
            logger.info(f"Appointment processing completed for lead {lead['id']}")
            return "OK"
            
        except Exception as e:
            logger.error(f"Error handling appointment creation: {e}")
            return "ERROR"
    
    def _handle_appointment_canceled(self, payload: Dict) -> str:
        """Handle appointment cancellation webhook"""
        try:
            # Extract cancellation data
            event_id = payload.get('event', {}).get('uri', '').split('/')[-1]
            
            if not event_id:
                logger.error("No event ID in cancellation webhook")
                return "ERROR"
            
            # Find appointment by Calendly event ID
            appointment = self._find_appointment_by_event_id(event_id)
            
            if not appointment:
                logger.warning(f"No appointment found for event ID: {event_id}")
                return "OK"
            
            # Update appointment status
            db_service.update_appointment_status(appointment['id'], 'canceled')
            
            # Update lead stage back to qualified
            db_service.update_lead(appointment['lead_id'], {'stage': 'qualified'})
            
            # Cancel pending followups
            self._cancel_pending_followups(appointment['lead_id'])
            
            # Send cancellation notice via WhatsApp
            self._send_cancellation_notice(appointment)
            
            logger.info(f"Appointment cancellation processed for appointment {appointment['id']}")
            return "OK"
            
        except Exception as e:
            logger.error(f"Error handling appointment cancellation: {e}")
            return "ERROR"
    
    def _extract_appointment_data(self, payload: Dict) -> Optional[Dict]:
        """Extract appointment data from Calendly webhook payload"""
        try:
            event_data = payload.get('event', {})
            invitee_data = payload.get('invitee', {})
            
            # Parse scheduled time
            start_time_str = event_data.get('start_time')
            if not start_time_str:
                return None
            
            # Convert to local timezone
            scheduled_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            local_tz = get_timezone()
            scheduled_time = scheduled_time.astimezone(local_tz)
            
            return {
                'event_id': event_data.get('uri', '').split('/')[-1],
                'scheduled_time': scheduled_time.isoformat(),
                'attendee_email': invitee_data.get('email'),
                'attendee_name': invitee_data.get('name'),
                'meeting_duration': event_data.get('event_type', {}).get('duration', 30),
                'location': event_data.get('location', {}).get('location', 'TBD')
            }
            
        except Exception as e:
            logger.error(f"Error extracting appointment data: {e}")
            return None
    
    def _find_lead_by_email(self, email: str) -> Optional[Dict]:
        """Find lead by email address"""
        # Note: This requires updating the leads table to include email
        # For now, we'll implement a fallback to find by recent activity
        try:
            # TODO: Implement email-based lookup when schema is updated
            # For now, find the most recent lead in scheduling stage
            
            recent_leads = db_service.get_recent_leads_by_stage('scheduling_in_progress', hours=2)
            
            if recent_leads:
                # Return the most recent one (assumption: last person to start scheduling)
                return recent_leads[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding lead by email {email}: {e}")
            return None
    
    def _find_appointment_by_event_id(self, event_id: str) -> Optional[Dict]:
        """Find appointment by Calendly event ID"""
        try:
            return db_service.get_appointment_by_calendly_id(event_id)
        except Exception as e:
            logger.error(f"Error finding appointment by event ID {event_id}: {e}")
            return None
    
    def _schedule_reminder_messages(self, lead: Dict, appointment_data: Dict):
        """Schedule reminder messages for the appointment"""
        try:
            scheduled_time = datetime.fromisoformat(appointment_data['scheduled_time'])
            
            # Evening before reminder (if appointment is not tomorrow)
            evening_before = scheduled_time.replace(hour=19, minute=0, second=0) - timedelta(days=1)
            if evening_before > get_current_time():
                reminder_content = self._get_evening_before_reminder(appointment_data)
                db_service.create_followup(
                    lead_id=lead['id'],
                    message_type='evening_before_reminder',
                    send_at=evening_before,
                    content=reminder_content
                )
                logger.info(f"Evening before reminder scheduled for {evening_before}")
            
            # Morning of reminder
            morning_of = scheduled_time.replace(hour=9, minute=0, second=0)
            if morning_of > get_current_time() and morning_of < scheduled_time:
                reminder_content = self._get_morning_of_reminder(appointment_data)
                db_service.create_followup(
                    lead_id=lead['id'],
                    message_type='morning_of_reminder',
                    send_at=morning_of,
                    content=reminder_content
                )
                logger.info(f"Morning of reminder scheduled for {morning_of}")
            
            # 3 hours before reminder
            three_hours_before = scheduled_time - timedelta(hours=3)
            if three_hours_before > get_current_time():
                reminder_content = self._get_three_hours_before_reminder(appointment_data)
                db_service.create_followup(
                    lead_id=lead['id'],
                    message_type='three_hours_before_reminder',
                    send_at=three_hours_before,
                    content=reminder_content
                )
                logger.info(f"3 hours before reminder scheduled for {three_hours_before}")
            
        except Exception as e:
            logger.error(f"Error scheduling reminder messages: {e}")
    
    def _send_appointment_confirmation(self, lead: Dict, appointment_data: Dict):
        """Send appointment confirmation message via WhatsApp"""
        try:
            scheduled_time = datetime.fromisoformat(appointment_data['scheduled_time'])
            formatted_time = scheduled_time.strftime('%d/%m/%Y בשעה %H:%M')
            
            confirmation_msg = f"""
🎉 מעולה! הפגישה נקבעה בהצלחה!

📅 תאריך ושעה: {formatted_time}
📍 מיקום: {appointment_data.get('location', 'יישלח בהמשך')}
⏱️ משך: {appointment_data.get('meeting_duration', 30)} דקות

אני אשלח לך תזכורות לפני הפגישה.

יש לך שאלות נוספות? אני כאן לעזור! 😊
"""
            
            # Send via WhatsApp (this will be handled by the messaging service)
            from app.services.messaging_service import messaging_service
            messaging_service.send_message_to_lead(lead['id'], confirmation_msg)
            
        except Exception as e:
            logger.error(f"Error sending appointment confirmation: {e}")
    
    def _send_cancellation_notice(self, appointment: Dict):
        """Send cancellation notice via WhatsApp"""
        try:
            cancellation_msg = """
😔 הפגישה שלנו בוטלה.

אם אתה עדיין מעוניין לראות דירות, אני יכול לעזור לך לתאם פגישה חדשה.

פשוט כתב לי ואני אסדר הכל! 😊
"""
            
            from app.services.messaging_service import messaging_service
            messaging_service.send_message_to_lead(appointment['lead_id'], cancellation_msg)
            
        except Exception as e:
            logger.error(f"Error sending cancellation notice: {e}")
    
    def _cancel_pending_followups(self, lead_id: int):
        """Cancel pending followup messages for a lead"""
        try:
            db_service.cancel_pending_followups(lead_id)
            logger.info(f"Canceled pending followups for lead {lead_id}")
        except Exception as e:
            logger.error(f"Error canceling pending followups for lead {lead_id}: {e}")
    
    def _normalize_time_preference(self, preference: str) -> Optional[str]:
        """Normalize time preference to standard format"""
        pref_lower = preference.lower().strip()
        
        # Morning patterns
        morning_patterns = ['בוקר', 'morning', 'בקר', 'בוקרים', 'בבוקר']
        # Afternoon patterns
        afternoon_patterns = ['אחר הצהריים', 'אחרי הצהריים', 'צהריים', 'afternoon', 'אחה\"צ']
        # Evening patterns
        evening_patterns = ['ערב', 'בערב', 'ערבים', 'evening', 'לילה']
        
        for pattern in morning_patterns:
            if pattern in pref_lower:
                return 'morning'
        
        for pattern in afternoon_patterns:
            if pattern in pref_lower:
                return 'afternoon'
        
        for pattern in evening_patterns:
            if pattern in pref_lower:
                return 'evening'
        
        return None
    
    def _get_time_preference_clarification(self) -> str:
        """Get message for clarifying time preference"""
        return ("לא הבנתי איזה מועד אתה מעדיף. 🤔\n\n"
               "אנא בחר אחת מהאפשרויות:\n"
               "🌅 בוקר (9:00-12:00)\n"
               "☀️ אחר הצהריים (13:00-17:00)\n"
               "🌙 ערב (18:00-21:00)\n\n"
               "פשוט כתב 'בוקר', 'אחר הצהריים' או 'ערב'")
    
    def _generate_scheduling_message(self, time_preference: str, calendly_link: str) -> str:
        """Generate scheduling message with Calendly link"""
        time_labels = {
            'morning': 'בבוקר (9:00-12:00)',
            'afternoon': 'אחר הצהריים (13:00-17:00)',
            'evening': 'בערב (18:00-21:00)'
        }
        
        time_label = time_labels.get(time_preference, time_preference)
        
        return f"""
מעולה! 🎉

אני מכין עבורך קישור לתיאום פגישת צפייה {time_label}.

👇 לחץ על הקישור הזה לבחירת התאריך והשעה המדויקים:

{calendly_link}

הפגישה תקח בערך 30 דקות, ואני אלווה אותך לראות את הדירות שהכי מתאימות לך.

לאחר שתבחר מועד, אני אשלח לך תזכורות ופרטים נוספים! 😊
"""
    
    def _get_evening_before_reminder(self, appointment_data: Dict) -> str:
        """Get evening before reminder content"""
        scheduled_time = datetime.fromisoformat(appointment_data['scheduled_time'])
        formatted_time = scheduled_time.strftime('%H:%M')
        
        return f"""
היי! 👋

רק להזכיר שמחר בשעה {formatted_time} יש לנו פגישת צפייה בדירות! 🏠

אני מצפה לפגוש אותך ולהציג לך כמה דירות מעולות.

יש שאלות לפני מחר? אני כאן! 😊
"""
    
    def _get_morning_of_reminder(self, appointment_data: Dict) -> str:
        """Get morning of reminder content"""
        scheduled_time = datetime.fromisoformat(appointment_data['scheduled_time'])
        formatted_time = scheduled_time.strftime('%H:%M')
        
        return f"""
בוקר טוב! ☀️

רק להזכיר שהיום בשעה {formatted_time} יש לנו פגישת צפייה בדירות!

📍 המיקום: {appointment_data.get('location', 'יישלח בקרוב')}

נתראה בקרוב! 😊
"""
    
    def _get_three_hours_before_reminder(self, appointment_data: Dict) -> str:
        """Get 3 hours before reminder content"""
        scheduled_time = datetime.fromisoformat(appointment_data['scheduled_time'])
        formatted_time = scheduled_time.strftime('%H:%M')
        
        return f"""
היי! ⏰

עוד 3 שעות יש לנו פגישה בשעה {formatted_time}!

רק כדי להיות בטוח שאתה זוכר 😊

מחכה לפגוש אותך! 🏠
"""


# Global Calendly service instance
calendly_service = CalendlyService()
