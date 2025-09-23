import requests
from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI
import os
from dotenv import load_dotenv
import asyncio
import logging

load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = AzureOpenAI(
    api_key=os.getenv("CHAT_MODEL_API_KEY"),
    api_version="2023-07-01-preview",
    azure_endpoint=os.getenv("CHAT_MODEL_ENDPOINT")
)

INTENT_SYSTEM_PROMPT = """
You are an IAM provisioning assistant. Your job is to classify user requests into one of the following intents:

User operations:
- list_users
- list_top_users
- get_user_details
- create_user
- update_user
- delete_user

Group operations:
- list_groups
- get_group_details
- create_group
- update_group
- delete_group
- add_user_to_group
- remove_user_from_group
- assign_owner_to_group

Respond with a JSON object like:
{
  "intent": "create_group"
}
Only return the JSON. Do not explain or add commentary.
"""

def detect_intent(prompt: str) -> str:
    """Detect user intent using Azure OpenAI"""
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        content = response.choices[0].message.content
        return eval(content)["intent"]
    except Exception as e:
        logger.error(f"Intent detection failed: {e}")
        return "unknown"

class ProvisioningAgent:
    def __init__(self):
        self.credential = DefaultAzureCredential()
        self.graph_base_url = "https://graph.microsoft.com/v1.0"
        self.token = self.get_access_token()
        logger.info("🔐 Access token acquired.")

    def get_access_token(self) -> str:
        """Get Microsoft Graph access token"""
        token = self.credential.get_token("https://graph.microsoft.com/.default")
        return token.token

    def _headers(self):
        """Get headers for Graph API requests"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def list_users(self):
        """List all users in Azure AD"""
        url = f"{self.graph_base_url}/users"
        try:
            response = requests.get(url, headers=self._headers(), timeout=30)
            if response.status_code == 200:
                users = response.json().get("value", [])
                return [f"- {u['displayName']} ({u['userPrincipalName']})" for u in users]
            else:
                return [f"❌ Error: {response.status_code} - {response.text}"]
        except Exception as e:
            logger.error(f"List users failed: {e}")
            return [f"❌ Error: {str(e)}"]

    def list_top_users(self, count=10):
        """List top N users"""
        url = f"{self.graph_base_url}/users?$top={count}"
        try:
            response = requests.get(url, headers=self._headers(), timeout=30)
            if response.status_code == 200:
                users = response.json().get("value", [])
                return [f"- {u['displayName']} ({u['userPrincipalName']})" for u in users]
            else:
                return [f"❌ Error: {response.status_code} - {response.text}"]
        except Exception as e:
            logger.error(f"List top users failed: {e}")
            return [f"❌ Error: {str(e)}"]

    def get_user_details(self, user_id):
        """Get detailed information about a specific user"""
        url = f"{self.graph_base_url}/users/{user_id}"
        try:
            response = requests.get(url, headers=self._headers(), timeout=30)
            if response.status_code == 200:
                user = response.json()
                return [
                    f"👤 Display Name: {user.get('displayName')}",
                    f"📧 Email: {user.get('userPrincipalName')}",
                    f"🏢 Department: {user.get('department', 'N/A')}",
                    f"🧑‍💼 Job Title: {user.get('jobTitle', 'N/A')}",
                    f"📱 Phone: {user.get('businessPhones', ['N/A'])[0] if user.get('businessPhones') else 'N/A'}",
                    f"🏙️ City: {user.get('city', 'N/A')}",
                    f"🌍 Country: {user.get('country', 'N/A')}"
                ]
            else:
                return [f"❌ Error: {response.status_code} - {response.text}"]
        except Exception as e:
            logger.error(f"Get user details failed: {e}")
            return [f"❌ Error: {str(e)}"]

    def create_user(self, display_name, user_principal_name, password):
        """Create a new user in Azure AD"""
        url = f"{self.graph_base_url}/users"
        payload = {
            "accountEnabled": True,
            "displayName": display_name,
            "mailNickname": user_principal_name.split("@")[0],
            "userPrincipalName": user_principal_name,
            "passwordProfile": {
                "forceChangePasswordNextSignIn": True,
                "password": password
            }
        }
        try:
            response = requests.post(url, headers=self._headers(), json=payload, timeout=30)
            if response.status_code == 201:
                return f"✅ User '{display_name}' created successfully."
            else:
                return f"❌ Error: {response.status_code} - {response.text}"
        except Exception as e:
            logger.error(f"Create user failed: {e}")
            return f"❌ Error: {str(e)}"

    def update_user(self, user_id, field, value):
        """Update a user's field"""
        url = f"{self.graph_base_url}/users/{user_id}"
        payload = {field: value}
        try:
            response = requests.patch(url, headers=self._headers(), json=payload, timeout=30)
            if response.status_code == 204:
                return f"✅ User '{user_id}' updated: {field} → {value}"
            else:
                return f"❌ Error: {response.status_code} - {response.text}"
        except Exception as e:
            logger.error(f"Update user failed: {e}")
            return f"❌ Error: {str(e)}"

    def delete_user(self, user_id):
        """Delete a user from Azure AD"""
        url = f"{self.graph_base_url}/users/{user_id}"
        try:
            response = requests.delete(url, headers=self._headers(), timeout=30)
            if response.status_code == 204:
                return f"🗑️ User '{user_id}' deleted successfully."
            else:
                return f"❌ Error: {response.status_code} - {response.text}"
        except Exception as e:
            logger.error(f"Delete user failed: {e}")
            return f"❌ Error: {str(e)}"

    # Group Management Methods
    def list_groups(self):
        """List all groups in Azure AD"""
        url = f"{self.graph_base_url}/groups"   
        try:
            response = requests.get(url, headers=self._headers(), timeout=30)
            if response.status_code == 200:
                groups = response.json().get("value", [])
                return [f"- {group['displayName']} ({group['mailNickname']})" for group in groups]
            else:
                return [f"❌ Error fetching groups: {response.status_code} - {response.text}"]
        except Exception as e:
            logger.error(f"List groups failed: {e}")
            return [f"❌ Error: {str(e)}"]

    def create_group(self, display_name: str, mail_nickname: str, is_security_enabled: bool = True):
        """Create a new group"""
        url = f"{self.graph_base_url}/groups"
        payload = {
            "displayName": display_name,
            "mailEnabled": False,
            "mailNickname": mail_nickname,
            "securityEnabled": True,
            "groupTypes": [] if is_security_enabled else ["Unified"]
        }
        try:
            response = requests.post(url, headers=self._headers(), json=payload, timeout=30)
            if response.status_code == 201:
                return f"✅ Group '{display_name}' created successfully."
            else:
                return f"❌ Error creating group: {response.status_code} - {response.text}"
        except Exception as e:
            logger.error(f"Create group failed: {e}")
            return f"❌ Error: {str(e)}"
        
    def Add_user_to_group(self, user_id: str, group_id: str):
        """Add user to group"""
        url = f"{self.graph_base_url}/groups/{group_id}/members/$ref"
        payload = {
            "@odata.id": f"{self.graph_base_url}/users/{user_id}"
        }
        try:
            response = requests.post(url, headers=self._headers(), json=payload, timeout=30)
            if response.status_code == 204:
                return f"✅ User '{user_id}' added to group '{group_id}' successfully."
            else:
                return f"❌ Error adding user to group: {response.status_code} - {response.text}"
        except Exception as e:
            logger.error(f"Add user to group failed: {e}")
            return f"❌ Error: {str(e)}"
        
    def remove_user_from_group(self, user_id: str, group_id: str):
        """Remove user from group"""
        url = f"{self.graph_base_url}/groups/{group_id}/members/{user_id}/$ref"
        try:
            response = requests.delete(url, headers=self._headers(), timeout=30)
            if response.status_code == 204:
                return f"✅ User '{user_id}' removed from group '{group_id}' successfully."
            else:
                return f"❌ Error removing user from group: {response.status_code} - {response.text}"
        except Exception as e:
            logger.error(f"Remove user from group failed: {e}")
            return f"❌ Error: {str(e)}"
        
    def group_details(self, group_id: str):
        """Get group details"""
        url = f"{self.graph_base_url}/groups/{group_id}"
        try:
            response = requests.get(url, headers=self._headers(), timeout=30)
            if response.status_code == 200:
                group = response.json()
                return [
                    f"👥 Group Name: {group.get('displayName')}",
                    f"📧 Mail Nickname: {group.get('mailNickname')}",
                    f"🔒 Security Enabled: {group.get('securityEnabled')}",
                    f"📅 Created Date: {group.get('createdDateTime')}"
                ]
            else:
                return [f"❌ Error fetching group details: {response.status_code} - {response.text}"]
        except Exception as e:
            logger.error(f"Get group details failed: {e}")
            return [f"❌ Error: {str(e)}"]
        
    def assign_owner(self, group_id: str, owner_id: str):
        """Assign owner to group"""
        url = f"{self.graph_base_url}/groups/{group_id}/owners/$ref"
        payload = {
            "@odata.id": f"{self.graph_base_url}/users/{owner_id}"
        }
        try:
            response = requests.post(url, headers=self._headers(), json=payload, timeout=30)
            if response.status_code == 204:
                return f"✅ Owner '{owner_id}' assigned to group '{group_id}' successfully."
            else:
                return f"❌ Error assigning owner: {response.status_code} - {response.text}"
        except Exception as e:
            logger.error(f"Assign owner failed: {e}")
            return f"❌ Error: {str(e)}"
        
    def delete_group(self, group_id: str):
        """Delete a group"""
        url = f"{self.graph_base_url}/groups/{group_id}"
        try:
            response = requests.delete(url, headers=self._headers(), timeout=30)
            if response.status_code == 204:
                return f"🗑️ Group '{group_id}' deleted successfully."
            else:
                return f"❌ Error deleting group: {response.status_code} - {response.text}"
        except Exception as e:
            logger.error(f"Delete group failed: {e}")
            return f"❌ Error: {str(e)}"

    def chat(self):
        """Interactive chat interface for terminal usage"""
        print("💬 ProvisioningAgent ready. Type 'exit' to quit.\n")
        while True:
            user_input = input("You: ")
            if user_input.lower() == "exit":
                break

            intent = detect_intent(user_input)

            if intent == "list_users":
                users = self.list_users()
                print("\n👥 Users in Entra ID:")
                for u in users:
                    print(u)

            elif intent == "list_top_users":
                count = input("How many users would you like to list? (default 10): ")
                try:
                    count = int(count)
                except ValueError:
                    count = 10
                users = self.list_top_users(count)
                print(f"\n👥 Top {count} Users:")
                for u in users:
                    print(u)

            elif intent == "get_user_details":
                user_id = input("Enter userPrincipalName or object ID: ")
                details = self.get_user_details(user_id)
                print("\n📄 User Details:")
                for line in details:
                    print(line)

            elif intent == "create_user":
                print("🆕 Let's create a new user.")
                name = input("Enter display name: ")
                email = input("Enter userPrincipalName (e.g., user@domain.com): ")
                password = input("Enter temporary password: ")
                result = self.create_user(name, email, password)
                print(result)

            elif intent == "update_user":
                user_id = input("Enter userPrincipalName or object ID: ")
                field = input("Which field to update? (e.g., jobTitle): ")
                value = input(f"New value for {field}: ")
                result = self.update_user(user_id, field, value)
                print(result)

            elif intent == "delete_user":
                user_id = input("Enter userPrincipalName or object ID: ")
                confirm = input(f"Are you sure you want to delete '{user_id}'? (yes/no): ")
                if confirm.lower() == "yes":
                    result = self.delete_user(user_id)
                    print(result)
                else:
                    print("❌ Deletion cancelled.")

            elif intent == "create_group":
                print("🆕 Let's create a new group.")
                display_name = input("Enter group display name: ")
                mail_nickname = input("Enter group mail nickname: ")
                is_security_enabled = input("Is this a security group? (yes/no): ").strip().lower() == "yes"
                result = self.create_group(display_name, mail_nickname, is_security_enabled)
                print(result)

            elif intent == "list_groups":
                groups = self.list_groups()
                print("\n👥 Groups in Entra ID:")
                for g in groups:
                    print(g)
            
            elif intent == "add_user_to_group":
                user_id = input("Enter user ID to add: ")
                group_id = input("Enter group ID to add the user to: ")
                result = self.Add_user_to_group(user_id, group_id)
                print(result)   

            elif intent == "remove_user_from_group":
                user_id = input("Enter user ID to remove: ")
                group_id = input("Enter group ID to remove the user from: ")
                result = self.remove_user_from_group(user_id, group_id)
                print(result)

            elif intent == "group_details":
                group_id = input("Enter group ID to get details: ")
                details = self.group_details(group_id)
                print("\n📄 Group Details:")
                for line in details:
                    print(line)
            
            elif intent == "assign_owner":
                group_id = input("Enter group ID to assign owner: ")
                owner_id = input("Enter owner user ID to assign: ")
                result = self.assign_owner(group_id, owner_id)
                print(result)

            elif intent == "delete_group":
                group_id = input("Enter group ID to delete: ")
                confirm = input(f"Are you sure you want to delete group '{group_id}'? (yes/no): ")
                if confirm.lower() == "yes":
                    result = self.delete_group(group_id)
                    print(result)
                else:
                    print("❌ Deletion cancelled.")

            else:
                print("🤖 I didn't quite catch that. Try rephrasing your request.")

if __name__ == "__main__":
    agent = ProvisioningAgent()
    agent.chat()
