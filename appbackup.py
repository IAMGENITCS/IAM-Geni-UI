import requests
import streamlit as st
import base64
import time
import msal
import os
from dotenv import load_dotenv
import ast
import json  # ← added

load_dotenv()

CLIENT_ID = os.getenv('CLIENT_ID')
TENANT_ID = os.getenv('TENANT_ID')
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["User.Read"]
API_BASE = "http://127.0.0.1:8000"
REDIRECT_URI = "http://localhost:8501"
logo_path = "tcs_logo.png"

def initiate_login():
    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
    return app.get_authorization_request_url(SCOPES, redirect_uri=REDIRECT_URI)

def handle_token_response():
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

def get_image_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

st.set_page_config(page_title="Geni - Identity and Access Management  Agentic AI Service", page_icon=logo_path, layout="wide")

auth_url = initiate_login()
azure_logout_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/logout?post_logout_redirect_uri={REDIRECT_URI}"

# AGGRESSIVE CSS with BULLETPROOF UNIFORM FIXED SIZE prompts styling + Entra Service styles
st.markdown("""
<style>
.header-container {
    position: fixed;
    top: 60px;
    left: 0;
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 10px 16px;
    border-bottom: 1px solid #e9ecef;
    background: black;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    z-index: 1500;
    transition: margin-left 0.3s ease, width 0.3s ease;
}

[data-testid="stSidebar"][aria-expanded="true"] ~ div .header-container {
    margin-left: 280px;
    width: calc(100% - 280px);
}

@media (max-width: 991px) {
    [data-testid="stSidebar"][aria-expanded="true"] ~ div .header-container {
        margin-left: 200px;
        width: calc(100% - 200px);
    }
}

@media (max-width: 600px) {
    [data-testid="stSidebar"][aria-expanded="true"] ~ div .header-container {
        margin-left: 0;
        width: 100%;
        top: 110px;
    }
    .header-title {
        font-size: 18px;
    }
    .header-container img {
        height: 30px;
    }
    .footer {
        height: 72px;
    }
    .stChatFloatingInputContainer {
        bottom: 80px !important;
    }
}

.main-content-logged-out {
    margin-top: 120px;
    text-align: center;
    font-size: 18px;
    font-weight: 700;
    color: #555555;
    padding: 10px 16px;
}

.block-container {
    padding-top: 106px;
    padding-bottom: 90px;
}

.header-left {
    display: flex;
    align-items: center;
    gap: 12px;
}

.header-right {
    display: flex;
    align-items: center;
    gap: 10px;
}

.header-container img {
    height: 36px;
    width: auto;
    display: block;
}

.header-title {
    font-size: 22px;
    font-weight: 700;
    line-height: 1;
    margin: 0;
    padding: 0;
    color: white;
}

.auth-button {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 14px;
    border: none;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 600;
    text-decoration: none;
    color: #fff !important;
    transition: transform .2s ease;
}

.login-btn {
    background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
}
.login-btn:hover {
    transform: translateY(-1px);
}
.logout-btn {
    background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
}
.logout-btn:hover {
    transform: translateY(-1px);
}

.centered-intro {
    text-align: center;
    font-size: 18px;
    color: #333;
    margin-top: 24px;
}

.message-container.no-messages {
    min-height: 30vh;
}

.footer {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    height: 30px;
    background: black;
    border-top: 1px solid white;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 16px;
    z-index: 10001;
    font-size: 12.5px;
    color: rgb(255 255 255);
}

.stChatFloatingInputContainer {
    bottom: 72px !important;
}

.st-emotion-cache-zy6yx3 {
    padding: 2rem 1rem 4rem !important;
}

/* Entra Service specific styles */
.quick-actions-container {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    justify-content: center;
    margin: 20px 0;
}

.quick-action-btn {
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    border: 2px solid #dee2e6;
    border-radius: 12px;
    padding: 12px 20px;
    font-weight: 600;
    font-size: 14px;
    transition: all 0.3s ease;
    cursor: pointer;
    min-width: 150px;
    text-align: center;
}

.quick-action-btn:hover {
    background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
    color: white;
    border-color: #007bff;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,123,255,0.3);
}

.operation-status {
    padding: 10px;
    border-radius: 8px;
    margin: 10px 0;
    font-weight: 600;
}

.status-running {
    background-color: #fff3cd;
    border-left: 4px solid #ffc107;
    color: #856404;
}

.status-success {
    background-color: #d1e7dd;
    border-left: 4px solid #198754;
    color: #0f5132;
}

.status-error {
    background-color: #f8d7da;
    border-left: 4px solid #dc3545;
    color: #721c24;
}

/* Sidebar generic styles — DEFAULT/WHITE look */
section[data-testid="stSidebar"] button {
    display: block;
    width: 100%;
    padding: 1px 8px;
    text-align: left;
    border-radius: 8px;
    margin-bottom: 6px;
    font-weight: 600;
    cursor: pointer;
    background: #e5e5e5 !important;   /* white background */
    color: #111 !important;           /* dark text */
    border: 1px solid transparent;    /* no visible border by default */
    box-shadow: none;
}
section[data-testid="stSidebar"] button:hover {
    background: #f5f7fb !important;   /* subtle light hover */
    color: #111 !important;
}

/* Profile box + hover card */
section[data-testid="stSidebar"] .profile-box {
    position: fixed;
    bottom: 20px;
    left: 12px;
    display: flex;
    align-items: center;
    gap: 10px;
    width: 230px;
    z-index: 9999;
    cursor: pointer;
}
section[data-testid="stSidebar"] .profile-initials {
    background: linear-gradient(135deg, #007bff, #0056b3);
    color: white;
    font-weight: bold;
    border-radius: 50%;
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
}
section[data-testid="stSidebar"] .profile-details {
    font-size: 13px;
    overflow: hidden;
    max-width: 160px;
    word-break: break-word;
    display: flex;
    flex-direction: column;
    gap: 2px;
}
section[data-testid="stSidebar"] .profile-displayname {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 150px;
    margin-bottom: 0;
    line-height: 1.1;
    font-weight: bold;
}
section[data-testid="stSidebar"] .profile-email {
    font-size: 11px;
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 150px;
    margin-top: 0;
    line-height: 1.1;
}

section[data-testid="stSidebar"] .hover-card {
    display: none;
    position: fixed;
    bottom: 60px;
    left: 12px;
    width: 260px;
    border-radius: 12px;
    box-shadow: 0 6px 20px rgba(0,0,0,0.75);
    padding: 10px;
    font-size: 13px;
    z-index: 999999 !important;
    background: #222 !important;
    color: #fafafa !important;
    border: 1px solid #444 !important;
}
section[data-testid="stSidebar"] .profile-box:hover ~ .hover-card {
    display: block;
}

/* Tables/DataFrames styling for dark mode */
.stTable, .stDataFrame {
    background-color: #1e1e1e !important;
    border-radius: 8px !important;
    overflow: hidden !important;
}
.stTable td, .stTable th {
    background-color: #1e1e1e !important;
    color: #f0f0f0 !important;
    border: 1px solid #444 !important;
}
.stTable th {
    background-color: #333 !important;
    font-weight: bold !important;
}
div[data-testid="stDataFrame"] {
    background-color: #1e1e1e !important;
    border-radius: 8px;
    overflow: hidden;
}
div[data-testid="stDataFrame"] table {
    color: #f0f0f0 !important;
}
div[data-testid="stDataFrame"] thead {
    background-color: #333 !important;
    color: #fff !important;
}
div[data-testid="stDataFrame"] tbody tr:nth-child(odd) {
    background-color: #2a2a2a !important;
}
div[data-testid="stDataFrame"] tbody tr:nth-child(even) {
    background-color: #1e1e1e !important;
}

/* NUCLEAR OPTION: BULLETPROOF UNIFORM BUTTON SIZING */
.prompt-grid-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 20px;
    padding: 20px;
    max-width: 1300px;
    margin: 0 auto;
}

.prompt-row {
    display: flex;
    justify-content: center;
    gap: 20px;
    width: 100%;
    flex-wrap: nowrap;
}

/* AGGRESSIVE: Multiple selector targeting for maximum specificity */
div.stButton:has(button[key^="prompt_"]),
.stButton:has(button[key^="prompt_"]),
div[data-testid="column"] div.stButton:has(button[key^="prompt_"]),
div[data-testid="column"] .stButton:has(button[key^="prompt_"]),
.element-container div.stButton:has(button[key^="prompt_"]),
.element-container .stButton:has(button[key^="prompt_"]) {
    width: 400px !important;
    min-width: 400px !important;
    max-width: 400px !important;
    height: 130px !important;
    min-height: 130px !important;
    max-height: 130px !important;
    margin: 0 !important;
    padding: 0 !important;
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    box-sizing: border-box !important;
    flex: none !important;
    flex-grow: 0 !important;
    flex-shrink: 0 !important;
    flex-basis: auto !important;
}

/* NUCLEAR: Multiple selectors for buttons themselves */
div.stButton > button[key^="prompt_"],
.stButton > button[key^="prompt_"],
div[data-testid="column"] div.stButton > button[key^="prompt_"],
div[data-testid="column"] .stButton > button[key^="prompt_"],
.element-container div.stButton > button[key^="prompt_"],
.element-container .stButton > button[key^="prompt_"],
button[key^="prompt_"] {
    width: 400px !important;
    min-width: 400px !important;
    max-width: 400px !important;
    height: 130px !important;
    min-height: 130px !important;
    max-height: 130px !important;
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%) !important;
    border: 2px solid #dee2e6 !important;
    border-radius: 12px !important;
    color: #495057 !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    line-height: 1.2 !important;
    padding: 12px !important;
    margin: 0 !important;
    
    /* CRITICAL: Force layout and prevent auto-sizing */
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    text-align: center !important;
    white-space: pre-wrap !important;
    word-wrap: break-word !important;
    overflow: hidden !important;
    box-sizing: border-box !important;
    flex: none !important;
    flex-grow: 0 !important;
    flex-shrink: 0 !important;
    flex-basis: auto !important;
    position: relative !important;
    
    /* Transitions */
    transition: all 0.3s ease !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
}

/* Hover effects with multiple selectors */
div.stButton > button[key^="prompt_"]:hover,
.stButton > button[key^="prompt_"]:hover,
div[data-testid="column"] div.stButton > button[key^="prompt_"]:hover,
div[data-testid="column"] .stButton > button[key^="prompt_"]:hover,
.element-container div.stButton > button[key^="prompt_"]:hover,
.element-container .stButton > button[key^="prompt_"]:hover,
button[key^="prompt_"]:hover {
    background: linear-gradient(135deg, #007bff 0%, #0056b3 100%) !important;
    color: white !important;
    border-color: #007bff !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 12px rgba(0,123,255,0.3) !important;
}

/* OVERRIDE STREAMLIT'S COLUMN BEHAVIOR - Multiple selectors */
div[data-testid="column"]:has(button[key^="prompt_"]),
[data-testid="column"]:has(button[key^="prompt_"]),
.element-container:has(button[key^="prompt_"]),
div[data-testid="column"]:has(.stButton button[key^="prompt_"]),
[data-testid="column"]:has(.stButton button[key^="prompt_"]) {
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    width: 400px !important;
    min-width: 400px !important;
    max-width: 400px !important;
    height: 130px !important;
    min-height: 130px !important;
    max-height: 130px !important;
    padding: 0 !important;
    margin: 0 auto !important;
    flex: none !important;
    flex-grow: 0 !important;
    flex-shrink: 0 !important;
    flex-basis: auto !important;
}

/* BUTTON TEXT CONTAINER - Multiple selectors */
div.stButton > button[key^="prompt_"] > div,
.stButton > button[key^="prompt_"] > div,
button[key^="prompt_"] > div,
div.stButton > button[key^="prompt_"] > *,
.stButton > button[key^="prompt_"] > *,
button[key^="prompt_"] > * {
    width: 100% !important;
    height: 100% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    text-align: center !important;
    overflow: hidden !important;
    box-sizing: border-box !important;
}

/* Responsive - maintain uniformity across all screen sizes */
@media (max-width: 1300px) {
    div.stButton:has(button[key^="prompt_"]),
    .stButton:has(button[key^="prompt_"]),
    div.stButton > button[key^="prompt_"],
    .stButton > button[key^="prompt_"],
    button[key^="prompt_"],
    div[data-testid="column"]:has(button[key^="prompt_"]),
    [data-testid="column"]:has(button[key^="prompt_"]) {
        width: 350px !important;
        min-width: 350px !important;
        max-width: 350px !important;
        height: 120px !important;
        min-height: 120px !important;
        max-height: 120px !important;
    }
    
    div.stButton > button[key^="prompt_"],
    .stButton > button[key^="prompt_"],
    button[key^="prompt_"] {
        font-size: 13px !important;
    }
}

@media (max-width: 1100px) {
    div.stButton:has(button[key^="prompt_"]),
    .stButton:has(button[key^="prompt_"]),
    div.stButton > button[key^="prompt_"],
    .stButton > button[key^="prompt_"],
    button[key^="prompt_"],
    div[data-testid="column"]:has(button[key^="prompt_"]),
    [data-testid="column"]:has(button[key^="prompt_"]) {
        width: 300px !important;
        min-width: 300px !important;
        max-width: 300px !important;
        height: 110px !important;
        min-height: 110px !important;
        max-height: 110px !important;
    }
    
    div.stButton > button[key^="prompt_"],
    .stButton > button[key^="prompt_"],
    button[key^="prompt_"] {
        font-size: 12px !important;
    }
    
    .prompt-row {
        gap: 15px;
    }
}

@media (max-width: 768px) {
    .prompt-row {
        flex-direction: column;
        align-items: center;
    }
    
    div.stButton:has(button[key^="prompt_"]),
    .stButton:has(button[key^="prompt_"]),
    div.stButton > button[key^="prompt_"],
    .stButton > button[key^="prompt_"],
    button[key^="prompt_"],
    div[data-testid="column"]:has(button[key^="prompt_"]),
    [data-testid="column"]:has(button[key^="prompt_"]) {
        width: 320px !important;
        min-width: 320px !important;
        max-width: 320px !important;
        height: 100px !important;
        min-height: 100px !important;
        max-height: 100px !important;
    }
    
    div.stButton > button[key^="prompt_"],
    .stButton > button[key^="prompt_"],
    button[key^="prompt_"] {
        font-size: 12px !important;
    }
}

.centered-intro {
    text-align: center;
    font-size: 18px;
    font-weight: 500;
    color: #495057;
    margin-bottom: 40px;
}
</style>
""", unsafe_allow_html=True)

