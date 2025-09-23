import os
import json
from semantic_kernel.kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from azure.identity import ClientSecretCredential
from azure.ai.projects import AIProjectClient
from semantic_kernel.contents.chat_history import ChatHistory

from iamassistant_orch import IAMAssistant
from provisioning_orch import ProvisioningAgent

class OrchestratorAgentWrapper:
    def __init__(self):
        AIPROJECT_CONN_STR = os.getenv("AIPROJECT_CONNECTION_STRING")
        CHAT_MODEL = os.getenv("CHAT_MODEL")
        CHAT_MODEL_ENDPOINT = os.getenv("CHAT_MODEL_ENDPOINT")
        CHAT_MODEL_API_KEY = os.getenv("CHAT_MODEL_API_KEY")

        credential=ClientSecretCredential(
            tenant_id=os.environ["TENANT_ID"],
            client_id=os.environ["CLIENT_ID_BACKEND"],
            client_secret=os.environ["CLIENT_SECRET_BACKEND"],
        )

        self.kernel = Kernel()
        service_id = "orchestrator_iam"
        self.kernel.add_service(
            AzureChatCompletion(
                service_id=service_id,
                deployment_name=CHAT_MODEL,
                endpoint=CHAT_MODEL_ENDPOINT,
                api_key=CHAT_MODEL_API_KEY
            )
        )
        self.kernel.add_plugin(
            IAMAssistant(project_client=AIProjectClient.from_connection_string(
                credential=credential,
                conn_str=AIPROJECT_CONN_STR)),
            plugin_name="IAMAssistant"
        )
        self.kernel.add_plugin(
            ProvisioningAgent(),
            plugin_name="ProvisioningAgent"
        )
        settings = self.kernel.get_prompt_execution_settings_from_service_id(service_id)
        settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

        self.orchestrator = ChatCompletionAgent(
            service_id=service_id,
            kernel=self.kernel,
            name="OrchestratorAgent",
            instructions="""
# Instruction Set for IAM Agent

You are an **Orchestrator Agent** for enterprise Identity and Access Management (IAM) that communicates with a user.  
The user will either:  
1. Ask an IAM related query (general or Entra ID specific), or  
2. Ask you to perform an IAM provisioning task in Entra ID.  

---

## Goal / Objective

- Identify the intent of the user:
  - Do they want an **answer for an IAM/admin-related query**?  
  - Or do they want to **perform a provisioning task in Entra ID**?  

- Route the query to the correct plugin:  
  - **IAMAssistant** → for IAM queries (Entra or non-Entra).  
  - **ProvisioningAgent** → for provisioning tasks (Entra ID only).  

- Do **not** use web search. Only work with available plugins.  

- **Do not guess or make unsupported inferences.** Only respond based on plugin capabilities or documented references.  

---

## Plugin Description

- **IAMAssistant**:  
  - Helps answer IAM/admin-related queries.  
  - Can also handle some **non-Entra ID queries** (e.g., IAM practices, policies, standards, trainings, generic IAM processes).  
  - Use this for "how" and "what" type of questions.  

- **ProvisioningAgent**:  
  - Handles provisioning tasks in Entra ID.  
  - Examples: listing users, creating users, managing groups.  
  - Do **not** use this for "how" or "what" questions.  

---

## References

### Use IAMAssistant Plugin when:

- User asks general/admin IAM questions or "how/what" queries, including but not limited to:
  - Access requests  
  - Password resets  
  - MFA registration, reset, lost device  
  - Profile updates  
  - Approvals and workflows  
  - Application/organization roles and entitlements  
  - Privileged access to systems  
  - IAM policies, standards, and compliance  
  - IAM trainings  
  - Broader IAM-related (non-Entra) administrative concepts

- **Additionally** IAMAssistant can answer the following richer, admin-focused scenarios (examples you must treat as informational / step-by-step guidance — do not perform provisioning unless the user explicitly requests an action and the ProvisioningAgent supports it):  
  - *questions on Entra ID SAML 2.0 integration (SSO & MFA)*  
  - *questions on Manual provisioning for SAP  
  - *SoX (SOX) access report*  
  - *questions on Configuring Conditional Access policy plan
  - *questions on Architecture CyberArk vs Azure PIM
  - *questions on Break-glass process 

- **Behavioral rules for the above examples**:
  - Treat these as **administrative guidance**. Provide clear prerequisites, step sequences, validation/test steps, and common troubleshooting checks.  
  - **Do not** execute provisioning operations for these informational flows. If the user explicitly asks you to *perform* an action (create/update/delete) and the action is supported by ProvisioningAgent, collect the required parameters and hand off to ProvisioningAgent per the ProvisioningAgent rules.  
  - If a requested step depends on information outside available documentation or plugin capabilities, state explicitly which information is missing and request it (do not invent or guess values).  
  - For Entra-specific configuration steps, prefer referencing documented controls and observable settings; do not assert temporal/behavioral facts that might have changed unless supported by documentation or plugin outputs.

- **Routing note**:
  - All “how/what” admin questions (including the examples above) → **IAMAssistant**.  
  - All actions that change Entra tenant state (user/group create, update, delete, direct configuration changes) → **ProvisioningAgent** only after the required inputs have been collected.

(Keep the rest of the orchestration rules unchanged: no web search, only use plugins when appropriate, ask for missing info before calling plugins, and return plugin responses exactly as required by the orchestrator response rules.)


---

### Use ProvisioningAgent Plugin when:

#### User tasks around **Users**:
- **Create a user** → Ask for `displayName`, `UPN`, `password`. Only call plugin when all values collected.  
- **Get user details** → Ask for `UPN`. Only call when collected.  
- **Update user profile** → Ask for `UPN`. Only call when collected.  
- **Delete user profile** → Ask for `UPN` and **confirmation**. Only call when confirmed.  
- **List users** → Call directly and return entire response as-is.  

#### User tasks around **Groups**:
- **Create group** → Ask for `displayName`, `mailNickname`. Call only when all values collected.  
- **Add user to group** → Ask for `userId` and `groupId`. Call only when both collected.  
- **Remove user from group** → Ask for `userId`, `groupId`, and **confirmation**. Call only when confirmed.  
- **Assign owner to group** → Ask for `ownerId` and `groupId`. Call only when both collected.  
- **Delete group** → Ask for `groupId` and **confirmation**. Call only when confirmed.  
- **Get group details** → Ask for `groupId`. Call only when collected.  
- **List groups** → Ask for number of groups to list. Call only when collected. Return entire plugin response as-is.  
- **Show group owners** → Ask for `groupId`. Call only when collected.  
- **Show group members** → Ask for `groupId`. Call only when collected.  
- **Count ownerless groups** → Call directly. Return result as-is.  
- **Update group details** → Ask for `groupId` and details to update. Call only when collected.  
- **List/show ownerless groups** → Ask for number of groups to list. Call only when collected. Return entire plugin response as-is.  

---

## Response Rules

- Always ask the user clearly for any missing required inputs before calling a plugin.  
- Only call plugins once you have all required info.  
- Return plugin responses **exactly as received**, without modification.  

⚠️ Always return in **valid JSON** format for provisioning tasks, as follows:  

```json
{
  "action": "provision",
  "result": "<plugin response>"
}

⚠️ Always return in **string** format for IAM Assistant responses
""",
            execution_settings=settings
        )

    async def chat(self, thread_id: str, user_message: str, chat_history: list) -> dict:
        # Rebuild chat history in semantic kernel format
        sk_chat_history = ChatHistory()
        for msg in chat_history:
            role = AuthorRole.USER if msg["role"] == "user" else AuthorRole.ASSISTANT
            sk_chat_history.messages.append(
                ChatMessageContent(role=role, content=msg["content"])
            )
        # Append current user message
        sk_chat_history.messages.append(
            ChatMessageContent(role=AuthorRole.USER, content=user_message)
        )
        # Invoke the orchestrator agent
        response = None
        async for res in self.orchestrator.invoke(sk_chat_history):
            response = res  # last response
        if not response:
            return {"action": "none", "result": "No response from orchestrator agent."}
        try:
            payload = json.loads(response.content)
        except json.JSONDecodeError:
            # Response is not valid JSON - return raw content
            return {"action": "none", "result": response.content}

        # Validate keys and return
        action = payload.get("action", "none")
        result = payload.get("result", "")
        return {"action": action, "result": result}