"""
Google Calendar integration views for ARES.

Handles OAuth authentication, reading calendar events, and creating scheduled tasks.
"""

from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime
import json
import logging
import os
import re
import traceback
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .models import GoogleCalendarCredential, ScheduledTask
from .auth import require_auth
from .utils import _get_setting, _set_setting

logger = logging.getLogger(__name__)

# Google OAuth 2.0 scopes
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# OAuth redirect URI (should match what's configured in Google Cloud Console)
REDIRECT_URI = os.getenv('GOOGLE_CALENDAR_REDIRECT_URI', 'http://localhost:8000/api/v1/calendar/oauth/callback')


def _get_google_credentials(user_id="default"):
    """
    Get Google Calendar credentials for a user.
    
    Returns Credentials object if available, None otherwise.
    
    This function will also check if the user_id is a Telegram chat_id and
    resolve it to the linked ARES user_id if available.
    """
    from .utils import _get_canonical_user_id
    
    # Resolve canonical user_id (handles Telegram chat_id -> ARES user_id mapping)
    canonical_user_id = _get_canonical_user_id(user_id, default_user_id=user_id)
    
    try:
        cred_record = GoogleCalendarCredential.objects.get(user_id=canonical_user_id, enabled=True)
        
        # Load credentials from stored token
        cred_dict = json.loads(cred_record.token)
        creds = Credentials.from_authorized_user_info(cred_dict, SCOPES)
        
        # Refresh token if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Update stored token
            cred_record.token = json.dumps({
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes
            })
            cred_record.save()
        
        return creds
    except GoogleCalendarCredential.DoesNotExist:
        return None
    except Exception as e:
        logger.error(f"Error loading Google credentials for user {user_id}: {e}")
        return None


@require_http_methods(["GET"])
@require_auth
def calendar_status(request):
    """
    Check Google Calendar integration status for the current user.
    """
    # Get user_id from Auth0 token, fallback to 'default'
    user_id = request.auth0_user.get('sub', 'default') if hasattr(request, 'auth0_user') else 'default'
    
    try:
        cred = GoogleCalendarCredential.objects.get(user_id=user_id)
        connected = cred.enabled and _get_google_credentials(user_id) is not None
        
        return JsonResponse({
            "connected": connected,
            "enabled": cred.enabled,
            "calendar_id": cred.calendar_id,
            "last_sync_at": cred.last_sync_at.isoformat() if cred.last_sync_at else None,
        })
    except GoogleCalendarCredential.DoesNotExist:
        return JsonResponse({
            "connected": False,
            "enabled": False,
            "calendar_id": None,
            "last_sync_at": None,
        })


@require_http_methods(["GET"])
@require_auth
def calendar_connect(request):
    """
    Initiate Google Calendar OAuth flow.
    
    Redirects user to Google OAuth consent screen.
    """
    # Get user_id from Auth0 token, fallback to 'default'
    user_id = request.auth0_user.get('sub', 'default') if hasattr(request, 'auth0_user') else 'default'
    
    # Get OAuth client credentials from environment
    client_id = os.getenv('GOOGLE_CALENDAR_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CALENDAR_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        return JsonResponse({
            "error": "Google Calendar OAuth credentials not configured. Set GOOGLE_CALENDAR_CLIENT_ID and GOOGLE_CALENDAR_CLIENT_SECRET environment variables."
        }, status=400)
    
    # Build OAuth flow
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES,
    )
    flow.redirect_uri = REDIRECT_URI
    
    # Store user_id in session for callback
    request.session['calendar_oauth_user_id'] = user_id
    
    # Generate authorization URL
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',  # Force consent to get refresh token
    )
    
    # Store state in session (for verification)
    request.session['calendar_oauth_state'] = state
    request.session['calendar_oauth_user_id'] = user_id
    
    return JsonResponse({
        "authorization_url": authorization_url,
        "state": state,
    })


