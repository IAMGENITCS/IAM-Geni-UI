import os
import json
from semantic_kernel.kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.contents.chat_history import ChatHistory
from provisioning_orch_new import ProvisioningAgent


class EntraAgentWrapper:
    def __init__(self):
        CHAT_MODEL = os.getenv("CHAT_MODEL")
        CHAT_MODEL_ENDPOINT = os.getenv("CHAT_MODEL_ENDPOINT")
        CHAT_MODEL_API_KEY = os.getenv("CHAT_MODEL_API_KEY")

        self.kernel = Kernel()
        service_id = "entra_only"
        self.kernel.add_service(
            AzureChatCompletion(
                service_id=service_id,
                deployment_name=CHAT_MODEL,
                endpoint=CHAT_MODEL_ENDPOINT,
                api_key=CHAT_MODEL_API_KEY,
            )
        )
        # Register only the Entra Provisioning plugin
        self.kernel.add_plugin(
            ProvisioningAgent(),
            plugin_name="EntraProvisioning",
        )

        settings = self.kernel.get_prompt_execution_settings_from_service_id(service_id)
        settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

        self.agent = ChatCompletionAgent(
            service_id=service_id,
            kernel=self.kernel,
            name="EntraAgent",
            instructions=(
                """
# Entra-Only Provisioning Agent

You are an Entra ID Provisioning Agent. You should only use the EntraProvisioning plugin functions to fulfill user requests.
- Do not use web search.
- Ask for missing required inputs before calling a function.
- Return plugin responses as-is.

When performing a provisioning operation, always return valid JSON of the form:
{
  "action": "provision",
  "result": "<plugin response>"
}
                """
            ),
            execution_settings=settings,
        )

    async def chat(self, thread_id: str, user_message: str, chat_history: list) -> dict:
        sk_chat_history = ChatHistory()
        for msg in chat_history:
            role = AuthorRole.USER if msg.get("role") == "user" else AuthorRole.ASSISTANT
            sk_chat_history.messages.append(
                ChatMessageContent(role=role, content=msg.get("content", ""))
            )
        sk_chat_history.messages.append(
            ChatMessageContent(role=AuthorRole.USER, content=user_message)
        )

        response = None
        async for res in self.agent.invoke(sk_chat_history):
            response = res  # last response
        if not response:
            return {"action": "none", "result": "No response from Entra agent."}

        try:
            payload = json.loads(response.content)
        except json.JSONDecodeError:
            # Return raw content if not JSON
            return {"action": "none", "result": response.content}

        action = payload.get("action", "none")
        result = payload.get("result", "")
        return {"action": action, "result": result}
