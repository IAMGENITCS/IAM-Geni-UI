import os
import json
import requests
from dotenv import load_dotenv
from semantic_kernel.functions import kernel_function
from azure.identity import AzureCliCredential
from datetime import datetime, timedelta

load_dotenv()

class ProvisioningAgent:
    def __init__(self):
        print("🔧 Initializing Provisioning Agent...")
        # Acquire token for Graph
        self.credential = AzureCliCredential()
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

    @kernel_function(description="Get details for a specific group by its group name.")
    async def get_group_details(self, group_name: str) -> str:
        # Step 1: Resolve group ID from name
        lookup_url = f"{self.graph_base_url}/groups?$filter=displayName eq '{group_name}'&$select=id,displayName,mailNickname,securityEnabled,createdDateTime"
        lookup_resp = requests.get(lookup_url, headers=self._headers)
        if lookup_resp.status_code != 200:
            return f"❌ Error resolving group name '{group_name}': {lookup_resp.status_code} – {lookup_resp.text}"

        groups = lookup_resp.json().get("value", [])
        if not groups:
            return f"❌ No group found with name '{group_name}'"
        if len(groups) > 1:
            return f"⚠️ Multiple groups found with name '{group_name}'. Please use group ID instead."

        g = groups[0]
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

    @kernel_function(description="Delete an existing group in Entra ID by its name.")
    async def delete_group(self, group_name: str) -> str:
        # Step 1: Resolve group ID from name
        lookup_url = f"{self.graph_base_url}/groups?$filter=displayName eq '{group_name}'&$select=id"
        lookup_resp = requests.get(lookup_url, headers=self._headers)
        if lookup_resp.status_code != 200:
            return f"❌ Error resolving group name '{group_name}': {lookup_resp.status_code} – {lookup_resp.text}"

        groups = lookup_resp.json().get("value", [])
        if not groups:
            return f"❌ No group found with name '{group_name}'"
        if len(groups) > 1:
            return f"⚠️ Multiple groups found with name '{group_name}'. Please use group ID instead."

        group_id = groups[0]["id"]

        # Step 2: Delete the group
        url = f"{self.graph_base_url}/groups/{group_id}"
        resp = requests.delete(url, headers=self._headers)
        if resp.status_code == 204:
            return f"🗑️ Group '{group_name}' deleted."
        return f"❌ Error deleting group '{group_name}': {resp.status_code} – {resp.text}"

    @kernel_function(description="Add a user to a group in Entra ID by group name.")
    async def add_user_to_group(self, user_id: str, group_name: str) -> str:
        # Resolve group ID
        lookup_url = f"{self.graph_base_url}/groups?$filter=displayName eq '{group_name}'&$select=id"
        lookup_resp = requests.get(lookup_url, headers=self._headers)
        if lookup_resp.status_code != 200:
            return f"❌ Error resolving group name '{group_name}': {lookup_resp.status_code} – {lookup_resp.text}"

        groups = lookup_resp.json().get("value", [])
        if not groups:
            return f"❌ No group found with name '{group_name}'"
        if len(groups) > 1:
            return f"⚠️ Multiple groups found with name '{group_name}'. Please use group ID instead."

        group_id = groups[0]["id"]

        # Add user to group
        url = f"{self.graph_base_url}/groups/{group_id}/members/$ref"
        payload = {"@odata.id": f"{self.graph_base_url}/users/{user_id}"}
        resp = requests.post(url, headers=self._headers, json=payload)
        if resp.status_code == 204:
            return f"✅ User '{user_id}' added to group '{group_name}'."
        return f"❌ Error adding user to group '{group_name}': {resp.status_code} – {resp.text}"


    @kernel_function(description="Remove a user from a group in Entra ID by group name.")
    async def remove_user_from_group(self, user_id: str, group_name: str) -> str:
        # Resolve group ID
        lookup_url = f"{self.graph_base_url}/groups?$filter=displayName eq '{group_name}'&$select=id"
        lookup_resp = requests.get(lookup_url, headers=self._headers)
        if lookup_resp.status_code != 200:
            return f"❌ Error resolving group name '{group_name}': {lookup_resp.status_code} – {lookup_resp.text}"

        groups = lookup_resp.json().get("value", [])
        if not groups:
            return f"❌ No group found with name '{group_name}'"
        if len(groups) > 1:
            return f"⚠️ Multiple groups found with name '{group_name}'. Please use group ID instead."

        group_id = groups[0]["id"]

        # Remove user from group
        url = f"{self.graph_base_url}/groups/{group_id}/members/{user_id}/$ref"
        resp = requests.delete(url, headers=self._headers)
        if resp.status_code == 204:
            return f"🚪 User '{user_id}' removed from group '{group_name}'."
        return f"❌ Error removing user from group '{group_name}': {resp.status_code} – {resp.text}"

    @kernel_function(description="Assign an owner to a group in Entra ID by group name.")
    async def assign_owner_to_group(self, owner_id: str, group_name: str) -> str:
        # Resolve group ID
        lookup_url = f"{self.graph_base_url}/groups?$filter=displayName eq '{group_name}'&$select=id"
        lookup_resp = requests.get(lookup_url, headers=self._headers)
        if lookup_resp.status_code != 200:
            return f"❌ Error resolving group name '{group_name}': {lookup_resp.status_code} – {lookup_resp.text}"

        groups = lookup_resp.json().get("value", [])
        if not groups:
            return f"❌ No group found with name '{group_name}'"
        if len(groups) > 1:
            return f"⚠️ Multiple groups found with name '{group_name}'. Please use group ID instead."

        group_id = groups[0]["id"]

        # Assign owner
        url = f"{self.graph_base_url}/groups/{group_id}/owners/$ref"
        payload = {"@odata.id": f"{self.graph_base_url}/users/{owner_id}"}
        resp = requests.post(url, headers=self._headers, json=payload)
        if resp.status_code == 204:
            return f"👑 User '{owner_id}' assigned as owner of group '{group_name}'."
        return f"❌ Error assigning owner to group '{group_name}': {resp.status_code} – {resp.text}"


    @kernel_function(description="Show group owners; returns a JSON array of rows as string.")
    async def get_group_owners(self, group_name: str) -> str:
        """
        Returns JSON string: [{"Display Name": ..., "UPN/Nickname": ..., "Id": ..., "Type": ...}, ...]
        """
        # Step 1: Resolve group ID from name
        lookup_url = f"{self.graph_base_url}/groups?$filter=displayName eq '{group_name}'&$select=id"
        lookup_resp = requests.get(lookup_url, headers=self._headers)
        if lookup_resp.status_code != 200:
            return f"❌ Error resolving group name '{group_name}': {lookup_resp.status_code} – {lookup_resp.text}"

        groups = lookup_resp.json().get("value", [])
        if not groups:
            return f"❌ No group found with name '{group_name}'"
        if len(groups) > 1:
            return f"⚠️ Multiple groups found with name '{group_name}'. Please use group ID instead."

        group_id = groups[0]["id"]

        # Step 2: Fetch owners
        url = f"{self.graph_base_url}/groups/{group_id}/owners?$select=id,displayName,userPrincipalName"
        rows = []
        while url:
            resp = requests.get(url, headers=self._headers)
            if resp.status_code != 200:
                return f"❌ Error fetching owners for group '{group_name}': {resp.status_code} – {resp.text}"

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
    async def get_group_members(self, group_name: str) -> str:
        """
        Returns JSON string: [{"Display Name": ..., "UPN/Nickname": ..., "Id": ..., "Type": ...}, ...]
        """
        # Step 1: Resolve group ID from name
        lookup_url = f"{self.graph_base_url}/groups?$filter=displayName eq '{group_name}'&$select=id"
        lookup_resp = requests.get(lookup_url, headers=self._headers)
        if lookup_resp.status_code != 200:
            return f"❌ Error resolving group name '{group_name}': {lookup_resp.status_code} – {lookup_resp.text}"

        groups = lookup_resp.json().get("value", [])
        if not groups:
            return f"❌ No group found with name '{group_name}'"
        if len(groups) > 1:
            return f"⚠️ Multiple groups found with name '{group_name}'. Please use group ID instead."

        group_id = groups[0]["id"]

        # Step 2: Fetch members
        url = f"{self.graph_base_url}/groups/{group_id}/members?$select=id,displayName,userPrincipalName"
        rows = []
        while url:
            resp = requests.get(url, headers=self._headers)
            if resp.status_code != 200:
                return f"❌ Error fetching members for group '{group_name}': {resp.status_code} – {resp.text}"

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
        List ownerless groups in Entra ID.

        Args:
            max_results (int): Maximum number of groups to return

        Returns:
            str: JSON string with structure:
            {
            "status": "success",
            "total": <int>,
            "groups": [
                {"groupId": "...", "groupName": "..."},
                ...
            ]
            }
        """
        page_size = min(max_results * 5, 999)
        url = f"{self.graph_base_url}/groups?$select=id,displayName&$top={page_size}"

        ownerless = []
        try:
            while url and len(ownerless) < max_results:
                resp = requests.get(url, headers=self._headers)
                if resp.status_code != 200:
                    return self._json({
                        "status": "error",
                        "message": f"Error fetching groups: {resp.status_code}",
                        "details": resp.text
                    })

                payload = resp.json()
                for g in payload.get("value", []):
                    if len(ownerless) >= max_results:
                        break

                    # 🔍 Check if group has owners
                    owners_url = f"{self.graph_base_url}/groups/{g['id']}/owners?$select=id&$top=50"
                    next_owners = owners_url
                    has_owner = False

                    while next_owners:
                        owners_resp = requests.get(next_owners, headers=self._headers)
                        if owners_resp.status_code != 200:
                            # skip but record error context
                            has_owner = True
                            break
                        owners_payload = owners_resp.json()
                        if owners_payload.get("value"):
                            has_owner = True
                            break
                        next_owners = owners_payload.get("@odata.nextLink")

                    if not has_owner:
                        ownerless.append({
                            "groupId": g.get("id"),
                            "groupName": g.get("displayName")
                        })

                url = payload.get("@odata.nextLink")

            return self._json({
                "status": "success",
                "total": len(ownerless),
                "groups": ownerless
            })

        except Exception as e:
            return self._json({
                "status": "error",
                "message": str(e)
            })


    @kernel_function(description="List Entra ID groups whose owners are inactive. Only includes groups that have owners.")
    async def list_groups_with_inactive_owners(self, limit: int = 0, count_only: bool = False) -> str:
        """
        Returns JSON string:
        {
        "status": "success",
        "total": <int>,
        "items": [
            {"groupId": "...", "groupName": "..."}
        ]
        }
        """
        groups_url = f"{self.graph_base_url}/groups?$select=id,displayName"
        try:
            groups_resp = requests.get(groups_url, headers=self._headers)
            if groups_resp.status_code != 200:
                return self._json({
                    "status": "error",
                    "message": "Error fetching groups",
                    "details": f"{groups_resp.status_code} – {groups_resp.text}"
                })

            groups = groups_resp.json().get("value", [])
            inactive_groups = []

            for group in groups:
                group_id = group["id"]
                group_name = group["displayName"]

                owners_url = f"{self.graph_base_url}/groups/{group_id}/owners?$select=id,userPrincipalName,accountEnabled"
                owners_resp = requests.get(owners_url, headers=self._headers)
                if owners_resp.status_code != 200:
                    continue  # skip if owners can't be fetched

                owners = owners_resp.json().get("value", [])
                if not owners:
                    continue  # skip groups with no owners

                # ✅ group is inactive if *all* owners are disabled
                active_owners = [o for o in owners if o.get("accountEnabled", True)]
                if not active_owners:
                    inactive_groups.append({
                        "groupId": group_id,
                        "groupName": group_name
                    })

            total = len(inactive_groups)

            if count_only:
                return self._json({
                    "status": "success",
                    "total": total,
                    "items": []
                })

            if limit > 0:
                inactive_groups = inactive_groups[:limit]

            return self._json({
                "status": "success",
                "total": total,
                "items": inactive_groups
            })

        except Exception as e:
            return self._json({
                "status": "error",
                "message": "Unexpected exception",
                "details": str(e)
            })
    
    @kernel_function(description="List guest users who haven't signed in for the last 90 days. Returns count or top N users.")
    async def list_inactive_guest_users(self, limit: int = 5, count_only: bool = False) -> str:
        """
        Returns JSON string:
        {
        "status": "success",
        "total": <int>,
        "items": [
            {
            "displayName": "...",
            "userPrincipalName": "...",
            "lastSignIn": "..." | null
            }
        ]
        }
        """
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        url = (
            f"{self.graph_base_url}/users?"
            f"$filter=userType eq 'Guest'"
            f"&$select=displayName,userPrincipalName,signInActivity"
            f"&$top=999"
        )

        try:
            resp = requests.get(url, headers=self._headers)
            if resp.status_code != 200:
                return self._json({
                    "status": "error",
                    "message": "Error fetching guest users",
                    "details": f"{resp.status_code} – {resp.text}"
                })

            users = resp.json().get("value", [])
            inactive_guests = []

            for user in users:
                display_name = user.get("displayName")
                upn = user.get("userPrincipalName")
                sign_in = user.get("signInActivity", {}).get("lastSignInDateTime")

                if not sign_in:
                    inactive_guests.append({
                        "displayName": display_name,
                        "userPrincipalName": upn,
                        "lastSignIn": None
                    })
                    continue

                try:
                    last_sign_in = datetime.strptime(sign_in, "%Y-%m-%dT%H:%M:%SZ")
                    if last_sign_in < cutoff_date:
                        inactive_guests.append({
                            "displayName": display_name,
                            "userPrincipalName": upn,
                            "lastSignIn": sign_in
                        })
                except Exception:
                    continue  # skip malformed dates

            total = len(inactive_guests)

            if count_only:
                return self._json({
                    "status": "success",
                    "total": total,
                    "items": []
                })

            if limit > 0:
                inactive_guests = inactive_guests[:limit]

            return self._json({
                "status": "success",
                "total": total,
                "items": inactive_guests
            })

        except Exception as e:
            return self._json({
                "status": "error",
                "message": "Unexpected exception",
                "details": str(e)
            })
        
    @kernel_function(description="List users who were added to the Global Administrator role in the last 30 days.")
    async def get_recent_global_admins(self) -> str:
        from datetime import datetime, timedelta

        # Step 1: Date cutoff (30 days ago in ISO8601 format)
        cutoff_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Step 2: Query directory audit logs for GA role assignment events
        url = (
            f"{self.graph_base_url}/auditLogs/directoryAudits"
            f"?$filter=activityDisplayName eq 'Add eligible member to role in PIM requested (timebound)'"
            f" and activityDateTime ge {cutoff_date}"
            f" and targetResources/any(tr: tr/displayName eq 'Global Administrator')"
        )

        resp = requests.get(url, headers=self._headers)
        if resp.status_code != 200:
            return f"❌ Error fetching audit logs: {resp.status_code} – {resp.text}"

        logs = resp.json().get("value", [])
        if not logs:
            return "✅ No new Global Administrators added in the last 30 days."

        new_admins = []
        for log in logs:
            for target in log.get("targetResources", []):
                if target.get("userPrincipalName") and target.get("displayName") != "Global Administrator":
                    new_admins.append(f"{target.get('userPrincipalName')} (added on {log.get('activityDateTime')})")

        if not new_admins:
            return "✅ No new Global Administrators added in the last 30 days."

        return "🆕 Global Administrators added in the last 30 days:\n" + "\n".join(f"- {u}" for u in new_admins)
    