@require_http_methods(["GET"])
@csrf_exempt
def calendar_oauth_callback(request):
    """
    Handle Google OAuth callback.
    
    This endpoint should be accessible without authentication (csrf_exempt)
    as it's called by Google's servers.
    """
    user_id = request.session.get('calendar_oauth_user_id', 'default')
    state = request.session.get('calendar_oauth_state')
    
    # Verify state
    if request.GET.get('state') != state:
        return JsonResponse({"error": "Invalid state parameter"}, status=400)
    
    # Get OAuth client credentials
    client_id = os.getenv('GOOGLE_CALENDAR_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CALENDAR_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        return JsonResponse({"error": "OAuth credentials not configured"}, status=500)
    
    # Build OAuth flow
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES,
    )
    flow.redirect_uri = REDIRECT_URI
    
    # Exchange authorization code for token
    # Ensure HTTPS is used when behind proxy
    authorization_response = request.build_absolute_uri()
    # Force HTTPS if X-Forwarded-Proto indicates HTTPS
    if request.META.get('HTTP_X_FORWARDED_PROTO') == 'https':
        authorization_response = authorization_response.replace('http://', 'https://', 1)
    
    try:
        flow.fetch_token(authorization_response=authorization_response)
        creds = flow.credentials
    except Exception as e:
        logger.error(f"Error fetching token: {e}")
        return JsonResponse({"error": f"Failed to exchange authorization code: {str(e)}"}, status=400)
    
    # Store credentials
    cred_dict = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    }
    
    GoogleCalendarCredential.objects.update_or_create(
        user_id=user_id,
        defaults={
            'token': json.dumps(cred_dict),
            'refresh_token': creds.refresh_token or '',
            'token_uri': creds.token_uri,
            'client_id': creds.client_id,
            'client_secret': creds.client_secret,
            'scopes': list(creds.scopes),
            'enabled': True,
        }
    )
    
    # Clean up session
    request.session.pop('calendar_oauth_user_id', None)
    request.session.pop('calendar_oauth_state', None)
    
    return JsonResponse({
        "success": True,
        "message": "Google Calendar connected successfully",
    })


@csrf_exempt
@require_http_methods(["POST"])
@require_auth
def calendar_disconnect(request):
    """
    Disconnect Google Calendar integration.
    """
    # Get user_id from Auth0 token, fallback to 'default'
    user_id = request.auth0_user.get('sub', 'default') if hasattr(request, 'auth0_user') else 'default'
    
    try:
        cred = GoogleCalendarCredential.objects.get(user_id=user_id)
        cred.enabled = False
        cred.save()
        return JsonResponse({"success": True, "enabled": False})
    except GoogleCalendarCredential.DoesNotExist:
        return JsonResponse({"error": "No calendar connection found"}, status=404)


