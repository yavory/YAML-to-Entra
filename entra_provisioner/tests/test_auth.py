import sys
from unittest.mock import MagicMock

# Mock azure.identity before importing entra
mock_azure_identity = MagicMock()
sys.modules["azure.identity"] = mock_azure_identity

import unittest
from unittest.mock import patch, mock_open
from entra_provisioner.entra import EntraClient

class TestEntraAuth(unittest.TestCase):

    def setUp(self):
        # Reset mocks
        mock_azure_identity.reset_mock()
        # Setup the classes we expect
        self.MockDefaultCred = mock_azure_identity.DefaultAzureCredential
        self.MockCertCred = mock_azure_identity.ClientCertificateCredential

    def test_default_auth(self):
        client = EntraClient()
        self.MockDefaultCred.assert_called_once()
        self.assertIsNone(client.token)

    def test_cert_auth(self):
        client_id = "test-client-id"
        tenant_id = "test-tenant-id"
        cert_path = "/path/to/cert.pem"

        # Mock opening the certificate file
        with patch("builtins.open", mock_open(read_data=b"fake-cert-data")):
            client = EntraClient(
                client_id=client_id,
                tenant_id=tenant_id,
                certificate_path=cert_path
            )

        self.MockCertCred.assert_called_once_with(
            tenant_id=tenant_id,
            client_id=client_id,
            certificate_path=cert_path
        )
        self.assertIsNone(client.token)

if __name__ == '__main__':
    unittest.main()
