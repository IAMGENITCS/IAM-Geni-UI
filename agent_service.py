import os
import threading
import traceback
import re
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from fastapi.security import OAuth2PasswordBearer
import jwt
import requests
import asyncio
import logging

# Import your existing components
from OrchestratorAgent import OrchestratorAgentWrapper
from IAMAssistant import IAMAssistant
from provisioningAgent import ProvisioningAgent, detect_intent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# NEW: Entra Service Models - FIXED REGEX ERROR
class EntraRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None

class EntraResponse(BaseModel):
    intent: str
    result: str
    thread_id: str

class UserCreateRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=100)
    user_principal_name: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')  # FIXED: pattern instead of regex
    password: str = Field(..., min_length=8)

class GroupCreateRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=100)
    mail_nickname: str = Field(..., min_length=1, max_length=100)
    is_security_enabled: bool = True

# Helper functions for Entra operations
def extract_user_id_from_message(message: str) -> str:
    """Extract user ID or email from natural language message"""
    # Look for email patterns
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, message)
    if emails:
        return emails[0]
    
    # Look for quoted text
    quoted = re.findall(r'"([^"]*)"', message)
    if quoted:
        return quoted[0]
    
    # Look for single quoted text
    single_quoted = re.findall(r"'([^']*)'", message)
    if single_quoted:
        return single_quoted[0]
    
    return ""

def extract_group_id_from_message(message: str) -> str:
    """Extract group ID from natural language message"""
    # Similar logic to user extraction
    words = message.split()
    for i, word in enumerate(words):
        if word.lower() in ['group', 'groups'] and i + 1 < len(words):
            return words[i + 1].strip('"\'')
    return ""

def extract_parameters_from_message(message: str, intent: str) -> Dict[str, str]:
    """Extract parameters needed for different intents"""
    params = {}
    
    if intent == "get_user_details":
        params["user_id"] = extract_user_id_from_message(message)
    elif intent == "get_group_details":
        params["group_id"] = extract_group_id_from_message(message)
    elif intent == "list_top_users":
        # Extract number
        numbers = re.findall(r'\d+', message)
        params["count"] = int(numbers[0]) if numbers else 10
    
    return params

# SIMPLIFIED: Remove async - use same pattern as your other endpoints
def execute_provisioning_action(agent: ProvisioningAgent, intent: str, message: str, params: Dict[str, str] = None) -> str:
    """Execute provisioning actions based on detected intent - SYNCHRONOUS like other endpoints"""
    
    if params is None:
        params = extract_parameters_from_message(message, intent)
    
    try:
        if intent == "list_users":
            result = agent.list_users()
            return "\n".join(result) if isinstance(result, list) else str(result)
            
        elif intent == "list_top_users":
            count = params.get("count", 10)
            result = agent.list_top_users(count)
            return "\n".join(result) if isinstance(result, list) else str(result)
            
        elif intent == "list_groups":
            result = agent.list_groups()
            return "\n".join(result) if isinstance(result, list) else str(result)
            
        elif intent == "get_user_details":
            user_id = params.get("user_id", "")
            if not user_id:
                return "❌ Please provide a valid user ID or email address."
            result = agent.get_user_details(user_id)
            return "\n".join(result) if isinstance(result, list) else str(result)
            
        elif intent == "get_group_details" or intent == "group_details":
            group_id = params.get("group_id", "")
            if not group_id:
                return "❌ Please provide a valid group ID."
            result = agent.group_details(group_id)
            return "\n".join(result) if isinstance(result, list) else str(result)
            
        else:
            return f"🤖 I understand you want to perform: **{intent}**\n\nFor security reasons, some operations require additional confirmation. Please use the direct endpoints for create, update, or delete operations."
            
    except Exception as e:
        logger.error(f"Provisioning action failed: {e}")
        return f"❌ Error executing {intent}: {str(e)}"

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

# NEW: Entra Service Endpoints - SYNCHRONOUS like your other endpoints
@app.post("/entra/thread", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
def create_entra_thread(token: str = Depends(verify_token)):
    try:
        thread_id = f"entra-{os.urandom(4).hex()}"
        return ThreadResponse(thread_id=thread_id)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to create Entra thread: {e}")

# SIMPLIFIED: Remove async - same pattern as /chat endpoint
@app.post("/entra/chat", response_model=EntraResponse)
def entra_chat(req: EntraRequest, token: str = Depends(verify_token)):
    try:
        # Log the operation
        user_info = token.get('preferred_username', 'unknown')
        logger.info(f"User {user_info} requested Entra operation: {req.message}")
        
        provisioning_agent = get_provisioning_agent()
        intent = detect_intent(req.message)
        
        # Execute the appropriate method based on intent - SYNCHRONOUS
        result = execute_provisioning_action(provisioning_agent, intent, req.message)
        
        thread_id = req.thread_id or f"entra-{os.urandom(4).hex()}"
        
        # Log the result
        logger.info(f"User {user_info} executed {intent} - Result: Success")
        
        return EntraResponse(
            intent=intent,
            result=result,
            thread_id=thread_id
        )
    except Exception as e:
        logger.error(f"Entra operation failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Entra operation failed: {e}")

# Direct CRUD endpoints for sensitive operations - SYNCHRONOUS
@app.post("/entra/users", response_model=dict)
def create_user_direct(req: UserCreateRequest, token: str = Depends(verify_token)):
    try:
        user_info = token.get('preferred_username', 'unknown')
        logger.info(f"User {user_info} creating new user: {req.display_name}")
        
        provisioning_agent = get_provisioning_agent()
        result = provisioning_agent.create_user(
            req.display_name, 
            req.user_principal_name, 
            req.password
        )
        
        logger.info(f"User creation result: {result}")
        return {"success": True, "message": result}
    except Exception as e:
        logger.error(f"User creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/entra/groups", response_model=dict)
def create_group_direct(req: GroupCreateRequest, token: str = Depends(verify_token)):
    try:
        user_info = token.get('preferred_username', 'unknown')
        logger.info(f"User {user_info} creating new group: {req.display_name}")
        
        provisioning_agent = get_provisioning_agent()
        result = provisioning_agent.create_group(
            req.display_name, 
            req.mail_nickname, 
            req.is_security_enabled
        )
        
        logger.info(f"Group creation result: {result}")
        return {"success": True, "message": result}
    except Exception as e:
        logger.error(f"Group creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/entra/users/{user_id}", response_model=dict)
def get_user_direct(user_id: str, token: str = Depends(verify_token)):
    try:
        provisioning_agent = get_provisioning_agent()
        result = provisioning_agent.get_user_details(user_id)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/entra/groups/{group_id}", response_model=dict)
def get_group_direct(group_id: str, token: str = Depends(verify_token)):
    try:
        provisioning_agent = get_provisioning_agent()
        result = provisioning_agent.group_details(group_id)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
