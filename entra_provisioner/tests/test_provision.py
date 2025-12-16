import unittest
import sys
from unittest.mock import patch, MagicMock

# Mock dependencies before import
sys.modules["azure.identity"] = MagicMock()
sys.modules["requests"] = MagicMock()
sys.modules["yaml"] = MagicMock()

# Mock Pydantic
class MockBaseModel:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

mock_pydantic = MagicMock()
mock_pydantic.BaseModel = MockBaseModel
mock_pydantic.Field = lambda *args, **kwargs: None
sys.modules["pydantic"] = mock_pydantic

from entra_provisioner.entra import EntraClient
from entra_provisioner.config import SAMLServiceProvider, Metadata, Spec, Claim, GroupAssignment

class TestEntraProvisioner(unittest.TestCase):

    @patch('entra_provisioner.entra.DefaultAzureCredential')
    @patch('entra_provisioner.entra.requests')
    def test_provision_app_new(self, mock_requests, mock_credential):
        # Test creating a NEW app and NEW service principal
        
        # Mock Auth
        mock_credential.return_value.get_token.return_value.token = "fake-token"

        # Mock Responses for GET calls (checking existence)
        mock_get_apps_resp = MagicMock()
        mock_get_apps_resp.status_code = 200
        mock_get_apps_resp.json.return_value = {"value": []} # No existing apps

        mock_get_sps_resp = MagicMock()
        mock_get_sps_resp.status_code = 200
        mock_get_sps_resp.json.return_value = {"value": []} # No existing SPs

        # Mock Responses for POST/PATCH calls
        # 1. Create App
        mock_app_resp = MagicMock()
        mock_app_resp.status_code = 201
        mock_app_resp.json.return_value = {"id": "app-obj-id", "appId": "client-id"}
        
        # 3. Patch App (identifierUris)
        mock_patch_app_resp = MagicMock()
        mock_patch_app_resp.status_code = 204

        # 4. Create SP
        mock_sp_resp = MagicMock()
        mock_sp_resp.status_code = 201
        mock_sp_resp.json.return_value = {"id": "sp-obj-id"}

        # 5. Patch SP (SAML)
        mock_patch_sp_resp = MagicMock()
        mock_patch_sp_resp.status_code = 204

        # 6. Assign Group
        mock_group_resp = MagicMock()
        mock_group_resp.status_code = 201

        # Configure side_effect for GET calls
        # 1. GET /applications, 2. GET /servicePrincipals
        mock_requests.get.side_effect = [mock_get_apps_resp, mock_get_sps_resp]

        # Configure side_effect for POST calls
        # Sequence: POST /applications, POST /servicePrincipals, POST /appRoleAssignedTo
        mock_requests.post.side_effect = [mock_app_resp, mock_sp_resp, mock_group_resp]
        
        
        # Configure side_effect for PATCH calls
        # Sequence: PATCH /applications/{id} (identifierUris), PATCH /servicePrincipals/{id} (SAML mode)
        mock_requests.patch.side_effect = [mock_patch_app_resp, mock_patch_sp_resp]

        client = EntraClient()
        config = SAMLServiceProvider(
            apiVersion="v1",
            kind="SAMLServiceProvider",
            metadata=Metadata(name="Test App", environment="dev"),
            spec=Spec(
                entityId="api://test",
                assertionConsumerServiceUrl="https://test.com/acs",
                singleLogoutServiceUrl="https://test.com/logout",
                claims=[Claim(name="email", source="user")],
                groupAssignments=[GroupAssignment(groupId="group-guid")]
            )
        )

        result = client.provision_app(config)

        self.assertEqual(result['appId'], "client-id")
        self.assertEqual(result['objectId'], "app-obj-id")
        self.assertEqual(result['servicePrincipalId'], "sp-obj-id")

        # Verify Calls
        # Check that we queried for existing apps first
        self.assertTrue(mock_requests.get.called)
        
        # Check App creation
        app_call = mock_requests.post.call_args_list[0]
        self.assertIn("Test App", app_call[1]['json']['displayName'])
        
        # Check SP creation
        sp_call = mock_requests.post.call_args_list[1]
        self.assertEqual(sp_call[1]['json']['appId'], "client-id")

        # Check identifierUris PATCH
        # First PATCH should be for app identifierUris
        patch_app_call = mock_requests.patch.call_args_list[0]
        self.assertIn("applications/app-obj-id", patch_app_call[0][0])
        # Verify it uses api://{client_id}
        self.assertEqual(patch_app_call[1]['json']['identifierUris'], ["api://client-id"])

    @patch('entra_provisioner.entra.DefaultAzureCredential')
    @patch('entra_provisioner.entra.requests')
    def test_provision_app_existing(self, mock_requests, mock_credential):
        # Test finding an EXISTING app and EXISTING service principal
        
        # Mock Auth
        mock_credential.return_value.get_token.return_value.token = "fake-token"

        # Mock Responses for GET calls (checking existence)
        mock_get_apps_resp = MagicMock()
        mock_get_apps_resp.status_code = 200
        # Return existing app
        mock_get_apps_resp.json.return_value = {
            "value": [{"id": "existing-app-obj-id", "appId": "existing-client-id", "displayName": "Test App"}]
        }

        mock_get_sps_resp = MagicMock()
        mock_get_sps_resp.status_code = 200
        # Return existing SP
        mock_get_sps_resp.json.return_value = {
            "value": [{"id": "existing-sp-obj-id"}]
        }

        # Mock Responses for POST/PATCH calls
        # Patch SP (SAML) - still happens
        mock_patch_resp = MagicMock()
        mock_patch_resp.status_code = 204

        # Assign Group - still happens
        mock_group_resp = MagicMock()
        mock_group_resp.status_code = 201

        # Configure side_effect for GET calls
        mock_requests.get.side_effect = [mock_get_apps_resp, mock_get_sps_resp]

        # Configure side_effect for POST calls
        # We expect only ONE POST call: for the group assignment. 
        # App and SP creation should be SKIPPED.
        mock_requests.post.side_effect = [mock_group_resp]
        mock_requests.patch.return_value = mock_patch_resp

        client = EntraClient()
        config = SAMLServiceProvider(
            apiVersion="v1",
            kind="SAMLServiceProvider",
            metadata=Metadata(name="Test App", environment="dev"),
            spec=Spec(
                entityId="api://test",
                assertionConsumerServiceUrl="https://test.com/acs",
                singleLogoutServiceUrl="https://test.com/logout",
                claims=[Claim(name="email", source="user")],
                groupAssignments=[GroupAssignment(groupId="group-guid")]
            )
        )

        result = client.provision_app(config)

        self.assertEqual(result['appId'], "existing-client-id")
        self.assertEqual(result['objectId'], "existing-app-obj-id")
        self.assertEqual(result['servicePrincipalId'], "existing-sp-obj-id")

        # Verify that we check for existence
        self.assertEqual(mock_requests.get.call_count, 2)
        
        # Verify that we did NOT call POST for App or SP creation
        # We only expect 1 POST call (for group assignment)
        self.assertEqual(mock_requests.post.call_count, 1)
        self.assertIn("appRoleAssignedTo", mock_requests.post.call_args[0][0])
        
        # Verify we still patched SAML mode
        self.assertTrue(mock_requests.patch.called)

if __name__ == '__main__':
    unittest.main()
