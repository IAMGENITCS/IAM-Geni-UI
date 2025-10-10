import os
import threading
import traceback
import re
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from fastapi.security import OAuth2PasswordBearer
from fastapi.encoders import jsonable_encoder
import jwt
import requests
import asyncio
import logging
from dotenv import load_dotenv


# Import your existing components
from OrchestratorAgent import OrchestratorAgentWrapper
from IAMAssistant import IAMAssistant
from provisioning_orch_new import ProvisioningAgent
# ADD NEW IMPORT:
from AD_Provisioning_Agent_Wrapper import ADProvisioningWrapper
# Dashboard plugin import
from IamDashboard.iamMetrics import IAMPlugin
from EntraAgentWrapper import EntraAgentWrapper


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env early so downstream modules can read them
load_dotenv()


app = FastAPI(title="IAM Assistant Service", version="1.0.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8501", "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Thread-safe singletons
_assistant_lock = threading.Lock()
_assistant: Optional[IAMAssistant] = None

_orchestrator_lock = threading.Lock()
_orchestrator_agent: Optional[OrchestratorAgentWrapper] = None

_provisioning_lock = threading.Lock()
_provisioning_agent: Optional[ProvisioningAgent] = None

# ADD NEW SINGLETON:
_ad_provisioning_lock = threading.Lock()
_ad_provisioning_agent: Optional[ADProvisioningWrapper] = None

# Entra-only agent singleton
_entra_agent_lock = threading.Lock()
_entra_agent: Optional[EntraAgentWrapper] = None

# Dashboard plugin singleton
_dashboard_lock = threading.Lock()
_dashboard_plugin: Optional[IAMPlugin] = None
# Dashboard cache
_dashboard_cache_lock = threading.Lock()
_dashboard_cache: Optional[Dict[str, Any]] = None
_dashboard_cache_ts: float = 0.0
_DASHBOARD_TTL_SECONDS = int(os.getenv("DASHBOARD_CACHE_TTL", "900"))  # default 15 min


def get_assistant() -> IAMAssistant:
    global _assistant
    if _assistant is None:
        with _assistant_lock:
            if _assistant is None:
                _assistant = IAMAssistant()
    return _assistant


def get_orchestrator_agent() -> OrchestratorAgentWrapper:
    global _orchestrator_agent
    if _orchestrator_agent is None:
        with _orchestrator_lock:
            if _orchestrator_agent is None:
                _orchestrator_agent = OrchestratorAgentWrapper()
    return _orchestrator_agent


def get_provisioning_agent() -> ProvisioningAgent:
    global _provisioning_agent
    if _provisioning_agent is None:
        with _provisioning_lock:
            if _provisioning_agent is None:
                _provisioning_agent = ProvisioningAgent()
    return _provisioning_agent


# ADD NEW GETTER:
def get_ad_provisioning_agent() -> ADProvisioningWrapper:
    global _ad_provisioning_agent
    if _ad_provisioning_agent is None:
        with _ad_provisioning_lock:
            if _ad_provisioning_agent is None:
                _ad_provisioning_agent = ADProvisioningWrapper()
    return _ad_provisioning_agent


def get_entra_agent() -> EntraAgentWrapper:
    global _entra_agent
    if _entra_agent is None:
        with _entra_agent_lock:
            if _entra_agent is None:
                _entra_agent = EntraAgentWrapper()
    return _entra_agent


def get_dashboard_plugin() -> IAMPlugin:
    """Thread-safe getter for the IAM Dashboard plugin."""
    global _dashboard_plugin
    if _dashboard_plugin is None:
        with _dashboard_lock:
            if _dashboard_plugin is None:
                _dashboard_plugin = IAMPlugin()
    return _dashboard_plugin


# Token verification
OPENID_CONFIG_URL = f"https://login.microsoftonline.com/{os.getenv('TENANT_ID')}/v2.0/.well-known/openid-configuration"


def get_jwk():
    try:
        response = requests.get(OPENID_CONFIG_URL)
        response.raise_for_status()
        openid_config = response.json()
        jwks_uri = openid_config['jwks_uri']
        jwks = requests.get(jwks_uri).json()
        return jwks['keys']
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error fetching public keys: {e}")


def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is missing")

        unverified_header = jwt.get_unverified_header(token)
        if unverified_header is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token header")

        kid = unverified_header['kid']
        keys = get_jwk()

        rsa_key = {}
        for key in keys:
            if key['kid'] == kid:
                rsa_key = {
                    'kty': key['kty'],
                    'kid': key['kid'],
                    'use': key['use'],
                    'n': key['n'],
                    'e': key['e']
                }
                break

        if not rsa_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unable to find appropriate key")

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            options={"verify_signature": False, "verify_aud": False},
            issuer=f"https://login.microsoftonline.com/{os.getenv('TENANT_ID')}/v2.0"
        )
        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Token verification failed: {str(e)}")


# --- Models ---
class ChatRequest(BaseModel):
    thread_id: str
    message: str

class ThreadResponse(BaseModel):
    thread_id: str

class ChatResponse(BaseModel):
    reply: str

class OrchestratorChatRequest(BaseModel):
    thread_id: str
    message: str
    chat_history: List[Dict[str, str]]

class OrchestratorChatResponse(BaseModel):
    action: str
    result: str

# Entra Service Models
"""
Legacy Entra request/response models removed; using EntraAgentChatRequest/Response instead.
"""

