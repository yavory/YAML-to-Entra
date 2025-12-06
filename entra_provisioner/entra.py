import logging
import requests
from azure.identity import DefaultAzureCredential
from .config import EntraAppConfig

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.microsoft.com/v1.0"

class EntraClient:
    def __init__(self):
        self.credential = DefaultAzureCredential()
        self.token = None

    def _get_headers(self):
        if not self.token:
            # Scope for MS Graph
            self.token = self.credential.get_token("https://graph.microsoft.com/.default").token
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def provision_app(self, config: EntraAppConfig):
        headers = self._get_headers()
        
        # 1. Create Application
        app_payload = {
            "displayName": config.name,
            "signInAudience": "AzureADMyOrg",
            "web": {
                "redirectUris": config.reply_urls,
                "homePageUrl": config.sign_on_url,
                "logoutUrl": config.logout_url
            },
            "identifierUris": config.identifier_uris
        }
        
        logger.info(f"Creating application: {config.name}")
        resp = requests.post(f"{GRAPH_API_BASE}/applications", json=app_payload, headers=headers)
        if resp.status_code != 201:
            raise Exception(f"Failed to create application: {resp.text}")
        
        app_data = resp.json()
        app_id = app_data['id']
        client_id = app_data['appId']
        logger.info(f"Created App Registration. Object ID: {app_id}, App ID: {client_id}")

        # 2. Create Service Principal (Enterprise App)
        sp_payload = {
            "appId": client_id
        }
        logger.info(f"Creating Service Principal for {config.name}")
        resp = requests.post(f"{GRAPH_API_BASE}/servicePrincipals", json=sp_payload, headers=headers)
        if resp.status_code != 201:
             # It might already exist if we are retrying, but for a new app it shouldn't.
            raise Exception(f"Failed to create Service Principal: {resp.text}")
        
        sp_data = resp.json()
        sp_id = sp_data['id']
        logger.info(f"Created Service Principal. Object ID: {sp_id}")

        # 3. Configure SAML (preferredSingleSignOnMode)
        # Note: 'saml' mode is set on the Service Principal
        # We also might need to add a claim mapping or similar, but basic SAML app just needs this.
        patch_sp_payload = {
            "preferredSingleSignOnMode": "saml"
            # tag as 'WindowsAzureActiveDirectoryGalleryApplicationNonPrimaryV1' is sometimes needed for legacy behavior 
            # but usually just setting mode is enough for non-gallery apps.
            # Actually, to make it a "Non-Gallery" SAML app, we usually need to add specific tags.
            # "tags": ["WindowsAzureActiveDirectoryCustomSingleSignOnApplication"]
        }
        # Add the tag to ensure it shows up correctly as a custom SAML app
        patch_sp_payload["tags"] = ["WindowsAzureActiveDirectoryCustomSingleSignOnApplication"]

        logger.info(f"Configuring SAML mode for {config.name}")
        resp = requests.patch(f"{GRAPH_API_BASE}/servicePrincipals/{sp_id}", json=patch_sp_payload, headers=headers)
        if resp.status_code != 204:
             logger.warning(f"Failed to set SAML mode: {resp.text}")

        # 4. Assign Owners if specified
        if config.owners:
            for owner_id in config.owners:
                self._add_owner(app_id, owner_id, headers, "applications")
                self._add_owner(sp_id, owner_id, headers, "servicePrincipals")

        return {"appId": client_id, "objectId": app_id, "servicePrincipalId": sp_id}

    def _add_owner(self, resource_id, owner_id, headers, resource_type):
        # owner_id must be a GUID (User Object ID).
        # Payload looks like: { "@odata.id": "https://graph.microsoft.com/v1.0/directoryObjects/{id}" }
        payload = {
            "@odata.id": f"{GRAPH_API_BASE}/directoryObjects/{owner_id}"
        }
        logger.info(f"Adding owner {owner_id} to {resource_type}/{resource_id}")
        resp = requests.post(f"{GRAPH_API_BASE}/{resource_type}/{resource_id}/owners/$ref", json=payload, headers=headers)
        if resp.status_code != 204 and resp.status_code != 201:
            logger.warning(f"Failed to add owner {owner_id}: {resp.text}")

