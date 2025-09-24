"""
Scheduler service for background tasks and automated messaging.
Handles reminder scheduling, abandoned lead follow-ups, and daily metrics.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from flask import current_app
from app.services.database_service import db_service
from app.services.messaging_service import messaging_service
from app.config import get_current_time

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing background scheduled tasks"""
    
    def __init__(self):
        self.scheduler = None
        self._initialize_scheduler()
    
    def _initialize_scheduler(self):
        """Initialize the background scheduler"""
        try:
            self.scheduler = BackgroundScheduler()
            
            # Add jobs
            self._add_reminder_job()
            self._add_abandoned_lead_job()
            self._add_daily_metrics_job()
            
            logger.info("Background scheduler initialized with all jobs")
            
        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {e}")
            raise
    
    def start(self):
        """Start the scheduler"""
        try:
            if self.scheduler and not self.scheduler.running:
                self.scheduler.start()
                logger.info("Background scheduler started successfully")
            else:
                logger.warning("Scheduler already running or not initialized")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
    
    def stop(self):
        """Stop the scheduler"""
        try:
            if self.scheduler and self.scheduler.running:
                self.scheduler.shutdown(wait=False)
                logger.info("Background scheduler stopped")
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")
    
    def _add_reminder_job(self):
        """Add job for processing reminder messages"""
        self.scheduler.add_job(
            func=self.process_reminder_messages,
            trigger=IntervalTrigger(minutes=5),
            id='reminder_processor',
            name='Process Reminder Messages',
            replace_existing=True,
            max_instances=1
        )
        logger.info("Reminder processor job added (every 5 minutes)")
    
    def _add_abandoned_lead_job(self):
        """Add job for following up with abandoned leads"""
        self.scheduler.add_job(
            func=self.process_abandoned_leads,
            trigger=IntervalTrigger(hours=1),
            id='abandoned_lead_processor',
            name='Process Abandoned Leads',
            replace_existing=True,
            max_instances=1
        )
        logger.info("Abandoned lead processor job added (every hour)")
    
    def _add_daily_metrics_job(self):
        """Add job for collecting daily metrics"""
        self.scheduler.add_job(
            func=self.collect_daily_metrics,
            trigger=CronTrigger(hour=23, minute=55),  # 11:55 PM daily
            id='daily_metrics_collector',
            name='Collect Daily Metrics',
            replace_existing=True,
            max_instances=1
        )
        logger.info("Daily metrics collector job added (daily at 23:55)")
    
    def process_reminder_messages(self):
        """Process and send scheduled reminder messages"""
        try:
            logger.info("Processing reminder messages...")
            
            # Get pending followups
            pending_followups = db_service.get_pending_followups()
            
            if not pending_followups:
                logger.debug("No pending followups to process")
                return
            
            logger.info(f"Processing {len(pending_followups)} pending followups")
            
            sent_count = 0
            failed_count = 0
            
            for followup in pending_followups:
                try:
                    # Send the message
                    lead = followup.get('leads')
                    if not lead:
                        logger.error(f"No lead data for followup {followup['id']}")
                        continue
                    
                    success = messaging_service.send_message_to_phone(
                        lead['phone_number'], 
                        followup['content']
                    )
                    
                    if success:
                        # Mark as sent
                        db_service.mark_followup_sent(followup['id'])
                        sent_count += 1
                        logger.info(f"Reminder sent to lead {lead['id']}: {followup['message_type']}")
                    else:
                        failed_count += 1
                        logger.error(f"Failed to send reminder to lead {lead['id']}")
                        
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error processing followup {followup['id']}: {e}")
            
            logger.info(f"Reminder processing complete: {sent_count} sent, {failed_count} failed")
            
        except Exception as e:
            logger.error(f"Error in reminder processor: {e}")
    
    def process_abandoned_leads(self):
        """Process and follow up with abandoned leads"""
        try:
            logger.info("Processing abandoned leads...")
            
            # Get configuration
            abandoned_hours = current_app.config.get('ABANDONED_LEAD_HOURS', 4)
            
            # Get abandoned leads
            abandoned_leads = db_service.get_abandoned_leads(abandoned_hours)
            
            if not abandoned_leads:
                logger.debug("No abandoned leads found")
                return
            
            logger.info(f"Found {len(abandoned_leads)} abandoned leads")
            
            sent_count = 0
            failed_count = 0
            
            for lead in abandoned_leads:
                try:
                    # Generate nudge message
                    nudge_message = self._generate_nudge_message(lead)
                    
                    # Send the nudge
                    success = messaging_service.send_message_to_phone(
                        lead['phone_number'], 
                        nudge_message
                    )
                    
                    if success:
                        # Update last interaction time
                        db_service.update_lead(lead['id'], {
                            'last_interaction': get_current_time().isoformat()
                        })
                        
                        # Log the nudge
                        db_service.log_conversation(lead['id'], 'bot', nudge_message)
                        
                        sent_count += 1
                        logger.info(f"Nudge sent to abandoned lead {lead['id']}")
                    else:
                        failed_count += 1
                        logger.error(f"Failed to send nudge to lead {lead['id']}")
                        
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error processing abandoned lead {lead['id']}: {e}")
            
            logger.info(f"Abandoned lead processing complete: {sent_count} sent, {failed_count} failed")
            
        except Exception as e:
            logger.error(f"Error in abandoned lead processor: {e}")
    
    def collect_daily_metrics(self):
        """Collect and save daily metrics"""
        try:
            logger.info("Collecting daily metrics...")
            
            current_time = get_current_time()
            today = current_time.date()
            
            # Calculate metrics for today
            metrics = self._calculate_daily_metrics(today)
            
            # Save metrics
            db_service.save_daily_metrics(current_time, metrics)
            
            logger.info(f"Daily metrics collected and saved: {metrics}")
            
        except Exception as e:
            logger.error(f"Error collecting daily metrics: {e}")
    
    def _generate_nudge_message(self, lead: Dict) -> str:
        """Generate nudge message for abandoned leads"""
        name = lead.get('name', 'שם')
        
        # Different messages based on lead profile
        budget = lead.get('budget')
        rooms = lead.get('rooms')
        
        if budget and rooms:
            return f"""היי {name}! 👋

ראיתי שהתחלנו לחפש עבורך דירה של {rooms} חדרים בתקציב של {budget} ש"ח, אבל עדיין לא סיימנו את התהליך.

יש לי כמה דירות חדשות שהגיעו שעשויות לעניין אותך! 🏠

אשמח לשמוע איך אפשר להמשיך לעזור לך 😊"""
        else:
            return f"""היי {name}! 👋

ראיתי שהתחלנו לחפש עבורך דירה, אבל עדיין לא סיימנו את התהליך.

יש לי כמה דירות נהדרות שהגיעו שעשויות לעניין אותך! 🏠

אשמח לשמוע איך אפשר להמשיך לעזור לך 😊"""
    
    def _calculate_daily_metrics(self, date) -> Dict:
        """Calculate metrics for a specific date"""
        try:
            # Date range for the day
            start_of_day = datetime.combine(date, datetime.min.time())
            end_of_day = datetime.combine(date, datetime.max.time())
            
            # Total inquiries (new leads created today)
            total_inquiries = db_service.count_leads_by_date_range(
                start_of_day, end_of_day, stage=None
            )
            
            # Qualified leads (leads that reached 'qualified' stage today)
            qualified_leads = db_service.count_leads_by_date_range(
                start_of_day, end_of_day, stage='qualified'
            )
            
            # Tours scheduled (appointments created today)
            tours_scheduled = db_service.count_appointments_by_date_range(
                start_of_day, end_of_day, status='scheduled'
            )
            
            # Tours completed (appointments that happened today)
            tours_completed = db_service.count_completed_appointments_by_date(date)
            
            return {
                'total_inquiries': total_inquiries,
                'qualified_leads': qualified_leads,
                'tours_scheduled': tours_scheduled,
                'tours_completed': tours_completed
            }
            
        except Exception as e:
            logger.error(f"Error calculating daily metrics for {date}: {e}")
            return {
                'total_inquiries': 0,
                'qualified_leads': 0,
                'tours_scheduled': 0,
                'tours_completed': 0
            }
    
    def schedule_appointment_reminders(self, lead_id: int, appointment_time: datetime):
        """Schedule reminders for a specific appointment"""
        try:
            logger.info(f"Scheduling appointment reminders for lead {lead_id}")
            
            # Evening before reminder (if appointment is not tomorrow)
            evening_before = appointment_time.replace(hour=19, minute=0, second=0) - timedelta(days=1)
            if evening_before > get_current_time():
                db_service.create_followup(
                    lead_id=lead_id,
                    message_type='evening_before_reminder',
                    send_at=evening_before,
                    content=self._get_evening_reminder_content(appointment_time)
                )
            
            # Morning of reminder
            morning_of = appointment_time.replace(hour=9, minute=0, second=0)
            if morning_of > get_current_time() and morning_of < appointment_time:
                db_service.create_followup(
                    lead_id=lead_id,
                    message_type='morning_of_reminder',
                    send_at=morning_of,
                    content=self._get_morning_reminder_content(appointment_time)
                )
            
            # 3 hours before reminder
            three_hours_before = appointment_time - timedelta(hours=3)
            if three_hours_before > get_current_time():
                db_service.create_followup(
                    lead_id=lead_id,
                    message_type='three_hours_before_reminder',
                    send_at=three_hours_before,
                    content=self._get_three_hours_reminder_content(appointment_time)
                )
            
            logger.info(f"Appointment reminders scheduled for lead {lead_id}")
            
        except Exception as e:
            logger.error(f"Error scheduling appointment reminders for lead {lead_id}: {e}")
    
    def _get_evening_reminder_content(self, appointment_time: datetime) -> str:
        """Get evening before reminder content"""
        formatted_time = appointment_time.strftime('%H:%M')
        return f"""היי! 👋

רק להזכיר שמחר בשעה {formatted_time} יש לנו פגישת צפייה בדירות! 🏠

אני מצפה לפגוש אותך ולהציג לך כמה דירות מעולות.

יש שאלות לפני מחר? אני כאן! 😊"""
    
    def _get_morning_reminder_content(self, appointment_time: datetime) -> str:
        """Get morning of reminder content"""
        formatted_time = appointment_time.strftime('%H:%M')
        return f"""בוקר טוב! ☀️

רק להזכיר שהיום בשעה {formatted_time} יש לנו פגישת צפייה בדירות!

נתראה בקרוב! 😊"""
    
    def _get_three_hours_reminder_content(self, appointment_time: datetime) -> str:
        """Get 3 hours before reminder content"""
        formatted_time = appointment_time.strftime('%H:%M')
        return f"""היי! ⏰

עוד 3 שעות יש לנו פגישה בשעה {formatted_time}!

רק כדי להיות בטוח שאתה זוכר 😊

מחכה לפגוש אותך! 🏠"""


# Global scheduler service instance
scheduler_service = SchedulerService()
