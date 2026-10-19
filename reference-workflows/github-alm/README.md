# GitHub ALM reference workflows

Companion files for **Agent Factory ALM with GitHub Actions**:

- [Passwordless connectivity validation](af-pilot-oidc-validate-GIT.yml)
- [Managed solution release](af-pilot-solution-release-GIT.yaml)
- [Offline article](../../articles/311-github-alm-for-copilot-studio.html)

These are sanitized copies of the lab YAML, not active workflows in this backup repository. The source WordPress article and local original YAML files are unchanged.

## Replace placeholders before use

| Placeholder | Required value |
|---|---|
| `YOUR-GITHUB-OWNER/YOUR-REPOSITORY` | Repository that will run the release workflow |
| `YOUR-ENTRA-CLIENT-ID` | Entra application client ID |
| `YOUR-ENTRA-TENANT-ID` | Entra directory tenant ID |
| `https://YOUR-DEV-ORG.crm.dynamics.com` | Exact DEV Dataverse URL |
| `https://YOUR-TEST-ORG.crm.dynamics.com` | Exact TEST Dataverse URL |
| `https://YOUR-PROD-ORG.crm.dynamics.com` | Exact PROD Dataverse URL |

Use the same values in each GitHub environment's `PP_CLIENT_ID_GIT`, `PP_TENANT_ID_GIT`, and `PP_ENVIRONMENT_URL_GIT` variables. Retain the correct regional Dataverse hostname for your tenant; do not copy the example hostname blindly.

The lab environment names, solution unique name, and package name remain intact. Adapt them if your setup differs.

## Deploying these workflows elsewhere

Copy the reviewed files into `.github/workflows/` in your intended ALM repository only after configuring Entra OIDC trust, Dataverse application users, and the three GitHub environments. Inspect the actual OIDC subject in your repository rather than copying identifiers from another repository.

The validation workflow authenticates without importing a solution. The release workflow can import into TEST and, when explicitly requested, PROD. Its confirmation text is not an independent reviewer approval. Configure appropriate environment protection and workflow-change controls before real production use.

No client secrets or authentication tokens are included. These reference files have not been executed as part of this backup operation.
