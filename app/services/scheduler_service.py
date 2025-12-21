import logging
from datetime import datetime, time, timedelta
from typing import List, Dict, Any, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from .firebase_service import firebase_service
from ..models.notification import (
    NotificationRequest,
    IndividualNotificationRequest,
    TopicNotificationRequest,
    GameNotificationTemplates,
    NotificationType,
    ScheduledNotificationRequest
)

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for scheduling and managing automated notifications."""
    
    def __init__(self):
        self.scheduler = None
        self._initialize_scheduler()
    
    def _initialize_scheduler(self):
        """Initialize the APScheduler instance."""
        jobstores = {
            'default': MemoryJobStore(),
        }
        executors = {
            'default': ThreadPoolExecutor(20),
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 3
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores, 
            executors=executors, 
            job_defaults=job_defaults
        )
        logger.info("Scheduler service initialized")
    
    def start(self):
        """Start the scheduler."""
        if self.scheduler and not self.scheduler.running:
            self.scheduler.start()
            self._setup_recurring_jobs()
            logger.info("Scheduler service started")
    
    def shutdown(self):
        """Shutdown the scheduler."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler service stopped")
    
    def _setup_recurring_jobs(self):
        """Set up recurring notification jobs."""
        # Daily challenge reminder - 9:00 AM every day
        self.scheduler.add_job(
            func=self._send_daily_challenge_reminder,
            trigger=CronTrigger(hour=9, minute=0),
            id='daily_challenge_reminder',
            name='Daily Challenge Reminder',
            replace_existing=True
        )
        
        # Weekly leaderboard update - Sunday 6:00 PM
        self.scheduler.add_job(
            func=self._send_weekly_leaderboard_update,
            trigger=CronTrigger(day_of_week=6, hour=18, minute=0),
            id='weekly_leaderboard_update',
            name='Weekly Leaderboard Update',
            replace_existing=True
        )
        
        # Retention campaign for inactive users - every 3 days at 2:00 PM
        self.scheduler.add_job(
            func=self._send_retention_notifications,
            trigger=CronTrigger(hour=14, minute=0),
            id='retention_campaign',
            name='User Retention Campaign',
            replace_existing=True
        )
        
        logger.info("Recurring notification jobs scheduled")
    
    async def schedule_notification(self, request: ScheduledNotificationRequest) -> Dict[str, Any]:
        """Schedule a notification for future delivery."""
        try:
            job_id = f"scheduled_notification_{datetime.utcnow().timestamp()}"
            
            # Create the trigger for the scheduled time
            trigger = DateTrigger(run_date=request.scheduled_time)
            
            # Schedule the job
            self.scheduler.add_job(
                func=self._send_scheduled_notification,
                trigger=trigger,
                args=[request],
                id=job_id,
                name=f"Scheduled: {request.title}",
                replace_existing=True
            )
            
            logger.info(f"Notification scheduled for {request.scheduled_time}, job ID: {job_id}")
            
            return {
                "success": True,
                "message": "Notification scheduled successfully",
                "job_id": job_id,
                "scheduled_time": request.scheduled_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to schedule notification: {e}")
            return {
                "success": False,
                "message": f"Failed to schedule notification: {str(e)}",
                "error": str(e)
            }
    
    async def cancel_scheduled_notification(self, job_id: str) -> Dict[str, Any]:
        """Cancel a scheduled notification."""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Scheduled notification cancelled: {job_id}")
            
            return {
                "success": True,
                "message": "Scheduled notification cancelled"
            }
            
        except Exception as e:
            logger.error(f"Failed to cancel scheduled notification: {e}")
            return {
                "success": False,
                "message": f"Failed to cancel notification: {str(e)}",
                "error": str(e)
            }
    
    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """Get list of all scheduled jobs."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        return jobs
    
    async def _send_scheduled_notification(self, request: ScheduledNotificationRequest):
        """Execute a scheduled notification."""
        try:
            logger.info(f"Executing scheduled notification: {request.title}")
            
            if request.recipient_type == "topics":
                # Send to topics
                for topic in request.recipients:
                    topic_request = TopicNotificationRequest(
                        title=request.title,
                        body=request.body,
                        notification_type=request.notification_type,
                        priority=request.priority,
                        data=request.data,
                        image_url=request.image_url,
                        route=request.route,
                        route_params=request.route_params,
                        topic=topic
                    )
                    await firebase_service.send_to_topic(topic_request)
            else:
                # Send to individual tokens
                for token in request.recipients:
                    individual_request = IndividualNotificationRequest(
                        title=request.title,
                        body=request.body,
                        notification_type=request.notification_type,
                        priority=request.priority,
                        data=request.data,
                        image_url=request.image_url,
                        route=request.route,
                        route_params=request.route_params,
                        fcm_token=token
                    )
                    await firebase_service.send_to_token(individual_request)
            
            logger.info(f"Scheduled notification sent successfully: {request.title}")
            
        except Exception as e:
            logger.error(f"Failed to send scheduled notification: {e}")
    
    async def _send_daily_challenge_reminder(self):
        """Send daily challenge reminder to all users."""
        try:
            logger.info("Sending daily challenge reminders")
            
            notification = GameNotificationTemplates.daily_challenge()
            topic_request = TopicNotificationRequest(
                title=notification.title,
                body=notification.body,
                notification_type=notification.notification_type,
                priority=notification.priority,
                data=notification.data,
                route=notification.route,
                topic="daily_challenge"  # Users subscribed to daily challenges
            )
            
            result = await firebase_service.send_to_topic(topic_request)
            logger.info(f"Daily challenge reminder sent: {result.message}")
            
        except Exception as e:
            logger.error(f"Failed to send daily challenge reminder: {e}")
    
    async def _send_weekly_leaderboard_update(self):
        """Send weekly leaderboard update notification."""
        try:
            logger.info("Sending weekly leaderboard update")
            
            notification = NotificationRequest(
                title="📊 Weekly Leaderboard Updated!",
                body="See how you ranked this week and check out the new challenges!",
                notification_type=NotificationType.SPECIAL_EVENT,
                route="leaderboard",
                data={"action": "weekly_update", "period": "weekly"}
            )
            
            topic_request = TopicNotificationRequest(
                title=notification.title,
                body=notification.body,
                notification_type=notification.notification_type,
                priority=notification.priority,
                data=notification.data,
                route=notification.route,
                topic="leaderboard_updates"
            )
            
            result = await firebase_service.send_to_topic(topic_request)
            logger.info(f"Weekly leaderboard update sent: {result.message}")
            
        except Exception as e:
            logger.error(f"Failed to send weekly leaderboard update: {e}")
    
    async def _send_retention_notifications(self):
        """Send retention notifications to inactive users."""
        try:
            logger.info("Sending retention notifications")
            
            # This would typically query your user database to find inactive users
            # For now, we'll send a general retention message to the retention topic
            
            notification = NotificationRequest(
                title="🐍 We miss you!",
                body="Come back and beat your high score! New achievements await!",
                notification_type=NotificationType.DAILY_REMINDER,
                route="home",
                data={"action": "retention", "campaign": "comeback"}
            )
            
            topic_request = TopicNotificationRequest(
                title=notification.title,
                body=notification.body,
                notification_type=notification.notification_type,
                priority=notification.priority,
                data=notification.data,
                route=notification.route,
                topic="retention_campaign"
            )
            
            result = await firebase_service.send_to_topic(topic_request)
            logger.info(f"Retention notifications sent: {result.message}")
            
        except Exception as e:
            logger.error(f"Failed to send retention notifications: {e}")
    
    async def schedule_tournament_notifications(
        self, 
        tournament_name: str, 
        tournament_id: str,
        start_time: datetime,
        reminder_times: List[int] = [60, 15, 5]  # minutes before start
    ) -> List[str]:
        """Schedule tournament-related notifications."""
        job_ids = []
        
        try:
            # Schedule reminder notifications
            for minutes_before in reminder_times:
                reminder_time = start_time - timedelta(minutes=minutes_before)
                
                if reminder_time > datetime.utcnow():
                    notification = NotificationRequest(
                        title=f"🏆 Tournament Starting Soon!",
                        body=f"{tournament_name} starts in {minutes_before} minutes!",
                        notification_type=NotificationType.TOURNAMENT,
                        route="tournament_detail",
                        route_params={"tournament_id": tournament_id},
                        data={"tournament_id": tournament_id, "minutes_until": minutes_before}
                    )
                    
                    job_id = f"tournament_reminder_{tournament_id}_{minutes_before}min"
                    
                    self.scheduler.add_job(
                        func=self._send_tournament_reminder,
                        trigger=DateTrigger(run_date=reminder_time),
                        args=[notification, tournament_id],
                        id=job_id,
                        name=f"Tournament Reminder: {tournament_name} ({minutes_before}min)",
                        replace_existing=True
                    )
                    
                    job_ids.append(job_id)
            
            # Schedule tournament start notification
            start_notification = GameNotificationTemplates.tournament_started(tournament_name, tournament_id)
            start_job_id = f"tournament_start_{tournament_id}"
            
            self.scheduler.add_job(
                func=self._send_tournament_start,
                trigger=DateTrigger(run_date=start_time),
                args=[start_notification, tournament_id],
                id=start_job_id,
                name=f"Tournament Start: {tournament_name}",
                replace_existing=True
            )
            
            job_ids.append(start_job_id)
            
            logger.info(f"Scheduled {len(job_ids)} tournament notifications for {tournament_name}")
            return job_ids
            
        except Exception as e:
            logger.error(f"Failed to schedule tournament notifications: {e}")
            return []
    
    async def _send_tournament_reminder(self, notification: NotificationRequest, tournament_id: str):
        """Send tournament reminder notification."""
        topic_request = TopicNotificationRequest(
            title=notification.title,
            body=notification.body,
            notification_type=notification.notification_type,
            priority=notification.priority,
            data=notification.data,
            route=notification.route,
            route_params=notification.route_params,
            topic=f"tournament_{tournament_id}"
        )
        
        await firebase_service.send_to_topic(topic_request)
    
    async def _send_tournament_start(self, notification: NotificationRequest, tournament_id: str):
        """Send tournament start notification."""
        topic_request = TopicNotificationRequest(
            title=notification.title,
            body=notification.body,
            notification_type=notification.notification_type,
            priority=notification.priority,
            data=notification.data,
            route=notification.route,
            route_params=notification.route_params,
            topic="tournaments"  # General tournament topic
        )
        
        await firebase_service.send_to_topic(topic_request)


# Global scheduler service instance
scheduler_service = SchedulerService()