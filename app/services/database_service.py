"""
Database service for managing all Supabase operations.
Handles all database interactions for the real estate leasing bot.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from supabase import create_client, Client
from flask import current_app
from app.config import get_current_time

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for managing all database operations with Supabase"""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self._initialized = False
    
    def _initialize_client(self):
        """Initialize Supabase client (lazy initialization)"""
        if self._initialized:
            return
            
        try:
            from flask import current_app
            url = current_app.config.get('SUPABASE_URL')
            key = current_app.config.get('SUPABASE_KEY')
            
            if not url or not key:
                raise ValueError("Supabase URL and KEY must be configured")
            
            self.client = create_client(url, key)
            self._initialized = True
            logger.info("Supabase client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise
    
    def _ensure_initialized(self):
        """Ensure the client is initialized before use"""
        if not self._initialized:
            self._initialize_client()
    
    # ==========================================
    # LEAD MANAGEMENT OPERATIONS
    # ==========================================
    
    def get_lead_by_phone(self, phone_number: str) -> Optional[Dict]:
        """Get lead by phone number"""
        try:
            self._ensure_initialized()
            logger.info(f"Fetching lead with phone: {phone_number}")
            
            response = self.client.table('leads').select('*').eq('phone_number', phone_number).execute()
            
            if response.data:
                logger.info(f"Lead found for phone: {phone_number}")
                return response.data[0]
            
            logger.info(f"No lead found for phone: {phone_number}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching lead by phone {phone_number}: {e}")
            raise
    
    def create_lead(self, phone_number: str, name: str) -> Dict:
        """Create a new lead"""
        try:
            self._ensure_initialized()
            logger.info(f"Creating new lead: {name} ({phone_number})")
            
            lead_data = {
                'phone_number': phone_number,
                'name': name,
                'stage': 'new',
                'created_at': get_current_time().isoformat(),
                'last_interaction': get_current_time().isoformat()
            }
            
            response = self.client.table('leads').insert(lead_data).execute()
            
            if response.data:
                new_lead = response.data[0]
                logger.info(f"Lead created successfully with ID: {new_lead['id']}")
                return new_lead
            
            raise Exception("Failed to create lead - no data returned")
            
        except Exception as e:
            logger.error(f"Error creating lead for {phone_number}: {e}")
            raise
    
    def update_lead(self, lead_id: int, updates: Dict) -> Dict:
        """Update lead information"""
        try:
            self._ensure_initialized()
            logger.info(f"Updating lead {lead_id} with data: {updates}")
            
            # Always update last_interaction
            updates['last_interaction'] = get_current_time().isoformat()
            
            response = self.client.table('leads').update(updates).eq('id', lead_id).execute()
            
            if response.data:
                updated_lead = response.data[0]
                logger.info(f"Lead {lead_id} updated successfully")
                return updated_lead
            
            raise Exception("Failed to update lead - no data returned")
            
        except Exception as e:
            logger.error(f"Error updating lead {lead_id}: {e}")
            raise
    
    def get_abandoned_leads(self, hours_threshold: int) -> List[Dict]:
        """Get leads that haven't been contacted in the specified hours"""
        try:
            self._ensure_initialized()
            cutoff_time = get_current_time() - timedelta(hours=hours_threshold)
            logger.info(f"Fetching abandoned leads since: {cutoff_time}")
            
            response = (self.client.table('leads')
                       .select('*')
                       .eq('stage', 'qualified')
                       .lt('last_interaction', cutoff_time.isoformat())
                       .execute())
            
            logger.info(f"Found {len(response.data)} abandoned leads")
            return response.data
            
        except Exception as e:
            logger.error(f"Error fetching abandoned leads: {e}")
            raise
    
    # ==========================================
    # PROPERTY AND UNIT OPERATIONS
    # ==========================================
    
    def get_available_units(self, filters: Optional[Dict] = None) -> List[Dict]:
        """Get available units with optional filters"""
        try:
            logger.info(f"Fetching available units with filters: {filters}")
            
            query = (self.client.table('units')
                    .select('*, properties(*)')
                    .eq('status', 'available'))
            
            if filters:
                if 'min_rooms' in filters:
                    query = query.gte('rooms', filters['min_rooms'])
                if 'max_rooms' in filters:
                    query = query.lte('rooms', filters['max_rooms'])
                if 'max_price' in filters:
                    query = query.lte('price', filters['max_price'])
                if 'min_price' in filters:
                    query = query.gte('price', filters['min_price'])
                if 'parking' in filters:
                    query = query.eq('has_parking', filters['parking'])
            
            response = query.execute()
            
            logger.info(f"Found {len(response.data)} available units")
            return response.data
            
        except Exception as e:
            logger.error(f"Error fetching available units: {e}")
            raise
    
    def get_unit_by_id(self, unit_id: int) -> Optional[Dict]:
        """Get unit by ID with property details"""
        try:
            logger.info(f"Fetching unit with ID: {unit_id}")
            
            response = (self.client.table('units')
                       .select('*, properties(*)')
                       .eq('id', unit_id)
                       .execute())
            
            if response.data:
                logger.info(f"Unit {unit_id} found")
                return response.data[0]
            
            logger.warning(f"Unit {unit_id} not found")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching unit {unit_id}: {e}")
            raise
    
    def update_unit_status(self, unit_id: int, status: str) -> Dict:
        """Update unit status (available, hold, rented)"""
        try:
            logger.info(f"Updating unit {unit_id} status to: {status}")
            
            response = (self.client.table('units')
                       .update({'status': status, 'updated_at': get_current_time().isoformat()})
                       .eq('id', unit_id)
                       .execute())
            
            if response.data:
                logger.info(f"Unit {unit_id} status updated to {status}")
                return response.data[0]
            
            raise Exception("Failed to update unit status")
            
        except Exception as e:
            logger.error(f"Error updating unit {unit_id} status: {e}")
            raise
    
    # ==========================================
    # APPOINTMENT OPERATIONS
    # ==========================================
    
    def create_appointment(self, lead_id: int, unit_id: int, calendly_data: Dict) -> Dict:
        """Create a new appointment"""
        try:
            logger.info(f"Creating appointment for lead {lead_id}, unit {unit_id}")
            
            appointment_data = {
                'lead_id': lead_id,
                'unit_id': unit_id,
                'calendly_event_id': calendly_data.get('event_id'),
                'scheduled_time': calendly_data.get('scheduled_time'),
                'attendee_email': calendly_data.get('attendee_email'),
                'status': 'scheduled',
                'created_at': get_current_time().isoformat()
            }
            
            response = self.client.table('appointments').insert(appointment_data).execute()
            
            if response.data:
                new_appointment = response.data[0]
                logger.info(f"Appointment created with ID: {new_appointment['id']}")
                return new_appointment
            
            raise Exception("Failed to create appointment")
            
        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            raise
    
    def get_upcoming_appointments(self, hours_ahead: int = 24) -> List[Dict]:
        """Get appointments scheduled within the next specified hours"""
        try:
            start_time = get_current_time()
            end_time = start_time + timedelta(hours=hours_ahead)
            
            logger.info(f"Fetching appointments between {start_time} and {end_time}")
            
            response = (self.client.table('appointments')
                       .select('*, leads(*), units(*, properties(*))')
                       .gte('scheduled_time', start_time.isoformat())
                       .lte('scheduled_time', end_time.isoformat())
                       .eq('status', 'scheduled')
                       .execute())
            
            logger.info(f"Found {len(response.data)} upcoming appointments")
            return response.data
            
        except Exception as e:
            logger.error(f"Error fetching upcoming appointments: {e}")
            raise
    
    # ==========================================
    # CONVERSATION LOG OPERATIONS
    # ==========================================
    
    def log_conversation(self, lead_id: int, message_type: str, content: str, 
                        message_id: Optional[str] = None) -> Dict:
        """Log a conversation message"""
        try:
            logger.debug(f"Logging {message_type} message for lead {lead_id}")
            
            log_data = {
                'lead_id': lead_id,
                'message_type': message_type,  # 'user' or 'bot'
                'content': content,
                'message_id': message_id,
                'timestamp': get_current_time().isoformat()
            }
            
            response = self.client.table('conversation_log').insert(log_data).execute()
            
            if response.data:
                logger.debug(f"Conversation logged with ID: {response.data[0]['id']}")
                return response.data[0]
            
            raise Exception("Failed to log conversation")
            
        except Exception as e:
            logger.error(f"Error logging conversation for lead {lead_id}: {e}")
            raise
    
    def get_conversation_history(self, lead_id: int, limit: int = 10) -> List[Dict]:
        """Get conversation history for a lead"""
        try:
            logger.debug(f"Fetching conversation history for lead {lead_id}")
            
            response = (self.client.table('conversation_log')
                       .select('*')
                       .eq('lead_id', lead_id)
                       .order('timestamp', desc=False)
                       .limit(limit)
                       .execute())
            
            logger.debug(f"Retrieved {len(response.data)} conversation messages")
            return response.data
            
        except Exception as e:
            logger.error(f"Error fetching conversation history for lead {lead_id}: {e}")
            raise
    
    # ==========================================
    # FOLLOWUP OPERATIONS
    # ==========================================
    
    def create_followup(self, lead_id: int, message_type: str, send_at: datetime, 
                       content: str) -> Dict:
        """Create a scheduled followup message"""
        try:
            logger.info(f"Creating {message_type} followup for lead {lead_id} at {send_at}")
            
            followup_data = {
                'lead_id': lead_id,
                'message_type': message_type,
                'content': content,
                'send_at': send_at.isoformat(),
                'status': 'pending',
                'created_at': get_current_time().isoformat()
            }
            
            response = self.client.table('followups').insert(followup_data).execute()
            
            if response.data:
                logger.info(f"Followup created with ID: {response.data[0]['id']}")
                return response.data[0]
            
            raise Exception("Failed to create followup")
            
        except Exception as e:
            logger.error(f"Error creating followup for lead {lead_id}: {e}")
            raise
    
    def get_pending_followups(self) -> List[Dict]:
        """Get all pending followups that should be sent"""
        try:
            current_time = get_current_time()
            logger.info(f"Fetching pending followups up to: {current_time}")
            
            response = (self.client.table('followups')
                       .select('*, leads(*)')
                       .eq('status', 'pending')
                       .lte('send_at', current_time.isoformat())
                       .execute())
            
            logger.info(f"Found {len(response.data)} pending followups")
            return response.data
            
        except Exception as e:
            logger.error(f"Error fetching pending followups: {e}")
            raise
    
    def mark_followup_sent(self, followup_id: int) -> Dict:
        """Mark a followup as sent"""
        try:
            logger.info(f"Marking followup {followup_id} as sent")
            
            response = (self.client.table('followups')
                       .update({
                           'status': 'sent',
                           'sent_at': get_current_time().isoformat()
                       })
                       .eq('id', followup_id)
                       .execute())
            
            if response.data:
                logger.info(f"Followup {followup_id} marked as sent")
                return response.data[0]
            
            raise Exception("Failed to mark followup as sent")
            
        except Exception as e:
            logger.error(f"Error marking followup {followup_id} as sent: {e}")
            raise
    
    # ==========================================
    # METRICS OPERATIONS
    # ==========================================
    
    def save_daily_metrics(self, date: datetime, metrics: Dict) -> Dict:
        """Save daily metrics"""
        try:
            logger.info(f"Saving daily metrics for {date.date()}")
            
            metrics_data = {
                'date': date.date().isoformat(),
                'total_inquiries': metrics.get('total_inquiries', 0),
                'qualified_leads': metrics.get('qualified_leads', 0),
                'tours_scheduled': metrics.get('tours_scheduled', 0),
                'tours_completed': metrics.get('tours_completed', 0),
                'created_at': get_current_time().isoformat()
            }
            
            # Try to update existing record or insert new one
            existing = (self.client.table('metrics_daily')
                       .select('*')
                       .eq('date', date.date().isoformat())
                       .execute())
            
            if existing.data:
                # Update existing
                response = (self.client.table('metrics_daily')
                           .update(metrics_data)
                           .eq('date', date.date().isoformat())
                           .execute())
            else:
                # Insert new
                response = self.client.table('metrics_daily').insert(metrics_data).execute()
            
            if response.data:
                logger.info(f"Daily metrics saved for {date.date()}")
                return response.data[0]
            
            raise Exception("Failed to save daily metrics")
            
        except Exception as e:
            logger.error(f"Error saving daily metrics for {date.date()}: {e}")
            raise
    
    def get_daily_metrics(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get daily metrics for a date range"""
        try:
            logger.info(f"Fetching daily metrics from {start_date.date()} to {end_date.date()}")
            
            response = (self.client.table('metrics_daily')
                       .select('*')
                       .gte('date', start_date.date().isoformat())
                       .lte('date', end_date.date().isoformat())
                       .order('date', desc=True)
                       .execute())
            
            logger.info(f"Retrieved {len(response.data)} daily metric records")
            return response.data
            
        except Exception as e:
            logger.error(f"Error fetching daily metrics: {e}")
            raise
    
    # ==========================================
    # ADDITIONAL HELPER METHODS
    # ==========================================
    
    def get_lead_by_id(self, lead_id: int) -> Optional[Dict]:
        """Get lead by ID"""
        try:
            logger.debug(f"Fetching lead with ID: {lead_id}")
            
            response = self.client.table('leads').select('*').eq('id', lead_id).execute()
            
            if response.data:
                return response.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error fetching lead {lead_id}: {e}")
            raise
    
    def get_recent_leads_by_stage(self, stage: str, hours: int) -> List[Dict]:
        """Get recent leads by stage within specified hours"""
        try:
            cutoff_time = get_current_time() - timedelta(hours=hours)
            
            response = (self.client.table('leads')
                       .select('*')
                       .eq('stage', stage)
                       .gte('last_interaction', cutoff_time.isoformat())
                       .order('last_interaction', desc=True)
                       .execute())
            
            return response.data
            
        except Exception as e:
            logger.error(f"Error fetching recent leads by stage {stage}: {e}")
            raise
    
    def get_appointment_by_calendly_id(self, calendly_event_id: str) -> Optional[Dict]:
        """Get appointment by Calendly event ID"""
        try:
            logger.debug(f"Fetching appointment with Calendly ID: {calendly_event_id}")
            
            response = (self.client.table('appointments')
                       .select('*')
                       .eq('calendly_event_id', calendly_event_id)
                       .execute())
            
            if response.data:
                return response.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error fetching appointment by Calendly ID {calendly_event_id}: {e}")
            raise
    
    def update_appointment_status(self, appointment_id: int, status: str) -> Dict:
        """Update appointment status"""
        try:
            logger.info(f"Updating appointment {appointment_id} status to: {status}")
            
            response = (self.client.table('appointments')
                       .update({
                           'status': status,
                           'updated_at': get_current_time().isoformat()
                       })
                       .eq('id', appointment_id)
                       .execute())
            
            if response.data:
                return response.data[0]
            
            raise Exception("Failed to update appointment status")
            
        except Exception as e:
            logger.error(f"Error updating appointment {appointment_id} status: {e}")
            raise
    
    def cancel_pending_followups(self, lead_id: int) -> int:
        """Cancel all pending followups for a lead"""
        try:
            logger.info(f"Canceling pending followups for lead {lead_id}")
            
            response = (self.client.table('followups')
                       .update({
                           'status': 'canceled',
                           'sent_at': get_current_time().isoformat()
                       })
                       .eq('lead_id', lead_id)
                       .eq('status', 'pending')
                       .execute())
            
            canceled_count = len(response.data) if response.data else 0
            logger.info(f"Canceled {canceled_count} pending followups for lead {lead_id}")
            
            return canceled_count
            
        except Exception as e:
            logger.error(f"Error canceling followups for lead {lead_id}: {e}")
            raise
    
    def count_leads_by_date_range(self, start_date: datetime, end_date: datetime, 
                                 stage: Optional[str] = None) -> int:
        """Count leads created in date range, optionally filtered by stage"""
        try:
            query = (self.client.table('leads')
                    .select('id', count='exact')
                    .gte('created_at', start_date.isoformat())
                    .lte('created_at', end_date.isoformat()))
            
            if stage:
                query = query.eq('stage', stage)
            
            response = query.execute()
            
            return response.count if response.count else 0
            
        except Exception as e:
            logger.error(f"Error counting leads by date range: {e}")
            return 0
    
    def count_appointments_by_date_range(self, start_date: datetime, end_date: datetime, 
                                       status: Optional[str] = None) -> int:
        """Count appointments created in date range, optionally filtered by status"""
        try:
            query = (self.client.table('appointments')
                    .select('id', count='exact')
                    .gte('created_at', start_date.isoformat())
                    .lte('created_at', end_date.isoformat()))
            
            if status:
                query = query.eq('status', status)
            
            response = query.execute()
            
            return response.count if response.count else 0
            
        except Exception as e:
            logger.error(f"Error counting appointments by date range: {e}")
            return 0
    
    def count_completed_appointments_by_date(self, date: datetime.date) -> int:
        """Count appointments completed on a specific date"""
        try:
            start_of_day = datetime.combine(date, datetime.min.time())
            end_of_day = datetime.combine(date, datetime.max.time())
            
            response = (self.client.table('appointments')
                       .select('id', count='exact')
                       .eq('status', 'completed')
                       .gte('scheduled_time', start_of_day.isoformat())
                       .lte('scheduled_time', end_of_day.isoformat())
                       .execute())
            
            return response.count if response.count else 0
            
        except Exception as e:
            logger.error(f"Error counting completed appointments for {date}: {e}")
            return 0


# Global database service instance
db_service = DatabaseService()
