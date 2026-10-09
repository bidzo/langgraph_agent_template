import os
import httpx
from fastmcp import FastMCP

# Initialize the FastMCP Server instance
mcp = FastMCP("Epicollect5 Server")

EPICOLLECT_BASE_URL = "https://five.epicollect.net"

#TODO ############################################################################################################
#  1. Greate a tool using Google Maps directions to output turn by turn directions to a specified meter
#  2. Create prompts templates for generating the above and other sophisticated queries that may be difficult
############################################################################################################

# Internal dictionary to hold credentials safely mapped to their project slugs
EPICOLLECT_CREDENTIALS = {
    "loss-control-meter-audits-western-region": {
        "client_id": "8134",
        "client_secret": "9QmlgsrpnfC3UgYhSpA2Wg5qBtmsg2vc7NCJ0hAF"
    },
    "loss-control-meter-audits-eastern-region": {
        "client_id": "8135",
        "client_secret": "TERSbkT11cb5KCWW89r1WYx4qCt14cHTgdaLHTF9"
    }
}

async def get_access_token(project_slug: str) -> str:
    """
    Exchanges Client ID and Secret for an Epicollect5 OAuth2 access token.
    Looks up hardcoded project credentials first; falls back to environment variables.
    """
    project_creds = EPICOLLECT_CREDENTIALS.get(project_slug.lower())

    if project_creds:
        client_id = project_creds["client_id"]
        client_secret = project_creds["client_secret"]
    else:
        client_id = os.environ.get("EPICOLLECT_CLIENT_ID")
        client_secret = os.environ.get("EPICOLLECT_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError(f"No credentials found for project '{project_slug}' in config or environment.")

    token_url = f"{EPICOLLECT_BASE_URL}/api/oauth/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=payload)
        response.raise_for_status()
        data = response.json()
        return data["access_token"]
# @mcp.tool
# async def get_project_data(project_slug: str, limit: int = 10) -> str:
#     """
#     Fetch raw entries and form data from a specific Epicollect5 project.
#
#     Args:
#         project_slug: The unique slug/name identifier of the Epicollect5 project.
#         limit: Max number of records to return (defaults to 10).
#     """
#     url = f"{EPICOLLECT_BASE_URL}/api/export/project/{project_slug}"
#     params = {"limit": limit}
#
#     try:
#         token = await get_access_token(project_slug=project_slug)
#         headers = {"Authorization": f"Bearer {token}"}
#
#         async with httpx.AsyncClient() as client:
#             response = await client.get(url, params=params, headers=headers)
#             response.raise_for_status()
#             return response.text
#
#     except httpx.HTTPStatusError as e:
#         return f"API Error ({e.response.status_code}): {e.response.text}"
#     except Exception as e:
#         return f"An unexpected error occurred: {str(e)}"

###########################################################################################
# Resources and Prompts Not being used for now u can aks AI zvoshanda sei
###########################################################################################
# ... (your existing imports and EPICOLLECT_CREDENTIALS dictionary)

# 1. DYNAMIC RESOURCE: The {region} in the URI acts as a wildcard variable
# @mcp.resource("audit://{region}/schema")
# async def get_region_schema(region: str) -> str:
#     """
#     Dynamically provides the form_ref and configuration for a specified region.
#     """
#     clean_region = region.lower().strip()
#
#     # Simple dynamic mapping to your existing project slugs
#     if "west" in clean_region:
#         return "Form Name: Meter Audits West | project_slug: loss-control-meter-audits-western-region | form_ref: 62fbde243ceb4ad78d46fd2832070a14_664c6dcb68975"
#     elif "east" in clean_region:
#         return "Form Name: Meter Audits East | project_slug: loss-control-meter-audits-eastern-region | form_ref: 73gcke..._easternref"
#     else:
#         return f"Unknown region '{region}'. Please specify 'western' or 'eastern'."
#
#
# # 2. DYNAMIC PROMPT: Claude Desktop will prompt the engineer for these arguments
# @mcp.prompt("analyze-recent-audits")
# def analyze_audits(region: str, max_entries: int = 50) -> str:
#     """
#     A dynamic template to audit entries for anomalies in a specified region.
#
#     Args:
#         region: The target region (e.g., 'western' or 'eastern').
#         max_entries: Number of recent audit records to pull.
#     """
#     return f"""You are an expert loss control engineer.
#
# 1. First, dynamically resolve the configuration for this request by reading the resource 'audit://{region}/schema'.
# 2. From the resource payload, extract the exact 'project_slug' and 'form_ref'.
# 3. Use the 'get_form_entries' tool to fetch the last {max_entries} entries using those parameters.
# 4. Review the data for anomalies and provide a concise, structured engineering report."""


@mcp.tool
async def get_form_entries(
    project_slug: str,
    form_ref: str = "62fbde243ceb4ad78d46fd2832070a14_664c6dcb68975",
    page: int = 1,
    per_page: int = 50,
    sort_by: str = "created_at",
    sort_order: str = "DESC"
) -> str:
    """
    Fetch meter audits records specifically from an individual form within an Epicollect5 project,
    these are meter audits findings in the field.

    Args:
        project_slug: The unique identifier of the project.
                      MUST be one of these exact strings:
                      - Use 'loss-control-meter-audits-western-region' if the user mentions Western Region / West.
                      - Use 'loss-control-meter-audits-eastern-region' if the user mentions Eastern Region / East.
        form_ref: The specific form reference identifier (e.g., 'form-1' or unique form key).
        page: Page number for pagination (defaults to 1).
        per_page: Total records per page (defaults to 50, max 100).
        sort_by: Field name to sort entries by (e.g., 'created_at', 'title').
        sort_order: Order of sort, either 'ASC' or 'DESC'.
    """
    # Endpoint pattern for targeted form entries data extraction
    url = f"{EPICOLLECT_BASE_URL}/api/export/entries/{project_slug}"
    params = {
        "form_ref": form_ref,
        "page": page,
        "per_page": per_page,
        "sort_by": sort_by,
        "sort_order": sort_order
    }

    try:
        token = await get_access_token(project_slug=project_slug)
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.text

    except httpx.HTTPStatusError as e:
        return f"API Form Entries Error ({e.response.status_code}): {e.response.text}"
    except Exception as e:
        return f"An unexpected error occurred while fetching form entries: {str(e)}"
if __name__ == "__main__":
    mcp.run()