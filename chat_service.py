import requests
import streamlit as st
from config import API_BASE

def get_thread_id(endpoint: str) -> str:
    """Creates a new thread and returns its ID."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
        r = requests.post(f"{API_BASE}/{endpoint}", timeout=120, headers=headers)
        r.raise_for_status()
        return r.json()["thread_id"]
    except Exception as e:
        st.error(f"Failed to create thread: {str(e)}", icon="🚨")
        st.stop()
        return None

def send_message(endpoint: str, payload: dict) -> str:
    """Sends a message to the chat endpoint and returns the reply."""
    try:
        headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
        r = requests.post(f"{API_BASE}/{endpoint}", json=payload, timeout=120, headers=headers)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Request to {endpoint} failed: {str(e)}", icon="🚨")
        return {"reply": "**Agent is currently busy, please wait a moment and try again.**"}