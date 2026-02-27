# Deployment Checklist

## Pre-Deployment Verification

### ✅ Code Changes Complete
- [x] Added `SECRETS_PATH = "/home/xero_secrets.json"` constant to processor.py
- [x] Updated `load_secrets()` to read from `/home/xero_secrets.json`
- [x] Updated `save_secrets()` to write to `/home/xero_secrets.json`
- [x] Added OAuth authorization route `/authorize-xero` in app.py
- [x] Added OAuth callback route `/callback` in app.py
- [x] Updated token refresh logic to persist rotated refresh tokens
- [x] Added "Authorize Xero" button to templates/index.html
- [x] Removed hardcoded refresh token dependencies
- [x] Updated .gitignore to exclude xero_secrets.json
- [x] All files compile without syntax errors

### ✅ Dependencies
- [x] fastapi - present in requirements.txt
- [x] requests - present in requirements.txt
- [x] All other dependencies verified

## Deployment Steps

### 1. Prepare Xero App Configuration
- [ ] Log in to https://developer.xero.com/app/manage
- [ ] Update redirect URI to: `https://your-app.azurewebsites.net/callback`
- [ ] Note your Client ID and Client Secret

### 2. Prepare Initial Secrets File
Create a local file `xero_secrets_initial.json`:
```json
{
  "client_id": "YOUR_XERO_CLIENT_ID",
  "client_secret": "YOUR_XERO_CLIENT_SECRET",
  "redirect_uri": "https://your-app.azurewebsites.net/callback",
  "refresh_token": "",
  "tenant_id": ""
}
```

### 3. Commit and Push Code
```bash
git add .
git commit -m "Implement OAuth flow with persistent token storage"
git push origin main
```

### 4. Wait for Azure Deployment
- [ ] Monitor Azure deployment logs
- [ ] Verify deployment completes successfully
- [ ] Check app is running: `https://your-app.azurewebsites.net`

### 5. Upload Secrets File to Azure
Option A - Using Azure Portal SSH:
```bash
# Connect to Azure SSH
# Then run:
cd /home
cat > xero_secrets.json << 'EOF'
{
  "client_id": "YOUR_XERO_CLIENT_ID",
  "client_secret": "YOUR_XERO_CLIENT_SECRET",
  "redirect_uri": "https://your-app.azurewebsites.net/callback",
  "refresh_token": "",
  "tenant_id": ""
}
EOF
```

Option B - Using Azure CLI:
```bash
az webapp ssh --name your-app-name --resource-group your-resource-group
# Then follow Option A steps
```

### 6. Authorize Xero
- [ ] Navigate to `https://your-app.azurewebsites.net`
- [ ] Click "Authorize Xero" button
- [ ] Log in to Xero
- [ ] Grant permissions
- [ ] Verify success message appears
- [ ] Verify redirect back to app works

### 7. Verify Token Storage
Using Azure SSH:
```bash
cat /home/xero_secrets.json
```
Should now contain:
- refresh_token (populated)
- tenant_id (populated)
- access_token (populated)

### 8. Test AP Process
- [ ] Download template from app
- [ ] Fill in test data
- [ ] Upload and run process
- [ ] Verify files download successfully
- [ ] Check Azure logs for any errors

### 9. Verify Token Rotation
- [ ] Run AP process multiple times
- [ ] Check `/home/xero_secrets.json` after each run
- [ ] Verify refresh_token value changes (token rotation working)
- [ ] Verify no authentication errors

## Post-Deployment Verification

### Functional Tests
- [ ] OAuth authorization flow works
- [ ] Callback handles tokens correctly
- [ ] Tokens persist to `/home/xero_secrets.json`
- [ ] Token refresh works automatically
- [ ] Refresh token rotation persists
- [ ] AP process runs successfully
- [ ] Files download correctly

### Error Scenarios
- [ ] Test with missing secrets file (should show clear error)
- [ ] Test with invalid refresh token (should prompt re-authorization)
- [ ] Test with expired access token (should auto-refresh)

## Rollback Plan

If issues occur:
1. Check Azure logs: `az webapp log tail --name your-app-name --resource-group your-resource-group`
2. Verify secrets file exists: SSH to `/home/xero_secrets.json`
3. Re-authorize if needed: Click "Authorize Xero" button
4. If critical failure, rollback deployment in Azure Portal

## Success Criteria

✅ All tests pass
✅ OAuth flow completes successfully
✅ Tokens persist across app restarts
✅ Token rotation works automatically
✅ AP process runs without errors
✅ No hardcoded tokens in code
✅ No environment variables needed

## Notes

- The `/home` directory in Azure App Service persists across restarts
- Tokens are automatically rotated by Xero and persisted
- No manual token management needed after initial authorization
- Re-authorization can be done anytime by clicking "Authorize Xero"
