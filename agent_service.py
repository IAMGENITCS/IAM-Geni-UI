import os
import threading
import traceback
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from fastapi.security import OAuth2PasswordBearer
import jwt
import requests
import asyncio

from OrchestratorAgent import OrchestratorAgentWrapper
from IAMAssistant import IAMAssistant  # Existing agent


app = FastAPI(title="IAM Assistant Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8501", "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

_assistant_lock = threading.Lock()
_assistant: Optional[IAMAssistant] = None

_orchestrator_lock = threading.Lock()
_orchestrator_agent: Optional[OrchestratorAgentWrapper] = None


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

# Token verification identical to existing code ...
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

# Orchestrator chat request with chat history
class OrchestratorChatRequest(BaseModel):
    thread_id: str
    message: str
    chat_history: List[Dict[str, str]]  # List of dicts with keys: 'role', 'content'

class OrchestratorChatResponse(BaseModel):
    action: str
    result: str

# Health check
@app.get("/healthz")
def healthz():
    return {"status": "ok"}


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


# New endpoint for orchestrator thread creation
@app.post("/orchestrator/thread", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
def create_orchestrator_thread(token: str = Depends(verify_token)):
    try:
        # For simplicity, use assistant thread creation (could be customized)
        # Or manage distinct thread IDs if needed
        tid = f"orch-{os.urandom(4).hex()}"  # generate random id for orchestrator session
        return ThreadResponse(thread_id=tid)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create orchestrator thread: {e}")

# Orchestrator chat endpoint
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
