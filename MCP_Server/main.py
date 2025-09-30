from   mcp.server.fastmcp import FastMCP
import httpx
import asyncio
import os
import json
import logging
from   auth_manager import apic_auth_manager
from   intersight_auth_manager import intersight_auth_manager 

# set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("APICmcp")

# Create MCP server instance (defaults used for initialization)
mcp = FastMCP("APICmcp")
#mcp = FastMCP("APICmcp")

@mcp.tool()
async def fetch_apic_class(class_name: str) -> str:
    """
    Fetches a class of Managed Object from Cisco APIC.
    Requires APIC authentication.

    Args:
        class_name (str): The class name of the Managed Object (e.g., 'fvTenant', 'topSystem').

    Returns:
        str: The JSON response from APIC.
    """
    logger.info(f"Logging in to APIC")
    await apic_auth_manager.initialize()
    client = await apic_auth_manager.get_authenticated_client()
    if not client:
        logger.error("Error: Unable to authenticate with APIC. Please check your credentials.")
    logger.info(f"Authenticated successfully with APIC: {apic_auth_manager.apic_base_url}")

    base_url = apic_auth_manager.apic_base_url
    url = f"{base_url}/api/class/{class_name}.json"

    try:
        response = await client.get(url, timeout=10.0)
        response.raise_for_status()
        return json.dumps(response.json(), indent=2) 
    except httpx.HTTPStatusError as e:
        return f"Error: APIC returned status {e.response.status_code} for {e.request.url}. Response: {e.response.text}"
    except httpx.RequestError as e:
        return f"Error: An error occurred while requesting {e.request.url}: {e}"
    except RuntimeError as e:
        return f"APIC Authentication Error: {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"

async def apic_rest_post(url: str, payload: dict) -> dict:
    """
    Performs a POST request to APIC's REST API to create or update a Managed Object.
    Requires APIC authentication.

    Args:
        url (str): The URL to POST to
        payload (dict): The JSON payload to POST to the REST API.

    Returns:
        dict: The JSON response from APIC or None if failed.   
    """
    logger.info(f"Logging in to APIC")
    await apic_auth_manager.initialize()
    client = await apic_auth_manager.get_authenticated_client()
    if not client:
        logger.error("Error: Unable to authenticate with APIC. Please check your credentials.")
        return None
    logger.info(f"Authenticated successfully with APIC: {apic_auth_manager.apic_base_url}")

    base_url = apic_auth_manager.apic_base_url
    full_url = f"{base_url}/{url}"
    try:
        response = await client.post(full_url, json=payload, timeout=10.0)
        response.raise_for_status()
        logger.info(f"Successfully posted to {full_url}")
        return response.json()
    except httpx.RequestError as e:
        logger.error(f"Error making request to {full_url}: {e}")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"Request to {full_url} failed with status {e.response.status_code}: {e.response.text}")
        return None
    

