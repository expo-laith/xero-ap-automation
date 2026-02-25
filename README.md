# Xero AP Automation

## Azure App Service (GitHub Deployment) Notes

### Project Description

This is a FastAPI-based internal tool that accepts an AP Run Excel upload, looks up matching Xero AP invoices, downloads invoice attachments, and returns a ZIP file grouped into category folders.

### Runtime / Startup

- Python runtime: `3.11`
- Azure App Service startup command (set in Portal):
  - `uvicorn app:app --host 0.0.0.0 --port 8000`
- FastAPI app import target is `app:app` because the project uses a flat `app.py` at repo root.

### Required Azure App Settings (Environment Variables)

Set these in **Azure Portal -> App Service -> Configuration -> Application settings**:

- `XERO_CLIENT_ID`
- `XERO_CLIENT_SECRET`
- `XERO_REDIRECT_URI`
- `XERO_TENANT_ID`
- `XERO_REFRESH_TOKEN` (required for token refresh flow)

Optional:

- `XERO_OUT_ROOT` (override output root; defaults to app working directory)
- `SCM_DO_BUILD_DURING_DEPLOYMENT=true`
- `ENABLE_ORYX_BUILD=true`

### How To Set Environment Variables (Local Development)

PowerShell (Windows):

```powershell
$env:XERO_CLIENT_ID="your-client-id"
$env:XERO_CLIENT_SECRET="your-client-secret"
$env:XERO_REDIRECT_URI="http://localhost:53682/callback"
$env:XERO_TENANT_ID="your-tenant-id"
$env:XERO_REFRESH_TOKEN="your-refresh-token"
```

Bash (macOS/Linux):

```bash
export XERO_CLIENT_ID="your-client-id"
export XERO_CLIENT_SECRET="your-client-secret"
export XERO_REDIRECT_URI="http://localhost:53682/callback"
export XERO_TENANT_ID="your-tenant-id"
export XERO_REFRESH_TOKEN="your-refresh-token"
```

### GitHub Deployment Center (Azure)

1. Push this repo to GitHub (do not include `xero_secrets.json`).
2. In Azure App Service, open **Deployment Center**.
3. Choose **GitHub** source and connect the repository/branch.
4. Ensure App Service is configured for Python 3.11.
5. Set the startup command to:
   - `uvicorn app:app --host 0.0.0.0 --port 8000`
6. Save and redeploy.

### Local Run

```bash
python -m uvicorn app:app --reload
```

### How To Test After Azure Deployment

1. Open the App Service URL.
2. Verify the root page (`/`) loads.
3. Click **Download Template** and confirm `AP_run_template.xlsx` downloads.
4. Upload a valid `.xlsx` file and submit.
5. Confirm the app returns a ZIP download.
6. If it fails, check **Log stream** in Azure and verify environment variables are set.

### Project Layout (Expected)

```text
app.py
processor.py
requirements.txt
templates/
  index.html
AP_run_template.xlsx
```
