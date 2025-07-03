import streamlit as st
import os
from datetime import datetime, timedelta
from agent import AppointmentAgent
from utils import initialize_session_state, format_message

# Configure page
st.set_page_config(
    page_title="AI Calendar Assistant",
    page_icon="📅",
    layout="centered"
)

def main():
    st.title("📅 AI Calendar Assistant")
    st.markdown("Chat with me to book appointments on your Google Calendar!")
    
    # Initialize session state
    initialize_session_state()
    
    # Initialize agent
    if 'agent' not in st.session_state:
        try:
                        # Check if OpenAI API key is available
            if not os.getenv("OPENAI_API_KEY"):
                st.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
                st.stop()
            st.session_state.agent = AppointmentAgent()
        except Exception as e:
            st.error(f"Failed to initialize AI agent: {str(e)}")
            st.stop()
    
    # Display conversation history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = st.session_state.agent.process_message(
                        prompt, 
                        st.session_state.conversation_context
                    )
                    
                    # Update conversation context
                    st.session_state.conversation_context = response.get('context', {})
                    
                    # Display response
                    st.markdown(response['message'])
                    
                    # Add assistant message to chat history
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": response['message']
                    })
                    
                except Exception as e:
                    error_msg = f"Sorry, I encountered an error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": error_msg
                    })
    
    # Sidebar with information
    with st.sidebar:
        st.header("ℹ️ About")
        st.markdown("""
        This AI assistant can help you:
        - Check your calendar availability
        - Book new appointments
        - Suggest optimal time slots
        - Handle scheduling conflicts
        
        Just chat naturally and I'll understand your intent!
        """)
        
        if st.button("Clear Conversation"):
            st.session_state.messages = []
            st.session_state.conversation_context = {}
            st.rerun()
        
        # Display current context (for debugging)
        if st.session_state.conversation_context:
            with st.expander("Current Context (Debug)"):
                st.json(st.session_state.conversation_context)

if __name__ == "__main__":
    main()
