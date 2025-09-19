import streamlit as st
import base64
from config import LOGO_PATH, TENANT_ID, REDIRECT_URI

# Original CSS for fixed header and footer
def load_css():
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
        box-shadow: 0 6px 20px rgba(0,0,0,0.25);
        padding: 10px;
        font-size: 13px;
        z-index: 999999 !important;
        background: #fff;
    }
    section[data-testid="stSidebar"] .profile-box:hover ~ .hover-card {
        display: block;
    }
    </style>
    """, unsafe_allow_html=True)


def get_image_base64(image_path: str) -> str:
    """Reads an image and returns its base64 encoded string."""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()
    except FileNotFoundError:
        st.error(f"Logo file not found at {image_path}. Please check the path.")
        return ""

def render_header(auth_url: str):
    """Renders the fixed header with the logo and login/logout button."""
    is_authed = st.session_state.get("authenticated", False)
    azure_logout_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/logout?post_logout_redirect_uri={REDIRECT_URI}"
    
    auth_btn_html = (
        f'<a class="auth-button logout-btn" href="{azure_logout_url}">Logout</a>'
        if is_authed else 
        f'<a class="auth-button login-btn" href="{auth_url}">Login</a>'
    )
    
    logo_base64 = get_image_base64(LOGO_PATH)
    st.markdown(f"""
    <div class="header-container">
        <div class="header-left">
            <img src="data:image/png;base64,{logo_base64}" alt="Logo" />
            <p class="header-title">Geni - Identity and Access Management Agentic AI Service</p>
        </div>
        <div class="header-right">
            {auth_btn_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_footer():
    """Renders the fixed footer."""
    st.markdown("""
    <div class="footer">
        Copyright © 2025 Tata Consultancy Services | Entry to this site is restricted to employees and affiliates.
    </div>
    """, unsafe_allow_html=True)

def render_sidebar(auth_url: str):
    """Renders the sidebar based on authentication status."""
    if st.session_state.get("authenticated", False):
        sidebar_button("Assistant for End users", "main_chat")
        sidebar_button("Assistant for IAM Admin users", "orchestrator_chat")
        sidebar_button("Entra ID Assistant", "entra_id_assistant")
        sidebar_button("Active Directory Assistant", "active_directory_assistant")
        sidebar_button("IAM Metrics Dashboard", "iam_metrics_dashboard")
        user_info = st.session_state.get("user_info", {})
        render_sidebar_profile(user_info)
    else:
        st.sidebar.title("Welcome")
        st.sidebar.write("Please log in to access the IAM Assistant features.")

def sidebar_button(label: str, page_name: str):
    """Renders a sidebar button with active state highlighting."""
    active = st.session_state.get("active_page") == page_name
    
    if st.sidebar.button(label, key=page_name):
        st.session_state["active_page"] = page_name
        st.rerun()
    
    bg_inactive = "#ffffff"
    bg_active = "#eaf3ff"
    text_color = "#111111"
    left_border = "4px solid #007bff" if active else "4px solid transparent"
    
    st.sidebar.markdown(f"""
    <style>
    div.stButton > button[key="{page_name}"] {{
        background: {bg_active if active else bg_inactive} !important;
        color: {text_color} !important;
        border-left: {left_border} !important;
    }}
    div.stButton > button[key="{page_name}"]:hover {{
        background: #f5f7fb !important;
        color: {text_color} !important;
    }}
    </style>
    """, unsafe_allow_html=True)

def render_sidebar_profile(user_info: dict):
    """Renders the fixed, hoverable profile box in the sidebar."""
    display_name = user_info.get("name", "User")
    email = user_info.get("preferred_username", "user@example.com")
    role = user_info.get("role", "Employee")
    initials = "".join([part[0].upper() for part in display_name.split()[:2]])
    
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