class EntraAgentChatRequest(BaseModel):
    thread_id: str
    message: str
    chat_history: List[Dict[str, str]]

class EntraAgentChatResponse(BaseModel):
    action: str
    result: str

# ADD NEW AD MODELS:
class ADProvisioningRequest(BaseModel):
    thread_id: str
    message: str

class ADProvisioningResponse(BaseModel):
    action: str
    result: str
    agent: str

class UserCreateRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=100)
    user_principal_name: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    password: str = Field(..., min_length=8)

class GroupCreateRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=100)
    mail_nickname: str = Field(..., min_length=1, max_length=100)
    is_security_enabled: bool = True


# Helper functions for Entra operations
"""
Removed legacy Entra intent parsing and execution helpers.
"""


# Health check
@app.get("/healthz")
def healthz():
    return {"status": "ok"}


# Existing endpoints
@app.post("/thread", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
def create_thread(token: str = Depends(verify_token)):
    try:
        assistant = get_assistant()
        tid = assistant.create_thread()
        return ThreadResponse(thread_id=tid)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create thread: {e}")


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, token: str = Depends(verify_token)):
    try:
        assistant = get_assistant()
        reply = assistant.chat_on_thread(thread_id=req.thread_id, user_query=req.message)
        return ChatResponse(reply=reply)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chat failed: {e}")


@app.post("/orchestrator/thread", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
def create_orchestrator_thread(token: str = Depends(verify_token)):
    try:
        tid = f"orch-{os.urandom(4).hex()}"
        return ThreadResponse(thread_id=tid)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create orchestrator thread: {e}")


@app.post("/orchestrator/chat", response_model=OrchestratorChatResponse)
async def orchestrator_chat(req: OrchestratorChatRequest, token: str = Depends(verify_token)):
    try:
        orchestrator_agent = get_orchestrator_agent()
        response = await orchestrator_agent.chat(
            thread_id=req.thread_id,
            user_message=req.message,
            chat_history=req.chat_history,
        )
        return response
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Orchestrator chat failed: {e}")


"""
Removed legacy /entra/thread and /entra/chat endpoints in favor of /entra/agent/*.
"""


# Entra-only Agent Orchestration Endpoints
@app.post("/entra/agent/thread", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
def create_entra_agent_thread(token: str = Depends(verify_token)):
    try:
        thread_id = f"entra-agent-{os.urandom(4).hex()}"
        return ThreadResponse(thread_id=thread_id)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create Entra Agent thread: {e}")


@app.post("/entra/agent/chat", response_model=EntraAgentChatResponse)
async def entra_agent_chat(req: EntraAgentChatRequest, token: str = Depends(verify_token)):
    try:
        entra_agent = get_entra_agent()
        response = await entra_agent.chat(
            thread_id=req.thread_id,
            user_message=req.message,
            chat_history=req.chat_history,
        )
        return EntraAgentChatResponse(action=response.get("action", "none"), result=response.get("result", ""))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Entra Agent chat failed: {e}")


# NEW: AD Provisioning Service Endpoints
@app.post("/ad/thread", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
def create_ad_thread(token: str = Depends(verify_token)):
    try:
        thread_id = f"ad-{os.urandom(4).hex()}"
        # Initialize chat history for this thread
        ad_agent = get_ad_provisioning_agent()
        ad_agent.create_thread(thread_id)
        return ThreadResponse(thread_id=thread_id)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create AD thread: {e}")


@app.post("/ad/chat", response_model=ADProvisioningResponse)
async def ad_provisioning_chat(req: ADProvisioningRequest, token: str = Depends(verify_token)):
    try:
        user_info = token.get('preferred_username', 'unknown')
        logger.info(f"User {user_info} requested AD operation: {req.message}")
        
        ad_agent = get_ad_provisioning_agent()
        response = await ad_agent.chat(req.thread_id, req.message)
        
        logger.info(f"AD operation completed for user {user_info}")
        
        return ADProvisioningResponse(
            action=response.get("action", "ad_provision"),
            result=response.get("result", ""),
            agent=response.get("agent", "AD_Provisioning_Agent")
        )
    except Exception as e:
        logger.error(f"AD provisioning chat failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AD provisioning chat failed: {e}")


# IAM Dashboard Endpoints
@app.get("/dashboard/summary", response_model=dict)
async def get_iam_dashboard_summary(token: str = Depends(verify_token), refresh: Optional[int] = 0):
    """Builds and returns the IAM dashboard metrics by aggregating Entra and AD data."""
    try:
        use_cache = not bool(refresh)
        global _dashboard_cache, _dashboard_cache_ts
        # Serve from cache if valid
        if use_cache:
            with _dashboard_cache_lock:
                import time as _t
                if _dashboard_cache is not None and (_t.time() - _dashboard_cache_ts) < _DASHBOARD_TTL_SECONDS:
                    return {"success": True, "data": _dashboard_cache}

        # Build fresh
        plugin = get_dashboard_plugin()
        raw_data = await plugin.build_iam_dashboard()
        data = jsonable_encoder(raw_data)

        # Update cache
        with _dashboard_cache_lock:
            import time as _t
            _dashboard_cache = data
            _dashboard_cache_ts = _t.time()

        return {"success": True, "data": data}
    except Exception as e:
        logger.error(f"Failed to build IAM dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to build IAM dashboard: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
