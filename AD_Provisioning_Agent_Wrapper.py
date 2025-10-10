import os
import json
import logging
from typing import Dict, Any
from dotenv import load_dotenv
from semantic_kernel.kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.contents.chat_history import ChatHistory

# IMPORTANT: Load environment variables first
load_dotenv()

# Debug: Print environment variables to check if they're loading correctly
print("🔧 Checking AD Environment Variables:")
print(f"AD_USERNAME: {os.getenv('AD_USERNAME')}")
print(f"AD_Server: {os.getenv('AD_Server')}")
print(f"AD_Domain: {os.getenv('AD_Domain')}")
print(f"AD_Base_DN: {os.getenv('AD_Base_DN')}")

# Import the AD plugin with error handling
try:
    from ADProvisioningAgent import AD_Provisioning_Agent
    print("✅ ADProvisioningAgent imported successfully")
except ImportError as e:
    logging.warning(f"❌ ADProvisioningAgent not found: {e}")
    AD_Provisioning_Agent = None

class ADProvisioningWrapper:
    def __init__(self):
        self.kernel = None
        self.orchestrator = None
        self.chat_histories: Dict[str, ChatHistory] = {}
        self._initialize_agent()
    
    def _initialize_agent(self):
        """Initialize the AD Provisioning Agent with error handling"""
        try:
            # Check if AD plugin is available
            if AD_Provisioning_Agent is None:
                logging.error("❌ AD_Provisioning_Agent class not available")
                self._create_fallback_agent()
                return

            # Check AD environment variables
            ad_username = os.getenv('AD_USERNAME')
            ad_server = os.getenv('AD_Server')
            ad_base_dn = os.getenv('AD_Base_DN')
            
            if not all([ad_username, ad_server, ad_base_dn]):
                logging.error("❌ Missing AD environment variables")
                print(f"Missing variables - Username: {ad_username}, Server: {ad_server}, Base_DN: {ad_base_dn}")
                self._create_fallback_agent()
                return

            # Azure AI Foundry connection
            AIPROJECT_CONN_STR = os.environ.get("AIPROJECT_CONNECTION_STRING")
            CHAT_MODEL = os.environ.get("CHAT_MODEL")
            CHAT_MODEL_ENDPOINT = os.environ.get("CHAT_MODEL_ENDPOINT")
            CHAT_MODEL_API_KEY = os.environ.get("CHAT_MODEL_API_KEY")
            
            # Check if required environment variables exist
            if not all([CHAT_MODEL, CHAT_MODEL_ENDPOINT, CHAT_MODEL_API_KEY]):
                logging.error("❌ Missing required Azure AI environment variables")
                self._create_fallback_agent()
                return
            
            # Initialize Kernel and AI service
            self.kernel = Kernel()
            service_id = "AD_Provisioning_Agent_Service"
            
            self.kernel.add_service(
                AzureChatCompletion(
                    service_id=service_id,
                    deployment_name=CHAT_MODEL,
                    endpoint=CHAT_MODEL_ENDPOINT,
                    api_key=CHAT_MODEL_API_KEY
                )
            )
            
            # Add AD_Provisioning_Agent plugin with detailed error handling
            try:
                logging.info("🔧 Attempting to initialize AD Provisioning Agent...")
                print(f"🔧 Connecting to AD Server: {ad_server}")
                
                ad_plugin = AD_Provisioning_Agent()
                
                self.kernel.add_plugin(
                    ad_plugin,
                    plugin_name="AD_Provisioning_Agent"
                )
                logging.info("✅ AD Provisioning Agent plugin added successfully")
                print("✅ AD connection successful!")
                
            except Exception as e:
                error_msg = str(e).lower()
                logging.error(f"❌ Failed to initialize AD plugin: {e}")
                
                # Specific error handling for different connection issues
                if "invalid server address" in error_msg:
                    print(f"❌ LDAP Server Address Issue: {ad_server}")
                    print("🔧 Check if your AD_Server format is correct (ldap://server.domain.com)")
                elif "bind" in error_msg or "authentication" in error_msg:
                    print(f"❌ LDAP Authentication Issue for user: {ad_username}")
                    print("🔧 Check AD_USERNAME and AD_PASSWORD in .env file")
                elif "network" in error_msg or "timeout" in error_msg:
                    print("❌ Network connectivity issue to AD server")
                    print("🔧 Check if AD server is reachable from this network")
                else:
                    print(f"❌ General LDAP Error: {e}")
                
                self._create_fallback_agent_with_error_details(str(e))
                return
            
            # Configure orchestrator (rest of the code same as before)
            settings = self.kernel.get_prompt_execution_settings_from_service_id(service_id)
            settings.function_choice_behavior = FunctionChoiceBehavior.Auto()
            
            # Create orchestrator with instructions
            self.orchestrator = ChatCompletionAgent(
                service_id=service_id,
                kernel=self.kernel,
                name="AD_Provisioning_Agent",
        instructions="""
# Instruction Set for AD Provisioning Agent

You are an AD Provisioning Agent that communicates with an Admin user and performs operations in Active Directory (AD) by invoking functions from the AD_Plugin. Do not use web search.

Goal:
- Detect the user intent and call the correct AD_Plugin function with the required parameters.
- When the user intent is to get totals first (e.g., list users/groups/ownerless groups), first call the appropriate function with count=0 (and list_all=False) to get the total and prompt for how many to list.

Available plugin: AD_Plugin
- Functions and expected usage patterns:
  - list_users(count=0, list_all=False)
    - If intent is "list users": call with count=0 to get totals first. If user says "list N" then call with count=N. If "list all" then call with list_all=True.
  - list_inactive_users(count=0, list_all=False)
    - If intent is about inactive/disabled users: same pattern as list_users.
  - get_user_details(common_name)
  - create_user(common_name, user_principal_name, password)
  - update_user(common_name, field, value)
  - delete_user(common_name)
  - ListGroups → list_groups(count=0, list_all=False) [Semantic Kernel function name is list_groups, exported as ListGroups]
  - get_group_details(common_name)
  - create_group(common_name, description)
  - show_group_owner(common_name)
  - show_group_members(common_name, count=0, list_all=False)
    - First return total and ask how many to show unless user asks for all or gives a number.
  - assign_group_owner(group_cn, owner_cn)
  - add_user_to_group(user_cn, group_cn)
  - remove_user_from_group(user_cn, group_cn)
  - delete_group(common_name)
  - groups_without_owner(action="list|count|both", count=0)
    - If intent is to know totals first: call with action="both", count=0. If user asks to list N, call with action="list", count=N.
  - update_group_details(group_cn, new_cn=None, description=None, owner_cn=None)
  - get_group_info(group_cn)
  - list_inactive_owner_groups(limit=5, count_only=False)
    - If user asks for count only: call with count_only=True. If user asks to list N: call with limit=N.
  - groups_not_following_naming_convention(allowed_prefixes=[...], count=0)
    - Ask for allowed_prefixes if not provided. First call with count=0 to get total, then ask how many to list.
  - groups with_zero_members(count=0)
    - If intent is to know totals first: call with count=0. If user asks to list N, call with count=N.  
    
Response rules:
- Ask for missing parameters clearly when needed (e.g., CNs, counts, prefixes, confirmation for destructive actions).
- Never fabricate counts or lists. Always call an AD_Plugin function to obtain totals/lists.
- Return ONLY a JSON object with this envelope and put the RAW plugin response string into result without modification or extra commentary:
{
  "action": "ad_provision",
  "agent": "<AD_Provisioning_Agent>",
  "result": "<raw JSON or string returned by the AD_Plugin function>"
}

Examples:
- User: "list users"
  -> Call AD_Plugin.list_users(count=0, list_all=False) and return the raw JSON in result.
- User: "list ownerless groups"
  -> Call AD_Plugin.groups_without_owner(action="both", count=0) and return the raw JSON in result.
        """,               
          execution_settings=settings
            )
            
            logging.info("✅ AD Provisioning Agent initialized successfully")
            print("✅ Full AD Agent setup completed!")
            
        except Exception as e:
            logging.error(f"❌ Failed to initialize AD Provisioning Agent: {e}")
            print(f"❌ Initialization failed: {e}")
            self._create_fallback_agent()
    
    def _create_fallback_agent(self):
        """Create a fallback agent when initialization fails"""
        logging.info("🔄 Creating fallback AD agent")
        self.kernel = None
        self.orchestrator = None
    
    def _create_fallback_agent_with_error_details(self, error: str):
        """Create a fallback agent with specific error details"""
        logging.info(f"🔄 Creating fallback AD agent due to: {error}")
        self.kernel = None
        self.orchestrator = None
        self.last_error = error
    
    def create_thread(self, thread_id: str):
        """Create a new chat thread"""
        self.chat_histories[thread_id] = ChatHistory()
        logging.info(f"✅ Created AD chat thread: {thread_id}")
    
    async def chat(self, thread_id: str, message: str) -> Dict[str, Any]:
        """Handle chat interaction with the AD Provisioning Agent"""
        try:
            # Check if agent is properly initialized
            if self.orchestrator is None:
                # Get specific error details if available
                error_details = getattr(self, 'last_error', 'Configuration issue')
                
                return {
                    "action": "ad_provision",
                    "agent": "AD_Provisioning_Agent",
                    "result": f"""❌ **AD Provisioning Agent Unavailable**

**Connection Details:**
- **Server**: {os.getenv('AD_Server')}
- **Username**: {os.getenv('AD_USERNAME')}
- **Base DN**: {os.getenv('AD_Base_DN')}

**Error**: {error_details}

**Troubleshooting Steps:**
1. **Test Connectivity**: Try pinging `dm-adds-idf-eus.identifencelab.com`
2. **Check Credentials**: Verify username `sanu@identifencelab.com` and password
3. **LDAP Port**: Ensure port 389 (LDAP) or 636 (LDAPS) is accessible
4. **Domain Controller**: Verify the AD server is running and reachable

**Contact your network administrator** for assistance with Active Directory connectivity."""
                }
            
            # Rest of the chat method (same as before)
            if thread_id not in self.chat_histories:
                self.create_thread(thread_id)
            
            chat_history = self.chat_histories[thread_id]
            
            chat_history.messages.append(
                ChatMessageContent(role=AuthorRole.USER, content=message)
            )
            
            async for response in self.orchestrator.invoke(chat_history):
                try:
                    payload = json.loads(response.content)
                    chat_history.messages.append(
                        ChatMessageContent(role=AuthorRole.ASSISTANT, content=response.content)
                    )
                    return payload
                    
                except json.JSONDecodeError:
                    chat_history.messages.append(
                        ChatMessageContent(role=AuthorRole.ASSISTANT, content=response.content)
                    )
                    return {
                        "action": "ad_provision",
                        "agent": "AD_Provisioning_Agent",
                        "result": response.content
                    }
            
            return {
                "action": "ad_provision",
                "agent": "AD_Provisioning_Agent", 
                "result": "No response received from agent"
            }
            
        except Exception as e:
            logging.error(f"❌ AD chat error for thread {thread_id}: {e}")
            return {
                "action": "ad_provision",
                "agent": "AD_Provisioning_Agent",
                "result": f"❌ Error processing request: {str(e)}"
            }
