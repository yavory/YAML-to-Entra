import unittest
from unittest.mock import patch, MagicMock
from entra_provisioner.entra import EntraClient
from entra_provisioner.config import SAMLServiceProvider, Metadata, Spec, Claim, GroupAssignment

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

        # 4. Assign Group
        mock_group_resp = MagicMock()
        mock_group_resp.status_code = 201

        # Configure side_effect for successive calls
        # Sequence: POST /applications, POST /servicePrincipals, PATCH /servicePrincipals, POST /owners (x2) if owners
        # New Sequence: POST /applications, POST /servicePrincipals, PATCH /servicePrincipals, POST /appRoleAssignedTo
        
        mock_requests.post.side_effect = [mock_app_resp, mock_sp_resp, mock_group_resp]
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

        self.assertEqual(result['appId'], "client-id")
        self.assertEqual(result['objectId'], "app-obj-id")
        self.assertEqual(result['servicePrincipalId'], "sp-obj-id")

        # Verify Calls
        # Check App creation payload
        app_call = mock_requests.post.call_args_list[0]
        self.assertIn("Test App", app_call[1]['json']['displayName'])
        self.assertIn("api://test", app_call[1]['json']['identifierUris'])
        self.assertIn("email", str(app_call[1]['json']['optionalClaims']))

        # Check SP creation
        sp_call = mock_requests.post.call_args_list[1]
        self.assertEqual(sp_call[1]['json']['appId'], "client-id")

        # Check SAML Patch
        patch_call = mock_requests.patch.call_args_list[0]
        self.assertIn("servicePrincipals/sp-obj-id", patch_call[0][0])
        self.assertEqual(patch_call[1]['json']['preferredSingleSignOnMode'], "saml")

        # Check Group Assignment
        group_call = mock_requests.post.call_args_list[2]
        self.assertIn("servicePrincipals/sp-obj-id/appRoleAssignedTo", group_call[0][0])
        self.assertEqual(group_call[1]['json']['principalId'], "group-guid")

if __name__ == '__main__':
    unittest.main()
