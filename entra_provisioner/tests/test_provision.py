import unittest
from unittest.mock import patch, MagicMock
from entra_provisioner.entra import EntraClient
from entra_provisioner.config import EntraAppConfig

class TestEntraProvisioner(unittest.TestCase):

    @patch('entra_provisioner.entra.DefaultAzureCredential')
    @patch('entra_provisioner.entra.requests')
    def test_provision_app(self, mock_requests, mock_credential):
        # Mock Auth
        mock_credential.return_value.get_token.return_value.token = "fake-token"

        # Mock Responses
        # 1. Create App
        mock_app_resp = MagicMock()
        mock_app_resp.status_code = 201
        mock_app_resp.json.return_value = {"id": "app-obj-id", "appId": "client-id"}
        
        # 2. Create SP
        mock_sp_resp = MagicMock()
        mock_sp_resp.status_code = 201
        mock_sp_resp.json.return_value = {"id": "sp-obj-id"}

        # 3. Patch SP (SAML)
        mock_patch_resp = MagicMock()
        mock_patch_resp.status_code = 204

        # 4. Add Owner
        mock_owner_resp = MagicMock()
        mock_owner_resp.status_code = 204

        # Configure side_effect for successive calls
        # Sequence: POST /applications, POST /servicePrincipals, PATCH /servicePrincipals, POST /owners (x2)
        mock_requests.post.side_effect = [mock_app_resp, mock_sp_resp, mock_owner_resp, mock_owner_resp]
        mock_requests.patch.return_value = mock_patch_resp

        client = EntraClient()
        config = EntraAppConfig(
            name="Test App",
            identifier_uris=["api://test"],
            reply_urls=["https://test.com"],
            owners=["owner-guid"]
        )

        result = client.provision_app(config)

        self.assertEqual(result['appId'], "client-id")
        self.assertEqual(result['objectId'], "app-obj-id")
        self.assertEqual(result['servicePrincipalId'], "sp-obj-id")

        # Verify Calls
        # Check App creation payload
        app_call = mock_requests.post.call_args_list[0]
        self.assertIn("Test App", app_call[1]['json']['displayName'])
        self.assertIn("api://test", app_call[1]['json']['identifierUris'])

        # Check SP creation
        sp_call = mock_requests.post.call_args_list[1]
        self.assertEqual(sp_call[1]['json']['appId'], "client-id")

        # Check SAML Patch
        patch_call = mock_requests.patch.call_args_list[0]
        self.assertIn("servicePrincipals/sp-obj-id", patch_call[0][0])
        self.assertEqual(patch_call[1]['json']['preferredSingleSignOnMode'], "saml")

if __name__ == '__main__':
    unittest.main()
