# Entra SAML Provisioner Walkthrough

I have implemented an OS-agnostic Python system to provision Entra ID SAML applications from a YAML configuration file.

## Prerequisites

- Python 3.8+
- An Azure Entra ID Tenant
- An account with permissions to create App Registrations (e.g., Application Developer, Cloud Application Administrator)

## Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   (Note: Dependencies include `azure-identity`, `requests`, `PyYAML`, `pydantic`)

2. Install the package (optional):
   ```bash
   pip install .
   ```

## Configuration

Create a YAML file (e.g., `my_apps.yaml`) describing your applications using the Kubernetes-style schema:

```yaml
apiVersion: v1
kind: SAMLServiceProvider
metadata:
  name: "My SAML App"
  environment: "production"
  description: "My SaaS Application"
spec:
  entityId: "api://my-saml-app"
  assertionConsumerServiceUrl: "https://myapp.com/acs"
  singleLogoutServiceUrl: "https://myapp.com/logout"
  claims:
    - name: "email"
      source: "user"
  groupAssignments:
    - groupId: "00000000-0000-0000-0000-000000000000"
```

## Usage

Run the provisioner:

```bash
python3 entra_provisioner/main.py my_apps.yaml
# Or if installed:
entra-provision my_apps.yaml
```

- The tool uses `DefaultAzureCredential`. You can authenticate via:
    - `az login` (Azure CLI)
    - Environment variables (`AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`)
    - VS Code Azure Account extension

## Testing

I have included unit tests that mock the MS Graph API calls. To run them:

```bash
python3 -m unittest discover -s entra_provisioner/tests
```

## Implementation Details

- **Language**: Python (OS agnostic)
- **Library**: `requests` for direct Graph API control, `azure-identity` for auth.
- **Validation**: Pydantic models ensure YAML validity before API calls.
- **Idempotency**: The script currently errors if the app exists (or creates a duplicate if allowed). Future improvements could check for existence first.