@mcp.tool()
async def make_aci_backup(scp_server_ip: str, scp_username: str, scp_password: str, remote_name: str, remote_path: str, export_policy_name: str) -> str:
    """
    Creates a backup of the APIC configuration.
    Requires APIC authentication.

    args:
        scp_server_ip (str): The IP address of the SCP server.
        scp_username (str): The username for the SCP server.
        scp_passwpord (str): The password for the SCP server.
        remote_path_name (str): The name of the remote path in APIC.
        export_policy_name (str): The name of the export policy.    
    
    Returns:
        str: The status of the backup operation.
    """
    # --- Create remote destination ---
    logger.info("Creating remote destination")
    remote_location_content = {
        "fileRemotePath": {
            "attributes": {
                "dn": f"uni/fabric/path-{remote_name}",
                "remotePort": "22",
                "name": remote_name,
                "descr": "MCP backup SCP Server",
                "protocol": "scp",
                "remotePath": remote_path,
                "userName": scp_username,
                "userPasswd": scp_password,
                "host": scp_server_ip,
                "status": "created,modified"
            },
            "children": [
                {
                    "fileRsARemoteHostToEpg": {
                        "attributes": {
                            "tDn": "uni/tn-mgmt/mgmtp-default/oob-default",
                            "status": "created,modified"
                        },
                        "children": []
                    }
                }
            ]
        }
    }
    await apic_rest_post(url="/api/node/mo/uni.json", payload=remote_location_content)

    # --- Enable Global AES Encryption Settings ---
    logger.info("Enabling Global AES Encryption Settings")
    aes_encryption_content = {
        "pkiExportEncryptionKey": {
            "attributes": {
                "dn": "uni/exportcryptkey",
                "strongEncryptionEnabled": "true",
                "passphrase": "mcpServermcpServermcpServer"
            },
            "children": []
        }
    }
    await apic_rest_post(url="/api/node/mo/uni.json", payload=aes_encryption_content)

    # --- Create an Export Policy ---
    logger.info("Creating an Export Policy")
    export_policy_content = {
        "configExportP": {
            "attributes": {
                "dn": f"uni/fabric/configexp-{export_policy_name}",
                "name": export_policy_name,
                "descr": "Export Policy for SCP",
                "adminSt": "triggered",
                "format": "json",
                "status": "created,modified"
            },
            "children": [{
                "configRsExportScheduler": {
                    "attributes": {
                        "tnTrigSchedPName": "EveryEightHours",
                        "status": "created,modified"
                    },
                    "children": []
                }
            },
            {
                "configRsRemotePath": {
                    "attributes": {
                        "tnFileRemotePathName": remote_name,
                        "status": "created,modified"
                    },
                    "children": []
                }
            }]
        }
    }
    await apic_rest_post(url="/api/node/mo/uni.json", payload=export_policy_content)

@mcp.tool()
async def create_tenant(tenant_name: str, description: str = "") -> str:
    """
    Creates a new tenant in Cisco APIC.
    Requires APIC authentication.

    Args:
        tenant_name (str): The name of the tenant to create.
        description (str): Optional description for the tenant.

    Returns:
        str: The result of the tenant creation operation.
    """
    logger.info(f"Creating tenant: {tenant_name}")
    
    # Create tenant payload following APIC REST API structure
    tenant_payload = {
        "fvTenant": {
            "attributes": {
                "dn": f"uni/tn-{tenant_name}",
                "name": tenant_name,
                "descr": description,
                "status": "created,modified"
            },
            "children": []
        }
    }
    
    try:
        result = await apic_rest_post(url="/api/node/mo/uni.json", payload=tenant_payload)
        if result:
            logger.info(f"Successfully created tenant: {tenant_name}")
            return f"✅ Tenant '{tenant_name}' created successfully. Description: {description}"
        else:
            logger.error(f"Failed to create tenant: {tenant_name}")
            return f"❌ Failed to create tenant '{tenant_name}'. Check APIC logs for details."
    except Exception as e:
        logger.error(f"Error creating tenant {tenant_name}: {e}")
        return f"❌ Error creating tenant '{tenant_name}': {str(e)}"

@mcp.tool()
async def create_vrf(tenant_name: str, vrf_name: str, description: str = "") -> str:
    """
    Creates a new VRF (Virtual Routing and Forwarding) instance in a specified tenant.
    Requires APIC authentication.

    Args:
        tenant_name (str): The name of the tenant where the VRF will be created.
        vrf_name (str): The name of the VRF to create.
        description (str): Optional description for the VRF.

    Returns:
        str: The result of the VRF creation operation.
    """
    logger.info(f"Creating VRF: {vrf_name} in tenant: {tenant_name}")
    
    # Create VRF payload following APIC REST API structure
    vrf_payload = {
        "fvCtx": {
            "attributes": {
                "dn": f"uni/tn-{tenant_name}/ctx-{vrf_name}",
                "name": vrf_name,
                "descr": description,
                "status": "created,modified"
            },
            "children": []
        }
    }
    
    try:
        result = await apic_rest_post(url="/api/node/mo/uni.json", payload=vrf_payload)
        if result:
            logger.info(f"Successfully created VRF: {vrf_name} in tenant: {tenant_name}")
            return f"✅ VRF '{vrf_name}' created successfully in tenant '{tenant_name}'. Description: {description}"
        else:
            logger.error(f"Failed to create VRF: {vrf_name} in tenant: {tenant_name}")
            return f"❌ Failed to create VRF '{vrf_name}' in tenant '{tenant_name}'. Check APIC logs for details."
    except Exception as e:
        logger.error(f"Error creating VRF {vrf_name} in tenant {tenant_name}: {e}")
        return f"❌ Error creating VRF '{vrf_name}' in tenant '{tenant_name}': {str(e)}"

