import os
import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class GoogleCalendarService:
    """Google Calendar API service for appointment management."""
    
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    def __init__(self):
        """Initialize Google Calendar service."""
        self.service = None
        self.calendar_id = '9d23676d1e15e9140e9cc944f3ff3355740f76401fa468835d8107fd4a96817d@group.calendar.google.com'
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Calendar API using service account."""
        try:
            # Load service account credentials
            if os.path.exists('credentials.json'):
                creds = Credentials.from_service_account_file(
                    'credentials.json', 
                    scopes=self.SCOPES
                )
                self.service = build('calendar', 'v3', credentials=creds)
                print("Successfully authenticated with service account")
            else:
                print("credentials.json not found, using mock service")
                self.service = MockCalendarService()
        except Exception as e:
            print(f"Authentication error: {e}")
            print("Falling back to mock service for development")
            self.service = MockCalendarService()
    
    def check_availability(self, start_time: datetime, duration_minutes: int = 60) -> bool:
        """Check if a time slot is available."""
        if isinstance(self.service, MockCalendarService):
            return self.service.check_availability(start_time, duration_minutes)
        
        try:
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            # Convert to RFC3339 format with timezone
            time_min = start_time.replace(tzinfo=timezone.utc).isoformat()
            time_max = end_time.replace(tzinfo=timezone.utc).isoformat()
            
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            return len(events) == 0  # Available if no conflicting events
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return False
        except Exception as e:
            print(f'Unexpected error: {e}')
            return False
    
    def create_event(self, title: str, start_time: datetime, duration_minutes: int = 60, 
                    description: str = '') -> Optional[str]:
        """Create a new calendar event."""
        if isinstance(self.service, MockCalendarService):
            return self.service.create_event(title, start_time, duration_minutes, description)
        
        try:
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            event = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_time.replace(tzinfo=timezone.utc).isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end_time.replace(tzinfo=timezone.utc).isoformat(),
                    'timeZone': 'UTC',
                },
            }
            
            event_result = self.service.events().insert(
                calendarId=self.calendar_id, 
                body=event
            ).execute()
            
            return event_result.get('id')
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return None
        except Exception as e:
            print(f'Unexpected error: {e}')
            return None
    
    def suggest_times(self, target_date: datetime, duration_minutes: int = 60, 
                     business_hours_only: bool = True) -> List[datetime]:
        """Suggest available time slots for a given date."""
        if isinstance(self.service, MockCalendarService):
            return self.service.suggest_times(target_date, duration_minutes, business_hours_only)
        
        suggestions = []
        
        # Define time range (business hours: 9 AM to 5 PM)
        if business_hours_only:
            start_hour, end_hour = 9, 17
        else:
            start_hour, end_hour = 8, 20
        
        # Check every 30-minute slot
        for hour in range(start_hour, end_hour):
            for minute in [0, 30]:
                candidate_time = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # Skip if in the past
                if candidate_time < datetime.now():
                    continue
                
                if self.check_availability(candidate_time, duration_minutes):
                    suggestions.append(candidate_time)
                
                # Limit to reasonable number of suggestions
                if len(suggestions) >= 10:
                    break
            
            if len(suggestions) >= 10:
                break
        
        return suggestions
    
    def get_events(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get events within a date range."""
        if isinstance(self.service, MockCalendarService):
            return self.service.get_events(start_date, end_date)
        
        try:
            time_min = start_date.replace(tzinfo=timezone.utc).isoformat()
            time_max = end_date.replace(tzinfo=timezone.utc).isoformat()
            
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            return events_result.get('items', [])
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []
        except Exception as e:
            print(f'Unexpected error: {e}')
            return []


class MockCalendarService:
    """Mock calendar service for development/testing."""
    
    def __init__(self):
        self.events = []
        self.next_event_id = 1
    
    def check_availability(self, start_time: datetime, duration_minutes: int = 60) -> bool:
        """Mock availability check - returns True for most times."""
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        # Simulate some busy times (e.g., 2 PM - 3 PM)
        if start_time.hour == 14:
            return False
        
        # Check against stored events
        for event in self.events:
            event_start = event['start_time']
            event_end = event_start + timedelta(minutes=event['duration'])
            
            # Check for overlap
            if (start_time < event_end and end_time > event_start):
                return False
        
        return True
    
    def create_event(self, title: str, start_time: datetime, duration_minutes: int = 60, 
                    description: str = '') -> str:
        """Mock event creation."""
        event_id = f"mock_event_{self.next_event_id}"
        self.next_event_id += 1
        
        self.events.append({
            'id': event_id,
            'title': title,
            'start_time': start_time,
            'duration': duration_minutes,
            'description': description
        })
        
        return event_id
    
    def suggest_times(self, target_date: datetime, duration_minutes: int = 60, 
                     business_hours_only: bool = True) -> List[datetime]:
        """Mock time suggestions."""
        suggestions = []
        
        if business_hours_only:
            start_hour, end_hour = 9, 17
        else:
            start_hour, end_hour = 8, 20
        
        for hour in range(start_hour, end_hour):
            for minute in [0, 30]:
                candidate_time = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                if candidate_time < datetime.now():
                    continue
                
                if self.check_availability(candidate_time, duration_minutes):
                    suggestions.append(candidate_time)
                
                if len(suggestions) >= 5:
                    return suggestions
        
        return suggestions
    
    def get_events(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Mock get events."""
        filtered_events = []
        for event in self.events:
            if start_date <= event['start_time'] <= end_date:
                filtered_events.append({
                    'id': event['id'],
                    'summary': event['title'],
                    'start': {'dateTime': event['start_time'].isoformat()},
                    'description': event.get('description', '')
                })
        return filtered_events