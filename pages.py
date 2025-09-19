import streamlit as st
import pandas as pd
import json
import ast
import time
from chat_service import get_thread_id, send_message

def show_intro(message: str):
    """Renders a centered introductory message."""
    st.markdown(f'<div class="centered-intro">{message}</div>', unsafe_allow_html=True)

def render_result_as_table_or_text(result_str: str, role_label: str):
    """
    Detects JSON and renders it as a table or a dataframe,
    otherwise falls back to plain text.
    """
    st.markdown("""<style>...</style>""", unsafe_allow_html=True) # Retain CSS

    try:
        parsed = json.loads(result_str)
    except Exception:
        parsed = None

    if isinstance(parsed, list):
        if len(parsed) == 0:
            st.info("No rows.")
            return
        try:
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
                groups = parsed["groups"]
                if groups and isinstance(groups[0], dict):
                    st.dataframe(pd.DataFrame(groups), use_container_width=True)
                else:
                    st.table(groups)
            except Exception:
                st.table(parsed["groups"])
        else:
            try:
                st.dataframe(pd.DataFrame([parsed]), use_container_width=True)
            except Exception:
                st.json(parsed)
    else:
        st.markdown(f"**{role_label}**: {result_str}")

def main_chat_page():
    """Logic and rendering for the End User chat page."""
    if "access_token" not in st.session_state:
        st.error("Access token is not found or invalid.", icon="🚨")
        return
    
    if "thread_id" not in st.session_state:
        st.session_state["thread_id"] = get_thread_id("thread")
        if not st.session_state["thread_id"]: return
    
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    
    container_class = "message-container no-messages" if not st.session_state["chat_history"] else "message-container"
    st.markdown(f'<div class="{container_class}">', unsafe_allow_html=True)
    if not st.session_state["chat_history"]:
        show_intro("You are using “Assistant for End users” functionality​")

    for user_msg, agent_msg in st.session_state["chat_history"]:
        with st.chat_message("user"):
            st.markdown(f"**You:** {user_msg}")
        with st.chat_message("assistant"):
            st.markdown(f"**IAM Assistant:** {agent_msg}")

    prompt = st.chat_input("Hi there! Geni is ready to help you on IAM – start using me")
    if prompt:
        with st.spinner("Thinking..."):
            payload = {"thread_id": st.session_state["thread_id"], "message": prompt}
            response = send_message("chat", payload)
            reply = response.get("reply", "**Agent is currently busy, please wait a moment and try again.**")
            
            typing_placeholder = st.empty()
            typing_message = ""
            for char in reply:
                typing_message += char
                typing_placeholder.markdown(f"**IAM Assistant**: {typing_message}")
                time.sleep(0.01)
            
            st.session_state["chat_history"].append((prompt, reply))
            st.rerun()

def orchestrator_chat_page():
    """Logic and rendering for the IAM Admin chat page."""
    if "access_token" not in st.session_state:
        st.error("Access token is not found or invalid.", icon="🚨")
        return
    
    if "orch_thread_id" not in st.session_state:
        st.session_state["orch_thread_id"] = get_thread_id("orchestrator/thread")
        if not st.session_state["orch_thread_id"]: return
    
    if "orchestrator_chat_history" not in st.session_state:
        st.session_state["orchestrator_chat_history"] = []
    
    container_class = "message-container no-messages" if not st.session_state["orchestrator_chat_history"] else "message-container"
    st.markdown(f'<div class="{container_class}">', unsafe_allow_html=True)
    if not st.session_state["orchestrator_chat_history"]:
        show_intro("You are using “Assistant for Admin users” functionality")
    
    for user_msg, agent_msg in st.session_state["orchestrator_chat_history"]:
        with st.chat_message("user"):
            st.markdown(f"**You:** {user_msg}")
        with st.chat_message("assistant"):
            render_result_as_table_or_text(agent_msg, role_label="Orchestrator")
    
    prompt = st.chat_input("Hi there! Geni is ready to help you on IAM – start using me")
    if prompt:
        with st.spinner("Thinking..."):
            chat_history_payload = [
                {"role": "user" if i % 2 == 0 else "assistant", "content": msg}
                for i, (um, am) in enumerate(st.session_state["orchestrator_chat_history"])
                for msg in (um, am)
            ]
            payload = {
                "thread_id": st.session_state["orch_thread_id"],
                "message": prompt,
                "chat_history": chat_history_payload,
            }
            response = send_message("orchestrator/chat", payload)
            reply = response.get("result", "**Orchestrator is currently busy, please try again later.**")

            is_structured = False
            try:
                json.loads(reply)
                is_structured = True
            except (json.JSONDecodeError, TypeError):
                pass
            
            with st.chat_message("assistant"):
                if is_structured:
                    render_result_as_table_or_text(reply, role_label="Orchestrator")
                else:
                    typing_placeholder = st.empty()
                    typing_message = ""
                    for char in reply:
                        typing_message += char
                        typing_placeholder.markdown(f"**Orchestrator**: {typing_message}")
                        time.sleep(0.01)
            
            st.session_state["orchestrator_chat_history"].append((prompt, reply))
            st.rerun()

def about_iam_page():
    """Renders the About IAM information page."""
    st.markdown('<div style="margin-top: 100px;"></div>', unsafe_allow_html=True)
    st.markdown("### About IAM")
    st.write("Identity and Access Management (IAM) is a framework of policies and technologies that ensure the right individuals have appropriate access to technology resources.")

def rules_and_regulations_page():
    """Renders the Rules and Regulations page."""
    st.markdown('<div style="margin-top: 100px;"></div>', unsafe_allow_html=True)
    st.markdown("### Rules and Regulations")
    st.write("1. Only authorized users can access the system.")
    st.write("2. Users must follow the company's security guidelines.")
    st.write("3. All actions performed in the system must be logged.")
    st.write("4. MFA must be enabled for sensitive areas.")