@require_http_methods(["GET"])
@require_auth
def calendar_events(request):
    """
    Get calendar events for the current user.
    
    Query parameters:
    - start: ISO datetime string (default: now)
    - end: ISO datetime string (default: now + 7 days)
    - max_results: Maximum number of events (default: 10)
    """
    # Get user_id from Auth0 token, fallback to 'default'
    user_id = request.auth0_user.get('sub', 'default') if hasattr(request, 'auth0_user') else 'default'
    
    creds = _get_google_credentials(user_id)
    if not creds:
        return JsonResponse({"error": "Google Calendar not connected"}, status=403)
    
    try:
        # Parse query parameters
        start_str = request.GET.get('start')
        end_str = request.GET.get('end')
        max_results = int(request.GET.get('max_results', 10))
        
        if start_str:
            time_min = parse_datetime(start_str)
        else:
            time_min = timezone.now()
        
        if end_str:
            time_max = parse_datetime(end_str)
        else:
            time_max = time_min + timedelta(days=7)
        
        # Build calendar service
        service = build('calendar', 'v3', credentials=creds)
        
        # Get calendar ID
        # Resolve canonical user_id to handle Telegram chat_id -> ARES user_id mapping
        from .utils import _get_canonical_user_id
        canonical_user_id = _get_canonical_user_id(user_id, default_user_id=user_id)
        
        cred_record = GoogleCalendarCredential.objects.get(user_id=canonical_user_id)
        calendar_id = cred_record.calendar_id
        
        # Fetch events
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        # Format events
        formatted_events = []
        for event in events:
            start = event.get('start', {}).get('dateTime') or event.get('start', {}).get('date')
            end = event.get('end', {}).get('dateTime') or event.get('end', {}).get('date')
            
            formatted_events.append({
                'id': event.get('id'),
                'title': event.get('summary', 'No Title'),
                'description': event.get('description', ''),
                'start': start,
                'end': end,
                'location': event.get('location', ''),
            })
        
        return JsonResponse({
            "events": formatted_events,
            "count": len(formatted_events),
        })
    except HttpError as e:
        logger.error(f"Google Calendar API error: {e}")
        return JsonResponse({"error": f"Calendar API error: {str(e)}"}, status=500)
    except Exception as e:
        logger.error(f"Error fetching calendar events: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@require_auth
def calendar_sync(request):
    """
    Sync calendar events and create scheduled tasks.
    
    Looks for events with specific patterns (e.g., "ARES: Good Morning")
    and creates ScheduledTask records for them.
    """
    # Get user_id from Auth0 token, fallback to 'default'
    user_id = request.auth0_user.get('sub', 'default') if hasattr(request, 'auth0_user') else 'default'
    
    creds = _get_google_credentials(user_id)
    if not creds:
        return JsonResponse({"error": "Google Calendar not connected"}, status=403)
    
    try:
        service = build('calendar', 'v3', credentials=creds)
        # Resolve canonical user_id to handle Telegram chat_id -> ARES user_id mapping
        from .utils import _get_canonical_user_id
        canonical_user_id = _get_canonical_user_id(user_id, default_user_id=user_id)
        
        cred_record = GoogleCalendarCredential.objects.get(user_id=canonical_user_id)
        calendar_id = cred_record.calendar_id
        
        # Look for events in the next 30 days
        time_min = timezone.now()
        time_max = time_min + timedelta(days=30)
        
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            maxResults=100,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        tasks_created = 0
        tasks_updated = 0
        
        for event in events:
            title = event.get('summary', '').strip()
            if not title:
                continue
            
            # Check for task patterns
            task_type = None
            if 'ARES: Good Morning' in title or 'ARES: good morning' in title.lower():
                task_type = ScheduledTask.TASK_GOOD_MORNING
            elif 'ARES:' in title:
                # Generic ARES task
                task_type = ScheduledTask.TASK_CUSTOM
                # Extract task name from title
                task_name = title.split('ARES:')[1].strip()
            
            if not task_type:
                continue
            
            # Parse event time
            start = event.get('start', {}).get('dateTime') or event.get('start', {}).get('date')
            if not start:
                continue
            
            try:
                if 'T' in start:
                    scheduled_time = parse_datetime(start)
                else:
                    # All-day event, use start of day
                    scheduled_time = datetime.fromisoformat(start).replace(tzinfo=timezone.get_current_timezone())
            except Exception as e:
                logger.warning(f"Could not parse event time {start}: {e}")
                continue
            
            # Only create tasks for future events
            if scheduled_time < timezone.now():
                continue
            
            event_id = event.get('id')
            
            # Create or update scheduled task
            task, created = ScheduledTask.objects.update_or_create(
                user_id=user_id,
                calendar_event_id=event_id,
                defaults={
                    'task_type': task_type,
                    'calendar_event_title': title,
                    'scheduled_time': scheduled_time,
                    'status': ScheduledTask.STATUS_PENDING,
                    'task_data': {
                        'description': event.get('description', ''),
                        'location': event.get('location', ''),
                    }
                }
            )
            
            if created:
                tasks_created += 1
            else:
                tasks_updated += 1
        
        # Update last sync time
        cred_record.last_sync_at = timezone.now()
        cred_record.save()
        
        return JsonResponse({
            "success": True,
            "tasks_created": tasks_created,
            "tasks_updated": tasks_updated,
            "events_processed": len(events),
        })
    except HttpError as e:
        logger.error(f"Google Calendar API error during sync: {e}")
        return JsonResponse({"error": f"Calendar API error: {str(e)}"}, status=500)
    except Exception as e:
        logger.error(f"Error syncing calendar: {e}")
        return JsonResponse({"error": str(e)}, status=500)


def _is_calendar_related_prompt(message: str) -> bool:
    """
    Determine if a user message is related to calendar/schedule.
    
    Returns True if the message contains calendar-related keywords.
    """
    if not message:
        return False
    
    message_lower = message.lower()
    
    # Calendar-related keywords
    calendar_keywords = [
        'calendar', 'schedule', 'event', 'events', 'appointment', 'appointments',
        'meeting', 'meetings', 'today', 'tomorrow', 'this week', 'next week',
        'upcoming', 'when', 'what\'s on', 'what is on', 'what am i doing',
        'when do i have', 'when is', 'when are', 'busy', 'free time',
        'availability', 'agenda', 'plans', 'planning'
    ]
    
    # Check if any keyword appears in the message
    for keyword in calendar_keywords:
        if keyword in message_lower:
            return True
    
    return False


def _parse_time_range_from_message(message: str) -> tuple:
    """
    Parse a user message to determine what time range to fetch calendar events for.
    
    Returns (time_min, time_max, max_results) tuple.
    
    IMPORTANT: Time ranges use LOCAL timezone (not UTC) to correctly capture
    events for the user's day. This ensures "today" means midnight-to-midnight
    in the user's timezone, not UTC.
    """
    message_lower = message.lower()
    
    # Get current time in LOCAL timezone (not UTC)
    # This is crucial for correct day boundaries
    local_tz = timezone.get_current_timezone()
    now_local = timezone.localtime(timezone.now())
    
    # Default: start from beginning of today in LOCAL timezone
    today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    time_min = today_start
    time_max = today_start + timedelta(days=7)
    max_results = 100  # Increased default
    
    # Today - midnight to midnight in local timezone
    if any(phrase in message_lower for phrase in ['today', 'this day', 'current day']):
        time_min = today_start
        time_max = today_start + timedelta(days=1)
        max_results = 100
    
    # Tomorrow
    elif 'tomorrow' in message_lower:
        tomorrow_start = today_start + timedelta(days=1)
        time_min = tomorrow_start
        time_max = tomorrow_start + timedelta(days=1)
        max_results = 100
    
    # This week
    elif 'this week' in message_lower:
        # Start of current week (Monday)
        days_since_monday = now_local.weekday()
        week_start = (today_start - timedelta(days=days_since_monday))
        time_min = week_start
        time_max = week_start + timedelta(days=7)
        max_results = 100
    
    # Next week
    elif 'next week' in message_lower:
        days_since_monday = now_local.weekday()
        next_monday = today_start - timedelta(days=days_since_monday) + timedelta(days=7)
        time_min = next_monday
        time_max = next_monday + timedelta(days=7)
        max_results = 100
    
    # This month
    elif 'this month' in message_lower:
        month_start = today_start.replace(day=1)
        time_min = month_start
        # Next month
        if now_local.month == 12:
            time_max = month_start.replace(year=now_local.year + 1, month=1)
        else:
            time_max = month_start.replace(month=now_local.month + 1)
        max_results = 200
    
    # Next month
    elif 'next month' in message_lower:
        if now_local.month == 12:
            next_month_start = today_start.replace(year=now_local.year + 1, month=1, day=1)
            time_max = next_month_start.replace(month=2)
        else:
            next_month_start = today_start.replace(month=now_local.month + 1, day=1)
            if next_month_start.month == 12:
                time_max = next_month_start.replace(year=now_local.year + 1, month=1)
            else:
                time_max = next_month_start.replace(month=next_month_start.month + 1)
        time_min = next_month_start
        max_results = 200
    
    # Upcoming / future events
    elif any(phrase in message_lower for phrase in ['upcoming', 'future', 'next few', 'coming']):
        time_min = now_local
        time_max = now_local + timedelta(days=30)
        max_results = 100
    
    # All events / everything
    elif any(phrase in message_lower for phrase in ['all events', 'everything', 'all my']):
        time_min = now_local
        time_max = now_local + timedelta(days=365)  # One year
        max_results = 500
    
    return time_min, time_max, max_results


def get_calendar_context_summary(user_id: str = "default", message: str = "") -> str:
    """
    Get calendar context summary for injection into system prompts.
    
    Analyzes the user message to determine what calendar information is relevant
    and fetches appropriate events.
    
    Always returns calendar context, even if calendar is not connected, so the AI
    is aware of calendar functionality.
    """
    try:
        logger.info(f"[CALENDAR CONTEXT] Getting calendar context for user_id={user_id}")
        print(f"[CALENDAR CONTEXT] Getting calendar context for user_id={user_id}")
        
        # Check if calendar is connected
        creds = _get_google_credentials(user_id)
        if not creds:
            logger.info(f"[CALENDAR CONTEXT] No credentials found for user_id={user_id}")
            print(f"[CALENDAR CONTEXT] No credentials found for user_id={user_id}")
            # Calendar not connected, but still provide context so AI knows about calendar
            return """## Calendar Information

You have access to calendar functionality. However, the calendar is not currently connected.
The user can connect their Google Calendar to enable calendar features.
When calendar is connected, you can reference events, meetings, and schedule information."""
        
        # Always include calendar context if connected (not just for calendar-related prompts)
        # This allows the AI to analyze and reference calendar in any context
        
        # Parse time range from message if it's calendar-related, otherwise use default
        if message and _is_calendar_related_prompt(message):
            time_min, time_max, max_results = _parse_time_range_from_message(message)
        else:
            # Default: start from beginning of today in LOCAL timezone
            # This ensures "today" means midnight-to-midnight in user's timezone
            now_local = timezone.localtime(timezone.now())
            today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
            time_min = today_start
            time_max = today_start + timedelta(days=7)
            max_results = 100  # Capture all events
        
        logger.info(f"Calendar query for user {user_id}: time_min={time_min}, time_max={time_max}, max_results={max_results}")
        
        # Build calendar service
        service = build('calendar', 'v3', credentials=creds)
        
        # Get calendar ID (defaults to "primary" if not set)
        # Resolve canonical user_id to handle Telegram chat_id -> ARES user_id mapping
        from .utils import _get_canonical_user_id
        canonical_user_id = _get_canonical_user_id(user_id, default_user_id=user_id)
        
        try:
            cred_record = GoogleCalendarCredential.objects.get(user_id=canonical_user_id)
            calendar_id = cred_record.calendar_id or "primary"
        except GoogleCalendarCredential.DoesNotExist:
            # Credentials exist but record not found, still provide context
            return """## Calendar Information

You have access to calendar functionality. However, the calendar is not currently connected.
The user can connect their Google Calendar to enable calendar features.
When calendar is connected, you can reference events, meetings, and schedule information."""
        
        # Fetch events
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            logger.info(f"No calendar events found for user {user_id} in range {time_min} to {time_max}")
            # No events found, but still provide context so AI knows calendar is connected
            time_range_str = f"{time_min.strftime('%Y-%m-%d')} to {time_max.strftime('%Y-%m-%d')}"
            return f"""## Calendar Information

You have access to the user's calendar. The calendar is connected, but there are no events in the range {time_range_str}.
You can still reference calendar functionality when answering questions about the user's schedule or availability."""
        
        # Log all event titles for debugging
        event_titles = [e.get('summary', 'No Title') for e in events]
        logger.info(f"Found {len(events)} calendar events for user {user_id}: {event_titles}")
        
        # Group events by date for better clarity
        events_by_date = {}
        events_without_date = []  # Track events that couldn't be parsed
        events_processed = 0
        
        for event in events:
            start = event.get('start', {}).get('dateTime') or event.get('start', {}).get('date')
            end = event.get('end', {}).get('dateTime') or event.get('end', {}).get('date')
            title = event.get('summary', 'No Title')
            description = event.get('description', '')
            location = event.get('location', '')
            
            if not start:
                # Skip events without start time
                logger.warning(f"Event '{title}' has no start time, skipping")
                continue
            
            # Parse date for grouping - convert to local timezone first
            event_date = None
            local_tz = timezone.get_current_timezone()
            try:
                if 'T' in start:
                    start_dt = parse_datetime(start)
                    if start_dt:
                        # Convert to local timezone before extracting date
                        if timezone.is_aware(start_dt):
                            start_dt_local = start_dt.astimezone(local_tz)
                        else:
                            start_dt_local = timezone.make_aware(start_dt, local_tz)
                        event_date = start_dt_local.date()
                else:
                    event_date = datetime.fromisoformat(start).date()
            except Exception as e:
                logger.warning(f"Could not parse date from '{start}' for event '{title}': {e}")
                # Use a fallback date key for unparseable dates
                event_date = "unknown"
            
            # Format datetime for display - use local timezone
            time_str = "Time TBD"
            try:
                if 'T' in start:
                    start_dt = parse_datetime(start)
                    end_dt = parse_datetime(end) if end and 'T' in end else None
                    if start_dt:
                        # Convert to local timezone for display
                        if timezone.is_aware(start_dt):
                            start_dt_local = start_dt.astimezone(local_tz)
                        else:
                            start_dt_local = start_dt
                        time_str = start_dt_local.strftime('%H:%M')
                        
                        if end_dt:
                            if timezone.is_aware(end_dt):
                                end_dt_local = end_dt.astimezone(local_tz)
                            else:
                                end_dt_local = end_dt
                            time_str += f" - {end_dt_local.strftime('%H:%M')}"
                        else:
                            time_str += " (time TBD)"
                else:
                    # All-day event
                    time_str = "All day"
            except Exception as e:
                logger.warning(f"Could not format time for event '{title}': {e}")
            
            event_info = {
                'time': time_str,
                'title': title,
                'location': location,
                'description': description,
                'start': start,
                'end': end
            }
            
            if event_date:
                if event_date not in events_by_date:
                    events_by_date[event_date] = []
                events_by_date[event_date].append(event_info)
                events_processed += 1
            else:
                events_without_date.append(event_info)
                events_processed += 1
        
        # Log if we're missing events
        if events_processed < len(events):
            logger.warning(f"Only processed {events_processed} out of {len(events)} events for user {user_id}")
        
        # Format events grouped by date
        formatted_sections = []
        
        # Sort dates properly (handle both date objects and strings)
        def sort_key(date):
            if isinstance(date, str):
                return (1, date)  # Put string dates at the end
            return (0, date)
        
        for event_date in sorted(events_by_date.keys(), key=sort_key):
            date_events = events_by_date[event_date]
            
            # Format date string
            if isinstance(event_date, str):
                date_str = f"Unknown date ({event_date})"
            else:
                date_str = event_date.strftime('%Y-%m-%d (%A)')
            
            # Build section for this date
            date_section = [f"\n{date_str}:"]
            
            # Number each event on this date to make them clearly distinct
            for idx, event_info in enumerate(date_events, 1):
                event_lines = [f"  {idx}. {event_info['time']}: {event_info['title']}"]
                
                if event_info['location']:
                    event_lines.append(f"     Location: {event_info['location']}")
                
                if event_info['description']:
                    # Truncate long descriptions
                    desc = event_info['description'][:150] + "..." if len(event_info['description']) > 150 else event_info['description']
                    # Clean up description (remove HTML, extra whitespace)
                    desc = desc.replace('\n', ' ').replace('\r', ' ').strip()
                    # Remove multiple spaces
                    desc = re.sub(r'\s+', ' ', desc)
                    if desc:
                        event_lines.append(f"     Description: {desc}")
                
                date_section.append('\n'.join(event_lines))
            
            formatted_sections.append('\n'.join(date_section))
        
        # Add events without dates at the end
        if events_without_date:
            formatted_sections.append("\nUnknown date:")
            for idx, event_info in enumerate(events_without_date, 1):
                event_lines = [f"  {idx}. {event_info['time']}: {event_info['title']}"]
                if event_info['location']:
                    event_lines.append(f"     Location: {event_info['location']}")
                if event_info['description']:
                    desc = event_info['description'][:150] + "..." if len(event_info['description']) > 150 else event_info['description']
                    desc = desc.replace('\n', ' ').replace('\r', ' ').strip()
                    desc = re.sub(r'\s+', ' ', desc)
                    if desc:
                        event_lines.append(f"     Description: {desc}")
                formatted_sections.append('\n'.join(event_lines))
        
        # Build context summary
        time_range_str = f"{time_min.strftime('%Y-%m-%d')} to {time_max.strftime('%Y-%m-%d')}"
        total_events = len(events)
        
        summary = f"""## Calendar Information

You have access to the user's calendar. Here are their events from {time_range_str} (Total: {total_events} events):

{chr(10).join(formatted_sections)}

IMPORTANT: When multiple events are listed for the same day, each event is numbered (1., 2., 3., etc.). Make sure to reference ALL events when answering questions about that day. Each numbered item is a separate, distinct event.

You can reference these events when answering questions about the user's schedule, availability, or upcoming plans.
When asked about calendar events, meetings, or schedule, use this information to provide accurate answers."""
        
        return summary
        
    except HttpError as e:
        logger.error(f"Google Calendar API error in get_calendar_context_summary: {e}")
        # Even on error, provide calendar context so AI knows about calendar functionality
        return """## Calendar Information

You have access to calendar functionality. The calendar connection encountered an error.
You can still reference calendar functionality, but event data may not be available."""
    except Exception as e:
        logger.error(f"Error in get_calendar_context_summary: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Even on error, provide calendar context so AI knows about calendar functionality
        return """## Calendar Information

You have access to calendar functionality. There was an error accessing the calendar.
You can still reference calendar functionality, but event data may not be available."""


@require_http_methods(["GET"])
@require_auth
def calendar_context_debug(request):
    """
    Debug endpoint to see what calendar context would be injected into the AI.
    
    Query parameters:
    - message: Optional test message to parse for time range
    """
    # Get user_id from Auth0 token, fallback to 'default'
    user_id = request.auth0_user.get('sub', 'default') if hasattr(request, 'auth0_user') else 'default'
    message = request.GET.get('message', '')
    
    try:
        context = get_calendar_context_summary(user_id=user_id, message=message)
        
        # Also get raw events for comparison
        creds = _get_google_credentials(user_id)
        raw_events = []
        
        if creds:
            try:
                service = build('calendar', 'v3', credentials=creds)
                # Resolve canonical user_id to handle Telegram chat_id -> ARES user_id mapping
                from .utils import _get_canonical_user_id
                canonical_user_id = _get_canonical_user_id(user_id, default_user_id=user_id)
                
                cred_record = GoogleCalendarCredential.objects.get(user_id=canonical_user_id)
                calendar_id = cred_record.calendar_id or "primary"
                
                # Get events for today
                today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
                today_end = today_start + timedelta(days=1)
                
                events_result = service.events().list(
                    calendarId=calendar_id,
                    timeMin=today_start.isoformat(),
                    timeMax=today_end.isoformat(),
                    maxResults=100,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                raw_events = events_result.get('items', [])
            except Exception as e:
                raw_events = [{"error": str(e)}]
        
        return JsonResponse({
            "user_id": user_id,
            "message": message,
            "calendar_connected": creds is not None,
            "context_length": len(context),
            "context": context,
            "raw_events_today": [
                {
                    "title": e.get('summary', 'No Title'),
                    "start": e.get('start', {}).get('dateTime') or e.get('start', {}).get('date'),
                    "end": e.get('end', {}).get('dateTime') or e.get('end', {}).get('date'),
                }
                for e in raw_events if not isinstance(e, dict) or 'error' not in e
            ],
            "raw_events_count": len(raw_events),
        })
    except Exception as e:
        return JsonResponse({
            "error": str(e),
            "traceback": traceback.format_exc(),
        }, status=500)

