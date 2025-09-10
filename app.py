import requests
import streamlit as st
import base64
import time
import msal
import os
from dotenv import load_dotenv
import streamlit.components.v1 as components
import ast

# Load environment variables
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

st.set_page_config(page_title="IAM GENI", page_icon=logo_path, layout="wide")

auth_url = initiate_login()
azure_logout_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/logout?post_logout_redirect_uri={REDIRECT_URI}"

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

/* Shift header right when sidebar open on large screens */
[data-testid="stSidebar"][aria-expanded="true"] ~ div .header-container {
    margin-left: 280px;
    width: calc(100% - 280px);
}

/* Adjust shift on medium screens */
@media (max-width: 991px) {
    [data-testid="stSidebar"][aria-expanded="true"] ~ div .header-container {
        margin-left: 200px;
        width: calc(100% - 200px);
    }
}

/* On mobile, sidebar overlays, move header down */
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

/* Styled login prompt below header */
.main-content-logged-out {
    margin-top: 120px;
    text-align: center;
    font-size: 18px;
    font-weight: 700; /* Bold */
    color: #555555;    /* Greyish for visibility */
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
            <p class="header-title">IAM GENI</p>
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

st.sidebar.title("Navigation")
chat_button = st.sidebar.button("Chat")
about_button = st.sidebar.button("About IAM")
rules_button = st.sidebar.button("Rules and Regulations")

# Auth logic
if st.query_params.get("app_logout") == "1":
    for k in ["authenticated", "access_token", "thread_id", "chat_history", "user_info"]:
        st.session_state.pop(k, None)
    try:
        st.query_params.clear()
    except Exception:
        pass
    components.html(f"""
        <script>
          try {{
            window.open("{azure_logout_url}", "azure_signout_" + Date.now(), "popup,width=600,height=500");
          }} catch (e) {{}}
        </script>
    """, height=0)
    st.success("Logged out.")
    st.rerun()

if "code" in st.query_params:
    with st.spinner("Finalizing sign-in..."):
        token_response = handle_token_response()
        if token_response and "access_token" in token_response:
            st.session_state["authenticated"] = True
            st.session_state["access_token"] = token_response.get("access_token")
            st.session_state["user_info"] = token_response.get("id_token_claims", {})
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
    st.markdown('<div class="centered-intro">Ask me anything about Identity and Access Management.</div>', unsafe_allow_html=True)

def main_chat_page():
    if "access_token" not in st.session_state or not st.session_state["access_token"]:
        st.error("Access token is not found or invalid.", icon="🚨")
        return

    if "thread_id" not in st.session_state:
        try:
            headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
            r = requests.post(f"{API_BASE}/thread", timeout=60, headers=headers)
            r.raise_for_status()
            st.session_state["thread_id"] = r.json()["thread_id"]
        except Exception as e:
            st.error(f"Failed to create thread: {str(e)}", icon="🚨")
            st.stop()

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    container_class = "message-container no-messages" if len(st.session_state["chat_history"]) == 0 else "message-container"
    st.markdown(f'<div class="{container_class}">', unsafe_allow_html=True)
    if len(st.session_state["chat_history"]) == 0:
        show_intro()

    container = st.container()
    for user_msg, agent_msg in st.session_state["chat_history"]:
        with container:
            with st.chat_message("user"):
                st.markdown(f"**You:** {user_msg}")
            with st.chat_message("assistant"):
                st.markdown(f"**IAM Assistant:** {agent_msg}")
    st.markdown('</div>', unsafe_allow_html=True)

    prompt = st.chat_input("Say something:")
    if prompt:
        user_input = prompt
        with st.spinner("Thinking..."):
            try:
                headers = {"Authorization": f"Bearer {st.session_state['access_token']}"}
                payload = {"thread_id": st.session_state["thread_id"], "message": user_input}
                r = requests.post(f"{API_BASE}/chat", json=payload, timeout=60, headers=headers)
                r.raise_for_status()
                reply = r.json().get("reply", "")
                if isinstance(reply, dict) and reply.get('code') == 'server_error':
                    reply = "**Agent is currently busy, please wait a moment and try again.**"
                elif isinstance(reply, str):
                    try:
                        parsed = ast.literal_eval(reply)
                        if isinstance(parsed, dict) and parsed.get('code') == 'server_error':
                            reply = "**Agent is currently busy, please wait a moment and try again.**"
                    except Exception:
                        if 'server_error' in reply:
                            reply = "**Agent is currently busy, please wait a moment and try again.**"
            except Exception:
                reply = "**Agent is currently busy, please wait a moment and try again.**"
        typing_placeholder = st.empty()
        typing_message = ""
        for char in reply:
            typing_message += char
            typing_placeholder.markdown(f"**IAM Assistant**: {typing_message}")
            time.sleep(0.01)
        st.session_state["chat_history"].append((user_input, reply))
        st.rerun()

def about_iam():
    st.write("**About IAM**")
    st.write("Identity and Access Management (IAM) is a framework of policies and technologies that ensure the right individuals have appropriate access to technology resources.")

def rules_and_regulations():
    st.write("**Rules and Regulations**")
    st.write("1. Only authorized users can access the system.")
    st.write("2. Users must follow the company's security guidelines.")
    st.write("3. All actions performed in the system must be logged.")
    st.write("4. MFA must be enabled for sensitive areas.")

if st.session_state.get("authenticated", False):
    if chat_button:
        main_chat_page()
    elif about_button:
        about_iam()
    elif rules_button:
        rules_and_regulations()
    else:
        main_chat_page()
else:
    st.markdown('<div class="main-content-logged-out">Please log in to access the IAM Assistant.</div>', unsafe_allow_html=True)
