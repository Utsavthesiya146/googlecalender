import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from openai import OpenAI
from calendar_service import GoogleCalendarService
import re

class AppointmentAgent:
    def __init__(self):
        """Initialize the appointment agent with OpenAI and Google Calendar services."""
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.calendar_service = GoogleCalendarService()
        
        self.system_prompt = """
        You are an AI calendar assistant that helps users book appointments. You can:
        1. Check calendar availability
        2. Suggest time slots
        3. Book appointments
        4. Handle scheduling conflicts
        
        Always respond in a helpful, conversational manner. When booking appointments, 
        gather all necessary information: title, date, time, duration, and description.
        
        Respond with JSON in this format:
        {
            "message": "your conversational response",
            "action": "check_availability|book_appointment|suggest_times|general_chat",
            "parameters": {
                "date": "YYYY-MM-DD",
                "time": "HH:MM",
                "duration": 60,
                "title": "Meeting Title",
                "description": "Meeting description"
            },
            "context": {
                "pending_booking": {...},
                "last_query": "...",
                "user_intent": "..."
            }
        }
        """
    
    def process_message(self, user_message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process user message and return appropriate response with actions."""
        if context is None:
            context = {}
        
        try:
            # Get AI response
            ai_response = self._get_ai_response(user_message, context)
            
            # Execute any required actions
            if ai_response.get('action') and ai_response['action'] != 'general_chat':
                result = self._execute_action(ai_response)
                if result:
                    ai_response['message'] = result.get('message', ai_response['message'])
                    ai_response['context'] = result.get('context', ai_response.get('context', {}))
            
            return ai_response
            
        except Exception as e:
            return {
                "message": f"I encountered an error: {str(e)}. Please try again.",
                "action": "error",
                "context": context
            }
    
    def _get_ai_response(self, user_message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get response from OpenAI."""
        messages = [
            {"role": "system", "content": self.system_prompt},
        ]
        
        # Add context if available
        if context:
            context_msg = f"Previous context: {json.dumps(context)}"
            messages.append({"role": "system", "content": context_msg})
        
        messages.append({"role": "user", "content": user_message})
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            response_format={"type": "json_object"}
        )
        
        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "message": response.choices[0].message.content,
                "action": "general_chat",
                "context": context
            }
    
    def _execute_action(self, ai_response: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the action specified by the AI response."""
        action = ai_response.get('action')
        parameters = ai_response.get('parameters', {})
        
        try:
            if action == 'check_availability':
                return self._check_availability(parameters, ai_response)
            elif action == 'book_appointment':
                return self._book_appointment(parameters, ai_response)
            elif action == 'suggest_times':
                return self._suggest_times(parameters, ai_response)
            else:
                return ai_response
                
        except Exception as e:
            return {
                "message": f"I had trouble with that request: {str(e)}. Could you please try again?",
                "context": ai_response.get('context', {})
            }
    
    def _check_availability(self, parameters: Dict[str, Any], ai_response: Dict[str, Any]) -> Dict[str, Any]:
        """Check calendar availability for given date/time."""
        date_str = parameters.get('date')
        time_str = parameters.get('time')
        duration = parameters.get('duration', 60)
        
        if not date_str:
            return {
                "message": "I need a specific date to check availability. What date are you thinking about?",
                "context": ai_response.get('context', {})
            }
        
        try:
            # Parse date and time
            if time_str:
                datetime_str = f"{date_str} {time_str}"
                start_time = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
            else:
                # Check availability for the whole day
                start_time = datetime.strptime(date_str, "%Y-%m-%d")
                
            is_available = self.calendar_service.check_availability(start_time, duration)
            
            if is_available:
                message = f"Great! You're available on {date_str}"
                if time_str:
                    message += f" at {time_str}"
                message += ". Would you like me to book an appointment?"
            else:
                message = f"You have a conflict on {date_str}"
                if time_str:
                    message += f" at {time_str}"
                message += ". Would you like me to suggest some alternative times?"
            
            return {
                "message": message,
                "context": {
                    **ai_response.get('context', {}),
                    "last_availability_check": {
                        "date": date_str,
                        "time": time_str,
                        "available": is_available
                    }
                }
            }
            
        except Exception as e:
            return {
                "message": f"I had trouble checking your calendar: {str(e)}",
                "context": ai_response.get('context', {})
            }
    
    def _book_appointment(self, parameters: Dict[str, Any], ai_response: Dict[str, Any]) -> Dict[str, Any]:
        """Book an appointment."""
        required_fields = ['date', 'time', 'title']
        missing_fields = [field for field in required_fields if not parameters.get(field)]
        
        if missing_fields:
            return {
                "message": f"I need more information to book the appointment. Please provide: {', '.join(missing_fields)}",
                "context": {
                    **ai_response.get('context', {}),
                    "pending_booking": parameters
                }
            }
        
        try:
            # Parse datetime
            datetime_str = f"{parameters['date']} {parameters['time']}"
            start_time = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
            duration = parameters.get('duration', 60)
            
            # Check availability first
            if not self.calendar_service.check_availability(start_time, duration):
                return {
                    "message": f"There's a conflict at {parameters['time']} on {parameters['date']}. Would you like me to suggest alternative times?",
                    "context": ai_response.get('context', {})
                }
            
            # Book the appointment
            event_id = self.calendar_service.create_event(
                title=parameters['title'],
                start_time=start_time,
                duration=duration,
                description=parameters.get('description', '')
            )
            
            if event_id:
                message = f"Perfect! I've booked '{parameters['title']}' for {parameters['date']} at {parameters['time']}."
                if duration != 60:
                    message += f" Duration: {duration} minutes."
                message += f" Event ID: {event_id}"
            else:
                message = "I had trouble booking the appointment. Please try again."
            
            return {
                "message": message,
                "context": {
                    **ai_response.get('context', {}),
                    "last_booking": {
                        "event_id": event_id,
                        "title": parameters['title'],
                        "datetime": datetime_str
                    }
                }
            }
            
        except Exception as e:
            return {
                "message": f"I encountered an error while booking: {str(e)}",
                "context": ai_response.get('context', {})
            }
    
    def _suggest_times(self, parameters: Dict[str, Any], ai_response: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest available time slots."""
        date_str = parameters.get('date')
        duration = parameters.get('duration', 60)
        
        if not date_str:
            return {
                "message": "What date would you like me to check for available times?",
                "context": ai_response.get('context', {})
            }
        
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
            suggestions = self.calendar_service.suggest_times(target_date, duration)
            
            if suggestions:
                message = f"Here are some available times on {date_str}:\n"
                for i, time_slot in enumerate(suggestions[:5], 1):  # Show top 5
                    formatted_time = time_slot.strftime("%H:%M")
                    message += f"{i}. {formatted_time}\n"
                message += "\nWhich time works best for you?"
            else:
                message = f"I couldn't find any available slots on {date_str}. Would you like to try a different date?"
            
            return {
                "message": message,
                "context": {
                    **ai_response.get('context', {}),
                    "suggested_times": [t.strftime("%H:%M") for t in suggestions[:5]]
                }
            }
            
        except Exception as e:
            return {
                "message": f"I had trouble finding available times: {str(e)}",
                "context": ai_response.get('context', {})
            }