def render_header():
    is_authed = st.session_state.get("authenticated", False)
    if is_authed:
        auth_btn_html = '<a class="auth-button logout-btn" href="?app_logout=1">Logout</a>'
    else:
        auth_btn_html = f'<a class="auth-button login-btn" href="{auth_url}">Login</a>'
    st.markdown(f"""
    <div class="header-container">
        <div class="header-left">
            <img src="data:image/png;base64,{get_image_base64(logo_path)}" alt="TCS Logo" />
            <p class="header-title">Geni - Identity and Access Management  Agentic AI Service</p>
        </div>
        <div class="header-right">
            {auth_btn_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

render_header()

st.markdown("""
<div class="footer">
    Copyright © 2025 Tata Consultancy Services | Entry to this site is restricted to employees and affiliates.
</div>
""", unsafe_allow_html=True)

if "active_page" not in st.session_state:
    st.session_state["active_page"] = "main_chat"

# ---------- Helper: Sidebar Button with Active State ----------
def sidebar_button(label, page_name):
    # Check if this button is the active page
    active = st.session_state.get("active_page") == page_name

    # Normal Streamlit button (unique key)
    if st.sidebar.button(label, key=page_name):
        st.session_state["active_page"] = page_name
        st.rerun()  # rerun to update highlight

    # Inject CSS to make inactive buttons white and active one subtly highlighted
    # Inactive: white bg, dark text. Active: very light blue bg, dark text, subtle left border.
    bg_inactive = "#ffffff"
    bg_active = "#eaf3ff"   # very light blue for active (subtle)
    text_color = "#111111"
    left_border = "4px solid #007bff" if active else "4px solid transparent"

    st.sidebar.markdown(f"""
    <style>
    /* target the actual button element Streamlit renders (wrapper div present) */
    div.stButton > button[key="{page_name}"] {{
        background: {bg_active if active else bg_inactive} !important;
        color: {text_color} !important;
        width: 100%;
        text-align: left;
        padding: 8px 12px;
        margin-bottom: 6px;
        border-radius: 8px;
        font-weight: 600;
        border: none;
        box-shadow: none;
        border-left: {left_border} !important;
    }}
    div.stButton > button[key="{page_name}"]:hover {{
        background: #f5f7fb !important;
        color: {text_color} !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# NEW: Disabled Sidebar Button for Non-Authenticated Users
def sidebar_button_disabled(label, page_name):
    """
    Sidebar button that shows login message when clicked by non-authenticated users
    """
    if st.sidebar.button(label, key=f"{page_name}_disabled"):
        st.sidebar.warning("🔒 Please log in to access this feature!")
        st.sidebar.info("👆 Click the Login button in the top-right corner.")
    
    # Apply styling to look like normal buttons but slightly muted
    st.sidebar.markdown(f"""
    <style>
    div.stButton > button[key="{page_name}_disabled"] {{
        background: #e9ecef !important;
        color: #495057 !important;
        width: 100%;
        text-align: left;
        padding: 8px 12px;
        margin-bottom: 6px;
        border-radius: 8px;
        font-weight: 600;
        border: 1px solid #ced4da !important;
        box-shadow: none;
    }}
    div.stButton > button[key="{page_name}_disabled"]:hover {{
        background: #f8f9fa !important;
        color: #495057 !important;
    }}
    </style>
    """, unsafe_allow_html=True)

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = {
        'name': 'Pradeep Vishwakarma',
        'preferred_username': 'pradeep.vishwakarma@example.com'
    }

# UPDATED SIDEBAR LOGIC
if st.session_state.get("authenticated", False):
    st.sidebar.markdown('<div style="height: 15vh;"></div>', unsafe_allow_html=True)
    sidebar_button("Assistant for End users", "main_chat")
    sidebar_button("Assistant for IAM Admin", "orchestrator_chat")
    sidebar_button("Microsoft Entra Service", "entra_id_assistant")
    sidebar_button("Active Directory Service", "active_directory_assistant")
    sidebar_button("IAM Dashboard & Reports", "iam_metrics_dashboard")

    user_info = st.session_state.get("user_info", {})

    def render_sidebar_profile(user_info: dict):
        """
        Render the fixed, hoverable profile box in the sidebar.
        """
        display_name = user_info.get("name", "User")
        email = user_info.get("preferred_username", "user@example.com")
        role = user_info.get("role", "Employee")

        initials = "".join([part[0].upper() for part in display_name.split()[:2]])

        # HTML structure injected into the sidebar
        st.sidebar.markdown(f"""
        <div class="profile-box">
            <div class="profile-initials">{initials}</div>
            <div class="profile-details">
                <strong class="profile-displayname">{display_name}</strong>
                <span class="profile-email" title="{email}">{email}</span>
            </div>
        </div>

        <div class="hover-card">
            <strong>Username:</strong> {display_name}<br/>
            <strong>Email:</strong> {email}<br/>
            <strong>Role:</strong> {role}<br/>
        </div>
        """, unsafe_allow_html=True)

    # render the profile once
    render_sidebar_profile(user_info)

else:
    st.sidebar.title("Welcome")
    st.sidebar.write("Please log in to access the IAM Assistant features.")
    
    # Add some spacing
    st.sidebar.markdown('<div style="height: 2vh;"></div>', unsafe_allow_html=True)
    
    # Show disabled navigation buttons
    sidebar_button_disabled("Assistant for End users", "main_chat")
    sidebar_button_disabled("Assistant for IAM Admin", "orchestrator_chat") 
    sidebar_button_disabled("Microsoft Entra Service", "entra_id_assistant")
    sidebar_button_disabled("Active Directory Service", "active_directory_assistant")
    sidebar_button_disabled("IAM Dashboard & Reports", "iam_metrics_dashboard")
    
    # Add informational message
    st.sidebar.markdown('<div style="margin-top: 20px; font-size: 12px; color: #666; font-style: italic;">Login to enable these features</div>', unsafe_allow_html=True)

# Handle logout - UPDATED with Entra variables
if st.query_params.get("app_logout") == "1":
    for k in [
        "authenticated", "access_token", "thread_id", "chat_history", "user_info",
        "orch_thread_id", "orchestrator_chat_history", "active_page", "selected_prompt", 
        "chat_input_value", "last_input", "original_prompt_value", "entra_thread_id", 
        "entra_chat_history", "show_user_input", "show_group_input", "show_create_user_form"
    ]:
        st.session_state.pop(k, None)
    try:
        st.query_params.clear()
    except Exception:
        pass
    st.rerun()

if "code" in st.query_params:
    with st.spinner("Finalizing sign-in..."):
        token_response = handle_token_response()
        if token_response and "access_token" in token_response:
            st.session_state["authenticated"] = True
            st.session_state["access_token"] = token_response.get("access_token")
            st.session_state["user_info"] = token_response.get("id_token_claims", {})
            st.session_state.setdefault("orchestrator_chat_history", [])
            st.session_state.setdefault("active_page", "main_chat")
            try:
                st.query_params.clear()
            except Exception:
                pass
            st.success("Signed in successfully.")
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("Authentication failed. Please try again.")
            try:
                st.query_params.clear()
            except Exception:
                pass

def show_intro():
    st.markdown('<div class="centered-intro">You are using "Assistant for End users" functionality​</div>', unsafe_allow_html=True)

# ---------- Load prompts from JSON file ----------
def load_prompts_from_file(filepath: str = "prompts.json"):
    """Load prompts from JSON file"""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data.get('prompts', [])
    except FileNotFoundError:
        st.error(f"Prompts file '{filepath}' not found. Please create the file with your prompts.")
        return []
    except json.JSONDecodeError:
        st.error(f"Error reading prompts file '{filepath}'. Please check the JSON format.")
        return []

# ---------- BULLETPROOF: Uniform grid system with aggressive CSS ----------
def show_suggested_prompts():
    """Display ALL prompts in simple sequential 3-column grid with BULLETPROOF fixed size"""
    
    # Load prompts from JSON file
    prompts = load_prompts_from_file()
    
    if not prompts:
        st.warning("No prompts found. Please add prompts to the prompts.json file.")
        return
    
    # Emoji mappings for prompts
    emoji_map = {
        0: "📝", 1: "🔄", 2: "🔐", 3: "🛡️", 4: "💼", 5: "🔧",
        6: "📋", 7: "⚙️", 8: "📊", 9: "🔍", 10: "🎯", 11: "📱", 12: "⚡"
    }
    
    cols = 3
    rows = (len(prompts) + cols - 1) // cols
    
    # Create centered container for the grid
    with st.container():
        st.markdown('<div class="prompt-grid-container">', unsafe_allow_html=True)
        
        # Render each row sequentially
        for r in range(rows):
            st.markdown('<div class="prompt-row">', unsafe_allow_html=True)
            
            # Create columns for this row
            cols_row = st.columns([1, 1, 1], gap="medium")
            
            for c in range(cols):
                prompt_index = r * cols + c
                
                with cols_row[c]:
                    if prompt_index < len(prompts):
                        # Display prompt button with aggressive text truncation
                        prompt_text = prompts[prompt_index]
                        emoji = emoji_map.get(prompt_index, "💡")
                        
                        # Aggressive truncation to ensure uniform button appearance
                        display_text = prompt_text
                        if len(prompt_text) > 45:
                            display_text = prompt_text[:42] + "..."
                        
                        button_text = f"{emoji}\n\n{display_text}"
                        
                        if st.button(button_text, key=f"prompt_{r}_{c}"):
                            st.session_state["chat_input_value"] = prompt_text  # Use full text
                            st.session_state["original_prompt_value"] = prompt_text
                            st.rerun()
                    else:
                        # Empty space to maintain grid structure
                        st.markdown('<div style="height: 130px; width: 400px; visibility: hidden;"></div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

def main_chat_page():
    if "access_token" not in st.session_state or not st.session_state["access_token"]:
        st.error("Access token is not found or invalid.", icon="🚨")
        return

    if "thread_id" not in st.session_state:
        try:
            headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
            r = requests.post(f"{API_BASE}/thread", timeout=120, headers=headers)
            r.raise_for_status()
            st.session_state["thread_id"] = r.json()["thread_id"]
        except Exception as e:
            st.error(f"Failed to create thread: {str(e)}", icon="🚨")
            st.stop()

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    
    # Initialize chat_input_value if not exists
    if "chat_input_value" not in st.session_state:
        st.session_state["chat_input_value"] = ""

    container_class = "message-container no-messages" if len(st.session_state["chat_history"]) == 0 else "message-container"
    st.markdown(f'<div class="{container_class}">', unsafe_allow_html=True)
    
    # Show intro and suggested prompts only if no chat history
    if len(st.session_state["chat_history"]) == 0:
        show_intro()
        show_suggested_prompts()

    container = st.container()
    for user_msg, agent_msg in st.session_state["chat_history"]:
        with container:
            with st.chat_message("user"):
                st.markdown(f"**You:** {user_msg}")
            with st.chat_message("assistant"):
                st.markdown(f"**IAM Assistant:** {agent_msg}")
    st.markdown('</div>', unsafe_allow_html=True)

    # Create chat input with dynamic value
    chat_placeholder = "Hi there! Geni is ready to help you on IAM – start using me"
    
    # Use regular chat input but check if there's a pre-filled value
    if st.session_state.get("chat_input_value"):
        # Show the pre-filled text input without message or button
        user_input = st.text_input(
            "Your message:", 
            value=st.session_state["chat_input_value"],
            key="chat_text_input",
            placeholder=chat_placeholder
        )
        
        # Handle Enter key press - auto-submit when user input changes
        if user_input != st.session_state.get("last_user_input", ""):
            st.session_state["last_user_input"] = user_input
            # Auto-submit on Enter (when user input changes)
            if user_input.strip() and user_input != st.session_state.get("original_prompt_value", ""):
                # Store the user input before processing
                current_user_input = user_input
                
                # Clear the pre-filled value
                st.session_state["chat_input_value"] = ""
                st.session_state["original_prompt_value"] = ""
                
                # Process the message
                with st.spinner("Thinking..."):
                    try:
                        headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
                        payload = {"thread_id": st.session_state["thread_id"], "message": current_user_input}
                        r = requests.post(f"{API_BASE}/chat", json=payload, timeout=120, headers=headers)
                        r.raise_for_status()
                        reply = r.json().get("reply", "")
                        
                        # Check for server error responses
                        is_server_busy = False
                        if isinstance(reply, dict) and reply.get('code') == 'server_error':
                            reply = "**Agent is currently busy, please wait a moment and try again.**"
                            is_server_busy = True
                        elif isinstance(reply, str):
                            try:
                                parsed = ast.literal_eval(reply)
                                if isinstance(parsed, dict) and parsed.get('code') == 'server_error':
                                    reply = "**Agent is currently busy, please wait a moment and try again.**"
                                    is_server_busy = True
                            except Exception:
                                if 'server_error' in reply:
                                    reply = "**Agent is currently busy, please wait a moment and try again.**"
                                    is_server_busy = True
                    except Exception:
                        reply = "**Agent is currently busy, please wait a moment and try again.**"
                        is_server_busy = True
                
                # If server is busy, put the original query back in the input
                if is_server_busy:
                    st.session_state["chat_input_value"] = current_user_input
                
                typing_placeholder = st.empty()
                typing_message = ""
                for char in reply:
                    typing_message += char
                    typing_placeholder.markdown(f"**IAM Assistant**: {typing_message}")
                    time.sleep(0.01)
                st.session_state["chat_history"].append((current_user_input, reply))
                st.rerun()
    else:
        # Regular chat input when no pre-filled value
        prompt = st.chat_input(chat_placeholder)
        if prompt:
            # Store the user input before processing
            current_user_input = prompt
            
            with st.spinner("Thinking..."):
                try:
                    headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
                    payload = {"thread_id": st.session_state["thread_id"], "message": current_user_input}
                    r = requests.post(f"{API_BASE}/chat", json=payload, timeout=120, headers=headers)
                    r.raise_for_status()
                    reply = r.json().get("reply", "")
                    
                    # Check for server error responses
                    is_server_busy = False
                    if isinstance(reply, dict) and reply.get('code') == 'server_error':
                        reply = "**Agent is currently busy, please wait a moment and try again.**"
                        is_server_busy = True
                    elif isinstance(reply, str):
                        try:
                            parsed = ast.literal_eval(reply)
                            if isinstance(parsed, dict) and parsed.get('code') == 'server_error':
                                reply = "**Agent is currently busy, please wait a moment and try again.**"
                                is_server_busy = True
                        except Exception:
                            if 'server_error' in reply:
                                reply = "**Agent is currently busy, please wait a moment and try again.**"
                                is_server_busy = True
                except Exception:
                    reply = "**Agent is currently busy, please wait a moment and try again.**"
                    is_server_busy = True
            
            # If server is busy, put the original query back in the input
            if is_server_busy:
                st.session_state["chat_input_value"] = current_user_input
            
            typing_placeholder = st.empty()
            typing_message = ""
            for char in reply:
                typing_message += char
                typing_placeholder.markdown(f"**IAM Assistant**: {typing_message}")
                time.sleep(0.01)
            st.session_state["chat_history"].append((current_user_input, reply))
            st.rerun()

# ---------- Helper: render structured (JSON) or plain text for Orchestrator ----------
def _render_result_as_table_or_text(result_str: str, role_label: str = "Orchestrator"):
    """
    Detects JSON returned by the ProvisioningAgent and renders as a table.
    Falls back to plain text if not JSON.
    """

    # Try to parse JSON
    try:
        parsed = json.loads(result_str)
    except Exception:
        parsed = None

    if isinstance(parsed, list):
        if len(parsed) == 0:
            st.info("No rows.")
            return
        try:
            import pandas as pd
            if isinstance(parsed[0], dict):
                st.dataframe(pd.DataFrame(parsed), use_container_width=True)
            else:
                st.dataframe(pd.DataFrame(parsed, columns=["Value"]), use_container_width=True)
        except Exception:
            st.table(parsed)
    elif isinstance(parsed, dict):
        if "groups" in parsed and isinstance(parsed["groups"], list):
            st.markdown(f"**Total:** {parsed.get('count', len(parsed['groups']))}")
            try:
                import pandas as pd
                groups = parsed["groups"]
                if groups and isinstance(groups[0], dict):
                    st.dataframe(pd.DataFrame(groups), use_container_width=True)
                else:
                    st.table(groups)
            except Exception:
                st.table(parsed["groups"])
        else:
            try:
                import pandas as pd
                st.dataframe(pd.DataFrame([parsed]), use_container_width=True)
            except Exception:
                st.json(parsed)
    else:
        st.markdown(f"**{role_label}**: {result_str}")

# ---------- Orchestrator Chat Page ----------
def orchestrator_chat_page():
    if "access_token" not in st.session_state or not st.session_state["access_token"]:
        st.error("Access token is not found or invalid.", icon="🚨")
        return

    if "orch_thread_id" not in st.session_state:
        try:
            headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
            r = requests.post(f"{API_BASE}/orchestrator/thread", timeout=120, headers=headers)
            r.raise_for_status()
            st.session_state["orch_thread_id"] = r.json()["thread_id"]
        except Exception as e:
            st.error(f"Failed to create orchestrator thread: {str(e)}", icon="🚨")
            st.stop()

    if "orchestrator_chat_history" not in st.session_state:
        st.session_state["orchestrator_chat_history"] = []

    container_class = "message-container no-messages" if len(st.session_state["orchestrator_chat_history"]) == 0 else "message-container"
    st.markdown(f'<div class="{container_class}">', unsafe_allow_html=True)
    if len(st.session_state["orchestrator_chat_history"]) == 0:
        st.markdown('<div class="centered-intro">You are using "Assistant for Admin users" functionality</div>', unsafe_allow_html=True)

    container = st.container()
    for user_msg, agent_msg in st.session_state["orchestrator_chat_history"]:
        with container:
            with st.chat_message("user"):
                st.markdown(f"**You:** {user_msg}")
            with st.chat_message("assistant"):
                _render_result_as_table_or_text(agent_msg, role_label="Orchestrator")

    prompt = st.chat_input("Hi there! Geni is ready to help you on IAM – start using me")
    if prompt:
        user_input = prompt
        with st.spinner("Thinking..."):
            try:
                headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
                payload = {
                    "thread_id": st.session_state["orch_thread_id"],
                    "message": user_input,
                    "chat_history": [
                        {"role": "user", "content": um} if i % 2 == 0 else {"role": "assistant", "content": am}
                        for i, (um, am) in enumerate(st.session_state["orchestrator_chat_history"])
                    ],
                }
                r = requests.post(f"{API_BASE}/orchestrator/chat", json=payload, timeout=120, headers=headers)
                r.raise_for_status()
                reply = r.json().get("result", "")
            except Exception as e:
                reply = "**Orchestrator is currently busy, please try again later.**"

        is_structured = False
        try:
            parsed = json.loads(reply)
            is_structured = isinstance(parsed, (list, dict))
        except Exception:
            is_structured = False

        with st.chat_message("assistant"):
            if is_structured:
                _render_result_as_table_or_text(reply, role_label="Orchestrator")
            else:
                typing_placeholder = st.empty()
                typing_message = ""
                for char in reply:
                    typing_message += char
                    typing_placeholder.markdown(f"**Orchestrator**: {typing_message}")
                    time.sleep(0.01)

        st.session_state["orchestrator_chat_history"].append((user_input, reply))
        st.rerun()

# NEW: Entra Service Page
def entra_service_page():
    """Microsoft Entra Service chat interface"""
    if "access_token" not in st.session_state or not st.session_state["access_token"]:
        st.error("Access token is not found or invalid.", icon="🚨")
        return

    if "entra_thread_id" not in st.session_state:
        st.session_state["entra_thread_id"] = f"entra-{int(time.time())}"

    if "entra_chat_history" not in st.session_state:
        st.session_state["entra_chat_history"] = []

    container_class = "message-container no-messages" if len(st.session_state["entra_chat_history"]) == 0 else "message-container"
    st.markdown(f'<div class="{container_class}">', unsafe_allow_html=True)
    
    if len(st.session_state["entra_chat_history"]) == 0:
        st.markdown('<div class="centered-intro">🔐 Microsoft Entra Service - Direct IAM Operations</div>', unsafe_allow_html=True)
        
        # Add quick action buttons
        st.markdown("### Quick Actions")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📋 List All Users", key="list_users_btn"):
                process_entra_command("list all users")
        
        with col2:
            if st.button("👥 List All Groups", key="list_groups_btn"):
                process_entra_command("list all groups")
        
        with col3:
            if st.button("ℹ️ Get User Details", key="user_details_btn"):
                st.session_state["show_user_input"] = True
                st.rerun()
        
        # Additional action buttons
        col4, col5, col6 = st.columns(3)
        
        with col4:
            if st.button("📊 List Top 10 Users", key="list_top_users_btn"):
                process_entra_command("list top 10 users")
        
        with col5:
            if st.button("🔍 Group Details", key="group_details_btn"):
                st.session_state["show_group_input"] = True
                st.rerun()
        
        with col6:
            if st.button("🆕 Create User", key="create_user_btn"):
                st.session_state["show_create_user_form"] = True
                st.rerun()
        
        # Show input forms if requested
        if st.session_state.get("show_user_input", False):
            with st.form("user_details_form"):
                user_email = st.text_input("Enter user email or ID:")
                if st.form_submit_button("Get Details"):
                    if user_email:
                        process_entra_command(f"get details for user {user_email}")
                        st.session_state["show_user_input"] = False
                        st.rerun()
        
        if st.session_state.get("show_group_input", False):
            with st.form("group_details_form"):
                group_id = st.text_input("Enter group ID or name:")
                if st.form_submit_button("Get Group Details"):
                    if group_id:
                        process_entra_command(f"get details for group {group_id}")
                        st.session_state["show_group_input"] = False
                        st.rerun()
        
        if st.session_state.get("show_create_user_form", False):
            with st.form("create_user_form"):
                st.markdown("#### Create New User")
                display_name = st.text_input("Display Name:")
                user_principal_name = st.text_input("Email (UserPrincipalName):")
                password = st.text_input("Temporary Password:", type="password")
                
                if st.form_submit_button("Create User"):
                    if display_name and user_principal_name and password:
                        try:
                            headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
                            payload = {
                                "display_name": display_name,
                                "user_principal_name": user_principal_name,
                                "password": password
                            }
                            
                            r = requests.post(f"{API_BASE}/entra/users", json=payload, timeout=120, headers=headers)
                            r.raise_for_status()
                            
                            result = r.json().get("message", "User created successfully")
                            st.session_state["entra_chat_history"].append(
                                (f"Create user: {display_name} ({user_principal_name})", result, "create_user")
                            )
                            st.session_state["show_create_user_form"] = False
                            st.success("User creation request submitted!")
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Failed to create user: {str(e)}")
                    else:
                        st.error("Please fill in all fields")

    # Display chat history
    container = st.container()
    for user_msg, agent_msg, intent in st.session_state["entra_chat_history"]:
        with container:
            with st.chat_message("user"):
                st.markdown(f"**You:** {user_msg}")
            with st.chat_message("assistant"):
                st.markdown(f"**Intent:** `{intent}`")
                
                # Format the response better
                if isinstance(agent_msg, list):
                    for item in agent_msg:
                        st.markdown(f"• {item}")
                elif agent_msg.startswith("❌"):
                    st.error(agent_msg)
                elif agent_msg.startswith("✅"):
                    st.success(agent_msg)
                else:
                    # Check if it's formatted text with line breaks
                    if "\n" in agent_msg:
                        for line in agent_msg.split("\n"):
                            if line.strip():
                                if line.startswith("-"):
                                    st.markdown(f"• {line[1:].strip()}")
                                else:
                                    st.markdown(line)
                    else:
                        st.markdown(f"**Result:** {agent_msg}")

    st.markdown('</div>', unsafe_allow_html=True)

    # Chat input
    prompt = st.chat_input("Ask me to perform IAM operations (e.g., 'list users', 'create group', 'get user details')")
    if prompt:
        process_entra_command(prompt)

def process_entra_command(user_input: str):
    """Process Entra service commands"""
    with st.spinner("Executing IAM operation..."):
        try:
            headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
            payload = {
                "message": user_input,
                "thread_id": st.session_state["entra_thread_id"]
            }
            
            r = requests.post(f"{API_BASE}/entra/chat", json=payload, timeout=120, headers=headers)
            r.raise_for_status()
            
            response_data = r.json()
            intent = response_data.get("intent", "unknown")
            result = response_data.get("result", "No response received")
            
            # Add to chat history
            st.session_state["entra_chat_history"].append((user_input, result, intent))
            st.rerun()
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to execute command: {str(e)}"
            st.session_state["entra_chat_history"].append((user_input, error_msg, "error"))
            st.rerun()
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            st.session_state["entra_chat_history"].append((user_input, error_msg, "error"))
            st.rerun()

def about_iam():
    st.markdown('<div style="margin-top: 100px;"></div>', unsafe_allow_html=True)
    st.markdown("### About IAM")
    st.write("Identity and Access Management (IAM) is a framework of policies and technologies that ensure the right individuals have appropriate access to technology resources.")

def rules_and_regulations():
    st.markdown('<div style="margin-top: 100px;"></div>', unsafe_allow_html=True)
    st.markdown("### Rules and Regulations")
    st.write("1. Only authorized users can access the system.")
    st.write("2. Users must follow the company's security guidelines.")
    st.write("3. All actions performed in the system must be logged.")
    st.write("4. MFA must be enabled for sensitive areas.")

# UPDATED Main routing logic with Entra Service
if st.session_state.get("authenticated", False):
    active_page = st.session_state.get("active_page", "main_chat")
   
    if active_page == "main_chat":
        main_chat_page()
    elif active_page == "orchestrator_chat":
        orchestrator_chat_page()
    elif active_page == "entra_id_assistant":
        entra_service_page()
    elif active_page == "active_directory_assistant":
        st.markdown('<div class="centered-intro">🏢 Active Directory Service - Coming Soon</div>', unsafe_allow_html=True)
        st.info("This service will be available in the next update.")
    elif active_page == "iam_metrics_dashboard":
        st.markdown('<div class="centered-intro">📊 IAM Dashboard & Reports - Coming Soon</div>', unsafe_allow_html=True)
        st.info("Dashboard and reporting features will be available in the next update.")
    elif active_page == "about_iam":
        about_iam()
    elif active_page == "rules":
        rules_and_regulations()
    else:
        main_chat_page()
else:
    st.markdown("""
<div style="display:flex; justify-content:center; align-items:center; height:80vh; text-align:center; font-size:18px; line-height:1.6;">
    <div>
        Ask any thing on Identity and Access Management
        <br>
        Click the links on the left side to understand more on how these assistants can help you
        <br>
        Login if you want to start using them!
    </div>
</div>
""", unsafe_allow_html=True)