@mcp.tool()
async def create_bridge_domain(tenant_name: str, vrf_name: str, bd_name: str, description: str = "") -> str:
    """
    Creates a new Bridge Domain in a specified tenant and VRF.
    Requires APIC authentication.

    Args:
        tenant_name (str): The name of the tenant where the BD will be created.
        vrf_name (str): The name of the VRF to associate with the BD.
        bd_name (str): The name of the Bridge Domain to create.
        description (str): Optional description for the Bridge Domain.

    Returns:
        str: The result of the Bridge Domain creation operation.
    """
    logger.info(f"Creating Bridge Domain: {bd_name} in tenant: {tenant_name}, VRF: {vrf_name}")
    
    # Create Bridge Domain payload following APIC REST API structure
    bd_payload = {
        "fvBD": {
            "attributes": {
                "dn": f"uni/tn-{tenant_name}/BD-{bd_name}",
                "name": bd_name,
                "descr": description,
                "status": "created,modified"
            },
            "children": [
                {
                    "fvRsCtx": {
                        "attributes": {
                            "tnFvCtxName": vrf_name,
                            "status": "created,modified"
                        },
                        "children": []
                    }
                }
            ]
        }
    }
    
    try:
        result = await apic_rest_post(url="/api/node/mo/uni.json", payload=bd_payload)
        if result:
            logger.info(f"Successfully created Bridge Domain: {bd_name} in tenant: {tenant_name}")
            return f"✅ Bridge Domain '{bd_name}' created successfully in tenant '{tenant_name}' and associated with VRF '{vrf_name}'. Description: {description}"
        else:
            logger.error(f"Failed to create Bridge Domain: {bd_name} in tenant: {tenant_name}")
            return f"❌ Failed to create Bridge Domain '{bd_name}' in tenant '{tenant_name}'. Check APIC logs for details."
    except Exception as e:
        logger.error(f"Error creating Bridge Domain {bd_name} in tenant {tenant_name}: {e}")
        return f"❌ Error creating Bridge Domain '{bd_name}' in tenant '{tenant_name}': {str(e)}"

# ============================================================================
# CISCO INTERSIGHT TOOLS
# ============================================================================

@mcp.tool()
async def get_intersight_servers() -> str:
    """
    Retrieves a list of physical servers from Cisco Intersight.
    Requires Intersight authentication.

    Returns:
        str: JSON response containing server information from Intersight.
    """
    logger.info("Fetching servers from Cisco Intersight")
    
    try:
        result = await intersight_auth_manager.make_request(
            method="GET",
            endpoint="/api/v1/compute/PhysicalSummaries"
        )
        
        if result:
            logger.info("Successfully retrieved servers from Intersight")
            return json.dumps(result, indent=2)
        else:
            logger.error("No data received from Intersight")
            return "❌ No server data received from Intersight"
            
    except Exception as e:
        logger.error(f"Error fetching servers from Intersight: {e}")
        return f"❌ Error fetching servers from Intersight: {str(e)}"

@mcp.tool()
async def get_intersight_organizations() -> str:
    """
    Retrieves a list of organizations from Cisco Intersight.
    Requires Intersight authentication.

    Returns:
        str: JSON response containing organization information from Intersight.
    """
    logger.info("Fetching organizations from Cisco Intersight")
    
    try:
        result = await intersight_auth_manager.make_request(
            method="GET",
            endpoint="/api/v1/organization/Organizations"
        )
        
        if result:
            logger.info("Successfully retrieved organizations from Intersight")
            return json.dumps(result, indent=2)
        else:
            logger.error("No data received from Intersight")
            return "❌ No organization data received from Intersight"
            
    except Exception as e:
        logger.error(f"Error fetching organizations from Intersight: {e}")
        return f"❌ Error fetching organizations from Intersight: {str(e)}"

