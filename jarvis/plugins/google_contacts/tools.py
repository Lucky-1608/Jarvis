"""
Jarvis OS — Google Contacts Tools.

Provides 3 tools for Google People API (Contacts) interaction.
"""

from jarvis.database.core import AsyncSessionLocal
from jarvis.integrations.google_client import GoogleClient, get_google_account
from jarvis.tools.base import Tool, ToolCategory, ToolMetadata, ToolParameter, ToolResult

PEOPLE_BASE = "https://people.googleapis.com/v1"
PERSON_FIELDS = "names,emailAddresses,phoneNumbers,organizations,biographies,photos"


async def _get_client_and_account(account_email=None):
    db = AsyncSessionLocal()
    account = await get_google_account(db, account_email=account_email)
    if not account:
        await db.close()
        return None, None, None
    client = GoogleClient(db, account)
    return db, account, client


def _format_contact(person: dict) -> str:
    names = person.get("names", [])
    name = names[0].get("displayName", "(unnamed)") if names else "(unnamed)"

    emails = person.get("emailAddresses", [])
    email_str = ", ".join(e.get("value", "") for e in emails) if emails else "N/A"

    phones = person.get("phoneNumbers", [])
    phone_str = ", ".join(p.get("value", "") for p in phones) if phones else "N/A"

    orgs = person.get("organizations", [])
    org_str = ""
    if orgs:
        org = orgs[0]
        org_str = f"\n   🏢 {org.get('name', '')} — {org.get('title', '')}"

    return f"👤 **{name}**\n   📧 {email_str}\n   📱 {phone_str}{org_str}"


class ContactsSearchTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="contacts_search",
            description="Search Google Contacts by name, email, or phone number.",
            category=ToolCategory.COMMUNICATION,
            dangerous=False,
            parameters=[
                ToolParameter(name="query", type="string", description="Search query (name, email, or phone number)"),
                ToolParameter(name="max_results", type="integer", description="Max results (1-30)", required=False, default=10),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        query = kwargs.get("query", "")
        max_results = min(int(kwargs.get("max_results", 10)), 30)
        account_email = kwargs.get("account_email")

        db, _, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                resp = await client.get(
                    f"{PEOPLE_BASE}/people:searchContacts",
                    params={"query": query, "readMask": PERSON_FIELDS, "pageSize": max_results},
                )
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"People API error: {resp.status_code} — {resp.text}")

                results = resp.json().get("results", [])
                if not results:
                    return ToolResult(success=True, output=f"No contacts found matching '{query}'.")

                output = f"Found {len(results)} contact(s):\n\n"
                for i, r in enumerate(results, 1):
                    person = r.get("person", {})
                    output += f"{i}. {_format_contact(person)}\n\n"

                return ToolResult(success=True, output=output)
        finally:
            await db.close()


class ContactsGetDetailsTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="contacts_get_details",
            description="Get full details for a specific contact by resource name.",
            category=ToolCategory.COMMUNICATION,
            dangerous=False,
            parameters=[
                ToolParameter(name="resource_name", type="string", description="Contact resource name (e.g., 'people/c1234567890')"),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        resource_name = kwargs.get("resource_name")
        if not resource_name:
            return ToolResult(success=False, error="resource_name is required")

        account_email = kwargs.get("account_email")
        db, _, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                resp = await client.get(
                    f"{PEOPLE_BASE}/{resource_name}",
                    params={"personFields": PERSON_FIELDS},
                )
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"Contact not found: {resp.status_code}")

                person = resp.json()
                return ToolResult(success=True, output=_format_contact(person), metadata=person)
        finally:
            await db.close()


class ContactsListAllTool(Tool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="contacts_list_all",
            description="List all Google Contacts with pagination.",
            category=ToolCategory.COMMUNICATION,
            dangerous=False,
            parameters=[
                ToolParameter(name="max_results", type="integer", description="Max contacts to return (1-100)", required=False, default=25),
                ToolParameter(name="account_email", type="string", description="Specific Google account to use", required=False),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        max_results = min(int(kwargs.get("max_results", 25)), 100)
        account_email = kwargs.get("account_email")

        db, _, client = await _get_client_and_account(account_email)
        if not client:
            return ToolResult(success=False, error="No Google account connected.")

        try:
            async with client:
                resp = await client.get(
                    f"{PEOPLE_BASE}/people/me/connections",
                    params={"personFields": PERSON_FIELDS, "pageSize": max_results, "sortOrder": "LAST_NAME_ASCENDING"},
                )
                if resp.status_code != 200:
                    return ToolResult(success=False, error=f"People API error: {resp.status_code}")

                connections = resp.json().get("connections", [])
                total = resp.json().get("totalPeople", len(connections))

                if not connections:
                    return ToolResult(success=True, output="No contacts found.")

                output = f"📇 **{total} total contacts** (showing {len(connections)}):\n\n"
                for i, person in enumerate(connections, 1):
                    output += f"{i}. {_format_contact(person)}\n\n"

                return ToolResult(success=True, output=output)
        finally:
            await db.close()
