import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, Any, List

def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if 'messages' not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant", 
                "content": "Hello! I'm your AI calendar assistant. I can help you check availability, book appointments, and manage your schedule. What can I help you with today?"
            }
        ]
    
    if 'conversation_context' not in st.session_state:
        st.session_state.conversation_context = {}

def format_message(message: str, role: str = "user") -> Dict[str, str]:
    """Format a message for the chat interface."""
    return {"role": role, "content": message}

def format_datetime(dt: datetime) -> str:
    """Format datetime for display."""
    return dt.strftime("%Y-%m-%d %H:%M")

def parse_user_date_input(user_input: str) -> str:
    """Parse natural language date input and return YYYY-MM-DD format."""
    user_input = user_input.lower().strip()
    
    # Handle common date formats
    today = datetime.now().date()
    
    if 'today' in user_input:
        return today.strftime("%Y-%m-%d")
    elif 'tomorrow' in user_input:
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    elif 'next week' in user_input:
        return (today + timedelta(days=7)).strftime("%Y-%m-%d")
    elif 'monday' in user_input:
        days_ahead = 0 - today.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    # Add more natural language parsing as needed
    
    return user_input  # Return as-is if no pattern matches

def parse_user_time_input(user_input: str) -> str:
    """Parse natural language time input and return HH:MM format."""
    user_input = user_input.lower().strip()
    
    # Handle common time formats
    if 'morning' in user_input:
        return "09:00"
    elif 'afternoon' in user_input:
        return "14:00"
    elif 'evening' in user_input:
        return "18:00"
    elif 'noon' in user_input:
        return "12:00"
    
    return user_input  # Return as-is if no pattern matches

def validate_datetime_string(date_str: str, time_str: str = None) -> bool:
    """Validate if date and time strings are in correct format."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        if time_str:
            datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False

def get_business_hours() -> List[str]:
    """Get list of business hours in HH:MM format."""
    hours = []
    for hour in range(9, 17):  # 9 AM to 5 PM
        for minute in [0, 30]:
            time_str = f"{hour:02d}:{minute:02d}"
            hours.append(time_str)
    return hours

def format_duration(minutes: int) -> str:
    """Format duration in minutes to human-readable format."""
    if minutes < 60:
        return f"{minutes} minutes"
    else:
        hours = minutes // 60
        remaining_minutes = minutes % 60
        if remaining_minutes == 0:
            return f"{hours} hour{'s' if hours > 1 else ''}"
        else:
            return f"{hours} hour{'s' if hours > 1 else ''} {remaining_minutes} minutes"

def extract_appointment_details(text: str) -> Dict[str, Any]:
    """Extract appointment details from natural language text."""
    import re
    
    details = {}
    
    # Extract time patterns (basic regex patterns)
    time_patterns = [
        r'(\d{1,2}):(\d{2})\s*(am|pm)?',
        r'(\d{1,2})\s*(am|pm)',
        r'at\s+(\d{1,2}):(\d{2})',
        r'at\s+(\d{1,2})\s*(am|pm)'
    ]
    
    for pattern in time_patterns:
        match = re.search(pattern, text.lower())
        if match:
            if len(match.groups()) >= 2:
                hour, minute = match.groups()[:2]
                details['time'] = f"{hour.zfill(2)}:{minute.zfill(2)}"
            break
    
    # Extract date patterns
    date_patterns = [
        r'(\d{1,2})/(\d{1,2})/(\d{4})',
        r'(\d{4})-(\d{1,2})-(\d{1,2})',
        r'(today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)'
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text.lower())
        if match:
            if match.group(0) in ['today', 'tomorrow', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
                details['date'] = parse_user_date_input(match.group(0))
            else:
                # Handle date formats
                groups = match.groups()
                if len(groups) == 3:
                    if len(groups[0]) == 4:  # YYYY-MM-DD
                        details['date'] = f"{groups[0]}-{groups[1].zfill(2)}-{groups[2].zfill(2)}"
                    else:  # MM/DD/YYYY
                        details['date'] = f"{groups[2]}-{groups[0].zfill(2)}-{groups[1].zfill(2)}"
            break
    
    # Extract duration
    duration_pattern = r'(\d+)\s*(minute|hour|min|hr)s?'
    match = re.search(duration_pattern, text.lower())
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        if unit in ['hour', 'hr']:
            details['duration'] = value * 60
        else:
            details['duration'] = value
    
    return details
