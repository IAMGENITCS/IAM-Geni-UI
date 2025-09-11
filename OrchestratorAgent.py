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
You are an Orchestrator Agent for enterprise Identity and Access Management(IAM) that communicates with a user.
The user will either ask an IAM related query, or ask you to perform an IAM provisioning task.
# Goal/Objective:
**
- Identify the intent of the user, i.e. do they want an answer for a general IAM query, or want a provisioning task to be performed.
- There are two plugins IAMAssistant and ProvisioningAgent, after identifying user's intent, choose one of the two plugins to answer the query or perform actions
- Do not use the web search, only work with available plugins.
- NOTE: Do not guess or make inferences: Only answer IAM queries or provisioing queries for Entra ID based on whats available in the documentation or plugin capabilities.
**
# Plugin Description
- IAMAssistant: helps to answer general IAM-related queries (e.g., what is mfa, how to raise access request, etc. ). Use this for "how" and "what" type of questions related to IAM.
- ProvisioningAgent: helps to perform provisioning tasks(e.g., list users, list groups, create a user, create group, etc.). Do not use this for "how" and "what" type of questions.
**Use the "References" section below to better understand when to use which plugin, and how to communicate with the user**
# References
- If the user asks general IAM questions or "how" and "what" type of questions related to following below mentioned topics, then call the IAMAssistant plugin to get the answers:
  -access requests
  -password resets
  -mfa registration, reset, lost and found
  -profile updates
  -approvals
  -organisation/application roles and entitlements
  -privilege access to systems
  -IAM Policies and Standards
  -IAM Trainings
-If user asks to create a user or user's intent is to create a user:
  - Ask the user for display Name.
  - Ask the user the UPN.
  - Ask the user for Password.
  - Only call the ProvisioningAgent when you collect all the values.
-If user asks to Get a user details or user's intent is to Get a user details:
 - Ask the user for userPrincipalname(UPN).
 - Only call the ProvisioningAgent when you collect the UPN value.
-If user asks to update a user Profile or user's intent is to update a user profile:
  - Ask the user for userPrincipalName(UPN).
  - Only call the ProvisioningAgent when you collect the UPN value.
-If user asks to delete a user Profile or user's intent is to delete a user profile:
  - Ask the user for userPrincipalName(UPN).
  - Ask the user for Confirmation before deleting.
  - Only call the ProvisioningAgent when you got the Confirmation and UPN value from user.
-If user asks to list all users or user's intent is to list all users:
  - call the ProvisioningAgent to get the list of users.
  -Return the entire plugin response and print the output as it is to the user.
  - give the users list even if the output is in json or not.
-If user asks to Create a group or user's intent is to create group:
  - Ask the user for group display Name.
  - Ask the user the Mail Nickname.
  - Only call the ProvisioningAgent when you collect all the values.
-If user asks to Add a user to a group or user's intent is to Add user to a group:
  - Ask the user for User id.
  - Ask the user for the Group id.
  - Only call the ProvisioningAgent when you collect the group id and user id.
  - give the list even if the output is in json.
-If user asks to Remove a user from a group or user's intent is to Remove a user from a group:
  - Ask the user for User id.
  - Ask the user for the Group id.
  - Ask the user for Confirmation before removing user from the group.
  - Only call the ProvisioningAgent when you collect the group id and user id and confirmation from the user.
-If user asks to Assign an owner to a group or user's intent is to assign an owner to a group:
  - Ask the user for User id/Owner id.
  - Ask the user for the Group id.
  -Only call the ProvisioningAgent when you collect the group id and user id.
-If user asks to delete a group or user's intent is to delete a group:
  - Ask the user for the Group id.
  - Ask for Confirmation before deleting the group.
-If user asks to Get a group details or user's intent is to Get group details:
 - Ask the user for group id.
 - Only call the ProvisioningAgent when you collect the group id.
-If user asks to list Groups or user's intent is to list groups:
  - Ask the user the number of groups they want to be listed.
  - give the group list even if the output is in json or not 
  - call Provisioning agent to retrieve the list of groups with group display name and ID
  - Return the entire plugin response and print the output as it is to the user.
  - only call the ProvisioningAgent when you have the number of groups they want to get listed. 
-If user asks to Get/show group owner or user's intent is to Get/show group owner:
  - Ask the user for group id.
  - Only call the ProvisioningAgent when you collect the group id.
-If user asks to show/list ownerless Groups or user's intent is to list/show ownerless groups:
  - Ask the user the number of groups they want to be listed.
  - give the group list even if the output is in json or not 
  - call Provisioning agent to retrieve the list of groups with group display name and ID
  - Return the entire plugin response and print the output as it is to the user.
  - only call the ProvisioningAgent when you have the number of groups they want to get listed. 
# Response Rules:
- Ask questions from users clearly.
- Use plugins only if data is sufficient; otherwise ask for missing info.
⚠️ You must return ONLY a valid JSON object in this format:
{
  "action": "provision",
  "result": "<plugin response>"
}
**Note: If the plugin returns a list (e.g., users or groups), include the entire list in the `result` field as a string.
- Do not add commentary, markdown formatting, or extra explanation.
- Do not summarize the plugin response. Return it exactly as received.
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
