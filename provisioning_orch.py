import os
import json
import requests
from dotenv import load_dotenv
from semantic_kernel.functions import kernel_function
from azure.identity import DefaultAzureCredential

load_dotenv()

class ProvisioningAgent:
    def __init__(self):
        print("🔧 Initializing Provisioning Agent...")
        # Acquire token for Graph
        self.credential = DefaultAzureCredential()
        token = self.credential.get_token("https://graph.microsoft.com/.default")
        self._headers = {
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json"
        }
        self.graph_base_url = "https://graph.microsoft.com/v1.0"
        print("✅ Provisioning Agent ready.\n")

    # --------------------- Helpers --------------------- #
    def _json(self, data) -> str:
        """Return JSON string (keeps orchestrator 'print-as-is' contract)."""
        return json.dumps(data, ensure_ascii=False)

    # --------------------- User Operations --------------------- #

    @kernel_function(description="List users; returns a JSON array of rows as string.")
    async def list_users(self, max_results: int = 25) -> str:
        """
        Returns JSON string: [{"Display Name": ..., "UPN": ..., "Id": ...}, ...]
        """
        page_size = min(max_results, 999)
        url = f"{self.graph_base_url}/users?$select=id,displayName,userPrincipalName,accountEnabled&$top={page_size}"

        rows = []
        while url and len(rows) < max_results:
            resp = requests.get(url, headers=self._headers)
            if resp.status_code != 200:
                return f"❌ Error listing users: {resp.status_code} – {resp.text}"

            payload = resp.json()
            for u in payload.get("value", []):
                if len(rows) >= max_results:
                    break
                rows.append({
                    "Display Name": u.get("displayName"),
                    "UPN": u.get("userPrincipalName"),
                    "Id": u.get("id"),
                    "Enabled": u.get("accountEnabled")
                })

            url = payload.get("@odata.nextLink")

        if not rows:
            return self._json([])

        return self._json(rows)

    @kernel_function(description="Get details for a specific user by UPN or object ID.")
    async def get_user_details(self, user_id: str) -> str:
        url = f"{self.graph_base_url}/users/{user_id}"
        resp = requests.get(url, headers=self._headers)
        if resp.status_code != 200:
            return f"❌ Error fetching user '{user_id}': {resp.status_code} – {resp.text}"
        u = resp.json()
        details = [
            f"👤 Display Name: {u.get('displayName')}",
            f"📧 UPN: {u.get('userPrincipalName')}",
            f"🏢 Department: {u.get('department','N/A')}",
            f"🧑‍💼 Title: {u.get('jobTitle','N/A')}"
        ]
        return "\n".join(details)

    @kernel_function(description="Create a new user in Entra ID.")
    async def create_user(self,
                          display_name: str = "",
                          user_principal_name: str = "",
                          password: str = "") -> str:

        url = f"{self.graph_base_url}/users"
        payload = {
            "accountEnabled": True,
            "displayName": display_name,
            "mailNickname": user_principal_name.split("@")[0] if "@" in user_principal_name else user_principal_name,
            "userPrincipalName": user_principal_name,
            "passwordProfile": {
                "forceChangePasswordNextSignIn": True,
                "password": password
            }
        }
        resp = requests.post(url, headers=self._headers, json=payload)
        if resp.status_code == 201:
            return f"✅ User '{display_name}' created."
        return f"❌ Error creating user: {resp.status_code} – {resp.text}"

    @kernel_function(description="Update a field for an existing user.")
    async def update_user(self,
                          user_id: str,
                          field: str,
                          value: str) -> str:
        url = f"{self.graph_base_url}/users/{user_id}"
        payload = {field: value}
        resp = requests.patch(url, headers=self._headers, json=payload)
        if resp.status_code == 204:
            return f"✅ Updated user '{user_id}': set {field} = {value}"
        return f"❌ Error updating user: {resp.status_code} – {resp.text}"

    @kernel_function(description="Delete a user from Entra ID.")
    async def delete_user(self, user_id: str) -> str:
        url = f"{self.graph_base_url}/users/{user_id}"
        resp = requests.delete(url, headers=self._headers)
        if resp.status_code == 204:
            return f"🗑️ User '{user_id}' deleted."
        return f"❌ Error deleting user: {resp.status_code} – {resp.text}"

    # --------------------- Group Operations --------------------- #

    @kernel_function(description="List groups; returns a JSON array of rows as string.")
    async def list_groups(self, max_results: int) -> str:
        """
        Returns JSON string:
        [{"Group Name": ..., "Group ID": ..., "Mail Nickname": ..., "Security Enabled": ...}, ...]
        """
        page_size = min(max_results, 999)
        url = f"{self.graph_base_url}/groups?$select=id,displayName,mailNickname,securityEnabled&$top={page_size}"

        rows = []
        while url and len(rows) < max_results:
            resp = requests.get(url, headers=self._headers)
            if resp.status_code != 200:
                return f"❌ Error listing groups: {resp.status_code} – {resp.text}"

            payload = resp.json()
            for g in payload.get("value", []):
                if len(rows) >= max_results:
                    break
                rows.append({
                    "Group Name": g.get("displayName"),
                    "Group ID": g.get("id"),
                    "Mail Nickname": g.get("mailNickname"),
                    "Security Enabled": g.get("securityEnabled")
                })

            url = payload.get("@odata.nextLink")

        if not rows:
            return self._json([])

        return self._json(rows)

    @kernel_function(description="Get details for a specific group by its object ID.")
    async def get_group_details(self, group_id: str) -> str:
        url = f"{self.graph_base_url}/groups/{group_id}"
        resp = requests.get(url, headers=self._headers)
        if resp.status_code != 200:
            return f"❌ Error fetching group '{group_id}': {resp.status_code} – {resp.text}"
        g = resp.json()
        details = [
            f"👥 Name: {g.get('displayName')}",
            f"📧 Nickname: {g.get('mailNickname')}",
            f"🔒 Security Enabled: {g.get('securityEnabled')}",
            f"📅 Created: {g.get('createdDateTime')}"
        ]
        return "\n".join(details)

    @kernel_function(description="Create a new security-enabled group in Entra ID.")
    async def create_group(self,
                           display_name: str,
                           mail_nickname: str) -> str:
        url = f"{self.graph_base_url}/groups"
        payload = {
            "displayName": display_name,
            "mailEnabled": False,
            "mailNickname": mail_nickname,
            "securityEnabled": True,
            "groupTypes": []
        }
        resp = requests.post(url, headers=self._headers, json=payload)
        if resp.status_code == 201:
            return f"✅ Group '{display_name}' created."
        return f"❌ Error creating group: {resp.status_code} – {resp.text}"

    @kernel_function(description="Delete an existing group in Entra ID.")
    async def delete_group(self, group_id: str) -> str:
        url = f"{self.graph_base_url}/groups/{group_id}"
        resp = requests.delete(url, headers=self._headers)
        if resp.status_code == 204:
            return f"🗑️ Group '{group_id}' deleted."
        return f"❌ Error deleting group: {resp.status_code} – {resp.text}"

    @kernel_function(description="Add a user to a group in Entra ID.")
    async def add_user_to_group(self,
                                user_id: str,
                                group_id: str) -> str:
        url = f"{self.graph_base_url}/groups/{group_id}/members/$ref"
        payload = {"@odata.id": f"{self.graph_base_url}/users/{user_id}"}
        resp = requests.post(url, headers=self._headers, json=payload)
        if resp.status_code == 204:
            return f"✅ User '{user_id}' added to group '{group_id}'."
        return f"❌ Error adding user to group: {resp.status_code} – {resp.text}"

    @kernel_function(description="Remove a user from a group in Entra ID.")
    async def remove_user_from_group(self,
                                     user_id: str,
                                     group_id: str) -> str:
        url = f"{self.graph_base_url}/groups/{group_id}/members/{user_id}/$ref"
        resp = requests.delete(url, headers=self._headers)
        if resp.status_code == 204:
            return f"🚪 User '{user_id}' removed from group '{group_id}'."
        return f"❌ Error removing user from group: {resp.status_code} – {resp.text}"

    @kernel_function(description="Assign an owner to a group in Entra ID.")
    async def assign_owner_to_group(self,
                                    owner_id: str,
                                    group_id: str) -> str:
        url = f"{self.graph_base_url}/groups/{group_id}/owners/$ref"
        payload = {"@odata.id": f"{self.graph_base_url}/users/{owner_id}"}
        resp = requests.post(url, headers=self._headers, json=payload)
        if resp.status_code == 204:
            return f"👑 User '{owner_id}' assigned as owner of group '{group_id}'."
        return f"❌ Error assigning owner: {resp.status_code} – {resp.text}"

    @kernel_function(description="Show group owners; returns a JSON array of rows as string.")
    async def get_group_owners(self, group_id: str) -> str:
        """
        Returns JSON string: [{"Display Name": ..., "UPN/Nickname": ..., "Id": ..., "Type": ...}, ...]
        """
        url = f"{self.graph_base_url}/groups/{group_id}/owners?$select=id,displayName,userPrincipalName,mailNickname,@odata.type"

        rows = []
        while url:
            resp = requests.get(url, headers=self._headers)
            if resp.status_code != 200:
                return f"❌ Error fetching owners for group '{group_id}': {resp.status_code} – {resp.text}"

            payload = resp.json()
            for o in payload.get("value", []):
                rows.append({
                    "Display Name": o.get("displayName"),
                    "UPN/Nickname": o.get("userPrincipalName") or o.get("mailNickname") or "",
                    "Id": o.get("id"),
                    "Type": (o.get("@odata.type") or "").split(".")[-1]
                })
            url = payload.get("@odata.nextLink")

        return self._json(rows)

    @kernel_function(description="Show group members; returns a JSON array of rows as string.")
    async def get_group_members(self, group_id: str) -> str:
        """
        Returns JSON string: [{"Display Name": ..., "UPN/Nickname": ..., "Id": ..., "Type": ...}, ...]
        """
        url = f"{self.graph_base_url}/groups/{group_id}/members?$select=id,displayName,userPrincipalName,mailNickname,@odata.type"

        rows = []
        while url:
            resp = requests.get(url, headers=self._headers)
            if resp.status_code != 200:
                return f"❌ Error fetching members for group '{group_id}': {resp.status_code} – {resp.text}"

            payload = resp.json()
            for m in payload.get("value", []):
                rows.append({
                    "Display Name": m.get("displayName"),
                    "UPN/Nickname": m.get("userPrincipalName") or m.get("mailNickname") or "",
                    "Id": m.get("id"),
                    "Type": (m.get("@odata.type") or "").split(".")[-1]
                })
            url = payload.get("@odata.nextLink")

        return self._json(rows)

    @kernel_function(description="Count ownerless groups; returns JSON object as string.")
    async def count_ownerless_groups(self) -> str:
        """
        Returns JSON string: {"count": N, "groups": [{"Group Name": ..., "Group ID": ...}, ...]}
        """
        url = f"{self.graph_base_url}/groups?$select=id,displayName&$top=999"

        ownerless = []
        while url:
            resp = requests.get(url, headers=self._headers)
            if resp.status_code != 200:
                return f"❌ Error listing groups: {resp.status_code} – {resp.text}"

            payload = resp.json()
            for g in payload.get("value", []):
                owners_url = f"{self.graph_base_url}/groups/{g['id']}/owners?$select=id&$top=50"
                has_owner = False
                next_owners = owners_url
                # check owners (may paginate)
                while next_owners:
                    owners_resp = requests.get(next_owners, headers=self._headers)
                    if owners_resp.status_code != 200:
                        has_owner = True  # skip on error, assume owner exists to avoid false positives
                        break
                    owners_payload = owners_resp.json()
                    owners_vals = owners_payload.get("value", [])
                    if owners_vals:
                        has_owner = True
                        break
                    next_owners = owners_payload.get("@odata.nextLink")

                if not has_owner:
                    ownerless.append({"Group Name": g.get("displayName"), "Group ID": g.get("id")})

            url = payload.get("@odata.nextLink")

        return self._json({"count": len(ownerless), "groups": ownerless})

    @kernel_function(description="List ownerless groups; returns a JSON array of rows as string.")
    async def list_ownerless_groups(self, max_results: int) -> str:
        """
        Returns JSON string: [{"Group Name": ..., "Group ID": ...}, ...]
        """
        page_size = min(max_results * 5, 999)
        url = f"{self.graph_base_url}/groups?$select=id,displayName&$top={page_size}"

        rows = []
        while url and len(rows) < max_results:
            resp = requests.get(url, headers=self._headers)
            if resp.status_code != 200:
                return f"❌ Error fetching groups: {resp.status_code} – {resp.text}"

            payload = resp.json()
            for g in payload.get("value", []):
                if len(rows) >= max_results:
                    break

                owners_url = f"{self.graph_base_url}/groups/{g['id']}/owners?$select=id&$top=50"
                next_owners = owners_url
                has_owner = False
                while next_owners:
                    owners_resp = requests.get(next_owners, headers=self._headers)
                    if owners_resp.status_code != 200:
                        has_owner = True  # skip on error
                        break
                    owners_payload = owners_resp.json()
                    if owners_payload.get("value"):
                        has_owner = True
                        break
                    next_owners = owners_payload.get("@odata.nextLink")

                if not has_owner:
                    rows.append({"Group Name": g.get("displayName"), "Group ID": g.get("id")})

            url = payload.get("@odata.nextLink")

        if not rows:
            return self._json([])

        return self._json(rows)