@mcp.tool()
async def get_intersight_alarms() -> str:
    """
    Retrieves active alarms from Cisco Intersight.
    Requires Intersight authentication.

    Returns:
        str: JSON response containing alarm information from Intersight.
    """
    logger.info("Fetching alarms from Cisco Intersight")
    
    try:
        result = await intersight_auth_manager.make_request(
            method="GET",
            endpoint="/api/v1/cond/Alarms?$filter=Severity in ('Critical', 'Major', 'Minor', 'Warning')"
        )
        
        if result:
            logger.info("Successfully retrieved alarms from Intersight")
            return json.dumps(result, indent=2)
        else:
            logger.error("No alarm data received from Intersight")
            return "❌ No alarm data received from Intersight"
            
    except Exception as e:
        logger.error(f"Error fetching alarms from Intersight: {e}")
        return f"❌ Error fetching alarms from Intersight: {str(e)}"

@mcp.tool()
async def create_intersight_server_profile(profile_name: str, organization_name: str, description: str = "") -> str:
    """
    Creates a new server profile in Cisco Intersight.
    Requires Intersight authentication.

    Args:
        profile_name (str): The name of the server profile to create.
        organization_name (str): The organization where the profile will be created.
        description (str): Optional description for the server profile.

    Returns:
        str: The result of the server profile creation operation.
    """
    logger.info(f"Creating server profile: {profile_name} in organization: {organization_name}")
    
    # First, get the organization MOID (get all orgs and filter locally to avoid auth issues)
    try:
        org_result = await intersight_auth_manager.make_request(
            method="GET",
            endpoint="/api/v1/organization/Organizations"
        )
        
        if not org_result.get('Results'):
            return f"❌ No organizations found in Intersight"
        
        # Filter organizations locally
        matching_orgs = [org for org in org_result['Results'] if org.get('Name') == organization_name]
        
        if not matching_orgs:
            available_orgs = [org.get('Name', 'Unknown') for org in org_result['Results']]
            return f"❌ Organization '{organization_name}' not found in Intersight. Available organizations: {', '.join(available_orgs)}"
        
        org_moid = matching_orgs[0]['Moid']
        logger.info(f"Found organization MOID: {org_moid}")
        
    except Exception as e:
        logger.error(f"Error finding organization {organization_name}: {e}")
        return f"❌ Error finding organization '{organization_name}': {str(e)}"
    
    # Create server profile payload
    profile_payload = {
        "Name": profile_name,
        "Description": description,
        "Organization": {
            "Moid": org_moid,
            "ObjectType": "organization.Organization"
        },
        "ObjectType": "server.Profile"
    }
    
    try:
        result = await intersight_auth_manager.make_request(
            method="POST",
            endpoint="/api/v1/server/Profiles",
            data=profile_payload
        )
        
        if result:
            logger.info(f"Successfully created server profile: {profile_name}")
            return f"✅ Server profile '{profile_name}' created successfully in organization '{organization_name}'. Description: {description}"
        else:
            logger.error(f"Failed to create server profile: {profile_name}")
            return f"❌ Failed to create server profile '{profile_name}'. Check Intersight logs for details."
            
    except Exception as e:
        logger.error(f"Error creating server profile {profile_name}: {e}")
        return f"❌ Error creating server profile '{profile_name}': {str(e)}"

@mcp.tool()
async def get_intersight_hyperflex_clusters() -> str:
    """
    Retrieves HyperFlex cluster information from Cisco Intersight.
    Requires Intersight authentication.

    Returns:
        str: JSON response containing HyperFlex cluster information from Intersight.
    """
    logger.info("Fetching HyperFlex clusters from Cisco Intersight")
    
    try:
        result = await intersight_auth_manager.make_request(
            method="GET",
            endpoint="/api/v1/hyperflex/Clusters"
        )
        
        if result:
            logger.info("Successfully retrieved HyperFlex clusters from Intersight")
            return json.dumps(result, indent=2)
        else:
            logger.error("No HyperFlex cluster data received from Intersight")
            return "❌ No HyperFlex cluster data received from Intersight"
            
    except Exception as e:
        logger.error(f"Error fetching HyperFlex clusters from Intersight: {e}")
        return f"❌ Error fetching HyperFlex clusters from Intersight: {str(e)}"


if __name__ == "__main__":
    logger.info("Starting MCP server APICmcp on STDIO...")
    mcp.run()
