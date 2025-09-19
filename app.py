import streamlit as st
from config import REDIRECT_URI
import auth
import ui
import pages

st.set_page_config(
    page_title="Geni - Identity and Access Management Agentic AI Service", 
    page_icon="tcs_logo.png", 
    layout="wide"
)

# Apply global CSS
ui.load_css()

# Initialize session state variables
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = {}
if "active_page" not in st.session_state:
    st.session_state["active_page"] = "main_chat"

# Handle login and logout
auth.process_login()
auth.handle_logout()

# Render UI components
auth_url = auth.initiate_login()
ui.render_header(auth_url)
ui.render_footer()
ui.render_sidebar(auth_url)

# Page routing
if st.session_state.get("authenticated", False):
    active_page = st.session_state.get("active_page", "main_chat")
    if active_page == "main_chat":
        pages.main_chat_page()
    elif active_page == "orchestrator_chat":
        pages.orchestrator_chat_page()
    elif active_page == "about_iam":
        pages.about_iam_page()
    elif active_page == "rules":
        pages.rules_and_regulations_page()
    else:
        pages.main_chat_page()
else:
    st.markdown("""
<div style="display:flex; justify-content:center; align-items:center; height:80vh; text-align:center; font-size:18px; line-height:1.6;">
    <div>
        Ask anything on Identity and Access Management
        <br>
        Click the links on the left side to understand more on how these assistants can help you
        <br>
        Login if you want to start using them!
    </div>
</div>
""", unsafe_allow_html=True)