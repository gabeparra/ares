"""
Django management command to process scheduled tasks from Google Calendar.

This command should be run periodically (e.g., via cron or systemd timer)
to check for pending tasks and execute them.

Usage:
    python3 manage.py process_scheduled_tasks
    python3 manage.py process_scheduled_tasks --user-id default
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import json
import logging
import httpx

from api.models import ScheduledTask, GoogleCalendarCredential
from api.telegram_views import _get_telegram_chat_id_by_identifier

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process scheduled tasks from Google Calendar and execute them'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=str,
            default='default',
            help='User ID to process tasks for (default: default)',
        )
        parser.add_argument(
            '--look-ahead-minutes',
            type=int,
            default=5,
            help='How many minutes ahead to look for tasks (default: 5)',
        )

    def handle(self, *args, **options):
        user_id = options['user_id']
        look_ahead_minutes = options['look_ahead_minutes']
        
        now = timezone.now()
        look_ahead = now + timedelta(minutes=look_ahead_minutes)
        
        self.stdout.write(f'Processing scheduled tasks for user: {user_id}')
        self.stdout.write(f'Current time: {now}')
        self.stdout.write(f'Looking for tasks up to: {look_ahead}')
        
        # Find pending tasks that should be executed now
        pending_tasks = ScheduledTask.objects.filter(
            user_id=user_id,
            status=ScheduledTask.STATUS_PENDING,
            scheduled_time__lte=look_ahead,
            scheduled_time__gte=now - timedelta(minutes=5),  # Allow 5 minute window
        ).order_by('scheduled_time')
        
        task_count = pending_tasks.count()
        self.stdout.write(f'Found {task_count} pending tasks')
        
        for task in pending_tasks:
            self.stdout.write(f'\nProcessing task: {task.task_type} at {task.scheduled_time}')
            
            try:
                if task.task_type == ScheduledTask.TASK_GOOD_MORNING:
                    self._execute_good_morning_task(task, user_id)
                elif task.task_type == ScheduledTask.TASK_REMINDER:
                    self._execute_reminder_task(task, user_id)
                elif task.task_type == ScheduledTask.TASK_CUSTOM:
                    self._execute_custom_task(task, user_id)
                else:
                    self.stdout.write(self.style.WARNING(f'Unknown task type: {task.task_type}'))
                    task.status = ScheduledTask.STATUS_FAILED
                    task.error_message = f'Unknown task type: {task.task_type}'
                    task.save()
                    
            except Exception as e:
                logger.error(f'Error executing task {task.id}: {e}', exc_info=True)
                self.stdout.write(self.style.ERROR(f'Error: {e}'))
                task.status = ScheduledTask.STATUS_FAILED
                task.error_message = str(e)
                task.save()
        
        self.stdout.write(self.style.SUCCESS(f'\nProcessed {task_count} tasks'))

    def _execute_good_morning_task(self, task, user_id):
        """Execute a good morning message task."""
        self.stdout.write('Executing good morning task...')
        
        # Get calendar events for today
        from api.calendar_views import _get_google_credentials
        
        creds = _get_google_credentials(user_id)
        if not creds:
            raise Exception("Google Calendar not connected")
        
        from googleapiclient.discovery import build
        service = build('calendar', 'v3', credentials=creds)
        
        cred_record = GoogleCalendarCredential.objects.get(user_id=user_id)
        calendar_id = cred_record.calendar_id
        
        # Get today's events
        now = timezone.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        try:
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=start_of_day.isoformat(),
                timeMax=end_of_day.isoformat(),
                maxResults=20,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Filter out ARES tasks
            today_events = []
            for event in events:
                title = event.get('summary', '').strip()
                if title and 'ARES:' not in title:
                    start = event.get('start', {}).get('dateTime') or event.get('start', {}).get('date')
                    today_events.append({
                        'title': title,
                        'start': start,
                        'location': event.get('location', ''),
                    })
        except Exception as e:
            logger.warning(f"Could not fetch today's events: {e}")
            today_events = []
        
        # Build good morning message
        message_parts = ["🌅 Good morning!"]
        
        if today_events:
            message_parts.append("\n\n📅 Here's what awaits you today:")
            for event in today_events[:10]:  # Limit to 10 events
                time_str = ""
                if event['start']:
                    try:
                        from django.utils.dateparse import parse_datetime
                        event_time = parse_datetime(event['start'])
                        if event_time:
                            time_str = event_time.strftime("%H:%M")
                    except Exception:
                        pass
                
                event_line = f"• {time_str} {event['title']}" if time_str else f"• {event['title']}"
                if event.get('location'):
                    event_line += f" ({event['location']})"
                message_parts.append(event_line)
        else:
            message_parts.append("\n\n📅 You have a free day ahead! No scheduled events.")
        
        message = "\n".join(message_parts)
        
        # Send via Telegram
        self._send_telegram_message(user_id, message)
        
        # Mark task as completed
        task.status = ScheduledTask.STATUS_COMPLETED
        task.executed_at = timezone.now()
        task.save()
        
        self.stdout.write(self.style.SUCCESS('Good morning message sent!'))

    def _execute_reminder_task(self, task, user_id):
        """Execute a reminder task."""
        self.stdout.write('Executing reminder task...')
        
        message = f"⏰ Reminder: {task.calendar_event_title}"
        if task.task_data.get('description'):
            message += f"\n\n{task.task_data['description']}"
        
        self._send_telegram_message(user_id, message)
        
        task.status = ScheduledTask.STATUS_COMPLETED
        task.executed_at = timezone.now()
        task.save()
        
        self.stdout.write(self.style.SUCCESS('Reminder sent!'))

    def _execute_custom_task(self, task, user_id):
        """Execute a custom task."""
        self.stdout.write('Executing custom task...')
        
        # Extract task name from title (format: "ARES: Task Name")
        title = task.calendar_event_title
        if 'ARES:' in title:
            task_name = title.split('ARES:')[1].strip()
        else:
            task_name = title
        
        message = f"📋 Task: {task_name}"
        if task.task_data.get('description'):
            message += f"\n\n{task.task_data['description']}"
        
        self._send_telegram_message(user_id, message)
        
        task.status = ScheduledTask.STATUS_COMPLETED
        task.executed_at = timezone.now()
        task.save()
        
        self.stdout.write(self.style.SUCCESS('Custom task executed!'))

    def _send_telegram_message(self, user_id, message):
        """Send a message via Telegram."""
        token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        if not token:
            raise Exception("TELEGRAM_BOT_TOKEN not configured")
        
        # Get Telegram chat ID for user
        # Try to find by user_id or common identifiers
        chat_id = _get_telegram_chat_id_by_identifier(user_id, user_id=user_id)
        
        if not chat_id:
            # Try common identifiers
            for identifier in ['gabe', 'gabu', user_id]:
                chat_id = _get_telegram_chat_id_by_identifier(identifier, user_id=user_id)
                if chat_id:
                    break
        
        if not chat_id:
            raise Exception(f"Could not find Telegram chat ID for user {user_id}")
        
        # Send message
        send_url = f"https://api.telegram.org/bot{token}/sendMessage"
        with httpx.Client(timeout=10.0) as client:
            response = client.post(send_url, json={
                "chat_id": int(chat_id),
                "text": message,
            })
            
            if response.status_code != 200:
                result = response.json() if response.status_code == 200 else {}
                error_desc = result.get("description") or f"HTTP {response.status_code}"
                raise Exception(f"Failed to send Telegram message: {error_desc}")
            
            self.stdout.write(f'Message sent to Telegram chat {chat_id}')

