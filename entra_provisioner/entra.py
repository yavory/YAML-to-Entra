import logging
import requests
from azure.identity import DefaultAzureCredential, ClientCertificateCredential
from .config import SAMLServiceProvider

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

class EntraClient:
    def __init__(self, client_id=None, tenant_id=None, certificate_path=None):
        if client_id and tenant_id and certificate_path:
            with open(certificate_path, "rb") as cert_file:
                logger.info(f"Using ClientCertificateCredential with client_id={client_id}, tenant_id={tenant_id}")
                self.credential = ClientCertificateCredential(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    certificate_path=certificate_path
                )
        else:
            logger.info("Using DefaultAzureCredential")
            self.credential = DefaultAzureCredential()
        self.token = None

    def _get_headers(self):
        if not self.token:
            self.token = self.credential.get_token("https://graph.microsoft.com/.default").token
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def provision_app(self, config: SAMLServiceProvider):
        headers = self._get_headers()
        spec = config.spec
        
        # 1. Create Application
        # We use replyUrlsWithType for better SAML support if possible, but web.redirectUris is standard.
        # Mapping:
        # entityId -> identifierUris
        # assertionConsumerServiceUrl -> redirectUris
        
        app_payload = {
            "displayName": config.metadata.name,
            "signInAudience": "AzureADMyOrg",
            "web": {
                "redirectUris": [spec.assertionConsumerServiceUrl],
                "homePageUrl": spec.singleLogoutServiceUrl, # Mapping SLO to homepage as a placeholder or exact SLO field if beta
                "logoutUrl": spec.singleLogoutServiceUrl
            },
            "identifierUris": [spec.entityId]
        }
        
        # Add Optional Claims if present
        if spec.claims:
            # This is a simplified mapping. Real claim mapping policies are complex.
            # We will add them to optionalClaims idToken/accessToken/saml2Token
            claims_map = []
            for claim in spec.claims:
                claims_map.append({
                    "name": claim.name,
                    "source": claim.source, # null or "user"
                    "essential": False,
                    "additionalProperties": []
                })
            
            app_payload["optionalClaims"] = {
                "saml2Token": claims_map
            }

        logger.info(f"Creating application: {config.metadata.name}")
        resp = requests.post(f"{GRAPH_API_BASE}/applications", json=app_payload, headers=headers)
        if resp.status_code != 201:
            raise Exception(f"Failed to create application: {resp.text}")
        
        app_data = resp.json()
        app_id = app_data['id']
        client_id = app_data['appId']
        logger.info(f"Created App Registration. Object ID: {app_id}, App ID: {client_id}")

        # 2. Create Service Principal
        sp_payload = {
            "appId": client_id
        }
        logger.info(f"Creating Service Principal for {config.metadata.name}")
        resp = requests.post(f"{GRAPH_API_BASE}/servicePrincipals", json=sp_payload, headers=headers)
        if resp.status_code != 201:
            raise Exception(f"Failed to create Service Principal: {resp.text}")
        
        sp_data = resp.json()
        sp_id = sp_data['id']
        logger.info(f"Created Service Principal. Object ID: {sp_id}")

        # 3. Configure SAML mode
        patch_sp_payload = {
            "preferredSingleSignOnMode": "saml",
            "tags": ["WindowsAzureActiveDirectoryCustomSingleSignOnApplication"]
        }

        logger.info(f"Configuring SAML mode for {config.metadata.name}")
        resp = requests.patch(f"{GRAPH_API_BASE}/servicePrincipals/{sp_id}", json=patch_sp_payload, headers=headers)
        if resp.status_code != 204:
             logger.warning(f"Failed to set SAML mode: {resp.text}")

        # 4. Group Assignments
        # To assign a group, we create an AppRoleAssignment on the group or the SP.
        # POST /servicePrincipals/{resourceSpId}/appRoleAssignedTo 
        # { "principalId": "{groupId}", "resourceId": "{resourceSpId}", "appRoleId": "00...00" (default) }
        
        if spec.groupAssignments:
            for group_assign in spec.groupAssignments:
                self._assign_group(sp_id, group_assign.groupId, headers)

        return {"appId": client_id, "objectId": app_id, "servicePrincipalId": sp_id}

    def _assign_group(self, sp_id, group_id, headers):
        # Default Access Role (User) is usually all zeros.
        # If the app defines roles, we would need to look them up.
        # For now, we assume default access.
        default_role_id = "00000000-0000-0000-0000-000000000000"
        
        payload = {
            "principalId": group_id,
            "resourceId": sp_id,
            "appRoleId": default_role_id
        }
        logger.info(f"Assigning group {group_id} to Service Principal {sp_id}")
        resp = requests.post(f"{GRAPH_API_BASE}/servicePrincipals/{sp_id}/appRoleAssignedTo", json=payload, headers=headers)
        if resp.status_code != 201:
             logger.warning(f"Failed to assign group {group_id}: {resp.text}")
