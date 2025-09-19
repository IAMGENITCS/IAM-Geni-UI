import msal
import streamlit as st
import time
from config import CLIENT_ID, AUTHORITY, REDIRECT_URI, SCOPES

def initiate_login():
    """Returns the authorization URL for MSAL."""
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
    return app.get_authorization_request_url(SCOPES, redirect_uri=REDIRECT_URI)

def handle_token_response():
    """Handles the token response from the redirect."""
    code = st.query_params.get('code')
    if not code:
        return None
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
    token_response = app.acquire_token_by_authorization_code(
        code,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    if "access_token" in token_response:
        return token_response
    return None

def process_login():
    """Processes the login flow, handling redirects and session state."""
    if "code" in st.query_params:
        with st.spinner("Finalizing sign-in..."):
            token_response = handle_token_response()
            if token_response and "access_token" in token_response:
                st.session_state["authenticated"] = True
                st.session_state["access_token"] = token_response.get("access_token")
                st.session_state["user_info"] = token_response.get("id_token_claims", {})
                st.session_state.setdefault("orchestrator_chat_history", [])
                st.session_state.setdefault("active_page", "main_chat")
                st.query_params.clear()
                st.success("Signed in successfully.")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Authentication failed. Please try again.")
                st.query_params.clear()

def handle_logout():
    """Handles the logout process by clearing session state and rerunning."""
    if st.query_params.get("app_logout") == "1":
        for k in [
            "authenticated", "access_token", "thread_id", "chat_history", "user_info",
            "orch_thread_id", "orchestrator_chat_history", "active_page"
        ]:
            st.session_state.pop(k, None)
        st.query_params.clear()
        st.rerun()